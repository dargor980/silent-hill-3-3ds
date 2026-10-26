"""Check hand-fixed contract vectors, not an unimplemented runtime or private assets.

Integer/rational clocks and high-precision Decimal poses are intentionally
independent of tools.pipeline, the C++ evaluator and private acquisition code.
HL-T4b/c must additionally run their implementation against these literals.
"""

import json
import struct
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pytest

DATA = json.loads(
    (Path(__file__).parents[1] / "fixtures/synthetic/heather-locomotion-v1.json").read_text()
)
CLIPS = {row["id"]: row for row in DATA["clips"]}
Q = DATA["q12"]


def rational_mix(a, b, fraction):
    return [
        Fraction(x) * (1 - fraction) + Fraction(y) * fraction for x, y in zip(a, b, strict=True)
    ]


def decimal_nlerp(a, b, fraction):
    a, b = [Decimal(str(v)) for v in a], [Decimal(str(v)) for v in b]
    sign = -1 if sum(x * y for x, y in zip(a, b, strict=True)) < 0 else 1
    mixed = [x * (1 - fraction) + sign * y * fraction for x, y in zip(a, b, strict=True)]
    norm = sum(v * v for v in mixed).sqrt()
    return [v / norm for v in mixed]


def assert_quaternion(actual, expected):
    assert [float(v) for v in actual] == pytest.approx(expected, abs=1e-12, rel=0)
    assert float(sum(v * v for v in actual)) == pytest.approx(1, abs=1e-14, rel=0)


@pytest.mark.parametrize("clip", DATA["clips"], ids=lambda row: str(row["id"]))
def test_descriptor_literal_bytes_and_packed_range(clip):
    wire = bytes.fromhex(clip["wire_hex"])
    fields = [clip[k] for k in ("id", "count", "speed", "start", "end", "loop", "trailing")]
    assert struct.unpack("<HHhHHBBII", wire) == (*fields, clip["packed_first"], 0)
    assert len(wire) == DATA["wire"]["descriptor_bytes"]
    assert clip["count"] == clip["end"] - clip["start"] + 1
    assert clip["increment"] == clip["speed"] * DATA["ticks"]
    assert clip["period"] == clip["count"] * Q
    assert struct.unpack(">H", wire[:2])[0] != clip["id"]


def test_ranges_cover_58_samples_without_cross_clip_wrap():
    ranges = [list(range(c["packed_first"], c["packed_first"] + c["count"])) for c in DATA["clips"]]
    assert sum(ranges, []) == list(range(58))
    # Whole-buffer wrap would select a different clip after each endpoint.
    for indices in ranges:
        assert (indices[-1] + 1) % 58 != indices[0]
    masks = [set(row["source_bones"]) for row in DATA["channels"]]
    assert [len(mask) for mask in masks] == [15, 21]
    assert not masks[0] & masks[1]
    assert len(masks[0] | masks[1]) == 36
    assert all(0 <= b < 73 for mask in masks for b in mask)


@pytest.mark.parametrize("row", DATA["clock"], ids=lambda row: row["id"])
def test_clock_literals_by_exact_phase_arithmetic(row):
    clip = CLIPS[row["target"]]
    recursive = row["kind"] == "mode5_exit"
    fixed = row["kind"] == "mode3"
    increment, period = clip["increment"], clip["period"]
    advance_count = 0 if fixed else 2 if recursive else 1
    phase = (row["counter"] + increment * int(recursive)) % period
    assert row["pose_phase"] == phase
    assert row["counter_out"] == (row["counter"] + increment * advance_count) % period
    sample, fraction = divmod(Fraction(phase, Q), 1)
    relative = [int(sample), (int(sample) + 1) % clip["count"]]
    assert row["frames"] == [clip["start"] + j for j in relative]
    assert row["packed_frames"] == [clip["packed_first"] + j for j in relative]
    assert row["fraction"] == fraction * Q
    if "source_frames" in row:
        source = CLIPS[row["source"]]
        assert row["source_frames"] == [source["start"] + j for j in relative]
    if not fixed:
        assert phase != row["counter_out"], "post-return phase must fail the pose oracle"
    if recursive:
        assert row["counter_out"] != (row["counter"] + increment) % period
    if row["frames"][0] == clip["end"]:
        assert row["frames"][1] != clip["end"], "clamping loses the endpoint interpolation"


