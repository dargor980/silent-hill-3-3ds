"""Synthetic integration of morph geometry, multiple CLUTs and PSMT4."""

import struct

import pytest
from test_character_mesh import mutate
from test_character_morphs import morph_model
from test_texture_probe import own_block, own_file

from tools.pipeline.decoders import ps2_morph_materials as decoder


def textured_morph(*, bpp=4, units=8, selector=7):
    raw = bytearray(morph_model())
    table = len(raw)
    raw.extend(struct.pack("<I", 0))
    struct.pack_into("<I", raw, 32 + 13 * 4, table - 32)
    struct.pack_into("<i", raw, 516, selector)
    raw.extend(bytes(-len(raw) % 16))
    sector = len(raw)
    struct.pack_into("<3I", raw, 8, 1, sector, sector)
    block = bytearray(own_block(bpp=bpp, width=128, height=128, count=units))
    block[26] = {4: 2, 8: 1}[bpp]
    raw.extend(own_file(bytes(block)))
    return bytes(raw), sector, table


@pytest.mark.parametrize(("bpp", "units", "selector"), [(4, 8, 7), (8, 8, 3), (8, 4, 4)])
def test_morphs_and_selector_are_preserved(bpp, units, selector):
    raw, sector, _ = textured_morph(bpp=bpp, units=units, selector=selector)
    result = decoder.decode_morph_materials(raw)
    assert result.sector_offset == sector and result.image_table == (0,)
    assert result.geometry.mesh.texture_descriptors == ((0, selector),)
    assert len(result.geometry.targets) == 1 and result.geometry.references[0][0].count == 3
    assert result.images[0].bpp == bpp and selector in result.images[0].selectors
    assert result.headers[0][:48] == raw[sector + 32 : sector + 80]


@pytest.mark.parametrize(
    ("kind", "value", "error"),
    [
        ("count", 0, "CT_IMAGE_COUNT"),
        ("count", 17, "CT_IMAGE_COUNT"),
        ("count", 2, "CT_IMAGE_COUNT"),
        ("sector", 33, "CM_SECTION_RANGE"),
        ("sector", 1 << 24, "CM_SECTION_RANGE"),
        ("table", 1, "CM_SECTION_RANGE"),
        ("table_value", 1, "CT_IMAGE_TABLE_VARIANT"),
        ("palette", 8, "CT_PALETTE_REFERENCE"),
        ("shift", 1, "CT_TRANSFER_VARIANT"),
        ("padding", 0, "CT_TRANSFER_VARIANT"),
    ],
)
def test_invalid_layouts(kind, value, error):
    raw, sector, table = textured_morph()
    at, code = {
        "count": (8, "I"),
        "sector": (12, "I"),
        "table": (84, "I"),
        "table_value": (table, "I"),
        "palette": (516, "i"),
        "shift": (sector + 58, "B"),
        "padding": (sector + 45, "B"),
    }[kind]
    with pytest.raises(ValueError, match=error):
        decoder.decode_morph_materials(mutate(raw, at, "<" + code, value))


def test_missing_cbp_selector_in_short_clut_is_rejected():
    raw, _, _ = textured_morph(units=4, selector=2)
    with pytest.raises(ValueError, match="CT_PALETTE_REFERENCE"):
        decoder.decode_morph_materials(raw)


def test_pixel_budget_precedes_decoding(monkeypatch):
    raw, _, _ = textured_morph()
    monkeypatch.setattr(decoder, "MAX_PIXELS", 1)
    monkeypatch.setattr(decoder, "decode_indexed", lambda *_: pytest.fail("pixels before budget"))
    with pytest.raises(ValueError, match="CT_PIXEL_BUDGET"):
        decoder.decode_morph_materials(raw)


def test_image_table_cannot_alias_a_valid_zero_descriptor():
    raw, _, _ = textured_morph()
    with pytest.raises(ValueError, match="CM_SECTION_OVERLAP"):
        decoder.decode_morph_materials(mutate(raw, 84, "<I", 480))


@pytest.mark.parametrize("delta", (-1, -4096, 1))
def test_texture_sector_is_exact(delta):
    raw, _, _ = textured_morph()
    with pytest.raises(ValueError):
        decoder.decode_morph_materials(raw[:delta] if delta < 0 else raw + b"x")
