"""Bounded embedded indexed material set for the explicit morph MDL profile."""

import struct
from dataclasses import dataclass

from tools.inspectors.texture_probe import probe_texture
from tools.pipeline.decoders.ps2_character_materials import CharacterMaterialError
from tools.pipeline.decoders.ps2_character_mesh import _disjoint, _range
from tools.pipeline.decoders.ps2_character_morphs import MorphMesh, decode_morph_mesh
from tools.pipeline.decoders.ps2_indexed import IndexedImage, decode_indexed

MAX_IMAGES = 16
MAX_PIXELS = 8 * 1024 * 1024


@dataclass(frozen=True)
class MorphMaterials:
    geometry: MorphMesh
    sector_offset: int
    image_table: tuple[int, ...]
    structure: dict
    images: tuple[IndexedImage, ...]
    headers: tuple[bytes, ...]


def decode_morph_materials(data: bytes) -> MorphMaterials:
    geometry = decode_morph_mesh(data)
    mesh, skeleton = geometry.mesh, geometry.mesh.skeleton
    h, base = skeleton.model_header_words, skeleton.model_offset
    count, sector = skeleton.file_header_words[2:4]
    if not 1 <= count <= MAX_IMAGES or count != h[12]:
        raise CharacterMaterialError("CT_IMAGE_COUNT")
    _range(sector, 32, base + 128, len(data), 16)
    table = base + h[13]
    _range(table, 4 * count, base + 128, sector, 4)
    image_table = struct.unpack_from(f"<{count}I", data, table)
    if image_table != tuple(range(count)):
        raise CharacterMaterialError("CT_IMAGE_TABLE_VARIANT")
    spans = [
        (table, table + 4 * count),
        (skeleton.matrices_offset, skeleton.matrices_offset + 64 * len(skeleton.parents)),
        (skeleton.parents_offset, skeleton.parents_offset + len(skeleton.parents)),
        (base + h[6], base + h[6] + 2 * h[5]),
        (base + h[7], base + h[7] + 64 * h[5]),
        (base + h[15], base + h[15] + 8 * h[14]),
        (base + h[18], base + h[20] + 8 * h[19]),
        *((part.offset, part.offset + part.header_words[0]) for part in mesh.submeshes),
        *(
            (
                t.offset,
                ((t.offset + 8 * len(t.position_deltas) + 15) & ~15) + 8 * len(t.normal_deltas),
            )
            for t in geometry.targets
        ),
    ]
    _disjoint(spans)
    if any(b > sector for _, b in spans):
        raise CharacterMaterialError("CT_SECTION_OVERLAP")
    area = data[sector:]
    structure = probe_texture(len(area), lambda start, size: area[start : start + size])
    blocks = structure["blocks"]
    if len(blocks) != count:
        raise CharacterMaterialError("CT_IMAGE_COUNT")
    if sum(b["width"] * b["height"] for b in blocks) > MAX_PIXELS:
        raise CharacterMaterialError("CT_PIXEL_BUDGET")
    for b in blocks:
        if (
            b["opaque"]["bit_shift"] != {4: 2, 8: 1}[b["bpp"]]
            or b["padding_declared"] != b["padding_computed"]
        ):
            raise CharacterMaterialError("CT_TRANSFER_VARIANT")
    images, headers = [], []
    for b in blocks:
        start, size = b["indices"]["offset"], b["indices"]["size"]
        clut, clut_size = b["clut"]["data_offset"], b["clut"]["size"]
        images.append(
            decode_indexed(
                b["width"],
                b["height"],
                b["bpp"],
                area[start : start + size],
                area[clut : clut + clut_size],
            )
        )
        headers.append(area[b["header_offset"] : start] + area[b["clut"]["header_offset"] : clut])
    if any(selector not in images[i].selectors for i, selector in mesh.texture_descriptors):
        raise CharacterMaterialError("CT_PALETTE_REFERENCE")
    return MorphMaterials(geometry, sector, image_table, structure, tuple(images), tuple(headers))
