"""Validate HRC literals before HM-T4b.2; no native-contact success is implied."""

import copy
import json
import struct
from fractions import Fraction
from pathlib import Path

import pytest

from tests.python.helpers.heather_room_contact_oracle import (
    observe,
    prepare,
    rational,
    scalar_bits,
    touches_rectangle,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/synthetic/heather-room-contacts-v1.json"
DATA = json.loads(FIXTURE.read_text())
SCENES = DATA["scenes"]
QUERIES = DATA["queries"]
BY_ID = {row["id"]: row for row in QUERIES}


def test_fixture_identity_and_coverage():
    assert DATA["schema"] == "heather-room-contacts-v1"
    assert DATA["provenance"] == "authored_synthetic_no_game_assets"
    assert len(BY_ID) == len(QUERIES) == 96
    assert len({row["id"] for row in DATA["preparation"]}) == 30
    assert len(bytes.fromhex(DATA["output_sentinel_hex"])) == 12
    assert {row["expected"]["result"] for row in QUERIES} == {
        "ok",
        "unavailable",
        "invalid_query",
        "out_of_bounds",
        "off_floor",
        "invalid_start",
    }
    assert {row["expected"] for row in DATA["preparation"]} == {
        "ok",
        "unsupported_profile",
        "capacity_exceeded",
        "budget_exceeded",
        "invalid_geometry",
        "empty_floor",
    }
    assert all(prepare(scene) == "ok" for scene in SCENES.values())
    profile = json.loads((ROOT / "schemas/heather-room-profile-v1.json").read_text())
    assert profile["contacts"]["profile"] == SCENES["base"]["profile"]
    assert profile["contacts"]["footprint_half_extent"] == 175
    assert profile["contacts"]["guard"] == 1
    assert profile["contacts"]["expected_blockers"] == 32
    assert profile["budgets"]["contact_working_bytes"] == 4096


@pytest.mark.parametrize("row", DATA["preparation"], ids=lambda row: row["id"])
def test_preparation_literals(row):
    scene = copy.deepcopy(SCENES[row["scene"]])
    scene.update(row["replace"])
    before = copy.deepcopy(scene)
    assert prepare(scene, **row["accounting"]) == row["expected"]
    assert row["publish"] is (row["expected"] == "ok")
    assert scene == before


@pytest.mark.parametrize("row", QUERIES, ids=lambda row: row["id"])
def test_query_literals_with_independent_edges(row):
    before = copy.deepcopy(row)
    assert observe(SCENES[row["scene"]], row) == row["expected"]
    assert row == before
    assert 0 <= row["ordinal"] <= 4294967295
    assert len(row["from"]) == len(row["requested"]) == 3


@pytest.mark.parametrize("row", QUERIES, ids=lambda row: row["id"])
def test_ordinal_and_blocker_order_do_not_affect_predicate(row):
    scene = copy.deepcopy(SCENES[row["scene"]])
    scene["blockers"].reverse()
    for ordinal in (0, 4294967295):
        assert observe(scene, dict(row, ordinal=ordinal)) == row["expected"]


@pytest.mark.parametrize(
    "name",
    [
        "cross_free_endpoints",
        "oblique_crossing",
        "oblique_clear",
        "corner_tangent",
        "corner_gap_one_ulp",
        "face_tangent",
        "face_outside_one_ulp",
        "point_tangent",
        "subnormal_crossing",
        "no_round_expansion",
    ],
)
def test_segment_symmetry_when_both_endpoints_are_valid(name):
    row = BY_ID[name]
    scene = SCENES[row["scene"]]
    end = dict(row, **{"from": row["requested"]})
    if observe(scene, end)["result"] != "ok":
        # Crossing into the subnormal-width obstacle deliberately has an invalid endpoint.
        assert name == "subnormal_crossing"
        return
    reversed_row = dict(row, **{"from": row["requested"], "requested": row["from"]})
    assert observe(scene, reversed_row) == row["expected"]


@pytest.mark.parametrize(
    "name",
    [
        "free_straight",
        "cross_free_endpoints",
        "corner_tangent",
        "corner_gap_one_ulp",
        "face_tangent",
        "endpoint_contact",
        "start_on_face",
        "floor_outside_one_ulp",
    ],
)
def test_swapping_x_and_z_preserves_geometry(name):
    row = copy.deepcopy(BY_ID[name])
    scene = copy.deepcopy(SCENES[row["scene"]])
    scene["floor"] = scene["floor"][2:] + scene["floor"][:2]
    scene["blockers"] = [box[2:] + box[:2] for box in scene["blockers"]]
    scene["origin"].reverse()
    row["from"].reverse()
    row["requested"].reverse()
    assert observe(scene, row) == row["expected"]


def test_exact_corner_parameter_and_adjacent_gap():
    row = BY_ID["corner_tangent"]
    a, b = ([rational(v) for v in row[key]] for key in ("from", "requested"))
    t = Fraction(81, 137)
    assert tuple(a[k] + t * (b[k] - a[k]) for k in (0, 2)) == (-176, -276)
    assert BY_ID["corner_gap_one_ulp"]["expected"]["copy_from"] == "requested"
    assert BY_ID["corner_inside_one_ulp"]["expected"]["copy_from"] == "from"


def test_endpoint_only_or_open_boundary_mutants_would_disagree():
    row = BY_ID["cross_free_endpoints"]
    for endpoint in ("from", "requested"):
        null_query = dict(row, **{"from": row[endpoint], "requested": row[endpoint]})
        assert observe(SCENES["base"], null_query)["blocked"] is False
    assert row["expected"]["blocked"] is True
    tangent = BY_ID["face_tangent"]
    assert rational(tangent["from"][2]) == 100 + 176
    assert tangent["expected"]["blocked"] is True


def test_no_binary64_rounding_or_flush_to_zero_in_predicates():
    tiny = rational("f32:00000001")
    assert tiny == Fraction(1, 2**149)
    assert tiny - 176 > -176
    assert float(tiny) - 176 == -176  # A double-expanded box falsely rejects this spawn.
    assert BY_ID["no_round_expansion"]["expected"]["result"] == "ok"
    assert BY_ID["subnormal_outside"]["expected"]["result"] == "ok"
    assert BY_ID["negative_zero_on_box"]["expected"]["result"] == "invalid_start"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("signed_zero_free", [0xC3480000, 0, 0x80000000]),
        ("signed_zero_block", [0xC3FA0000, 0x80000000, 0x80000000]),
        ("signed_zero_null", [0xC3FA0000, 0, 0x80000000]),
    ],
)
def test_output_copy_rule_has_explicit_signed_zero_bits(name, expected):
    row = BY_ID[name]
    selected = row[row["expected"]["copy_from"]]
    assert [scalar_bits(value) for value in selected] == expected


