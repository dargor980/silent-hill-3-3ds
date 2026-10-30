"""Feed HRC bits into the native core/port; compare with the independent edge oracle."""

import copy
import json
import random
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.python.helpers.heather_room_contact_oracle import (  # noqa: E402
    observe,
    prepare,
    scalar_bits,
)

ERRORS = dict(
    zip(
        [
            "ok",
            "unsupported_profile",
            "capacity_exceeded",
            "budget_exceeded",
            "invalid_geometry",
            "empty_floor",
            "unavailable",
            "invalid_query",
            "out_of_bounds",
            "off_floor",
            "invalid_start",
        ],
        range(11),
        strict=True,
    )
)
PORTS = {"accepted": 0, "unavailable": 1, "unsupported": 2}


def generated_queries():
    rng = random.Random(0x4B2)

    def f32(value):
        return "f32:" + struct.pack(">f", value).hex()

    for i in range(768):
        # Varied exponents, cancellation, carries and direction signs. Every fourth
        # rectangle is deliberately placed near the midpoint of a long segment.
        a = [rng.uniform(-800000, 800000), 0, rng.uniform(-800000, 800000)]
        b = [rng.uniform(-800000, 800000), 0, rng.uniform(-800000, 800000)]
        if i % 4 == 0:
            cx, cz = (a[0] + b[0]) / 2, (a[2] + b[2]) / 2
        else:
            cx, cz = rng.uniform(-500000, 500000), rng.uniform(-500000, 500000)
        box = [f32(cx - 300), f32(cx + 300), f32(cz - 300), f32(cz + 300)]
        if i % 3 == 0:
            a[i % 2 * 2] = (-1 if i % 2 else 1) * 2.0 ** (-149 + i % 140)
        scene = {
            "profile": "static-xz-aabb-stop-v1",
            "half_extent": 175,
            "guard": 1,
            "origin": [0, 0, 0],
            "floor_y": 0,
            "floor": [-1000000, 1000000, -1000000, 1000000],
            "blockers": [box],
        }
        query = {
            "id": f"dyadic-{i}",
            "from": list(map(f32, a)),
            "requested": list(map(f32, b)),
            "ordinal": i,
        }
        yield scene, query


def verify(executable):
    data = json.loads((ROOT / "tests/fixtures/synthetic/heather-room-contacts-v1.json").read_text())
    lines, expectations, labels = [], [], []
    sentinel = list(struct.unpack("<3I", bytes.fromhex(data["output_sentinel_hex"])))

    def send(kind, label, scene, query, accounting, expected):
        values = [kind, 1 if scene["profile"] == "static-xz-aabb-stop-v1" else 0]
        values += [
            scalar_bits(v)
            for v in [
                scene["half_extent"],
                scene["guard"],
                *scene["origin"],
                scene["floor_y"],
                *scene["floor"],
            ]
        ]
        values += [
            len(scene["blockers"]),
            accounting["resident_bytes"],
            accounting["scratch_bytes"],
        ]
        values += [scalar_bits(v) for box in scene["blockers"] for v in box]
        values += [int(query.get("ready", True))]
        values += [scalar_bits(v) for v in [*query["from"], *query["requested"]]]
        values += [query["ordinal"]]
        lines.append(" ".join(map(str, values)))
        expectations.append(expected)
        labels.append(label)

    for row in data["preparation"]:
        scene = copy.deepcopy(data["scenes"][row["scene"]])
        scene.update(row["replace"])
        if prepare(scene, **row["accounting"]) != row["expected"]:
            raise AssertionError(f"Preparation literal: {row['id']}")
        send(
            0,
            row["id"],
            scene,
            {"from": [0, 0, 0], "requested": [0, 0, 0], "ordinal": 0},
            row["accounting"],
            [ERRORS[row["expected"]], ERRORS["unavailable"], 1, *sentinel],
        )

    queries = [(data["scenes"][q["scene"]], q) for q in data["queries"]]
    queries += list(generated_queries())
    for scene, query in queries:
        expected = observe(scene, query)
        if "expected" in query and query["expected"] != expected:
            raise AssertionError(f"Query literal: {query['id']}")
        selected = expected["copy_from"]
        output = [scalar_bits(v) for v in query[selected]] if selected else sentinel
        send(
            1,
            query["id"],
            scene,
            query,
            {"resident_bytes": 576, "scratch_bytes": 2560},
            [0, ERRORS[expected["result"]], PORTS[expected["port"]], *output],
        )

    process = subprocess.run(
        [executable, "vectors"],
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        timeout=45,
        check=True,
    )
    actual = [list(map(int, line.split())) for line in process.stdout.splitlines()]
    if len(actual) != len(expectations):
        raise AssertionError(f"Missing native results: {len(actual)}/{len(expectations)}")
    for label, result, expected in zip(labels, actual, expectations, strict=True):
        if result != expected:
            raise AssertionError(f"{label}: native {result} != exact oracle {expected}")
    print(
        f"HRC core/port: {len(expectations)} cases (126 fixed + 768 generated); "
        "exact bits, repeat, aliases, atomicity and allocation guard passed"
    )


if __name__ == "__main__":
    verify(sys.argv[1])
