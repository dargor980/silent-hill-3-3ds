"""Independent invented SRI2 bytes; no imports from producers or readers."""

import struct
import zlib


def own_sri2():
    bones = (
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        21,
        24,
        25,
        26,
        27,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
    )
    upper = {1, 3, 5, 7, 8, 10, 12, 13, 14, 16, 17, 21, 27, 33, 35}
    payload = bytearray(struct.pack("<4f36i", 1, -2, 3, 0.01, -1, -1, *([1] * 34)))
    for b in bones:
        payload.extend(struct.pack("<HBB", b, 2 if b in upper else 1, 0))
    for c in (
        (101, 10, 307, 0, 9, 1, 0, 0, 0),
        (109, 24, 1996, 80, 103, 1, 0, 10, 0),
        (113, 24, 2227, 176, 199, 1, 0, 34, 0),
    ):
        payload.extend(struct.pack("<HHhHHBBII", *c))
    for source in (*range(10), *range(80, 104), *range(176, 200)):
        for b in bones:
            payload.extend(struct.pack("<7f", (source + b) / 16, -b / 32, -0.0, 0, 0, 0.6, 0.8))
    for b in (1, 35):
        payload.extend(struct.pack("<I16f", b, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 2, -3, 4, 1))
    for i in range(3):
        payload.extend(
            struct.pack(
                "<8h3H4BH",
                16 + i,
                -16,
                32,
                0,
                4096,
                0,
                -4096,
                4096,
                1366,
                1365,
                1364,
                35,
                3,
                0,
                1,
                0,
            )
        )
    payload.extend(struct.pack("<6H", 0, 1, 2, 2, 1, 0))
    files = {}
    for i in range(2):
        raw = bytes((17 + i, 31 + i, 67 + i, 128)) * 128 * 256
        files[f"texture-{i:02}.rgba"] = raw
        payload.extend(struct.pack("<7I", i * 3, 3, i, 128, 256, i, zlib.crc32(raw)))
    files["heather.sri"] = (
        struct.pack(
            "<8s22I",
            b"S3RIv2\0\0",
            36,
            58,
            2,
            3,
            6,
            2,
            3,
            2,
            25,
            1,
            522,
            525,
            len(payload),
            zlib.crc32(payload),
            *([0] * 8),
        )
        + payload
    )
    return files


def changed(raw, offset, fmt, *values, fix_crc=True):
    out = bytearray(raw)
    struct.pack_into("<" + fmt, out, offset, *values)
    if fix_crc and offset >= 96:
        struct.pack_into("<I", out, 60, zlib.crc32(out[96:]))
    return bytes(out)


def invalid_sri2(raw):
    for at, value in (
        (0, 0),
        (8, 0),
        (8, 73),
        (12, 57),
        (16, 129),
        (20, 2),
        (20, 8193),
        (24, 2),
        (24, 4),
        (24, 18001),
        (28, 0),
        (28, 17),
        (32, 2),
        (36, 1),
        (40, 30),
        (44, 2),
        (48, 523),
        (52, 526),
        (56, 0),
        (56, 0xFFFFFFFF),
        (60, 0),
    ):
        yield f"header-{at}-{value}", changed(raw, at, "I", value)
    yield "SRI1", raw[:4] + b"v1" + raw[6:]
    yield "trailer", raw + b"\0"
    yield "crc", changed(raw, 460, "I", 1, fix_crc=False)
    for at in range(64, 96):
        yield f"reserved-{at}", changed(raw, at, "B", 1)
    for b in range(36):
        for offset, fmt, value in (
            (112 + 4 * b, "i", b),
            (256 + 4 * b, "H", 73),
            (258 + 4 * b, "B", 3),
            (259 + 4 * b, "B", 1),
        ):
            yield f"bone-{offset}", changed(raw, offset, fmt, value)
    for at in range(400, 460):
        yield f"descriptor-{at}", changed(raw, at, "B", raw[at] ^ 1)
    for at in (96, 100, 104, 460, 460 + 28 * 36 * 57):
        for bits in (0x7FC00000, 0x7F800000, 0xFF800000, 0x47C35080):
            yield f"number-{at}-{bits}", changed(raw, at, "I", bits)
    for scale in (0.0, -1.0, 1.1, float("nan")):
        yield f"scale-{scale}", changed(raw, 108, "f", scale)
    for q in ((0, 0, 0, 0), (0, 0, 0, 1.002), (0, 0, 0.2, 0.8), (float("nan"), 0, 0, 1)):
        yield f"quaternion-{q}", changed(raw, 472, "4f", *q)
    helpers = 460 + 28 * 36 * 58
    vertices = helpers + 2 * 68
    indices = vertices + 3 * 28
    materials = indices + 12
    for at, fmt, value in (
        (helpers, "I", 36),
        (helpers + 4, "f", float("inf")),
        (helpers + 16, "f", 1),
        (helpers + 64, "f", 0),
        (vertices + 16, "H", 4097),
        (vertices + 16, "H", 0),
        (vertices + 22, "B", 36),
        (vertices + 23, "B", 0),
        (vertices + 23, "B", 4),
        (vertices + 23, "B", 2),
        (vertices + 24, "B", 2),
        (vertices + 26, "H", 1),
        (indices, "H", 3),
        (materials, "I", 3),
        (materials + 4, "I", 0),
        (materials + 4, "I", 4),
        (materials + 4, "I", 0xFFFFFFFF),
        (materials + 8, "I", 1),
        (materials + 12, "I", 127),
        (materials + 16, "I", 1025),
        (materials + 20, "I", 2),
        (materials + 28, "I", 0),
    ):
        yield f"geometry-{at}-{value}", changed(raw, at, fmt, value)
    blend = changed(raw, materials + 20, "I", 1)
    yield "blend-order", changed(blend, materials + 48, "I", 0)
    # One fewer material, with a consistent header and CRC, leaves uncovered indices.
    short = bytearray(raw[:-28])
    struct.pack_into("<I", short, 28, 1)
    struct.pack_into("<II", short, 56, len(short) - 96, zlib.crc32(short[96:]))
    yield "material-coverage", bytes(short)
    for at in (
        1,
        64,
        95,
        96,
        111,
        255,
        399,
        459,
        460,
        helpers - 1,
        helpers,
        vertices - 1,
        vertices,
        indices - 1,
        indices,
        materials - 1,
        len(raw) - 1,
    ):
        yield f"truncated-{at}", raw[:at]