@pytest.mark.parametrize("row", DATA["mode3_sequences"])
def test_mode3_blend_schedule_has_one_exit_advance(row):
    blends = row["blends"]
    assert blends == [row["first"] + i * row["delta"] for i in range(len(blends))]
    assert all(0 < beta < Q for beta in blends)
    assert blends[-1] + row["delta"] == row["exit_sum"] >= Q
    assert row["exit_counter"] == CLIPS[row["target"]]["increment"]
    assert row["exit_counter"] != 2 * CLIPS[row["target"]]["increment"]
    if row["target"] == 101:
        assert row["first"] == 640 * 2
        assert row["delta"] == (640 - 460) * 2
        assert row["first"] != row["delta"]


@pytest.mark.parametrize("row", DATA["mode5_sequences"])
def test_mode5_complete_sequence_by_total_distance_not_state_machine(row):
    clip = CLIPS[row["target"]]
    rows = row["rows_blend_pose_counter"]
    assert len(rows) == 11
    for ordinal, (blend, pose, counter) in enumerate(rows, 1):
        # The exit has one extra advance before evaluating, plus the usual one after.
        pre_advances = ordinal - 1 if ordinal <= 10 else 11
        distance = row["initial_counter"] + pre_advances * clip["increment"]
        assert pose == distance % clip["period"]
        assert counter == (distance + clip["increment"]) % clip["period"]
        assert blend == (384 * ordinal if ordinal <= 10 else 0)
    assert 384 * 10 < Q <= 384 * 11
    assert rows[0][2] < row["initial_counter"]  # wrap inside each blend sequence


@pytest.mark.parametrize("row", DATA["full_loops"])
def test_complete_loop_requires_total_advance_not_just_wrap(row):
    clip = CLIPS[row["clip"]]
    assert row["advance"] == row["updates"] * clip["increment"]
    assert row["advance"] >= clip["period"]
    assert row["advance"] - clip["increment"] < clip["period"]
    assert row["counter_out"] == row["advance"] % clip["period"]


def test_mode5_pose_order_has_observable_noncommutativity():
    v = DATA["pose"]["mode5_order"]
    with localcontext() as context:
        context.prec = 60
        beta, fraction = Decimal(v["blend"]) / Q, Decimal(v["fraction"]) / Q
        a, b = v["source_quaternions"], v["target_quaternions"]
        endpoints = [decimal_nlerp(x, y, beta) for x, y in zip(a, b, strict=True)]
        actual = decimal_nlerp(*endpoints, fraction)
        assert_quaternion(actual, v["expected_quaternion"])
        wrong = decimal_nlerp(decimal_nlerp(*a, fraction), decimal_nlerp(*b, fraction), beta)
        assert (
            max(abs(float(x - y)) for x, y in zip(actual, wrong, strict=True))
            > v["wrong_order_max_difference_min"]
        )
    endpoints = [
        rational_mix(x, y, Fraction(v["blend"], Q))
        for x, y in zip(v["source_translations"], v["target_translations"], strict=True)
    ]
    assert rational_mix(*endpoints, Fraction(v["fraction"], Q)) == [
        Fraction(n, d) for n, d in v["expected_translation_rational"]
    ]


