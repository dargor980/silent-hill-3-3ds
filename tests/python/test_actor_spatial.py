"""Synthetic actor prefixes, with independent literal offsets and matrix columns."""

import struct
from dataclasses import FrozenInstanceError

import pytest

from tools.inspectors.actor_spatial import inspect_actor_spatial


def block():
    # Asymmetric, exact quarter-turn and translation; not taken from any game.
    header = bytes.fromhex("102030405060708090a0b0c03412d0e0f0010203")
    spatial = struct.pack("<11f", 1, 1, 1, 3, -5, 7, 1, 0, 0.5, 0, 0)
    columns = struct.pack("<16f", 0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 3, -5, 7, 1)
    return header + spatial + columns


def replace_word(raw, offset, word):
    return raw[:offset] + word + raw[offset + 4 :]


def test_exact_layout_raw_fields_and_immutability():
    raw = block()
    item = inspect_actor_spatial(raw, expected_kind=0x1234)
    assert item.kind == 0x1234 and item.scale == (1, 1, 1)
    assert item.position == (3, -5, 7, 1) and item.rotation == (0, 0.5, 0, 0)
    assert item.matrix_columns == (0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 3, -5, 7, 1)
    assert item.observations == () and item.raw == raw
    rebuilt = raw[:20] + struct.pack(
        "<27f", *item.scale, *item.position, *item.rotation, *item.matrix_columns
    )
    assert rebuilt == raw
    with pytest.raises(FrozenInstanceError):
        item.position = (0, 0, 0, 1)


@pytest.mark.parametrize("size", list(range(128)) + [129, 256, 4096])
def test_truncation_and_extra_data_rejected(size):
    with pytest.raises(ValueError, match="128 immutable"):
        inspect_actor_spatial((block() + bytes(4096))[:size], expected_kind=0x1234)


@pytest.mark.parametrize("data", [None, "", 128, bytearray(128), memoryview(bytes(128))])
def test_nonimmutable_bytes_rejected(data):
    with pytest.raises(ValueError, match="128 immutable"):
        inspect_actor_spatial(data, expected_kind=0x1234)


@pytest.mark.parametrize("kind", [True, False, 1.0, None, "4660", 0, -1, 65536])
def test_invalid_expected_kind_rejected(kind):
    with pytest.raises(ValueError, match="range"):
        inspect_actor_spatial(block(), expected_kind=kind)


def test_wrong_kind_and_byte_order_rejected():
    for kind in (1, 0x3412, 0x1235, 65535):
        with pytest.raises(ValueError, match="mismatch"):
            inspect_actor_spatial(block(), expected_kind=kind)
    for kind in (1, 65535):
        raw = block()[:12] + struct.pack("<H", kind) + block()[14:]
        assert inspect_actor_spatial(raw, expected_kind=kind).kind == kind


@pytest.mark.parametrize("offset", range(20, 128, 4))
@pytest.mark.parametrize("word", ["0000807f", "000080ff", "0100c07f"])
def test_each_float_rejects_infinity_and_nan(offset, word):
    raw = replace_word(block(), offset, bytes.fromhex(word))
    with pytest.raises(ValueError, match="Nonfinite"):
        inspect_actor_spatial(raw, expected_kind=0x1234)


@pytest.mark.parametrize(
    "offset,value,observations",
    [
        (20, 2, ("non_unit_scale",)),
        (24, -1, ("non_unit_scale",)),
        (28, 0, ("non_unit_scale",)),
        (44, 0.5, ("non_unit_position_w", "matrix_translation_differs")),
        (48, 0.25, ("nonzero_rotation_xz",)),
        (56, -0.25, ("nonzero_rotation_xz",)),
        (60, 1, ("nonzero_rotation_w",)),
        (76, 0.5, ("non_affine_matrix",)),
        (92, 0.5, ("non_affine_matrix",)),
        (108, 0.5, ("non_affine_matrix",)),
        (124, 0.5, ("non_affine_matrix", "matrix_translation_differs")),
        (112, 99, ("matrix_translation_differs",)),
    ],
)
def test_semantic_differences_are_preserved(offset, value, observations):
    raw = replace_word(block(), offset, struct.pack("<f", value))
    result = inspect_actor_spatial(raw, expected_kind=0x1234)
    assert result.raw == raw and result.observations == observations


def test_multiple_observations_keep_contract_order_without_repair():
    raw = block()
    for offset, value in ((20, -1), (44, 2), (48, 1), (60, 1), (76, 1)):
        raw = replace_word(raw, offset, struct.pack("<f", value))
    item = inspect_actor_spatial(raw, expected_kind=0x1234)
    assert item.observations == (
        "non_unit_scale",
        "non_unit_position_w",
        "nonzero_rotation_xz",
        "nonzero_rotation_w",
        "non_affine_matrix",
        "matrix_translation_differs",
    )
    assert item.raw == raw and item.scale[0] == -1 and item.position[3] == 2


def test_bitwise_translation_comparison_preserves_negative_zero():
    raw = replace_word(block(), 32, bytes.fromhex("00000000"))
    raw = replace_word(raw, 112, bytes.fromhex("00000080"))
    item = inspect_actor_spatial(raw, expected_kind=0x1234)
    assert item.position[0] == item.matrix_columns[12] == 0
    assert item.observations == ("matrix_translation_differs",)
    assert struct.pack("<f", item.matrix_columns[12]) == bytes.fromhex("00000080")
    raw = replace_word(raw, 32, bytes.fromhex("00000080"))
    assert inspect_actor_spatial(raw, expected_kind=0x1234).observations == ()


def test_finite_extremes_and_subnormals_are_not_clamped():
    raw = replace_word(block(), 32, bytes.fromhex("ffff7f7f"))
    raw = replace_word(raw, 112, bytes.fromhex("ffff7f7f"))
    raw = replace_word(raw, 52, bytes.fromhex("01000000"))
    item = inspect_actor_spatial(raw, expected_kind=0x1234)
    assert item.position[0] > 1e38 and 0 < item.rotation[1] < 1e-40
    assert item.raw == raw and item.observations == ()


def test_inventory_does_not_claim_rigidity_or_derive_a_matrix_from_yaw():
    for offset, value in ((64, 2), (72, 1)):  # shear and reflection, retained
        raw = replace_word(block(), offset, struct.pack("<f", value))
        item = inspect_actor_spatial(raw, expected_kind=0x1234)
        assert item.matrix_columns[(offset - 64) // 4] == value
        assert item.observations == () and item.raw == raw
        assert item.rotation == (0, 0.5, 0, 0)  # not repaired from matrix
