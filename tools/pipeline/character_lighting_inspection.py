"""SCL1 encoder for the verified mode-2/type-0x10 static inspection preset."""

import math
import struct
import zlib

from tools.pipeline.character_inspection import integers
from tools.pipeline.inspection_inputs import payload_crc


def vector(values, size, low, high):
    if len(values) != size or any(
        type(x) not in (float, int) or not math.isfinite(x) or not low <= x <= high for x in values
    ):
        raise ValueError("Invalid lighting vector")
    return struct.unpack(f"<{size}f", struct.pack(f"<{size}f", *values))


def encode_lighting(preset, mesh, character, clip, material):
    scm = payload_crc(character, b"S3CMv1\0\0")
    san = payload_crc(clip, b"S3ANv1\0\0")
    sct = payload_crc(material, b"S3CTv1\0\0")
    nv, ni = struct.unpack_from("<2I", character, 8)
    if not 45 <= nv <= 2048 or not 45 <= ni <= 4608 or ni % 3 or len(mesh["submeshes"]) != 15:
        raise ValueError("Unsupported lighting extent")
    if (
        len(character) != 32 + 220 + nv * 28 + ni * 2
        or len(clip) != 1248
        or struct.unpack_from("<4I", clip, 8) != (3, 24, 0x1449, 3686)
        or len(material) != 3145796
        or struct.unpack_from("<4I", material, 8) != (3, 512, 3, scm)
    ):
        raise ValueError("Lighting dependencies differ")
    counter = integers([preset["reference_counter"]], 1, 0, 98303)[0]
    t = vector(preset["model_to_capture"], 16, -100000, 100000)
    if (t[3], t[7], t[11], t[15]) != (0, 0, 0, 1):
        raise ValueError("Expected affine lighting transform")
    for c in range(3):
        for d in range(3):
            if abs(sum(t[c * 4 + r] * t[d * 4 + r] for r in range(3)) - (c == d)) > 0.002:
                raise ValueError("Expected rigid lighting transform")
    det = (
        t[0] * (t[5] * t[10] - t[9] * t[6])
        - t[4] * (t[1] * t[10] - t[9] * t[2])
        + t[8] * (t[1] * t[6] - t[5] * t[2])
    )
    if abs(det - 1) > 0.002:
        raise ValueError("Expected positive lighting basis")
    ambient = vector(preset["ambient"], 4, 0, 255)
    vector(ambient[:3], 3, 0, 16)
    if len(preset["directionals"]) != 3:
        raise ValueError("Expected three directional slots")
    values = list(t) + list(ambient)
    for light in preset["directionals"]:
        values.extend(vector(light["direction"], 3, -16, 16))
        values.extend(vector(light["color"], 4, 0, 16))
    spot = preset["spot"]
    if spot["type"] != 0x10 or type(spot["type"]) is not int:
        raise ValueError("Unsupported local light")
    for field, size, low, high in [
        ("position", 3, -100000, 100000),
        ("direction", 3, -16, 16),
        ("color", 4, 0, 16),
        ("attenuation", 4, -1000000, 1000000),
    ]:
        values.extend(vector(spot[field], size, low, high))
    payload = bytearray(struct.pack("<I55f", counter, *values))
    indices = struct.unpack_from(f"<{ni}H", character, len(character) - ni * 2)
    vertex_cursor = index_cursor = 0
    for submesh in mesh["submeshes"]:
        h = integers(submesh["header_words"], 36, 0, 0xFFFFFFFF)
        if h[16] & 255 != 2 or submesh["blend_partition"] is not False:
            raise ValueError("Unsupported submesh lighting mode")
        count, draw_count = len(submesh["vertices"]), len(submesh["triangles"]) * 3
        if (
            count < 3
            or draw_count < 3
            or vertex_cursor + count > nv
            or index_cursor + draw_count > ni
        ):
            raise ValueError("Invalid lighting range")
        if any(
            not vertex_cursor <= v < vertex_cursor + count
            for v in indices[index_cursor : index_cursor + draw_count]
        ):
            raise ValueError("Lighting range crosses submesh")
        raw = struct.pack("<36I", *h)
        diffuse = vector(struct.unpack_from("<3f", raw, 0x60), 3, 0, 128)
        mat_ambient = vector(struct.unpack_from("<3f", raw, 0x70), 3, 0, 128)
        payload += struct.pack(
            "<4I6f", vertex_cursor, count, index_cursor, draw_count, *diffuse, *mat_ambient
        )
        vertex_cursor += count
        index_cursor += draw_count
    if (vertex_cursor, index_cursor) != (nv, ni):
        raise ValueError("Incomplete lighting ranges")
    return (
        struct.pack(
            "<8s10I", b"S3CLv1\0\0", 1, 15, 3, scm, san, sct, nv, ni, 824, zlib.crc32(payload)
        )
        + payload
    )
