"""Conservative candidate evidence; no format identification or corpus selection."""

import hashlib
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Protocol

from tools.inspectors.asset_catalog import MAX_ASSETS, asset_id
from tools.inspectors.inventory import validate_image_hash
from tools.pipeline.extract_assets import canonical, resource_plan
from tools.pipeline.private_output import COPIES
from tools.pipeline.profile import ProfileError

PREFIX_BYTES = 64
CATEGORIES = (
    "scene",
    "character",
    "animation",
    "alpha_material",
    "collision",
    "camera",
    "spanish_text",
    "sound",
    "sequence",
    "interaction_inventory",
    "enemy",
    "progress",
)


class CandidateReader(Protocol):
    def verify_set(self, resources: list[dict]) -> None: ...

    def read_verified(self, resource: dict, offset: int, length: int) -> bytes: ...


def _require(condition: bool):
    if not condition:
        raise ProfileError("CANDIDATE_EVIDENCE_MISMATCH", "Candidate evidence does not agree")


def validate_evidence(catalog: dict, receipt: dict, catalog_hash: str) -> list[dict]:
    """Reconcile pinned historical documents, not authenticate a new ISO/catalog."""
    try:
        _require(type(catalog["schema_version"]) is int and catalog["schema_version"] == 1)
        _require(type(receipt["schema_version"]) is int and receipt["schema_version"] == 1)
        _require(catalog["scope"] == "selected_mfa_entries")
        _require(catalog["tool"]["name"] == "sh3-asset-catalog")
        _require(receipt["tool"]["name"] == "sh3-mfa-extract")
        for document in (catalog, receipt):
            _require(type(document["tool"]["version"]) is int)
            _require(document["tool"]["version"] == 1)
            _require(document["capabilities"] == [])
            _require(document["payload_decoding"] == "not_performed")
        _require(receipt["status"] == "verified" and receipt["catalog_sha256"] == catalog_hash)
        for key in ("source", "selection", "summary"):
            _require(canonical(receipt[key]) == canonical(catalog[key]))
        source = catalog["source"]
        validate_image_hash(source["sha256"])
        _require(source["id"] == "iso:" + source["sha256"])
        _require(isinstance(source["profile"]["id"], str) and bool(source["profile"]["id"]))
        _require(source["profile"]["platform"] == "ps2")
        _require(type(source["size"]) is int and 0 < source["size"] <= (1 << 63) - 1)
        _require(type(catalog["entries"]) is list and 0 < len(catalog["entries"]) <= MAX_ASSETS)
        parents = {item["id"]: item for item in catalog["containers"]}
        _require(len(parents) == len(catalog["containers"]))
        for entry in catalog["entries"]:
            parent = parents[entry["container_id"]]
            _require(parent["result"]["status"] == "structural_candidate")
            _require(
                entry["origin"] == {"image_id": source["id"], "profile_id": source["profile"]["id"]}
            )
            for key in ("block_offset", "entry_index", "container_offset", "size"):
                _require(type(entry[key]) is int and entry[key] >= 0)
            _require(
                entry["id"] == asset_id(parent["id"], entry["block_offset"], entry["entry_index"])
            )
            _require(entry["container_offset"] + entry["size"] <= parent["size"])
            _require(isinstance(entry["source_name"], str))
        resources = resource_plan(catalog)
        _require(canonical(resources) == canonical(receipt["resources"]))
        expected = [{k: item[k] for k in ("id", "file", "size", "sha256")} for item in resources]
        _require(set(receipt["copies"]) == set(COPIES))
        for copy in COPIES:
            _require(canonical(receipt["copies"][copy]) == canonical(expected))
        _require(type(catalog["summary"]["entry_count"]) is int)
        _require(catalog["summary"]["entry_count"] == len(resources))
        _require(type(catalog["summary"]["payload_bytes"]) is int)
        _require(catalog["summary"]["payload_bytes"] == sum(item["size"] for item in resources))
        exclusions = {
            "containers": [
                {"id": c["id"], "code": c["result"]["code"]}
                for c in catalog["containers"]
                if c["result"]["status"] == "unknown"
            ],
            "outside_scope_ids": [item["id"] for item in catalog["outside_scope"]],
        }
        _require(canonical(exclusions) == canonical(receipt["exclusions"]))
        return resources
    except ProfileError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ProfileError("INVALID_CANDIDATE_EVIDENCE", "Malformed candidate evidence") from error


