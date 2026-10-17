"""WR01-WR08: validate a partial writer capture; never authenticate execution or mapping."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.capture_files import PrivateCaptureReader
from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.observation_capture import fields, require, uint
from tools.inspectors.origin_compare import compare_ranges
from tools.inspectors.return_compare import reference_item, validate_return
from tools.inspectors.state_files import inspect_private_state, read_private_state
from tools.inspectors.store_pair import validate_sw
from tools.inspectors.writer_state import read_writer_state
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.profile import ProfileError


def validate_context(plan, origin, origin_hash, capture, *, with_return=False):
    require(plan["kind"] == "sh3-origin-writer-observation-plan", "WRITER_PLAN")
    require(
        type(plan["schema_version"]) is int
        and plan["schema_version"] == 1
        and plan["new_session_required"] is True
        and plan["origin_report_sha256"] == origin_hash
        and plan["parent_session_id"] == origin["session_id"]
        and plan["parent_capture_sha256"] == origin["evidence"]["capture_sha256"]
        and plan["base_source"]["register"] == 4
        and type(plan["base_source"]["register"]) is int
        and plan["restore_event_sequence"] == origin["source_event_sequence"]
        and plan["restore_state_sha256"] == origin["comparisons"][0]["state_sha256"]
        and plan["resource"] == origin["resource"]
        and origin["status"] == "compared_full_candidate",
        "WRITER_PLAN",
    )
    resource = plan["resource"]
    fields(resource, "id size sha256")
    require(re.fullmatch(r"asset:[0-9a-f]{64}", resource["id"]) is not None, "WRITER_PLAN")
    require(type(resource["size"]) is int and 4 <= resource["size"] <= 4096, "WRITER_PLAN")
    validate_image_hash(resource["sha256"])
    fields(
        capture,
        "schema_version kind session_id environment_sha256 expected_crc source_state "
        "frames pairs closure" + (" return_sequence return_reference" if with_return else ""),
    )
    require(type(capture["schema_version"]) is int and capture["schema_version"] == 1)
    require(
        capture["kind"]
        == ("sh3-return-writer-capture" if with_return else "sh3-partial-writer-capture")
    )
    require(
        isinstance(capture["session_id"], str)
        and re.fullmatch(r"[0-9a-f]{32}", capture["session_id"]) is not None
        and capture["session_id"] != plan["parent_session_id"],
        "WRITER_SESSION",
    )
    validate_image_hash(capture["environment_sha256"])
    uint(capture["expected_crc"])
    fields(capture["source_state"], "name sha256")
    require(capture["source_state"]["sha256"] == plan["restore_state_sha256"], "WRITER_SOURCE")
    closure = capture["closure"]
    fields(
        closure,
        "emulator_closed socket_removed ipc_disabled baseline_unchanged "
        "stop_reason return_captured",
    )
    require(
        all(
            closure[k] is True
            for k in ("emulator_closed", "socket_removed", "ipc_disabled", "baseline_unchanged")
        )
        and closure["stop_reason"]
        == ("return_observed" if with_return else "partial_first_changed_store")
        and closure["return_captured"] is with_return,
        "WRITER_CLOSURE",
    )
    require(
        isinstance(capture["frames"], list)
        and 3 + with_return <= len(capture["frames"]) <= 513 + with_return
    )
    require(isinstance(capture["pairs"], list) and 1 <= len(capture["pairs"]) <= 256)
    return resource


def collect_writer_report(
    plan, plan_hash, origin, origin_hash, capture_hash, root, repository, *, with_return=False
):
    with PrivateCaptureReader(root, repository) as reader:
        capture = reader.document(capture_hash)
        resource = validate_context(plan, origin, origin_hash, capture, with_return=with_return)
        crc, source = capture["expected_crc"], capture["source_state"]
        restored = inspect_private_state(
            root,
            source["name"],
            source["sha256"],
            crc,
            repository,
            lambda raw, identity: read_writer_state(raw, identity, None, resource["size"]),
        )
        base = restored.cpu.gpr_low32[4]
        require(not restored.cpu.delay_slot, "WRITER_SOURCE")
        states, observations, names = [], [], set()
        for sequence, frame in enumerate(capture["frames"], 1):
            fields(
                frame,
                "sequence session_id environment_sha256 state_name state_sha256 "
                "virtual_sha256 paused_before_after",
            )
            require(
                type(frame["sequence"]) is int and frame["sequence"] == sequence, "WRITER_ORDER"
            )
            require(
                frame["session_id"] == capture["session_id"]
                and frame["environment_sha256"] == capture["environment_sha256"]
                and frame["paused_before_after"] is True,
                "WRITER_SESSION",
            )
            require(
                isinstance(frame["state_name"], str) and frame["state_name"] not in names,
                "WRITER_STATE",
            )
            names.add(frame["state_name"])
            state = inspect_private_state(
                root / "sstates",
                frame["state_name"],
                frame["state_sha256"],
                crc,
                repository,
                lambda raw, identity: read_writer_state(raw, identity, base, resource["size"]),
            )
            virtual = reader.blob(frame["virtual_sha256"], resource["size"])
            require(state.data == virtual, "WRITER_VIRTUAL_MISMATCH")
            states.append(state)
            observations.append(
                {
                    "sequence": sequence,
                    "state_sha256": frame["state_sha256"],
                    "virtual_and_hypothetical_physical_equal": True,
                    "against_entry": compare_ranges(restored.data, state.data),
                }
            )
        entry = states[0]
        require(
            entry.cpu.pc == restored.cpu.pc
            and entry.gpr_low64 == restored.gpr_low64
            and not entry.cpu.delay_slot
            and entry.data == restored.data
            and hashlib.sha256(entry.data).hexdigest() == resource["sha256"],
            "WRITER_ENTRY",
        )
        results, last = [], 1
        for pair in capture["pairs"]:
            fields(
                pair,
                "before_sequence after_sequence operation code_pc code_size "
                "code_before_sha256 code_after_sha256",
            )
            first, second = pair["before_sequence"], pair["after_sequence"]
            require(
                type(first) is int
                and type(second) is int
                and last < first < second <= len(states)
                and second == first + 1,
                "WRITER_ORDER",
            )
            last = second
            before, after = states[first - 1], states[second - 1]
            uint(pair["code_pc"])
            require(
                pair["code_pc"] == before.cpu.pc and pair["operation"] == "step_into", "WRITER_CODE"
            )
            require(type(pair["code_size"]) is int and pair["code_size"] in (4, 8), "WRITER_CODE")
            result = validate_sw(
                before,
                after,
                base,
                reader.blob(pair["code_before_sha256"], pair["code_size"]),
                reader.blob(pair["code_after_sha256"], pair["code_size"]),
            )
            results.append({"before_sequence": first, "after_sequence": second, **result})
        if with_return:
            historical = reference_item(plan, origin, capture)
            ref = capture["return_reference"]
            reference = inspect_private_state(
                root,
                ref["name"],
                ref["sha256"],
                crc,
                repository,
                lambda raw, identity: read_writer_state(raw, identity, base, resource["size"]),
            )
            returned = validate_return(capture, states, restored, reference, historical, last)
            read_private_state(root, ref["name"], ref["sha256"], crc, repository)
        # Recheck earlier state files after all pairs, and publish only after reader close.
        read_private_state(root, source["name"], source["sha256"], crc, repository)
        for frame in capture["frames"]:
            read_private_state(
                root / "sstates", frame["state_name"], frame["state_sha256"], crc, repository
            )
    report = {
        "schema_version": 1,
        "tool": {"name": "sh3-camera-writer", "version": 1},
        "status": "consistent_partial_writer_capture",
        "evidence": {
            "plan_sha256": plan_hash,
            "origin_sha256": origin_hash,
            "capture_sha256": capture_hash,
            "restore_state_sha256": source["sha256"],
        },
        "historical_validation": "hash_pinned_report_not_reexecuted",
        "session_id": capture["session_id"],
        "environment_sha256": capture["environment_sha256"],
        "resource": resource,
        "entry_matches_restored_cpu_and_full_resource": True,
        "frames": observations,
        "pairs": results,
        "coverage": "partial_pairs_only",
        "return_captured": False,
        "closure": capture["closure"],
        "closure_verification": "declared",
        "mapping_verified": False,
        "mapping": "virtual_content_equals_hypothetical_physical_range_not_translation_proof",
        "origin_status": "pending",
        "execution_authentication": "not_provided",
        "resource_links": [],
        "capabilities": [],
        "f02_07_status": "pending",
    }
    if with_return:
        report.update(
            {
                "tool": {"name": "sh3-camera-writer-return", "version": 1},
                "status": "consistent_return_writer_capture",
                "coverage": "selected_subrange_pair_and_full_return",
                "return_captured": True,
                "return": returned,
            }
        )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("plan", "origin"):
        parser.add_argument("--" + key, type=Path, required=True)
        parser.add_argument("--" + key + "-sha256", required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--capture-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(not args.output.exists() and not args.output.is_symlink(), "OUTPUT_EXISTS")
        report = collect_writer_report(
            load_catalog(args.plan, args.plan_sha256),
            args.plan_sha256,
            load_catalog(args.origin, args.origin_sha256),
            args.origin_sha256,
            args.capture_sha256,
            args.capture_root,
            Path(__file__).resolve().parents[2],
        )
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError, KeyError, TypeError, ValueError, IndexError) as error:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "code": error.code if isinstance(error, ProfileError) else "WRITER_INPUT_OR_IO",
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "pairs": len(report["pairs"]),
                "mapping_verified": False,
                "origin_status": "pending",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
