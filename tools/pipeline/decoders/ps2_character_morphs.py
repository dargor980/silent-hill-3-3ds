"""Lossless MDL v3 morph data and VU bindings, without expression evaluation.

The explicit profile requires both position and normal arrays. The original
mesh decoder continues to reject morphs; callers opt into this separate reader.
"""

import struct
from dataclasses import dataclass

from tools.pipeline.decoders.ps2_character_mesh import (
    CharacterMesh,
    CharacterMeshError,
    _decode_character_mesh,
    _disjoint,
    _range,
)
from tools.pipeline.decoders.ps2_skeleton import decode_skeleton

RECIPE = "sh3-ps2-mdl-morph-position-normal-v1"
MAX_VERTICES = 4096
MAX_TARGETS = 128
MAX_REFS = 64


@dataclass(frozen=True)
class MorphTarget:
    offset: int
    position_deltas: tuple[tuple[int, ...], ...]
    normal_deltas: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class MorphReference:
    source_index: int
    vu_address: int
    count: int


@dataclass(frozen=True)
class MorphMesh:
    recipe: str
    mesh: CharacterMesh
    base_positions_q4: tuple[tuple[int, ...], ...]
    base_normals_q12: tuple[tuple[int, ...], ...]
    targets: tuple[MorphTarget, ...]
    # One entry per submesh, including empty tuples for rigid/base variants.
    references: tuple[tuple[MorphReference, ...], ...]


def decode_morph_mesh(data: bytes) -> MorphMesh:
    skeleton = decode_skeleton(data)
    h, base = skeleton.model_header_words, skeleton.model_offset
    count, target_count = h[17], h[19]
    if not 1 <= count <= MAX_VERTICES or not 1 <= target_count <= MAX_TARGETS:
        raise CharacterMeshError("CM_MORPH_COUNT")
    low, high = base + 128, len(data)
    positions_at, descriptors_at = base + h[18], base + h[20]
    normals_at = (positions_at + 6 * count + 15) & ~15
    _range(positions_at, count * 6, low, high, 16)
    _range(normals_at, count * 6, low, high, 16)
    _range(descriptors_at, target_count * 8, low, high, 16)
    if (normals_at + 6 * count + 15) & ~15 != descriptors_at:
        raise CharacterMeshError("CM_MORPH_NORMAL_LAYOUT")
    positions = tuple(struct.unpack_from("<3h", data, positions_at + 6 * i) for i in range(count))
    normals = tuple(struct.unpack_from("<3h", data, normals_at + 6 * i) for i in range(count))
    spans = [(positions_at, descriptors_at + target_count * 8)]
    targets = []
    for i in range(target_count):
        entries, relative = struct.unpack_from("<2I", data, descriptors_at + i * 8)
        if not 1 <= entries <= count:
            raise CharacterMeshError("CM_MORPH_DELTA_COUNT")
        offset = base + relative
        normal_offset = (offset + entries * 8 + 15) & ~15
        _range(offset, normal_offset + entries * 8 - offset, low, high, 16)
        spans.append((offset, normal_offset + entries * 8))
        _disjoint(spans)
        arrays = []
        for start in (offset, normal_offset):
            values = tuple(struct.unpack_from("<4h", data, start + 8 * j) for j in range(entries))
            indices = [v[3] for v in values]
            if len(set(indices)) != entries or any(not 0 <= v < count for v in indices):
                raise CharacterMeshError("CM_MORPH_VERTEX_REFERENCE")
            arrays.append(values)
        targets.append(MorphTarget(offset, *arrays))
    references = []

    def read_refs(offset, words):
        n, at = words[5], offset + words[6]
        if not 0 <= n <= MAX_REFS:
            raise CharacterMeshError("CM_MORPH_REF_COUNT")
        refs = ()
        if n:
            _range(at, 6 * n, offset + 144, offset + words[0], 2)
            refs = tuple(
                MorphReference(*struct.unpack_from("<3H", data, at + i * 6)) for i in range(n)
            )
            if any(not 1 <= r.count <= 256 or r.source_index + r.count > count for r in refs):
                raise CharacterMeshError("CM_MORPH_REF_SOURCE")
        references.append(refs)
        return ((at, at + n * 6),) if n else ()

    mesh = _decode_character_mesh(data, skeleton, morph_spans=spans, read_morph_refs=read_refs)
    for part, refs in zip(mesh.submeshes, references, strict=True):
        vertex_start = part.vif_header_words[2]
        used = set()
        for ref in refs:
            delta = ref.vu_address - vertex_start
            if delta < 0 or delta % 4 or delta // 4 + ref.count > len(part.vertices):
                raise CharacterMeshError("CM_MORPH_REF_DESTINATION")
            destinations = set(range(delta // 4, delta // 4 + ref.count))
            if destinations & used:
                raise CharacterMeshError("CM_MORPH_REF_OVERLAP")
            used.update(destinations)
    return MorphMesh(RECIPE, mesh, positions, normals, tuple(targets), tuple(references))
