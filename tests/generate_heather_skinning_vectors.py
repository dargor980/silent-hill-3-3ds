"""Regenerate the authored HS-T2 fixture; never reads private game resources."""

import copy
import hashlib
import json
from pathlib import Path

from tests.heather_skinning_oracle import bits, f32, prepare, reference

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/synthetic"


def matrix(translation=(0, 0, 0), quaternion=(0, 0, 0, 1)):
    x, y, z, w = quaternion
    # Independent explicit quaternion basis for authored poses.
    return list(
        map(
            f32,
            [
                1 - 2 * (y * y + z * z),
                2 * (x * y + z * w),
                2 * (x * z - y * w),
                0,
                2 * (x * y - z * w),
                1 - 2 * (x * x + z * z),
                2 * (y * z + x * w),
                0,
                2 * (x * z + y * w),
                2 * (y * z - x * w),
                1 - 2 * (x * x + y * y),
                0,
                *translation,
                1,
            ],
        )
    )


def cases():
    base = dict(
        id="identity-one",
        bones={"0": matrix(), "1": matrix((3, -2, 5))},
        helpers={
            "73": dict(target=0, matrix=matrix((2, 0, -1))),
            "74": dict(target=0, matrix=matrix((-3, 4, 1))),
        },
        palette=[0, 1, 73, 74],
        influences=[0],
        weights_q12=[4096, 0, 0],
        position_q4=[16, -32, 48],
        uv_q12=[-4096, 8192],
        instance=matrix((100000, 0, 140000)),
        clip_from_room=[1, 0, 0, 0.125, 0, 1.5, 0, -0.25, 0, 0, -0.5, 0.75, 0, 0, 0.125, 2],
    )
    out = []

    def add(name, **updates):
        row = copy.deepcopy(base)
        row.update(id=name, **updates)
        out.append(row)
        return row

    add("identity-one")
    add("two-full", influences=[0, 73], weights_q12=[1024, 3072, 0])
    add("two-deficient", influences=[1, 74], weights_q12=[2047, 2048, 0])
    add("three-4094", influences=[1, 73, 74], weights_q12=[1364, 1365, 1365])
    add("three-4095", influences=[1, 73, 74], weights_q12=[1365, 1365, 1365])
    add("three-4096", influences=[1, 73, 74], weights_q12=[2048, 1024, 1024])
    add("active-zero", influences=[0, 73], weights_q12=[4095, 0, 0])
    add("same-helper-twice", influences=[0, 73, 73], weights_q12=[2048, 1023, 1024])
    add(
        "origin-translation-w",
        instance=matrix((100231.5, -12.25, 140813.75)),
        influences=[0, 73, 74],
        weights_q12=[1364, 1365, 1365],
    )
    add("yaw-quarter", instance=matrix((100050, 10, 140075), (0, 1, 0, 0)))
    # Exact +pi/2 around Y, no transcendental approximation in this case.
    out[-1]["instance"][:12] = [0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0]
    add("q4-uv-extremes", position_q4=[-32768, 32767, -1], uv_q12=[-32768, 32767])
    edge = add(
        "last-local-matrix-29",
        palette=list(range(30)),
        influences=[29],
        bones={str(i): matrix((i, -i, i / 2)) for i in range(30)},
        helpers={},
    )
    assert edge["palette"][-1] == 29
    sparse = add(
        "last-helper-slot-200", palette=[0, 200], influences=[0, 200], weights_q12=[2048, 2047, 0]
    )
    sparse["helpers"] = {"200": dict(target=0, matrix=matrix((2, 3, -4)))}

    hg = json.loads((FIXTURES / "heather-turns-native-v1.json").read_bytes())
    for clip in hg["clips"]:
        for phase in (0, 4095, clip["period"] - 1):
            j, fraction = divmod(phase, 4096)
            k = (j + 1) % clip["count"]
            # Authored steady pose translations exercise the frozen sample windows.
            t = (j * (4096 - fraction) + k * fraction) / 4096
            row = add(f"clip-{clip['id']}-{phase}")
            row["bones"]["0"] = matrix((t, -t / 2, clip["id"] / 16))
            row["hg"] = dict(
                clip=clip["id"],
                phase=phase,
                fraction=fraction,
                packed=[clip["packed_first"] + j, clip["packed_first"] + k],
            )
    for arc in hg["poses"]:
        for sample in arc["rows"]:
            row = add(
                f"hg-{arc['id']}-{sample['beta']}",
                influences=[0, 73, 74],
                weights_q12=[1364, 1365, 1365],
            )
            row["bones"]["0"] = matrix(
                [n / d for n, d in sample["translation"]], sample["quaternion"]
            )
            row["hg"] = dict(arc=arc["id"], beta=sample["beta"])
    for row in out:
        packed = prepare(row)
        exact = reference(row, packed)
        row["expected"] = dict(
            room_rational=[[v.numerator, v.denominator] for v in exact],
            vertex_hex=bits([v for a in packed["attributes"] for v in a]),
            uniform_wzyx_hex=bits([v for r in packed["rows"] for v in reversed(r)]),
            rows_xyz_w=packed["rows"],
        )
    return out


