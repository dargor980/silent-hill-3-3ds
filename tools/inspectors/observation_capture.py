"""Validate supplied observation evidence; never authenticate an emulator run."""

import hashlib
import re
from collections.abc import Callable

from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.observation_plan import object_hash
from tools.pipeline.profile import ProfileError

BlobReader = Callable[[str, int], bytes]


def require(condition: bool, code="CAPTURE_SCHEMA"):
    if not condition:
        raise ProfileError(code, "Capture does not satisfy observation contract")


def fields(value, names: str):
    require(isinstance(value, dict) and set(value) == set(names.split()))


def bounded_list(value, limit):
    require(isinstance(value, list) and len(value) <= limit, "CAPTURE_BUDGET")


def uint(value, maximum=(1 << 32) - 1):
    require(type(value) is int and 0 <= value <= maximum)


def value_at(event, register):
    return 0 if register == 0 else int(event["registers"][str(register)], 16)


def verify_blob(read_blob, digest, size):
    validate_image_hash(digest)
    uint(size, 4096)
    require(size > 0, "CAPTURE_RANGE")
    data = read_blob(digest, size)
    require(
        isinstance(data, bytes)
        and len(data) == size
        and hashlib.sha256(data).hexdigest() == digest,
        "CAPTURE_HASH",
    )


