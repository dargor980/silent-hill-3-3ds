"""HS-T3 native bytes against the frozen independent HSN oracle; synthetic only."""

import hashlib
import json
import random
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import heather_skinning_oracle as oracle
from tools.qa.skinning_shader import validate

ROOT = Path(__file__).resolve().parents[1]


def run(executable, mode, words):
    return subprocess.run(
        [executable, mode],
        input=" ".join(map(str, words)),
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()


def numeric(executable, fixture):
    words = [len(fixture["cases"])]
    for c in fixture["cases"]:
        words += [len(c["bones"])]
        for key, matrix in c["bones"].items():
            words += [int(key), *matrix]
        words += [len(c["helpers"])]
        for key, helper in c["helpers"].items():
            words += [int(key), helper["target"], *helper["matrix"]]
        words += [
            len(c["palette"]),
            *c["palette"],
            *c["position_q4"],
            *c["uv_q12"],
            *c["weights_q12"],
            len(c["influences"]),
            *c["influences"],
            *c["instance"],
        ]
    lines = run(executable, "--vectors", words)
    assert len(lines) == len(fixture["cases"])
    program = oracle.shader_program(bytes.fromhex(fixture["shader_hex"]))
    maximum = 0.0
    for c, line in zip(fixture["cases"], lines, strict=True):
        vertex, uniform = line.split()
        assert vertex == c["expected"]["vertex_hex"], c["id"]
        assert uniform == c["expected"]["uniform_wzyx_hex"], c["id"]
        prepared = oracle.prepare(c)
        prepared["attributes"] = [list(v) for v in struct.iter_unpack("<4f", bytes.fromhex(vertex))]
        prepared["rows"] = [
            list(reversed(v)) for v in struct.iter_unpack("<4f", bytes.fromhex(uniform))
        ]
        _, actual = oracle.execute_binary32(program, prepared)
        expected = list(map(float, oracle.reference(c, prepared)))
        error = max(abs(a - b) for a, b in zip(actual[:3], expected[:3], strict=True))
        assert error <= fixture["tolerances"]["host_room_abs"] and actual[3] == expected[3]
        maximum = max(maximum, error)
    return maximum


def vertex(primary, helpers=(), ordinal=0):
    return dict(
        position_q4=[ordinal % 30000, -16, 32],
        uv_q12=[-4096, 8192],
        weights_q12=[4096, 0, 0],
        influences=[primary, *helpers],
    )


def plan(executable, vertices, indices, materials, capacity=30):
    words = [capacity, len(vertices), len(indices), len(materials)]
    for v in vertices:
        helpers = [x - 73 for x in v["influences"][1:]]
        words += [
            *v["position_q4"],
            *v["uv_q12"],
            *v["weights_q12"],
            len(v["influences"]),
            v["influences"][0],
            *helpers,
            *([255] * (2 - len(helpers))),
        ]
    for m in materials:
        assert m[1] % 3 == 0
    words += indices + [x for m in materials for x in m]
    # Independent sequential set union and per-batch first-appearance map.
    batches, mapped, packed = [], [], []
    expected_error = False
    for material, (first, count, blend) in enumerate(materials):
        if blend:
            continue
        end = first + count
        while first < end:
            used, stop = set(), first
            while stop < end:
                triangle = set().union(
                    *(set(vertices[i]["influences"]) for i in indices[stop : stop + 3])
                )
                if len(used | triangle) > capacity:
                    break
                used |= triangle
                stop += 3
            if stop == first:
                expected_error = True
                break
            slots = sorted(used)
            batches.append([len(mapped), stop - first, material, *slots])
            remap = {}
            for original in indices[first:stop]:
                if original not in remap:
                    remap[original] = len(packed)
                    v = vertices[original]
                    local = [float(3 * slots.index(s)) for s in v["influences"]]
                    packed.append(
                        struct.pack(
                            "<16f",
                            *(x / 16 for x in v["position_q4"]),
                            1,
                            *(x / 4096 for x in v["weights_q12"]),
                            sum(v["weights_q12"]) / 4096,
                            *local,
                            *([0] * (4 - len(local))),
                            *(x / 4096 for x in v["uv_q12"]),
                            0,
                            1,
                        )
                    )
                mapped.append(remap[original])
            first = stop
    actual = run(executable, "--plan", words)
    if expected_error:
        assert actual == ["REJECT"]
        return None
    assert list(map(int, actual[0].split())) == [len(packed), len(mapped), len(batches)]
    assert [list(map(int, s.split())) for s in actual[1 : 1 + len(batches)]] == batches
    assert actual[-2] == struct.pack("<" + "H" * len(mapped), *mapped).hex()
    assert actual[-1] == b"".join(packed).hex()
    return [[b[0] // 3, b[1] // 3, b[3:]] for b in batches]


def main(executable):
    raw = (ROOT / "tests/fixtures/synthetic/heather-skinning-native-v1.json").read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == "89bc59bd630ee62d38a9ad64523eb5f0dbd91c1e0426c1a891bbf8f3301fc520"
    )
    fixture = json.loads(raw)
    shader = bytes.fromhex(fixture["shader_hex"])
    validate(shader)
    assert (ROOT / "engine/platform/3ds/render/skinning.v.pica").read_bytes() == (
        ROOT / "tests/fixtures/synthetic/heather-skinning-v1.v.pica"
    ).read_bytes()
    # The SDK double consumes the actual frozen binary, not an unrelated stub.
    import re

    header = (ROOT / "tests/cpp/render_doubles/skinning_shader_shbin.h").read_text()
    assert bytes(int(x, 16) for x in re.findall(r"0x([0-9a-f]{2})", header)) == shader
    maximum = numeric(executable, fixture)
    for case in fixture["batch_cases"]:
        vertices = []
        for triangle in case["triangles"]:
            primary = [s for s in triangle if s < 73] or [1]
            helpers = [s for s in triangle if s >= 73]
            for i in range(3):
                vertices.append(vertex(primary[i % len(primary)], helpers, len(vertices)))
        if not vertices:  # Empty opaque subset, valid SRI still contains a transparent triangle.
            vertices = [vertex(0)] * 3
            result = plan(executable, vertices, [0, 1, 2], [(0, 3, 1)], case["capacity"])
        else:
            result = plan(
                executable,
                vertices,
                list(range(len(vertices))),
                [(0, len(vertices), 0)],
                case["capacity"],
            )
        assert result == case.get("expected"), case["id"]
    rng = random.Random(0x48534E)
    for _ in range(64):
        vertices = [
            vertex(rng.randrange(73), rng.sample(range(73, 201), rng.randrange(3)), i)
            for i in range(120)
        ]
        indices = [rng.randrange(len(vertices)) for _ in range(360)]
        plan(executable, vertices, indices, [(0, 120, 0), (120, 180, 0), (300, 60, 1)])
    vertices = [vertex(i % 73, [73 + i % 128, 73 + (i + 37) % 128], i) for i in range(8192)]
    plan(executable, vertices, [i % 8192 for i in range(18000)], [(0, 18000, 0)])
    print(
        json.dumps(
            dict(
                hsn_numeric=54,
                frozen_partitions=6,
                random_plans=64,
                max_host_error=maximum,
                gpu_execution=False,
            )
        )
    )


if __name__ == "__main__":
    main(sys.argv[1])
