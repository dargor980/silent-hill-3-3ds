"""Independent CLD-to-room projection and native query comparison, test/audit only."""

import struct
import subprocess

from tests.cld_polygon_wire_oracle import observe as read_cld
from tests.python.helpers.heather_room_contact_oracle import observe, scalar_bits


def projection(raw):
    view = read_cld(raw)
    groups = view["groups"]
    if [len(g["records"]) for g in groups] != [1, 4, 26, 3, 0]:
        raise ValueError("ORACLE_COUNTS")
    boxes, roles = [], []
    floor = None
    for group in groups:
        if group["cells"][0]["indices"] != list(range(len(group["records"]))) or any(
            c["indices"] for c in group["cells"][1:]
        ):
            raise ValueError("ORACLE_REFERENCES")
        for row in group["records"]:
            points = row["vectors_xyzw"]
            words = row["vector_words"]
            key = group["index"], row["index"]
            axes = [sorted(range(4), key=lambda i: (points[i][k], i)) for k in (0, 2)]
            bounds = []
            for k, ordering in zip((0, 2), axes, strict=True):
                lo = ordering[0]
                # Tie uses the first source index for both lower and upper limits.
                hi = next(i for i in range(4) if points[i][k] == points[ordering[-1]][k])
                bounds += [f"f32:{words[lo][k]:08x}", f"f32:{words[hi][k]:08x}"]
            if key == (0, 0):
                floor, role = bounds, "floor"
            elif key == (2, 4):
                role = "ceiling_excluded"
            else:
                boxes.append(bounds)
                role = "blocker"
            roles.append(dict(group=key[0], index=key[1], offset=row["offset"], role=role))
    return (
        view,
        dict(
            profile="static-xz-aabb-stop-v1",
            origin=[100000, 0, 140000],
            floor_y=0,
            half_extent=175,
            guard=1,
            floor=floor,
            blockers=boxes,
        ),
        roles,
    )


def native_check(executable, scene, queries):
    lines, expected = [], []
    errors = {
        "ok": 0,
        "unavailable": 6,
        "invalid_query": 7,
        "out_of_bounds": 8,
        "off_floor": 9,
        "invalid_start": 10,
    }
    ports = {"accepted": 0, "unavailable": 1, "unsupported": 2}
    sentinel = list(struct.unpack("<3I", bytes.fromhex("a55ac33c966969963cc35aa5")))
    for query in queries:
        result = observe(scene, query)
        choice = result["copy_from"]
        output = [scalar_bits(v) for v in query[choice]] if choice else sentinel
        expected.append([0, errors[result["result"]], ports[result["port"]], *output])
        values = [
            1,
            1,
            *[
                scalar_bits(v)
                for v in [175, 1, *scene["origin"], scene["floor_y"], *scene["floor"]]
            ],
            len(scene["blockers"]),
            576,
            2560,
        ]
        values += [scalar_bits(v) for box in scene["blockers"] for v in box]
        values += [
            int(query.get("ready", True)),
            *[scalar_bits(v) for v in [*query["from"], *query["requested"]]],
            query["ordinal"],
        ]
        lines.append(" ".join(map(str, values)))
    run = subprocess.run(
        [str(executable), "vectors"],
        input="\n".join(lines) + "\n",
        text=True,
        capture_output=True,
        timeout=45,
        check=True,
    )
    actual = [list(map(int, line.split())) for line in run.stdout.splitlines()]
    # Never include private coordinates in a rejection message or report.
    if actual != expected:
        raise ValueError("ORACLE_NATIVE_MISMATCH")
    return [observe(scene, q) for q in queries]