def validate_capture(plan: dict, plan_hash: str, capture: dict, read_blob: BlobReader) -> dict:
    validate_image_hash(plan_hash)
    fields(
        capture,
        "schema_version kind session_id status plan_sha256 image_sha256 "
        "executable_sha256 catalog_sha256 environment outcomes events code_snapshots data_samples",
    )
    require(type(capture["schema_version"]) is int and capture["schema_version"] == 1)
    require(capture["kind"] == "sh3-runtime-capture")
    require(capture["status"] == "complete", "CAPTURE_INCOMPLETE")
    session = capture["session_id"]
    require(isinstance(session, str) and re.fullmatch(r"[0-9a-f]{32}", session) is not None)
    for field, expected in (
        ("plan_sha256", plan_hash),
        ("image_sha256", plan["source"]["sha256"]),
        ("executable_sha256", plan["executable"]["sha256"]),
        ("catalog_sha256", plan["catalog_sha256"]),
    ):
        require(capture[field] == expected, "CAPTURE_IDENTITY")
    env = capture["environment"]
    fields(env, "emulator version binary_sha256 bios_sha256 configuration_sha256 cpu method")
    for key in ("emulator", "version"):
        require(isinstance(env[key], str) and bool(env[key].strip()) and len(env[key]) <= 128)
    for key in ("binary_sha256", "bios_sha256", "configuration_sha256"):
        validate_image_hash(env[key])
    require(env["cpu"] == "EE" and env["method"] == "manual-debugger-v1")
    env_hash = object_hash(env)
    boundaries = {b["id"]: b for b in plan["boundaries"]}
    ranges = {r["id"]: r for r in plan["code_ranges"]}
    outcomes = capture["outcomes"]
    require(isinstance(outcomes, dict) and set(outcomes) == set(boundaries))
    require(all(isinstance(s, str) and s in ("observed", "not_reached") for s in outcomes.values()))
    events = capture["events"]
    bounded_list(events, 128)
    stages, observations, needed = {key: 0 for key in boundaries}, {}, set()
    active = None
    for sequence, event in enumerate(events, 1):
        fields(event, "sequence session_id environment_sha256 boundary_id point_id pc registers")
        uint(event["sequence"], 128)
        require(event["sequence"] == sequence, "CAPTURE_ORDER")
        require(
            event["session_id"] == session and event["environment_sha256"] == env_hash,
            "CAPTURE_SESSION",
        )
        bid = event["boundary_id"]
        require(isinstance(bid, str) and bid in boundaries, "CAPTURE_POINT")
        points = {p["id"]: p for p in boundaries[bid]["points"]}
        pid = event["point_id"]
        require(isinstance(pid, str) and pid in points, "CAPTURE_POINT")
        point = points[pid]
        uint(event["pc"])
        require(event["pc"] == point["pc"], "CAPTURE_POINT")
        registers = event["registers"]
        require(
            isinstance(registers, dict) and set(registers) == {str(r) for r in point["registers"]}
        )
        require(
            all(
                isinstance(v, str) and re.fullmatch(r"[0-9a-f]{8}", v) is not None
                for v in registers.values()
            )
        )
        phase, stage = point["phase"], stages[bid]
        if phase == "before_call":
            require(stage == 0 and active is None, "CAPTURE_ORDER")
            active, stages[bid] = bid, 1
        elif phase == "entry_after_slot":
            require(stage == 1 and active == bid, "CAPTURE_ORDER")
            returned = next(
                p["pc"] for p in boundaries[bid]["points"] if p["phase"] == "return_if_reached"
            )
            require(value_at(event, 31) == returned, "CAPTURE_CONTEXT")
            stages[bid] = 2
        elif phase == "checkpoint":
            require(stage == 2 and active == bid, "CAPTURE_ORDER")
        else:
            require(phase == "return_if_reached" and stage == 2 and active == bid, "CAPTURE_ORDER")
            active, stages[bid] = None, 3
        observations[(bid, phase)] = event
        needed.add(point["range_id"])
    require(
        all(stages[k] == (3 if v == "observed" else 0) for k, v in outcomes.items()),
        "CAPTURE_INCOMPLETE",
    )
    snapshots = capture["code_snapshots"]
    bounded_list(snapshots, 32)
    seen = set()
    for item in snapshots:
        fields(item, "range_id size sha256")
        rid = item["range_id"]
        require(isinstance(rid, str) and rid in needed and rid not in seen, "CAPTURE_CODE")
        seen.add(rid)
        window = ranges[rid]
        uint(item["size"], 4096)
        require(
            item["size"] == window["end"] - window["start"] and item["sha256"] == window["sha256"],
            "CAPTURE_CODE",
        )
        verify_blob(read_blob, item["sha256"], item["size"])
    require(seen == needed, "CAPTURE_CODE")
    samples = capture["data_samples"]
    bounded_list(samples, 16)
    for sample in samples:
        fields(sample, "event_sequence register address size sha256")
        uint(sample["event_sequence"], len(events))
        require(sample["event_sequence"] > 0, "CAPTURE_RANGE")
        event = events[sample["event_sequence"] - 1]
        uint(sample["register"], 31)
        require(str(sample["register"]) in event["registers"], "CAPTURE_RANGE")
        uint(sample["address"])
        uint(sample["size"], 4096)
        require(
            sample["address"] == value_at(event, sample["register"])
            and sample["address"] + sample["size"] <= 1 << 32,
            "CAPTURE_RANGE",
        )
        verify_blob(read_blob, sample["sha256"], sample["size"])
    results = []
    for bid, boundary in boundaries.items():
        same, argument = "not_observed", "not_observed"
        if outcomes[bid] == "observed":
            entry, returned = (
                observations[(bid, "entry_after_slot")],
                observations[(bid, "return_if_reached")],
            )
            same = (
                "equal"
                if value_at(entry, boundary["register"]) == value_at(returned, boundary["register"])
                else "different"
            )
            relation = boundary["argument_copy"]
            argument = "not_applicable"
            if relation is not None:
                before = observations[(bid, "before_call")]
                argument = (
                    "equal"
                    if value_at(entry, relation["entry_register"])
                    == value_at(before, relation["before_register"])
                    else "different"
                )
        results.append(
            {
                "boundary_id": bid,
                "status": outcomes[bid],
                "entry_copy_comparison": argument,
                "entry_return_comparison": same,
            }
        )
    return {
        "schema_version": 1,
        "tool": {"name": "sh3-observation-validator", "version": 1},
        "status": "validated_observations" if events else "validated_no_observations",
        "plan_sha256": plan_hash,
        "environment_sha256": env_hash,
        "event_count": len(events),
        "code_snapshot_count": len(snapshots),
        "data_sample_count": len(samples),
        "comparisons": results,
        "execution_authentication": "not_provided",
        "environment_identity": "declared_not_independently_verified",
        "resource_links": [],
        "capabilities": [],
        "f02_07_status": "pending",
    }
