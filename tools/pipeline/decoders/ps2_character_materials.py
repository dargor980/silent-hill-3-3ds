"""Bounded MDL image bindings, without claiming runtime GS material state."""

import struct
from dataclasses import dataclass

from tools.inspectors.texture_probe import probe_texture
from tools.pipeline.decoders.ps2_character_mesh import CharacterMesh, decode_character_mesh
from tools.pipeline.decoders.ps2_indexed8 import (
    IndexedTexture,
    decode_indexed8,
    validate_dimensions,
)

MAX_IMAGES = 16
MAX_PIXELS = 1024 * 1024


class CharacterMaterialError(ValueError):
    pass


@dataclass(frozen=True)
class CharacterMaterials:
    mesh: CharacterMesh
    sector_offset: int
    image_table: tuple[int, ...]
    structure: dict
    images: tuple[IndexedTexture, ...]
    headers: tuple[dict, ...]


def decode_character_materials(data: bytes) -> CharacterMaterials:
    mesh = decode_character_mesh(data)
    skeleton = mesh.skeleton
    head, file_head = skeleton.model_header_words, skeleton.file_header_words
    count, sector = file_head[2:4]
    base = skeleton.model_offset
    if not 1 <= count <= MAX_IMAGES or count != head[12]:
        raise CharacterMaterialError("CT_IMAGE_COUNT")
    if sector < base + 128 or sector % 16 or sector + 32 > len(data):
        raise CharacterMaterialError("CT_SECTOR_RANGE")
    table = base + head[13]
    if table < base + 128 or table % 4 or table + 4 * count > sector:
        raise CharacterMaterialError("CT_IMAGE_TABLE_RANGE")
    image_table = struct.unpack_from(f"<{count}I", data, table)
    if image_table != tuple(range(count)):
        raise CharacterMaterialError("CT_IMAGE_TABLE_VARIANT")
    # Mesh validation checks its own overlaps; include the image table and
    # require every known model span to precede the final texture sector.
    spans = [
        (table, table + 4 * count),
        (skeleton.matrices_offset, skeleton.matrices_offset + 64 * len(skeleton.parents)),
        (skeleton.parents_offset, skeleton.parents_offset + len(skeleton.parents)),
        (base + head[6], base + head[6] + 2 * head[5]),
        (base + head[7], base + head[7] + 64 * head[5]),
        (base + head[15], base + head[15] + 8 * head[14]),
        *((part.offset, part.offset + part.header_words[0]) for part in mesh.submeshes),
    ]
    spans = sorted((a, b) for a, b in spans if a != b)
    if any(b > sector for _, b in spans) or any(
        a[1] > b[0] for a, b in zip(spans, spans[1:], strict=False)
    ):
        raise CharacterMaterialError("CT_SECTION_OVERLAP")
    area = data[sector:]
    structure = probe_texture(len(area), lambda start, size: area[start : start + size])
    blocks = structure["blocks"]
    if len(blocks) != count:
        raise CharacterMaterialError("CT_IMAGE_COUNT")
    for block in blocks:
        if (
            block["bpp"] != 8
            or block["clut"]["declared_count"] != 4
            or block["opaque"]["bit_shift"] != 1
            or block["padding_declared"] != block["padding_computed"]
        ):
            raise CharacterMaterialError("CT_TRANSFER_VARIANT")
        validate_dimensions(block["width"], block["height"])
    if any(palette >= 4 for _, palette in mesh.texture_descriptors):
        raise CharacterMaterialError("CT_PALETTE_REFERENCE")
    # Stored CLUT units are not automatically equivalent to nonzero GS CBP
    # selectors. This MDL profile only establishes selector zero.
    if any(palette != 0 for _, palette in mesh.texture_descriptors):
        raise CharacterMaterialError("CT_PALETTE_VARIANT")
    image_pixels = sum(b["width"] * b["height"] for b in blocks)
    texture_pixels = sum(
        blocks[image]["width"] * blocks[image]["height"] for image, _ in mesh.texture_descriptors
    )
    if max(image_pixels, texture_pixels) > MAX_PIXELS:
        raise CharacterMaterialError("CT_PIXEL_BUDGET")
    images, headers = [], []
    for block in blocks:
        start, size = block["indices"]["offset"], block["indices"]["size"]
        clut = block["clut"]["data_offset"]
        images.append(
            decode_indexed8(
                block["width"],
                block["height"],
                area[start : start + size],
                area[clut : clut + 4096],
            )
        )
        headers.append(
            {
                "image_header_hex": area[block["header_offset"] : start].hex(),
                "clut_header_hex": area[clut - 48 : clut].hex(),
            }
        )
    return CharacterMaterials(mesh, sector, image_table, structure, tuple(images), tuple(headers))