def test_cached_stop_retains_interpolated_local_pose():
    v = DATA["pose"]["cached_stop"]
    with localcontext() as context:
        context.prec = 60
        fraction, beta = Decimal(v["source_fraction"]) / Q, Decimal(v["blend"]) / Q
        cached = decimal_nlerp(*v["source_quaternions"], fraction)
        assert_quaternion(cached, v["expected_cached_quaternion"])
        result = decimal_nlerp(cached, v["target_quaternion"], beta)
        assert_quaternion(result, v["expected_quaternion"])
        wrong = decimal_nlerp(v["source_quaternions"][0], v["target_quaternion"], beta)
        assert max(abs(x - y) for x, y in zip(result, wrong, strict=True)) > Decimal("0.1")
    cached_translation = rational_mix(*v["source_translations"], Fraction(v["source_fraction"], Q))
    assert rational_mix(cached_translation, v["target_translation"], Fraction(v["blend"], Q)) == [
        Fraction(n, d) for n, d in v["expected_translation_rational"]
    ]


def test_interrupted_pose_diagnostic_does_not_enable_runtime_transition():
    v = DATA["pose"]["interrupted_diagnostic"]
    assert v["runtime_supported"] is False
    with localcontext() as context:
        context.prec = 60
        cached = decimal_nlerp(v["idle"], v["walk"], Decimal(v["entry_blend"]) / Q)
        actual = decimal_nlerp(cached, v["idle"], Decimal(v["stop_blend"]) / Q)
        assert_quaternion(actual, v["expected_quaternion"])
        assert abs(actual[0]) > Decimal("0.07")  # discarding history would give zero


def test_hemisphere_avoids_antipodal_zero_norm():
    v = DATA["pose"]["hemisphere"]
    with localcontext() as context:
        context.prec = 60
        assert_quaternion(
            decimal_nlerp(v["first"], v["second"], Decimal(v["blend"]) / Q), v["expected"]
        )
    assert rational_mix(v["first"], v["second"], Fraction(1, 2)) == [0, 0, 0, 0]


def test_channels_compose_after_local_pose_assembly():
    v = DATA["pose"]["channels"]
    # Closed-form rotation about Z of an invented parent; child is identity.
    z, w = (Fraction(str(v["rotations"][0][i])) for i in (2, 3))
    cosine, sine = 1 - 2 * z * z, 2 * z * w
    x, y, z = v["translations"][1]
    px, py, pz = v["translations"][0]
    matrix = [
        cosine,
        sine,
        0,
        0,
        -sine,
        cosine,
        0,
        0,
        0,
        0,
        1,
        0,
        px + cosine * x - sine * y,
        py + sine * x + cosine * y,
        pz + z,
        1,
    ]
    assert matrix == [Fraction(str(n)) for n in v["expected_child_matrix_columns"]]
    assert v["evaluation_order"] == [v["owners"][1], v["owners"][0]]
    assert matrix[12:15] != [px + x, py + y, pz + z]  # model-space addition is wrong


def test_wire_lengths_and_header_offsets_without_production_encoder():
    v = DATA["wire"]
    b, f, h, vertices, indices, materials = v["counts_b_f_h_v_i_m"]
    payload_bytes = (
        16 + 8 * b + 60 + 28 * b * f + 68 * h + 28 * vertices + 2 * indices + 28 * materials
    )
    assert payload_bytes == v["payload_bytes"]
    assert v["file_bytes"] == payload_bytes + v["header_bytes"]
    header = struct.pack(
        "<8s22I",
        bytes.fromhex(v["magic_hex"]),
        b,
        f,
        h,
        vertices,
        indices,
        materials,
        3,
        DATA["ticks"],
        v["hz"],
        v["profile"],
        v["model_resource"],
        v["animation_resource"],
        payload_bytes,
        0,
        *([0] * v["reserved_words"]),
    )
    assert len(header) == 96
    assert header[:8] == b"S3RIv2\0\0" and header[:8] != b"S3RIv1\0\0"
    assert struct.unpack_from("<I", header, 32)[0] == 3
    assert struct.unpack_from("<II", header, 48) == (522, 525)
    assert struct.unpack_from("<I", header, 56)[0] == payload_bytes
    assert header[64:] == bytes(32)
