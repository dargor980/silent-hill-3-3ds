"""RL01-RL08: compare pinned EE sample hypotheses with two private extractions."""

import argparse
import hashlib
import json
from pathlib import Path

from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.candidates import validate_evidence
from tools.inspectors.capture_files import PrivateCaptureReader
from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.observation_capture import fields, require, uint, validate_capture
from tools.inspectors.observation_plan import object_hash
from tools.inspectors.resource_match import MAX_BYTES, MAX_HITS
from tools.inspectors.resource_scan_files import VerifiedResourceScanner
from tools.inspectors.state_files import inspect_private_state, read_private_state
from tools.inspectors.state_memory import sample_state
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.profile import ProfileError

INPUTS = ("plan", "observation", "observation-repeat", "catalog", "extraction", "state-index")


def select_samples(plan, capture, index, read_state, read_sample):
    fields(index, "schema_version capture_sha256 expected_crc states")
    require(type(index["schema_version"]) is int and index["schema_version"] == 1)
    uint(index["expected_crc"])
    states = index["states"]
    require(isinstance(states, list) and len(states) == len(capture["events"]) <= 128)
    boundaries = {b["id"]: b for b in plan["boundaries"]}
    samples, patterns, seen = [], {}, set()
    for item, event in zip(states, capture["events"], strict=True):
        fields(item, "sequence name sha256")
        uint(item["sequence"], 128)
        require(item["sequence"] == event["sequence"])
        validate_image_hash(item["sha256"])
        name = item["name"]
        require(isinstance(name, str) and name not in seen)
        seen.add(name)
        state = read_state(item)
        require(
            state.registers_at(event["pc"], [int(k) for k in event["registers"]])
            == event["registers"],
            "MEMORY_EVENT",
        )
        boundary = boundaries[event["boundary_id"]]
        point = next(p for p in boundary["points"] if p["id"] == event["point_id"])
        phases = (
            ("entry_after_slot",)
            if boundary["argument_copy"]
            else ("entry_after_slot", "return_if_reached")
        )
        if point["phase"] not in phases:
            continue
        for length in (64, 256):
            require(len(samples) < 10, "MATCH_BUDGET")
            sample = read_sample(item, event, boundary["register"], length)
            require(isinstance(sample, bytes) and len(sample) == length, "MATCH_SAMPLE")
            metadata = {
                "event_sequence": event["sequence"],
                "point_id": point["id"],
                "state_sha256": item["sha256"],
                "length": length,
                "sha256": hashlib.sha256(sample).hexdigest(),
            }
            identity = object_hash(metadata)
            active = len(set(sample)) > 1
            samples.append(
                {
                    "id": identity,
                    **metadata,
                    "status": "searched" if active else "non_discriminating",
                }
            )
            if active:
                patterns[identity] = sample
    require(bool(samples), "MATCH_SAMPLE")
    return samples, patterns


def scan_catalog(reader, resources, patterns):
    require(0 < len(resources) <= 100000, "MATCH_BUDGET")
    require(sum(r["size"] for r in resources) <= MAX_BYTES, "MATCH_BUDGET")
    reader.verify_set(resources)
    counts, matches = dict.fromkeys(patterns, 0), []
    for resource in resources:
        hits = reader.scan_verified(resource, patterns)
        require(isinstance(hits, dict) and set(hits) == set(patterns), "MATCH_READER")
        for sample_id, offsets in hits.items():
            require(isinstance(offsets, list) and len(offsets) <= MAX_HITS, "MATCH_READER")
            require(
                all(
                    type(o) is int and 0 <= o <= resource["size"] - len(patterns[sample_id])
                    for o in offsets
                ),
                "MATCH_READER",
            )
            require(offsets == sorted(set(offsets)), "MATCH_READER")
            counts[sample_id] += len(offsets)
            require(counts[sample_id] <= MAX_HITS, "MATCH_HITS")
            matches.extend(
                {
                    "sample_id": sample_id,
                    "resource_id": resource["id"],
                    "resource_sha256": resource["sha256"],
                    "resource_size": resource["size"],
                    "resource_offset": offset,
                }
                for offset in offsets
            )
    reader.verify_set(resources)
    reader.assert_stable()
    return sorted(matches, key=lambda m: (m["sample_id"], m["resource_id"], m["resource_offset"]))


