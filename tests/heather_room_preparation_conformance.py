"""Own CLD -> production preparation -> independent wire/edge oracles -> C++ port."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.cld_polygon_wire_oracle import identical  # noqa: E402
from tests.heather_room_preparation_oracle import native_check, projection  # noqa: E402
from tests.python.helpers.heather_room_preparation_fixture import cld  # noqa: E402
from tools.pipeline.heather_room_contacts import convert_cld  # noqa: E402


def check(executable):
    raw = cld()
    actual, contacts = convert_cld(raw)
    view, scene, roles = projection(raw)
    identical(actual, view)
    if contacts["scene"] != scene or contacts["record_roles"] != roles:
        raise ValueError("PREPARATION_PROJECTION_MISMATCH")
    spawn = [100275, 0, 140000]
    points = [
        spawn,
        [100230, 0, 139850],
        [100320, 0, 139850],
        [100320, 0, 140400],
        [100230, 0, 140400],
        [100230, 0, 139850],
    ]
    pairs = [(spawn, spawn), *zip(points, points[1:], strict=False)]
    # Crossing the own remote wall with both endpoints clear; blocked start;
    # strict floor boundary; invalid Y/NaN/range; signed zero and unavailable.
    pairs += [
        ([99200, 0, 140000], [99200, 0, 139200]),
        ([99200, 0, 140000], [99200, 0, 140000]),
        ([99200, 0, 139200], [99200, 0, 139200]),
        ([99302, 0, 139300], spawn),
        (spawn, [99176, 0, 140000]),
        ([99176, 0, 140000], spawn),
        (spawn, [100275, 1, 140000]),
        (spawn, ["f32:7fc00000", 0, 140000]),
        (spawn, [1000001, 0, 140000]),
        (spawn, [100275, "f32:80000000", 140000]),
    ]
    queries = [dict(**{"from": a}, requested=b, ordinal=i) for i, (a, b) in enumerate(pairs)]
    queries.append({**queries[0], "ready": False})
    results = native_check(executable, scene, queries)
    if any(r.get("blocked", True) for r in results[:6]):
        raise ValueError("OWN_ROUTE_NOT_FREE")
    if results[6].get("blocked") is not True:
        raise ValueError("OWN_CROSSING_NOT_BLOCKED")
    if any(r.get("blocked", True) for r in results[7:9]):
        raise ValueError("OWN_CROSSING_ENDPOINTS_NOT_FREE")
    print(f"Own preparation: 34 records, 32 boxes, {len(queries)} native/oracle queries PASS")


if __name__ == "__main__":
    check(Path(sys.argv[1]).resolve())
