"""OR01-OR08: compare a full candidate using a preserved entry base; no origin claim."""

import argparse
import json
from pathlib import Path

from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.capture_files import PrivateCaptureReader
from tools.inspectors.observation_capture import fields, require, validate_capture
from tools.inspectors.origin_compare import compare_ranges
from tools.inspectors.origin_memory import entry_base, preserved_range
from tools.inspectors.resource_link import INPUTS as LINK_INPUTS
from tools.inspectors.resource_link import collect_link_report
from tools.inspectors.resource_scan_files import VerifiedResourceScanner
from tools.inspectors.state_files import inspect_private_state, read_private_state
from tools.pipeline.extract_assets import load_catalog, resource_plan
from tools.pipeline.profile import ProfileError

INPUTS = (*LINK_INPUTS, "link", "link-repeat", "origin-plan")


class OriginResourceReader(VerifiedResourceScanner):
    def candidate(self, resource):
        self.scan_verified(resource, {})
        data = self.read_verified(resource, 0, resource["size"])
        self.assert_stable()
        return data


def validate_origin_plan(request, capture, plan, link, hashes, capture_hash):
    fields(
        request,
        "schema_version session_id capture_sha256 link_sha256 resource_id "
        "source_event_sequence base_register target_event_sequences",
    )
    require(type(request["schema_version"]) is int and request["schema_version"] == 1)
    require(
        request["session_id"] == capture["session_id"]
        and request["capture_sha256"] == capture_hash
        and request["link_sha256"] == hashes["link"],
        "ORIGIN_IDENTITY",
    )
    source, register, targets = (
        request[k] for k in ("source_event_sequence", "base_register", "target_event_sequences")
    )
    require(type(source) is int and 1 <= source <= len(capture["events"]), "ORIGIN_PLAN")
    require(type(register) is int and 1 <= register <= 31, "ORIGIN_PLAN")
    require(isinstance(targets, list) and 2 <= len(targets) <= 16, "ORIGIN_PLAN")
    require(
        all(type(n) is int and source <= n <= len(capture["events"]) for n in targets)
        and targets == sorted(set(targets))
        and targets[0] == source,
        "ORIGIN_PLAN",
    )
    event = capture["events"][source - 1]
    boundary = next(b for b in plan["boundaries"] if b["id"] == event["boundary_id"])
    point = next(p for p in boundary["points"] if p["id"] == event["point_id"])
    require(
        point["phase"] == "entry_after_slot" and register == boundary["register"], "ORIGIN_PLAN"
    )
    samples = {
        s["id"] for s in link["samples"] if s["event_sequence"] == source and s["length"] == 256
    }
    matches = [
        m
        for m in link["matches"]
        if m["sample_id"] in samples
        and m["resource_id"] == request["resource_id"]
        and m["resource_offset"] == 0
    ]
    require(len(matches) == 1 and 256 <= matches[0]["resource_size"] <= 4096, "ORIGIN_CANDIDATE")


def collect_origin_report(
    documents, hashes, capture_hash, capture_root, state_root, copy_a, copy_b, repository
):
    require(
        hashes["link"] == hashes["link-repeat"] and documents["link"] == documents["link-repeat"],
        "ORIGIN_LINK",
    )
    reproduced = collect_link_report(
        {k: documents[k] for k in LINK_INPUTS},
        {k: hashes[k] for k in LINK_INPUTS},
        capture_hash,
        capture_root,
        state_root,
        copy_a,
        copy_b,
        repository,
    )
    require(
        reproduced == documents["link"] and reproduced["status"] == "candidate_matches",
        "ORIGIN_LINK",
    )
    request, plan, index = (documents[k] for k in ("origin-plan", "plan", "state-index"))
    resources = resource_plan(documents["catalog"])
    with PrivateCaptureReader(capture_root, repository) as reader:
        capture = reader.document(capture_hash)
        receipt = validate_capture(plan, hashes["plan"], capture, reader.blob)
        receipt["capture_sha256"] = capture_hash
        require(receipt == documents["observation"], "ORIGIN_IDENTITY")
        validate_origin_plan(request, capture, plan, reproduced, hashes, capture_hash)
        resource = next(r for r in resources if r["id"] == request["resource_id"])

        def inspect(sequence, decoder):
            item = index["states"][sequence - 1]
            return inspect_private_state(
                state_root, item["name"], item["sha256"], index["expected_crc"], repository, decoder
            )

        source = request["source_event_sequence"]
        source_event = capture["events"][source - 1]
        base = inspect(
            source, lambda raw, crc: entry_base(raw, crc, source_event, request["base_register"])
        )
        comparisons, previous, previous_sequence = [], None, None
        with (
            OriginResourceReader(copy_a, repository) as first,
            OriginResourceReader(copy_b, repository) as second,
        ):
            first.verify_set(resources)
            second.verify_set(resources)
            candidate = first.candidate(resource)
            require(candidate == second.candidate(resource), "ORIGIN_COPIES")
            for sequence in request["target_event_sequences"]:
                event = capture["events"][sequence - 1]
                data = inspect(
                    sequence,
                    lambda raw, crc, e=event: preserved_range(raw, crc, e, base, resource["size"]),
                ).data
                comparisons.append(
                    {
                        "event_sequence": sequence,
                        "point_id": event["point_id"],
                        "state_sha256": index["states"][sequence - 1]["sha256"],
                        "against_resource": compare_ranges(candidate, data),
                        "previous_event_sequence": previous_sequence,
                        "against_previous": None
                        if previous is None
                        else compare_ranges(previous, data),
                    }
                )
                previous, previous_sequence = data, sequence
            for item in index["states"]:
                read_private_state(
                    state_root, item["name"], item["sha256"], index["expected_crc"], repository
                )
            reader.assert_stable()
    changes = [
        c for c in comparisons if c["against_previous"] and not c["against_previous"]["equal"]
    ]
    return {
        "schema_version": 1,
        "tool": {"name": "sh3-camera-resource-origin", "version": 1},
        "evidence": {
            **{k.replace("-", "_") + "_sha256": v for k, v in hashes.items()},
            "capture_sha256": capture_hash,
        },
        "session_id": capture["session_id"],
        "resource": {k: resource[k] for k in ("id", "size", "sha256")},
        "source_event_sequence": source,
        "base_policy": "preserved_entry_register_low32",
        "mapping": "low_direct_physical_offset_hypothesis_tlb_not_verified",
        "mapping_verified": False,
        "comparisons": comparisons,
        "first_observed_change": None
        if not changes
        else {
            "after_event_sequence": changes[0]["previous_event_sequence"],
            "by_event_sequence": changes[0]["event_sequence"],
            "difference_ranges": changes[0]["against_previous"]["difference_ranges"],
        },
        "status": "compared_full_candidate",
        "origin_status": "pending",
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
        report = collect_origin_report(
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
        code = error.code if isinstance(error, ProfileError) else "ORIGIN_INPUT_OR_IO"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "states_compared": len(report["comparisons"]),
                "origin_status": "pending",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
