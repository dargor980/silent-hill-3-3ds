"""Frozen HS-T2 vectors and executable shader-contract checks, host only."""

import copy
import hashlib
import json
import math
import struct
from fractions import Fraction
from pathlib import Path

import pytest

from tests.generate_heather_skinning_vectors import build, matrix
from tests.heather_skinning_oracle import (
    bits,
    execute_binary32,
    f32,
    prepare,
    projection_delta,
    reference,
    shader_program,
)
from tools.qa.skinning_workload import partition_palettes

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/synthetic"
RAW = (FIXTURES / "heather-skinning-native-v1.json").read_bytes()
DATA = json.loads(RAW)
SHADER = bytes.fromhex(DATA["shader_hex"])


def test_reproducible_fixture_and_pinned_dependencies():
    assert (
        hashlib.sha256(RAW).hexdigest()
        == "89bc59bd630ee62d38a9ad64523eb5f0dbd91c1e0426c1a891bbf8f3301fc520"
    )
    assert build(SHADER) == DATA
    assert hashlib.sha256(SHADER).hexdigest() == DATA["shader_sha256"]
    assert (
        hashlib.sha256((FIXTURES / "heather-skinning-v1.v.pica").read_bytes()).hexdigest()
        == DATA["shader_source_sha256"]
    )
    assert (
        hashlib.sha256((FIXTURES / "heather-turns-native-v1.json").read_bytes()).hexdigest()
        == DATA["hg_fixture_sha256"]
    )
    assert DATA["status"] == "specified_not_integrated"


@pytest.mark.parametrize("case", DATA["cases"], ids=lambda c: c["id"])
def test_exact_reference_packing_and_compiled_dataflow(case):
    prepared = prepare(case)
    expected = case["expected"]
    ref = reference(case, prepared)
    assert ref == [Fraction(n, d) for n, d in expected["room_rational"]]
    assert prepared["rows"] == expected["rows_xyz_w"]
    assert bits([v for r in prepared["rows"] for v in reversed(r)]) == expected["uniform_wzyx_hex"]
    vertex = bits([v for a in prepared["attributes"] for v in a])
    assert vertex == expected["vertex_hex"] and len(bytes.fromhex(vertex)) == 64
    out, room = execute_binary32(shader_program(SHADER), prepared)
    assert room[3] == sum(case["weights_q12"]) / 4096
    assert (
        max(abs(float(a) - b) for a, b in zip(ref, room, strict=True))
        <= DATA["tolerances"]["host_room_abs"]
    )
    clip = [sum(prepared["clip"][4 * r + c] * float(ref[c]) for c in range(4)) for r in range(4)]
    assert max(projection_delta(clip, out[0])) <= DATA["tolerances"]["projection_pixels"]
    assert out[1] == [1, 1, 1, 1] and out[2] == prepared["attributes"][3]


@pytest.mark.parametrize("case", DATA["batch_cases"], ids=lambda c: c["id"])
def test_frozen_contiguous_partitions(case):
    if "error" in case:
        with pytest.raises(ValueError, match=case["error"]):
            partition_palettes(case["triangles"], case["capacity"])
    else:
        assert [list(b) for b in partition_palettes(case["triangles"], case["capacity"])] == case[
            "expected"
        ]


@pytest.mark.parametrize("bad", DATA["rejections"], ids=lambda c: c["id"])
def test_declared_rejections(bad):
    case = copy.deepcopy(DATA["cases"][0])
    case[bad["field"]] = bad["value"]
    with pytest.raises(ValueError, match=bad["error"]):
        prepare(case)


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan, 1e100])
def test_non_finite_and_binary32_overflow(value):
    with pytest.raises(ValueError, match="HS_NUMBER"):
        f32(value)


@pytest.mark.parametrize(
    "kind",
    [
        "short",
        "affine",
        "bound",
        "instance",
        "reflection",
        "bone",
        "helper",
        "target",
        "clip",
        "vertex",
    ],
)
def test_matrix_and_reference_rejections(kind):
    case = copy.deepcopy(DATA["cases"][0])
    if kind == "short":
        case["bones"]["0"].pop()
    elif kind == "affine":
        case["bones"]["0"][3] = 1
    elif kind == "bound":
        case["bones"]["0"][12] = 1000001
    elif kind == "instance":
        case["instance"][0] = 2
    elif kind == "reflection":
        case["instance"][0] = -1
    elif kind == "bone":
        case["bones"]["73"] = case["bones"].pop("1")
    elif kind == "helper":
        case["helpers"]["72"] = case["helpers"].pop("73")
    elif kind == "target":
        case["helpers"]["73"]["target"] = 72
    elif kind == "clip":
        case["clip_from_room"] = []
    else:
        case["uv_q12"] = []
    with pytest.raises(ValueError, match="HS_"):
        prepare(case)