def build(shader):
    hg = (FIXTURES / "heather-turns-native-v1.json").read_bytes()
    # Hand-authored ordered partitions; expected results are not produced by HS-T1.
    batch_cases = [
        dict(id="empty", capacity=30, triangles=[], expected=[]),
        dict(id="one", capacity=30, triangles=[[0, 73, 74]], expected=[[0, 1, [0, 73, 74]]]),
        dict(
            id="exact30",
            capacity=30,
            triangles=[[i, i + 1, i + 2] for i in range(0, 30, 3)],
            expected=[[0, 10, list(range(30))]],
        ),
        dict(
            id="split31",
            capacity=30,
            triangles=[[i, i + 1, i + 2] for i in range(0, 30, 3)] + [[28, 29, 30]],
            expected=[[0, 10, list(range(30))], [10, 1, [28, 29, 30]]],
        ),
        dict(
            id="repeated",
            capacity=3,
            triangles=[[1, 73], [73, 1], [74], [1]],
            expected=[[0, 4, [1, 73, 74]]],
        ),
        dict(
            id="indivisible", capacity=2, triangles=[[0], [0, 73, 74]], error="HS_TRIANGLE_CAPACITY"
        ),
    ]
    return dict(
        schema="heather-skinning-native-v1",
        status="specified_not_integrated",
        provenance="authored_synthetic_no_game_assets",
        capacity=30,
        sdk_image=(ROOT / "toolchains/devkitpro-image.txt").read_text().strip(),
        hg_fixture_sha256=hashlib.sha256(hg).hexdigest(),
        shader_source_sha256=hashlib.sha256(
            (FIXTURES / "heather-skinning-v1.v.pica").read_bytes()
        ).hexdigest(),
        shader_hex=shader.hex(),
        shader_sha256=hashlib.sha256(shader).hexdigest(),
        tolerances=dict(
            host_room_abs=2e-5,
            gpu_room_abs=2e-4,
            gpu_room_relative=2e-4,
            projection_pixels=0.25,
            projectable_w_min=0.02,
            intermediate_w_exact=True,
        ),
        cases=cases(),
        batch_cases=batch_cases,
        projection_cases=[
            dict(
                id="quarter-pixel",
                reference=[0, 0, 0, 1],
                actual=[0.25 / 120, 0.25 / 200, 0, 1],
                pixels=[0.25, 0.25],
                accepted=True,
            ),
            dict(
                id="over-quarter",
                reference=[0, 0, 0, 1],
                actual=[0.251 / 120, 0, 0, 1],
                pixels=[0.251, 0],
                accepted=False,
            ),
            dict(
                id="near-plane",
                reference=[0, 0, 0, 0.02],
                actual=[0, 0, 0, 0.02],
                pixels=[0, 0],
                accepted=True,
            ),
            dict(
                id="no-perspective-divide",
                reference=[0, 0, 0, 1],
                actual=[0, 0, 0, 0],
                error="HS_PROJECTABILITY",
            ),
        ],
        transparency_cases=[
            dict(
                id="depth-and-ties",
                triangles=[
                    dict(id="hair-b", depth=5, material=12, first=3),
                    dict(id="glass", depth=5, material=13, first=0),
                    dict(id="hair-a", depth=5, material=12, first=0),
                    dict(id="far-glass", depth=6, material=13, first=3),
                ],
                expected=["far-glass", "hair-a", "hair-b", "glass"],
            ),
        ],
        draw_states=[
            "original_map_cpu_shader",
            "opaque_skinning_shader",
            "restore_cpu_shader_attributes_camera",
            "global_hair_glass_order",
        ],
        rejections=[
            dict(id="empty-palette", field="palette", value=[], error="HS_CAPACITY"),
            dict(id="capacity31", field="palette", value=list(range(31)), error="HS_CAPACITY"),
            dict(id="duplicate-slot", field="palette", value=[0, 0, 73], error="HS_PALETTE_ORDER"),
            dict(id="unsorted", field="palette", value=[73, 0], error="HS_PALETTE_ORDER"),
            dict(id="slot-negative", field="palette", value=[-1, 0], error="HS_SLOT"),
            dict(id="slot201", field="palette", value=[0, 201], error="HS_SLOT"),
            dict(id="absent-slot", field="influences", value=[7], error="HS_SLOT"),
            dict(id="inactive-weight", field="weights_q12", value=[4095, 1, 0], error="HS_WEIGHTS"),
            dict(id="weight-too-low", field="weights_q12", value=[4095, 0, 0], error="HS_WEIGHTS"),
            dict(id="weight-too-high", field="weights_q12", value=[4097, 0, 0], error="HS_WEIGHTS"),
            dict(id="weight-negative", field="weights_q12", value=[-1, 0, 0], error="HS_WEIGHTS"),
            dict(id="influences4", field="influences", value=[0, 1, 73, 74], error="HS_INFLUENCES"),
            dict(id="q4-overflow", field="position_q4", value=[32768, 0, 0], error="HS_VERTEX"),
            dict(id="uv-overflow", field="uv_q12", value=[0, -32769], error="HS_VERTEX"),
        ],
        required_runtime_failures=[
            "atomic_prepare",
            "atomic_frame",
            "sdk_uniform_bounds_before_write",
            "allocation_failure",
            "buffer_ownership",
            "suspend_resume",
            "cpu_fallback",
        ],
    )


if __name__ == "__main__":
    import sys

    data = build(Path(sys.argv[1]).read_bytes())
    (FIXTURES / "heather-skinning-native-v1.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"HS vectors: {len(data['cases'])} numeric, {len(data['batch_cases'])} batches")
