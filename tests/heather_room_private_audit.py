"""Explicit local hp34 audit. Only metadata leaves memory; no private fixture is written."""

import argparse
import json
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.cld_polygon_wire_oracle import identical  # noqa: E402
from tests.heather_room_preparation_oracle import native_check, projection  # noqa: E402
from tests.python.helpers.heather_room_contact_oracle import (  # noqa: E402
    observe,
    rational,
    scalar_bits,
)
from tools.pipeline.collision_polygon_inputs import PinnedInputs  # noqa: E402
from tools.pipeline.intermediate_assets import sha  # noqa: E402
from tools.pipeline.prepare_heather_room_contacts import _prepare, read_bundle  # noqa: E402


def require(condition, label):
    if not condition:
        raise ValueError(label)


def token(value):
    return "f32:" + struct.pack(">f", value).hex()


def queries_for(profile, scene):
    queries, expectations = [], []
    spawn = profile["spawn"]["world"]
    origin = profile["coordinates"]["origin"]

    def add(a, b, outcome, **options):
        queries.append(dict(**{"from": a}, requested=b, ordinal=len(queries), **options))
        expectations.append(outcome)

    add(spawn, spawn, "free")
    route = [spawn] + [
        [origin[0] + x, 0, origin[2] + z] for x, z in profile["inspection_route"]["local_xz"]
    ]
    for a, b in zip(route, route[1:], strict=False):
        add(a, b, "free")
    for a, b in zip(route[1:], route, strict=False):
        add(a, b, "free")
    # Authored point across the wall is already occupied: reject that start;
    # a sweep from the valid spawn towards it must retain the complete spawn.
    opposite = [origin[0] - 275, 0, origin[2]]
    add(opposite, opposite, "invalid_start")
    add(opposite, spawn, "invalid_start")
    add(spawn, opposite, "blocked")
    # Contact at the authored wall is closed; a single binary32 ULP separates it.
    boundary = scalar_bits(origin[0] + 176)
    for delta, status in ((-1, "invalid_start"), (0, "invalid_start"), (1, "free")):
        point = [f"f32:{boundary + delta:08x}", 0, origin[2]]
        add(point, point, status)
        add(spawn, point, "free" if delta == 1 else "blocked")
    for axis, lower, upper in ((0, 0, 1), (2, 2, 3)):
        for index, radius in ((lower, 176), (upper, -176)):
            point = spawn.copy()
            point[axis] = token(float(rational(scene["floor"][index]) + radius))
            add(point, spawn, "invalid_start")
            add(spawn, point, "blocked")
    # Every projected blocker rejects a point inside its footprint, regardless
    # of opaque flags. Rounding the midpoint to f32 remains inside the box.
    for box in scene["blockers"]:
        center = [
            token(float((rational(box[0]) + rational(box[1])) / 2)),
            0,
            token(float((rational(box[2]) + rational(box[3])) / 2)),
        ]
        add(center, spawn, "invalid_start")
        add(spawn, center, "blocked")
    for bad in ("f32:7fc00001", "f32:7f800000", "f32:ff800000"):
        add(spawn, [bad, 0, spawn[2]], "invalid_query")
    add([spawn[0], 1, spawn[2]], spawn, "off_floor")
    add(spawn, [spawn[0], 1, spawn[2]], "off_floor")
    add(spawn, [1000001, 0, spawn[2]], "out_of_bounds")
    add(spawn, [spawn[0], "f32:80000000", spawn[2]], "free")
    add(spawn, spawn, "unavailable", ready=False)
    results = [observe(scene, query) for query in queries]
    for index, (result, expected) in enumerate(zip(results, expectations, strict=True)):
        observed = result["result"]
        if observed == "ok":
            observed = "blocked" if result["blocked"] else "free"
        require(observed == expected, f"HP34_EXPECTATION_MISMATCH_{index}_{expected}_{observed}")
    return queries, results, dict(sorted(Counter(expectations).items()))


def audit(paths, executables, bundles=None):
    custody = PinnedInputs()
    packages, report = _prepare(paths, custody)
    code = [
        "tools/pipeline/heather_room_contacts.py",
        "tools/pipeline/prepare_heather_room_contacts.py",
        "tests/heather_room_private_audit.py",
        "tests/heather_room_preparation_oracle.py",
        "tests/cld_polygon_wire_oracle.py",
        "tests/python/helpers/heather_room_contact_oracle.py",
        "engine/domain/room_contacts.cpp",
        "engine/platform/common/room_movement_contacts.cpp",
    ]
    code_pins = {name: sha(custody.read(ROOT / name, 1024 * 1024)) for name in code}
    binaries = [
        dict(size=len(raw), sha256=sha(raw))
        for exe in executables
        for raw in [custody.read(exe, 16 * 1024 * 1024)]
    ]
    reports = []
    for copy, files in packages.items():
        if bundles:
            files, published_report = read_bundle(bundles / ("heather-room-contacts-v1-" + copy))
            require(
                (files, published_report) == (packages[copy], report), "HP34_PUBLISHED_MISMATCH"
            )
        view, scene, roles = projection(files["source.cld"])
        identical(json.loads(files["polygons.json"]), view)
        contacts = json.loads(files["contacts.json"])
        require(
            (contacts["scene"], contacts["record_roles"]) == (scene, roles), "HP34_BOX_MISMATCH"
        )
        queries, results, counts = queries_for(json.loads(files["room-profile.json"]), scene)
        for exe in executables:
            require(native_check(exe, scene, queries) == results, "HP34_NATIVE_MISMATCH")
        if bundles:
            require(
                read_bundle(bundles / ("heather-room-contacts-v1-" + copy)) == (files, report),
                "HP34_READBACK_CHANGED",
            )
        reports.append(
            dict(
                files={name: dict(size=len(raw), sha256=sha(raw)) for name, raw in files.items()},
                queries=len(queries),
                outcomes=counts,
            )
        )
    require(reports[0] == reports[1], "HP34_AB_MISMATCH")
    custody.verify()
    return dict(
        **report,
        status="verified",
        copies=2,
        identical_copies=True,
        independent_wire_and_projection=True,
        independent_rational_edges=True,
        spawn_valid=True,
        forward_route_segments=5,
        reverse_route_segments=5,
        native_executables=binaries,
        native_checks=2 * len(executables) * reports[0]["queries"],
        published_readback=bundles is not None,
        code_sha256=code_pins,
        **reports[0],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("profile", "catalog", "receipt", "copies"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--native", type=Path, action="append", required=True)
    parser.add_argument("--bundles", type=Path)
    args = parser.parse_args()
    try:
        result = audit(
            {k: getattr(args, k) for k in ("profile", "catalog", "receipt", "copies")},
            args.native,
            args.bundles,
        )
    except (ValueError, OSError, KeyError, AssertionError) as error:
        print(
            json.dumps(
                dict(
                    status="rejected",
                    error_type=type(error).__name__,
                    code=str(error) if str(error).startswith("HP34_") else "audit_failed",
                )
            )
        )
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
