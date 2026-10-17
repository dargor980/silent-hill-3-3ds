"""Reconcile private evidence and survey camera hypotheses without promoting types."""

import argparse
import json
from collections import Counter
from pathlib import Path, PurePosixPath

from tools.inspectors.camera_probe import MAX_CAMERA_BYTES, METHOD, CameraProbeError, probe_camera
from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.candidates import CandidateReader, validate_evidence
from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.pipeline.extract_assets import canonical, load_catalog
from tools.pipeline.profile import ProfileError


def camera_inputs(catalog: dict, receipt: dict, inventory: dict, hashes: dict) -> list[dict]:
    for key in ("catalog", "receipt", "inventory"):
        validate_image_hash(hashes[key])
    resources = validate_evidence(catalog, receipt, hashes["catalog"])
    try:
        valid = (
            type(inventory["schema_version"]) is int
            and inventory["schema_version"] == 1
            and inventory["scope"] == "candidate_inventory"
            and inventory["tool"] == {"name": "sh3-candidate-inventory", "version": 1}
            and type(inventory["tool"]["version"]) is int
            and inventory["evidence"]
            == {"catalog_sha256": hashes["catalog"], "receipt_sha256": hashes["receipt"]}
            and canonical(inventory["source"]) == canonical(catalog["source"])
            and canonical(inventory["selection"]) == canonical(catalog["selection"])
            and inventory["capabilities"] == []
            and inventory["f02_07_status"] == "pending"
            and inventory["corpus_id"] == "slice-es-normal-v1"
            and inventory["payload_decoding"] == "not_performed"
        )
        expected = sorted(
            [{k: item[k] for k in ("id", "container_id", "size", "sha256")} for item in resources],
            key=lambda item: item["id"],
        )
        observed = sorted(
            [
                {k: item[k] for k in ("id", "container_id", "size", "sha256")}
                for item in inventory["candidates"]
            ],
            key=lambda item: item["id"],
        )
        valid = valid and canonical(expected) == canonical(observed)
        by_id = {item["id"]: item for item in catalog["entries"]}
        for item in inventory["candidates"]:
            original = by_id[item["id"]]
            valid = valid and (
                item["origin"] == original["origin"]
                and item["state"] == "candidate"
                and item["classification"]["type"] == "unknown"
                and item["name_hint"]["status"] == "unverified"
                and item["name_hint"]["suffix"]
                == PurePosixPath(original["source_name"]).suffix.lower()
            )
        if not valid:
            raise ProfileError("CAMERA_EVIDENCE_MISMATCH", "Camera inventory evidence differs")
        return resources
    except ProfileError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise ProfileError("INVALID_CAMERA_EVIDENCE", "Malformed camera inventory") from error


def survey_camera(
    reader: CandidateReader, catalog: dict, receipt: dict, inventory: dict, hashes: dict
) -> dict:
    resources = camera_inputs(catalog, receipt, inventory, hashes)
    selected_ids = {
        item["id"]
        for item in catalog["entries"]
        if PurePosixPath(item["source_name"]).suffix.lower() == ".cam"
    }
    if not selected_ids:
        raise ProfileError("CAMERA_EMPTY_SELECTION", "No camera hints in evidence")
    reader.verify_set(resources)
    entries = []
    for item in resources:
        if item["id"] not in selected_ids:
            continue
        if item["size"] > MAX_CAMERA_BYTES:
            result = {"status": "unknown", "code": "CAMERA_BUDGET", "read": "not_performed"}
        else:
            data = reader.read_verified(item, 0, item["size"])
            if not isinstance(data, bytes) or len(data) != item["size"]:
                raise ProfileError("SIZE_MISMATCH", "Camera reader returned incomplete data")
            try:
                result = probe_camera(data)
            except CameraProbeError as error:
                result = {"status": "unknown", "code": error.code, "read": "verified"}
        entries.append(
            {
                **{k: item[k] for k in ("id", "container_id", "size", "sha256")},
                "state": "candidate",
                "classification": {"type": "unknown"},
                "dependencies": {"status": "not_inspected", "known": []},
                "result": result,
            }
        )
    reader.verify_set(resources)
    matched = [item["result"] for item in entries if item["result"]["status"] == "hypothesis_match"]
    tails = Counter(result["opaque_tail"]["size"] for result in matched)
    codes = Counter(
        item["result"]["code"] for item in entries if item["result"]["status"] == "unknown"
    )
    return {
        "schema_version": 1,
        "scope": "camera_hypothesis_survey",
        "tool": {"name": "sh3-camera-survey", "version": 1},
        "method": METHOD,
        "evidence": {key + "_sha256": hashes[key] for key in ("catalog", "receipt", "inventory")},
        "source": catalog["source"],
        "selection_basis": "unverified_catalog_suffix_cam",
        "entries": entries,
        "summary": {
            "selected_count": len(entries),
            "hypothesis_match_count": len(matched),
            "unknown_count": len(entries) - len(matched),
            "unknown_codes": dict(sorted(codes.items())),
            "prefix_record_count": sum(result["prefix_record_count"] for result in matched),
            "zero_prefix_count": sum(result["prefix_record_count"] == 0 for result in matched),
            "opaque_tail_sizes": [
                {"size": size, "count": count} for size, count in sorted(tails.items())
            ],
            "reference_range_disagreements": {
                key: sum(result["reference_range_disagreements"][key] for result in matched)
                for key in ("72", "76", "92", "108")
            },
            "files_with_reference_disagreements": sum(
                any(result["reference_range_disagreements"].values()) for result in matched
            ),
            "identified_count": 0,
        },
        "corpus_id": inventory["corpus_id"],
        "f02_07_status": "pending",
        "capabilities": [],
        "payload_decoding": "not_performed",
        "next_task": "F02.07/camera-consumer-eu",
        "unresolved": ["sh3_consumer", "opaque_tail", "field_semantics", "room_links", "behavior"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog", "receipt", "inventory", "private-copy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("catalog", "receipt", "inventory"):
        parser.add_argument("--" + name + "-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Camera report already exists")
        hashes = {
            name: getattr(args, name + "_sha256") for name in ("catalog", "receipt", "inventory")
        }
        documents = {
            name: load_catalog(getattr(args, name), digest) for name, digest in hashes.items()
        }
        with VerifiedPrivateReader(
            args.private_copy, Path(__file__).resolve().parents[2]
        ) as reader:
            report = survey_camera(reader, **documents, hashes=hashes)
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError) as error:
        code = error.code if isinstance(error, ProfileError) else "CAMERA_IO_ERROR"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "surveyed", **report["summary"], "f02_07_status": "pending"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
