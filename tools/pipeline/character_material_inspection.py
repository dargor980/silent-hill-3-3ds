"""SCT1: bounded opaque material groups attached to an unchanged SCM1 mesh."""

import struct
import zlib

from tools.pipeline.character_inspection import integers

TEXTURE_BYTES = 512 * 512 * 4
IMAGES = (0,) * 6 + (1,) * 3 + (2,) * 6


def encode_material(ranges, textures, character):
    if (
        len(character) < 32
        or character[:8] != b"S3CMv1\0\0"
        or struct.unpack_from("<I", character, 24)[0] != len(character) - 32
        or struct.unpack_from("<I", character, 28)[0] != zlib.crc32(character[32:])
    ):
        raise ValueError("Invalid SCM1 binding")
    count = struct.unpack_from("<I", character, 12)[0]
    if not 9 <= count <= 4608 or count % 3 or len(ranges) != 3 or len(textures) != 3:
        raise ValueError("Invalid material extent")
    payload, cursor = bytearray(), 0
    for image, row in enumerate(ranges):
        first, size, texture = integers(row, 3, 0, 4608)
        if first != cursor or not size or size % 3 or texture != image:
            raise ValueError("Invalid material range")
        payload += struct.pack("<3I", first, size, texture)
        cursor += size
    if cursor != count:
        raise ValueError("Material coverage differs")
    for raw in textures:
        if type(raw) is not bytes or len(raw) != TEXTURE_BYTES or max(raw[3::4]) > 128:
            raise ValueError("Invalid original RGBA texture")
        payload += raw
    return (
        struct.pack(
            "<8s6I",
            b"S3CTv1\0\0",
            3,
            512,
            3,
            struct.unpack_from("<I", character, 28)[0],
            len(payload),
            zlib.crc32(payload),
        )
        + payload
    )


def material_ranges(mesh, materials):
    if len(mesh["submeshes"]) != 15 or len(materials["bindings"]) != 15:
        raise ValueError("Expected fifteen verified submeshes")
    counts = [0, 0, 0]
    for i, (submesh, binding, image) in enumerate(
        zip(mesh["submeshes"], materials["bindings"], IMAGES, strict=True)
    ):
        if (
            binding["submesh"] != i
            or binding["image"] != image
            or binding["descriptor"] != image
            or binding["palette"] != 0
            or binding["blend_partition"] is not False
            or submesh["blend_partition"] is not False
            or submesh["texture_index"] != image
            or submesh["offset"] != binding["offset"]
            or submesh["header_words"] != binding["header_words"]
        ):
            raise ValueError("Mesh/material binding differs")
        counts[image] += 3 * len(submesh["triangles"])
    return [(0, counts[0], 0), (counts[0], counts[1], 1), (sum(counts[:2]), counts[2], 2)]
