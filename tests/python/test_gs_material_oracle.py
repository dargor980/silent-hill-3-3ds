"""Synthetic GS states and pixels: no game assets or external renderer needed."""

import pytest

from tools.qa.gs_material_oracle import (
    decode_draw_state,
    require_character_profile,
    sample_bilinear,
    shade_opaque,
)


def registers(context=0):
    # Independent synthetic addresses; observed material mode encoded by fields.
    c = context
    return {
        0: 4 | 1 << 3 | 1 << 4 | 1 << 5 | c << 9,
        0x1A: 1,
        6 + c: 64 | 8 << 14 | 19 << 20 | 9 << 26 | 9 << 30 | 1 << 34 | 2048 << 37 | 1 << 61,
        0x14 + c: 1 | 1 << 5 | 1 << 6,
        8 + c: 2 | 2 << 2 | 511 << 14 | 511 << 34,
        0x47 + c: 1 << 1 | 1 << 16 | 2 << 17,
        0x42 + c: 1 << 2 | 1 << 6,
        0x4C + c: 8 << 16,
        0x4E + c: 128 | 10 << 24,
        0x4A + c: 0,
        0x49: 0,
        0x45: 0,
        0x46: 1,
        0x3D: 0,
        0x3B: 128 | 128 << 32,
    }


@pytest.mark.parametrize("context", [0, 1])
def test_context_selection_and_enabled_states(context):
    s = require_character_profile(registers(context))
    assert s["primitive"]["context"] == context
    assert s["texture"]["tbp"] == 64 and s["texture"]["cbp"] == 2048
    assert s["texture"]["cld"] == 1 and s["texture"]["csm"] == 0
    assert s["primitive"]["abe"] == s["test"]["ate"] == s["test"]["date"] == 0
    assert s["depth"]["mask"] == s["frame"]["mask"] == 0
    assert s["test"]["ztst"] == 2


@pytest.mark.parametrize(
    "reg,bit",
    [
        (0, 6),
        (0, 8),
        (6, 35),
        (6, 55),
        (6, 56),
        (6, 61),
        (0x14, 5),
        (0x14, 2),
        (8, 0),
        (8, 14),
        (0x47, 0),
        (0x47, 14),
        (0x47, 17),
        (0x42, 0),
        (0x4C, 32),
        (0x4E, 32),
        (0x4A, 0),
        (0x49, 0),
        (0x45, 0),
        (0x46, 0),
        (0x3D, 0),
        (0x3B, 0),
    ],
)
def test_material_variants_require_a_separate_recipe(reg, bit):
    r = registers()
    r[reg] ^= 1 << bit
    with pytest.raises(ValueError, match="Unsupported"):
        require_character_profile(r)


def test_missing_register_and_prmode_do_not_get_defaults():
    r = registers()
    del r[0x47]
    with pytest.raises(ValueError, match="register 47"):
        decode_draw_state(r)
    r[0x1A] = 0
    with pytest.raises(ValueError, match="PRMODE"):
        decode_draw_state(r)


@pytest.mark.parametrize("bad", [-1, 1 << 64, True, 0.0, None])
def test_invalid_register_word(bad):
    r = registers()
    r[6] = bad
    with pytest.raises(ValueError, match="register 06"):
        decode_draw_state(r)


TEXTURE = bytes([0, 32, 64, 0, 128, 64, 32, 128, 64, 128, 0, 64, 255, 0, 128, 128])


def test_pixel_centers_clamp_and_fractional_bilinear():
    assert sample_bilinear(TEXTURE, 2, 2, 0.5, 0.5) == (0, 32, 64, 0)
    assert sample_bilinear(TEXTURE, 2, 2, 99, -99) == (128, 64, 32, 128)
    assert sample_bilinear(TEXTURE, 2, 2, 1, 1) == (111, 56, 56, 80)
    # Fractions below 1/16 do not move to the next interpolation step.
    assert sample_bilinear(TEXTURE, 2, 2, 0.55, 0.5) == (0, 32, 64, 0)
    assert sample_bilinear(TEXTURE, 2, 2, 0.5625, 0.5) == (8, 34, 62, 8)


@pytest.mark.parametrize(
    "width,height,data,u,v",
    [
        (0, 2, TEXTURE, 0, 0),
        (2, 2, TEXTURE[:-1], 0, 0),
        (1025, 1, b"", 0, 0),
        (True, 2, TEXTURE, 0, 0),
        (2, 2, TEXTURE, float("nan"), 0),
        (2, 2, TEXTURE, 0, float("inf")),
    ],
)
def test_invalid_sampling_inputs(width, height, data, u, v):
    with pytest.raises(ValueError):
        sample_bilinear(data, width, height, u, v)


def test_zero_alpha_writes_color_and_alpha_without_blending():
    assert shade_opaque((128, 64, 32, 0), (128, 64, 128, 125), 255) == (127, 31, 31, 0)
    assert shade_opaque((128, 64, 32, 128), (128, 64, 128, 125), 255) == (127, 31, 31, 125)


def test_modulation_saturates_before_black_fog_and_preserves_alpha():
    assert shade_opaque((255, 128, 64, 128), (255, 128, 64, 124), 128) == (127, 64, 16, 124)
    assert shade_opaque((255, 128, 64, 128), (255, 128, 64, 124), 0) == (0, 0, 0, 124)
    assert shade_opaque((128, 128, 128, 128), (10.5, 20.5, 30.5, 124.5), 255) == (9, 19, 29, 124)


@pytest.mark.parametrize(
    "texel,color,fog",
    [
        ((0, 0, 0), (128,) * 4, 255),
        ((0, 0, 0, 256), (128,) * 4, 255),
        ((0, 0, 0, 0), (128,) * 3, 255),
        ((0, 0, 0, 0), (float("nan"),) * 4, 255),
        ((0, 0, 0, 0), (128,) * 4, -1),
        ((0, 0, 0, 0), (128,) * 4, True),
    ],
)
def test_invalid_shading_inputs(texel, color, fog):
    with pytest.raises(ValueError):
        shade_opaque(texel, color, fog)
