"""Independent asymmetric position/normal morph vectors and invalid boundaries."""

import struct

import pytest
from test_character_mesh import model, mutate

from tools.pipeline.decoders.ps2_character_mesh import CharacterMeshError, decode_character_mesh
from tools.pipeline.decoders.ps2_character_morphs import decode_morph_mesh


def morph_model():
    data = bytearray(model())
    # Insert an entire aligned block before the existing submesh. The model
    # base is 32; absolute layout is intentionally different from private MDLs.
    block = bytearray(128)
    struct.pack_into("<9h", block, 0, 10, 20, -30, 40, -50, 60, 70, 80, 90)
    struct.pack_into("<9h", block, 32, 4096, 0, 0, 0, -4096, 0, 0, 0, 4096)
    struct.pack_into("<2I", block, 64, 2, 576)  # target at absolute 608
    struct.pack_into("<8h", block, 80, 1, -2, 3, 2, 4, 5, -6, 0)
    struct.pack_into("<8h", block, 96, -7, 8, 9, 0, 10, -11, 12, 2)
    data[528:528] = block
    struct.pack_into("<I", data, 32 + 9 * 4, 624)
    struct.pack_into("<4I", data, 32 + 17 * 4, 3, 496, 1, 560)
    # Insert 16 bytes for refs before palettes/packet, updating offsets.
    part = 656
    data[part + 144 : part + 144] = struct.pack("<3H", 0, 6, 3) + bytes(10)
    for index in (0, 2, 8, 10, 14):
        at = part + index * 4
        struct.pack_into("<I", data, at, struct.unpack_from("<I", data, at)[0] + 16)
    struct.pack_into("<2I", data, part + 20, 1, 144)
    return bytes(data)


def test_preserves_independent_position_and_normal_sparse_orders():
    decoded = decode_morph_mesh(morph_model())
    assert decoded.base_positions_q4 == ((10, 20, -30), (40, -50, 60), (70, 80, 90))
    assert decoded.base_normals_q12[1] == (0, -4096, 0)
    assert decoded.targets[0].position_deltas == ((1, -2, 3, 2), (4, 5, -6, 0))
    assert decoded.targets[0].normal_deltas == ((-7, 8, 9, 0), (10, -11, 12, 2))
    assert decoded.targets[0].offset == 608
    ref = decoded.references[0][0]
    assert (ref.source_index, ref.vu_address, ref.count) == (0, 6, 3)
    assert decoded.mesh.submeshes[0].vertices[1].position_q4 == (16, -8, 8)
    assert decoded.mesh.submeshes[0].header_words[35] == 0xBABE


def test_legacy_profile_still_rejects_morphs():
    with pytest.raises(CharacterMeshError, match="CM_MORPH_UNSUPPORTED"):
        decode_character_mesh(morph_model())


@pytest.mark.parametrize(
    ("offset", "code", "value", "error"),
    [
        (100, "I", 0, "CM_MORPH_COUNT"),
        (100, "I", 4097, "CM_MORPH_COUNT"),
        (108, "I", 0, "CM_MORPH_COUNT"),
        (108, "I", 129, "CM_MORPH_COUNT"),
        (104, "I", 497, "CM_SECTION_RANGE"),
        (112, "I", 544, "CM_MORPH_NORMAL_LAYOUT"),
        (592, "I", 0, "CM_MORPH_DELTA_COUNT"),
        (592, "I", 4, "CM_MORPH_DELTA_COUNT"),
        (596, "I", 0xFFFFFFF0, "CM_SECTION_RANGE"),
        (596, "I", 496, "CM_SECTION_OVERLAP"),
        (614, "h", -1, "CM_MORPH_VERTEX_REFERENCE"),
        (614, "h", 3, "CM_MORPH_VERTEX_REFERENCE"),
        (614, "h", 0, "CM_MORPH_VERTEX_REFERENCE"),
        (630, "h", 2, "CM_MORPH_VERTEX_REFERENCE"),
        (676, "I", 65, "CM_MORPH_REF_COUNT"),
        (680, "I", 143, "CM_SECTION_RANGE"),
        (680, "I", 160, "CM_SECTION_OVERLAP"),
        (800, "H", 1, "CM_MORPH_REF_SOURCE"),
        (804, "H", 0, "CM_MORPH_REF_SOURCE"),
        (804, "H", 257, "CM_MORPH_REF_SOURCE"),
        (802, "H", 5, "CM_MORPH_REF_DESTINATION"),
        (802, "H", 7, "CM_MORPH_REF_DESTINATION"),
        (802, "H", 22, "CM_MORPH_REF_DESTINATION"),
    ],
)
def test_rejects_invalid_sections_and_references(offset, code, value, error):
    with pytest.raises(CharacterMeshError, match=error):
        decode_morph_mesh(mutate(morph_model(), offset, "<" + code, value))


def test_rejects_overlapping_destinations_even_with_distinct_source_ranges():
    data = mutate(morph_model(), 676, "<I", 2)
    data = mutate(data, 800, "<6H", 0, 6, 1, 1, 6, 2)
    with pytest.raises(CharacterMeshError, match="CM_MORPH_REF_OVERLAP"):
        decode_morph_mesh(data)


def test_global_morph_spans_cannot_alias_helpers_or_submeshes():
    data = mutate(morph_model(), 32 + 7 * 4, "<I", 496)
    # Aliasing positions as helper matrices is rejected before consumption.
    with pytest.raises(CharacterMeshError):
        decode_morph_mesh(data)


@pytest.mark.parametrize("end", (1, 592, 607, 631, 800, 810, 850))
def test_truncation_is_bounded(end):
    with pytest.raises(ValueError):
        decode_morph_mesh(morph_model()[:end])