def collect_link_report(
    documents, hashes, capture_hash, capture_root, state_root, copy_a, copy_b, repository
):
    plan, catalog, extraction, index = (
        documents[k] for k in ("plan", "catalog", "extraction", "state-index")
    )
    require(documents["observation"] == documents["observation-repeat"], "MATCH_RECEIPT")
    require(hashes["observation"] == hashes["observation-repeat"], "MATCH_RECEIPT")
    resources = validate_evidence(catalog, extraction, hashes["catalog"])
    require(
        plan["catalog_sha256"] == hashes["catalog"]
        and plan["source"]["sha256"] == catalog["source"]["sha256"],
        "MATCH_IDENTITY",
    )
    with PrivateCaptureReader(capture_root, repository) as reader:
        capture = reader.document(capture_hash)
        observed = validate_capture(plan, hashes["plan"], capture, reader.blob)
        observed["capture_sha256"] = capture_hash
        require(
            observed == documents["observation"] and observed["status"] == "validated_observations",
            "MATCH_RECEIPT",
        )
        require(index.get("capture_sha256") == capture_hash, "MATCH_IDENTITY")

        def read_state(item):
            return read_private_state(
                state_root, item["name"], item["sha256"], index["expected_crc"], repository
            )

        def read_sample(item, event, register, length):
            return inspect_private_state(
                state_root,
                item["name"],
                item["sha256"],
                index["expected_crc"],
                repository,
                lambda raw, crc: sample_state(raw, crc, event, register, length),
            ).data

        samples, patterns = select_samples(plan, capture, index, read_state, read_sample)
        with (
            VerifiedResourceScanner(copy_a, repository) as first,
            VerifiedResourceScanner(copy_b, repository) as second,
        ):
            require(copy_a.resolve() != copy_b.resolve(), "MATCH_COPIES")
            a = scan_catalog(first, resources, patterns)
            b = scan_catalog(second, resources, patterns)
            require(a == b, "MATCH_COPIES")
            for item in index["states"]:
                read_state(item)
            reader.assert_stable()
        # Publication is performed only by the caller, after all contexts close.
    return {
        "schema_version": 1,
        "tool": {"name": "sh3-camera-resource-link", "version": 1},
        "evidence": {
            **{k.replace("-", "_") + "_sha256": v for k, v in hashes.items()},
            "capture_sha256": capture_hash,
        },
        "mapping": "low_direct_physical_offset_hypothesis_tlb_not_verified",
        "source_sha256": catalog["source"]["sha256"],
        "status": (
            "no_discriminating_samples"
            if not patterns
            else "candidate_matches"
            if a
            else "no_exact_matches"
        ),
        "samples": samples,
        "matches": a,
        "summary": {
            "sample_count": len(samples),
            "searched_count": len(patterns),
            "match_count": len(a),
            "resources_per_copy": len(resources),
            "bytes_per_copy": sum(r["size"] for r in resources),
            "copies_verified": 2,
        },
        "resource_links": [],
        "capabilities": [],
        "f02_07_status": "pending",
        "execution_authentication": "not_provided",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in INPUTS:
        parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    for name in ("capture-root", "state-root", "copy-a", "copy-b", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--capture-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Report already exists")
        hashes = {name: getattr(args, name.replace("-", "_") + "_sha256") for name in INPUTS}
        documents = {
            name: load_catalog(getattr(args, name.replace("-", "_")), hashes[name])
            for name in INPUTS
        }
        report = collect_link_report(
            documents,
            hashes,
            args.capture_sha256,
            args.capture_root,
            args.state_root,
            args.copy_a,
            args.copy_b,
            Path(__file__).resolve().parents[2],
        )
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError, KeyError, TypeError, ValueError, StopIteration) as error:
        code = error.code if isinstance(error, ProfileError) else "MATCH_INPUT_OR_IO"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": report["status"], **report["summary"], "f02_07_status": "pending"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