def test_translated_inputs_and_origin_metadata():
    for local_id, world_id in [
        ("cross_free_endpoints", "translated_crossing"),
        ("free_straight", "translated_free"),
    ]:
        local, world = BY_ID[local_id], BY_ID[world_id]
        for key in ("from", "requested"):
            assert [
                rational(b) - rational(a) for a, b in zip(local[key], world[key], strict=True)
            ] == [100000, 0, 140000]
        assert local["expected"] == world["expected"]
    assert BY_ID["origin_not_added"]["expected"] == BY_ID["free_straight"]["expected"]


def test_integer_width_derivation_against_fraction_decoder():
    # This validates the proposed encoding bound, not native limb arithmetic.
    for exponent in range(147):
        for mantissa in (0, 1, 0x7FFFFF):
            for sign in (0, 1):
                bits = (sign << 31) | (exponent << 23) | mantissa
                value = rational(f"f32:{bits:08x}")
                if abs(value) > 1_000_000:
                    continue
                integer = mantissa if exponent == 0 else ((1 << 23) + mantissa) << (exponent - 1)
                integer *= -1 if sign else 1
                assert Fraction(integer, 2**149) == value
                assert abs(integer).bit_length() <= 169
    largest_difference = (2_000_000 + 176) << 149
    assert largest_difference.bit_length() == 170 < 192
    assert (largest_difference**2).bit_length() == 340 < 352


@pytest.mark.parametrize(
    "value", [0.1, True, 16777217, "NaN", "f32:0", "f32:xxxxxxxx", "f32:-0000001", "f32:0000_001"]
)
def test_fixture_decoder_rejects_ambiguous_scalars(value):
    with pytest.raises((ValueError, struct.error)):
        scalar_bits(value)


@pytest.mark.parametrize(
    "a,b,box,expected",
    [
        ((-2, 0), (2, 0), (0, 0, -1, 1), True),
        ((-2, 0), (2, 0), (0, 0, 0, 0), True),
        ((-2, 1), (2, 1), (0, 0, 0, 0), False),
        ((0, 0), (0, 0), (0, 1, 0, 1), True),
        ((-1, -1), (-1, -1), (0, 1, 0, 1), False),
        ((2, 2), (3, 3), (0, 1, 0, 1), False),
        ((-2, 1), (2, 1), (0, 1, 0, 1), True),
    ],
)
def test_oracle_elementary_closed_edge_controls(a, b, box, expected):
    assert touches_rectangle(a, b, box) is expected
