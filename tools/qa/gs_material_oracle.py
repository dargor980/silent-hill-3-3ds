"""Pure, bounded reference for CT-T4's observed GS material.

No renderer, file I/O or game constants. Vertex lighting is an input: this
module does not infer it from the material. See ps2-character-materials-v1.md.
"""

import math
from collections.abc import Mapping, Sequence


def decode_draw_state(registers: Mapping[int, int]) -> dict:
    """Decode effective context registers; TEX2 must already be resolved."""

    def word(reg):
        value = registers.get(reg)
        if type(value) is not int or not 0 <= value < 1 << 64:
            raise ValueError(f"Missing or invalid GS register {reg:02x}")
        return value

    def fields(reg, layout):
        value = word(reg)
        return {name: (value >> bit) & ((1 << size) - 1) for name, bit, size in layout}

    if word(0x1A) != 1:
        raise ValueError("PRMODE-controlled draws require a separate profile")
    prim = fields(
        0,
        [
            ("type", 0, 3),
            ("iip", 3, 1),
            ("tme", 4, 1),
            ("fge", 5, 1),
            ("abe", 6, 1),
            ("aa1", 7, 1),
            ("fst", 8, 1),
            ("context", 9, 1),
        ],
    )
    c = prim["context"]
    return dict(
        primitive=prim,
        texture=fields(
            6 + c,
            [
                ("tbp", 0, 14),
                ("tbw", 14, 6),
                ("psm", 20, 6),
                ("tw", 26, 4),
                ("th", 30, 4),
                ("tcc", 34, 1),
                ("tfx", 35, 2),
                ("cbp", 37, 14),
                ("cpsm", 51, 4),
                ("csm", 55, 1),
                ("csa", 56, 5),
                ("cld", 61, 3),
            ],
        ),
        filter=fields(
            0x14 + c,
            [
                ("lcm", 0, 1),
                ("mxl", 2, 3),
                ("mmag", 5, 1),
                ("mmin", 6, 3),
                ("mtba", 9, 1),
                ("l", 19, 2),
                ("k", 32, 12),
            ],
        ),
        clamp=fields(
            8 + c,
            [
                ("wms", 0, 2),
                ("wmt", 2, 2),
                ("minu", 4, 10),
                ("maxu", 14, 10),
                ("minv", 24, 10),
                ("maxv", 34, 10),
            ],
        ),
        test=fields(
            0x47 + c,
            [
                ("ate", 0, 1),
                ("atst", 1, 3),
                ("aref", 4, 8),
                ("afail", 12, 2),
                ("date", 14, 1),
                ("datm", 15, 1),
                ("zte", 16, 1),
                ("ztst", 17, 2),
            ],
        ),
        alpha=fields(
            0x42 + c, [("a", 0, 2), ("b", 2, 2), ("c", 4, 2), ("d", 6, 2), ("fix", 32, 8)]
        ),
        frame=fields(0x4C + c, [("fbp", 0, 9), ("fbw", 16, 6), ("psm", 24, 6), ("mask", 32, 32)]),
        depth=fields(0x4E + c, [("zbp", 0, 9), ("psm", 24, 4), ("mask", 32, 1)]),
        fba=word(0x4A + c),
        pabe=word(0x49),
        dither=word(0x45),
        color_clamp=word(0x46),
        fog_color=word(0x3D),
        texa=word(0x3B),
    )


def require_character_profile(registers: Mapping[int, int]) -> dict:
    """Reject state changes instead of silently applying the CT-T4 recipe."""
    state = decode_draw_state(registers)
    expected = {
        "primitive": dict(type=4, iip=1, tme=1, fge=1, abe=0, aa1=0, fst=0),
        "texture": dict(tbw=8, psm=19, tw=9, th=9, tcc=1, tfx=0, cpsm=0, csm=0, csa=0, cld=1),
        "filter": dict(lcm=1, mxl=0, mmag=1, mmin=1, mtba=0, l=0, k=0),
        "clamp": dict(wms=2, wmt=2, minu=0, maxu=511, minv=0, maxv=511),
        "test": dict(ate=0, atst=1, aref=0, afail=0, date=0, datm=0, zte=1, ztst=2),
        "alpha": dict(a=0, b=1, c=0, d=1, fix=0),
        "frame": dict(psm=0, mask=0),
        "depth": dict(psm=10, mask=0),
    }
    for section, values in expected.items():
        if any(state[section][name] != value for name, value in values.items()):
            raise ValueError(f"Unsupported character material: {section}")
    for name, value in dict(
        fba=0, pabe=0, dither=0, color_clamp=1, fog_color=0, texa=0x8000000080
    ).items():
        if state[name] != value:
            raise ValueError(f"Unsupported character material: {name}")
    return state


def sample_bilinear(rgba: bytes, width: int, height: int, u: float, v: float) -> tuple:
    """GS 4-bit bilinear fractions, texel coordinates, clamp to full image."""
    if (
        type(width) is not int
        or type(height) is not int
        or not 1 <= width <= 1024
        or not 1 <= height <= 1024
        or not isinstance(rgba, bytes)
        or len(rgba) != width * height * 4
    ):
        raise ValueError("Invalid RGBA extent")
    if any(type(x) not in (float, int) or not math.isfinite(x) for x in (u, v)):
        raise ValueError("Invalid texture coordinate")
    u, v = u - 0.5, v - 0.5
    x, y = math.floor(u), math.floor(v)
    fu, fv = math.floor((u - x) * 16), math.floor((v - y) * 16)

    def texel(x, y):
        offset = (min(height - 1, max(0, y)) * width + min(width - 1, max(0, x))) * 4
        return rgba[offset : offset + 4]

    a, b, c, d = texel(x, y), texel(x + 1, y), texel(x, y + 1), texel(x + 1, y + 1)

    def lerp(a, b, f):
        return a + (b - a) * f // 16

    return tuple(lerp(lerp(a[i], b[i], fu), lerp(c[i], d[i], fu), fv) for i in range(4))


def shade_opaque(texel: Sequence[int], vertex_rgba: Sequence[float], fog: float) -> tuple:
    """MODULATE /128, black fog /256; alpha is stored, never blended/discarded.

    Interpolants retain seven fractional bits for color and fog. This reference
    omits rasterizer edge fill and SIMD interpolation roundoff (declared by audit).
    """
    if len(texel) != 4 or any(type(x) is not int or not 0 <= x <= 255 for x in texel):
        raise ValueError("Invalid texel")
    if len(vertex_rgba) != 4 or any(
        type(x) not in (float, int) or not math.isfinite(x) or not 0 <= x <= 255
        for x in (*vertex_rgba, fog)
    ):
        raise ValueError("Invalid color or fog")
    modulated = [
        min(255, t * math.trunc(c * 128) // 16384) for t, c in zip(texel, vertex_rgba, strict=True)
    ]
    return tuple(c * math.trunc(fog * 128) // 32768 for c in modulated[:3]) + (modulated[3],)