def _groups(candidates: list[dict], *, prefix: bool) -> list[dict]:
    groups = defaultdict(list)
    for item in candidates:
        observation = item["observations"]["prefix"] if prefix else item
        size = observation["length"] if prefix else observation["size"]
        if prefix and size == 0:
            continue
        groups[(size, observation["sha256"])].append(item["id"])
    return [
        {"length" if prefix else "size": size, "sha256": digest, "ids": sorted(ids)}
        for (size, digest), ids in sorted(groups.items())
        if len(ids) > 1
    ]


def collect_candidates(
    reader: CandidateReader, catalog: dict, receipt: dict, catalog_hash: str, receipt_hash: str
) -> dict:
    validate_image_hash(catalog_hash)
    validate_image_hash(receipt_hash)
    resources = validate_evidence(catalog, receipt, catalog_hash)
    reader.verify_set(resources)
    by_id = {item["id"]: item for item in catalog["entries"]}
    candidates = []
    for item in resources:
        length = min(PREFIX_BYTES, item["size"])
        prefix = reader.read_verified(item, 0, length)
        if not isinstance(prefix, bytes) or len(prefix) != length:
            raise ProfileError("SIZE_MISMATCH", "Reader returned an incomplete observation")
        candidates.append(
            {
                **{k: item[k] for k in ("id", "container_id", "size", "sha256")},
                "origin": by_id[item["id"]]["origin"],
                "state": "candidate",
                "classification": {"type": "unknown", "reason": "no_format_contract"},
                "dependencies": {"status": "not_inspected", "known": []},
                "name_hint": {
                    "suffix": PurePosixPath(by_id[item["id"]]["source_name"]).suffix.lower(),
                    "status": "unverified",
                    "method": "name-suffix-v1",
                },
                "observations": {
                    "integrity": "full_sha256_before_range",
                    "prefix": {
                        "offset": 0,
                        "length": length,
                        "sha256": hashlib.sha256(prefix).hexdigest(),
                        "method": "prefix-fingerprint-v1",
                    },
                },
            }
        )
    reader.verify_set(resources)
    content_groups, prefix_groups = (
        _groups(candidates, prefix=False),
        _groups(candidates, prefix=True),
    )
    return {
        "schema_version": 1,
        "scope": "candidate_inventory",
        "tool": {"name": "sh3-candidate-inventory", "version": 1},
        "evidence": {"catalog_sha256": catalog_hash, "receipt_sha256": receipt_hash},
        "source": catalog["source"],
        "selection": catalog["selection"],
        "exclusions": {
            "containers": sorted(receipt["exclusions"]["containers"], key=lambda item: item["id"]),
            "outside_scope_ids": sorted(receipt["exclusions"]["outside_scope_ids"]),
        },
        "candidates": candidates,
        "content_groups": content_groups,
        "prefix_groups": prefix_groups,
        "corpus_id": "slice-es-normal-v1",
        "categories": [
            {
                "category": name,
                "status": "unresolved",
                "ids": [],
                "reason": "no_validated_format_or_semantic_link",
                "next_task": "F02.07/formato-" + name,
            }
            for name in CATEGORIES
        ],
        "room_pair": {"status": "unresolved", "ids": [], "reason": "connections_not_inspected"},
        "summary": {
            "candidate_count": len(candidates),
            "payload_bytes": sum(item["size"] for item in candidates),
            "empty_count": sum(item["size"] == 0 for item in candidates),
            "content_group_count": len(content_groups),
            "prefix_group_count": len(prefix_groups),
            "identified_count": 0,
            "unresolved_category_count": len(CATEGORIES),
        },
        "payload_decoding": "not_performed",
        "capabilities": [],
        "f02_07_status": "pending",
    }