def test_hg_pose_coverage_and_sample_windows():
    hg = json.loads((FIXTURES / "heather-turns-native-v1.json").read_bytes())
    cases = {c["id"]: c for c in DATA["cases"]}
    for arc in hg["poses"]:
        for row in arc["rows"]:
            c = cases[f"hg-{arc['id']}-{row['beta']}"]
            assert c["hg"] == dict(arc=arc["id"], beta=row["beta"])
            assert c["bones"]["0"] == matrix(
                [n / d for n, d in row["translation"]], row["quaternion"]
            )
    for clip in hg["clips"]:
        for phase in (0, 4095, clip["period"] - 1):
            c = cases[f"clip-{clip['id']}-{phase}"]
            a = phase // 4096
            assert c["hg"]["packed"] == [
                clip["packed_first"] + a,
                clip["packed_first"] + (a + 1) % clip["count"],
            ]
    assert len([c for c in cases.values() if "hg" in c]) == 41


def test_sensitive_negative_controls():
    c = next(c for c in DATA["cases"] if c["id"] == "origin-translation-w")
    p = prepare(c)
    expected = list(map(float, reference(c, p)))
    wrong = copy.deepcopy(p)
    wrong["attributes"][1][3] = 1.0
    _, q = execute_binary32(shader_program(SHADER), wrong)
    assert q[3] != expected[3]
    wrong = copy.deepcopy(p)
    wrong["rows"] = [list(reversed(r)) for r in wrong["rows"]]
    _, q = execute_binary32(shader_program(SHADER), wrong)
    assert max(abs(a - b) for a, b in zip(q, expected, strict=True)) > 0.001
    wrong = copy.deepcopy(c)
    wrong["helpers"]["74"] = copy.deepcopy(wrong["helpers"]["73"])
    assert (
        max(
            abs(float(a) - float(b))
            for a, b in zip(reference(wrong, prepare(wrong)), expected, strict=True)
        )
        > 0.001
    )
    wrong = copy.deepcopy(c)
    wrong["weights_q12"] = [1366, 1365, 1365]
    assert reference(wrong, prepare(wrong))[3] != expected[3]


def test_shader_truncation_and_mutations_fail_closed():
    for end in range(len(SHADER)):
        with pytest.raises((ValueError, struct.error)):
            shader_program(SHADER[:end])
    p, v = 12, struct.unpack_from("<I", SHADER, 8)[0]
    fields = [0, 4, 8, p, p + 12, p + 20, v, v + 4, v + 8, v + 12, v + 28, v + 44, v + 52, v + 56]
    for offset in fields:
        b = bytearray(SHADER)
        struct.pack_into("<I", b, offset, 0xFFFFFFFF)
        with pytest.raises(ValueError, match="HS_SHBIN"):
            shader_program(bytes(b))
    code = p + struct.unpack_from("<I", SHADER, p + 8)[0]
    b = bytearray(SHADER)
    struct.pack_into("<I", b, code, 0xFFFFFFFF)
    with pytest.raises(ValueError, match="HS_SHBIN"):
        shader_program(bytes(b))


def test_shader_dynamic_address_rejected():
    p = prepare(DATA["cases"][0])
    for index in (-3, 88, 1.5):
        p["attributes"][2][0] = index
        with pytest.raises(ValueError, match="HS_SHADER_ADDRESS"):
            execute_binary32(shader_program(SHADER), p)


def test_projection_threshold_and_degenerate_w():
    assert projection_delta([0, 0, 0, 1], [0.25 / 120, 0.25 / 200, 0, 1]) == [0.25, 0.25]
    assert max(projection_delta([0, 0, 0, 1], [0.251 / 120, 0, 0, 1])) > 0.25
    for w in (0, -0.1, 0.019999):
        with pytest.raises(ValueError, match="HS_PROJECTABILITY"):
            projection_delta([0, 0, 0, 1], [0, 0, 0, w])
    with pytest.raises(ValueError, match="HS_NUMBER"):
        projection_delta([0, 0, 0, 1], [math.nan, 0, 0, 1])


@pytest.mark.parametrize("case", DATA["projection_cases"], ids=lambda c: c["id"])
def test_frozen_projection_acceptance(case):
    if "error" in case:
        with pytest.raises(ValueError, match=case["error"]):
            projection_delta(case["reference"], case["actual"])
    else:
        pixels = projection_delta(case["reference"], case["actual"])
        assert pixels == case["pixels"]
        assert (max(pixels) <= DATA["tolerances"]["projection_pixels"]) == case["accepted"]


def test_frozen_transparent_total_order():
    for case in DATA["transparency_cases"]:
        actual = sorted(case["triangles"], key=lambda t: (-t["depth"], t["material"], t["first"]))
        assert [t["id"] for t in actual] == case["expected"]
