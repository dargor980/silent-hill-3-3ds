"""Bounded MDL v3 mesh candidate, retaining integer source values (CM02-05).

No skinning or texture decode occurs here. Positions remain in their primary
bone's local frame; helper matrix application requires a separate runtime audit.
"""

import hashlib
import math
import struct
from dataclasses import dataclass

from tools.pipeline.decoders.ps2_character_vif import load_vif
from tools.pipeline.decoders.ps2_skeleton import Skeleton, decode_skeleton

MAX_HELPERS = 128
MAX_SUBMESHES = 256
MAX_GROUPS = 64


class CharacterMeshError(ValueError):
    pass


@dataclass(frozen=True)
class Vertex:
    position_q4: tuple[int, ...]
    normal_q12: tuple[int, ...]
    uv_q12: tuple[int, ...]
    bones: tuple[int, ...]
    weights_q12: tuple[int, ...]
    primary_bone: int


@dataclass(frozen=True)
class VertexGroup:
    header_words: tuple[int, ...]
    bone_addresses: tuple[int, ...]
    helper_indices: tuple[int, ...]


@dataclass(frozen=True)
class Submesh:
    offset: int
    blend_partition: bool
    header_words: tuple[int, ...]
    bone_palette: tuple[int, ...]
    helper_palette: tuple[int, ...]
    texture_index: int
    vif_sha256: str
    vif_header_words: tuple[int, ...]
    groups: tuple[VertexGroup, ...]
    vertices: tuple[Vertex, ...]
    strip_commands: tuple[int, ...]
    triangles: tuple[tuple[int, int, int], ...]
    suppressed_commands: int
    degenerate_triangles: int


@dataclass(frozen=True)
class CharacterMesh:
    skeleton: Skeleton
    helpers: tuple[tuple[int, int], ...]
    helper_matrix_words: tuple[tuple[int, ...], ...]
    texture_descriptors: tuple[tuple[int, int], ...]
    submeshes: tuple[Submesh, ...]


def _range(start, size, low, high, alignment=1):
    if start < low or size < 0 or start % alignment or start + size > high:
        raise CharacterMeshError("CM_SECTION_RANGE")


def _disjoint(spans):
    spans = sorted((start, end) for start, end in spans if start != end)
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:], strict=False)):
        raise CharacterMeshError("CM_SECTION_OVERLAP")


def _palette(data, start, count, maximum, low, high):
    if not 0 <= count <= maximum:
        raise CharacterMeshError("CM_PALETTE_COUNT")
    _range(start, count * 2, low, high, 2)
    values = struct.unpack_from(f"<{count}h", data, start)
    if len(set(values)) != count or any(not 0 <= value < maximum for value in values):
        raise CharacterMeshError("CM_PALETTE_REFERENCE")
    return values


def decode_character_mesh(data: bytes) -> CharacterMesh:
    skeleton = decode_skeleton(data)
    return _decode_character_mesh(data, skeleton)


def _decode_character_mesh(data, skeleton, *, morph_spans=(), read_morph_refs=None):
    """Shared bounded mesh reader; morph validation belongs to its own decoder."""
    header, base = skeleton.model_header_words, skeleton.model_offset
    if (header[17] or header[19]) and read_morph_refs is None:
        raise CharacterMeshError("CM_MORPH_UNSUPPORTED")
    helper_count = header[5]
    if not 0 <= helper_count <= MAX_HELPERS:
        raise CharacterMeshError("CM_HELPER_COUNT")
    if not 1 <= header[8] + header[10] <= MAX_SUBMESHES:
        raise CharacterMeshError("CM_SUBMESH_COUNT")
    if not 1 <= header[14] <= 256 or not 1 <= header[12] <= 256:
        raise CharacterMeshError("CM_TEXTURE_COUNT")
    helpers_at, matrices_at, textures_at = (base + header[index] for index in (6, 7, 15))
    low = base + 128
    _range(helpers_at, helper_count * 2, low, len(data), 2)
    _range(matrices_at, helper_count * 64, low, len(data), 16)
    _range(textures_at, header[14] * 8, low, len(data), 4)
    helpers = tuple(
        struct.unpack_from("<2b", data, helpers_at + i * 2) for i in range(helper_count)
    )
    if any(
        a == b or not 0 <= a < len(skeleton.parents) or not 0 <= b < len(skeleton.parents)
        for a, b in helpers
    ):
        raise CharacterMeshError("CM_HELPER_REFERENCE")
    matrix_words = []
    for index in range(helper_count):
        offset = matrices_at + index * 64
        matrix = struct.unpack_from("<16f", data, offset)
        if not all(math.isfinite(value) for value in matrix):
            raise CharacterMeshError("CM_HELPER_NONFINITE")
        if tuple(matrix[i] for i in (3, 7, 11, 15)) != (0, 0, 0, 1):
            raise CharacterMeshError("CM_HELPER_AFFINE")
        matrix_words.append(struct.unpack_from("<16I", data, offset))
    textures = tuple(
        struct.unpack_from("<2i", data, textures_at + i * 8) for i in range(header[14])
    )
    if any(not 0 <= image < header[12] or palette < 0 for image, palette in textures):
        raise CharacterMeshError("CM_TEXTURE_REFERENCE")
    spans = [
        *morph_spans,
        (skeleton.matrices_offset, skeleton.matrices_offset + len(skeleton.parents) * 64),
        (skeleton.parents_offset, skeleton.parents_offset + len(skeleton.parents)),
        (helpers_at, helpers_at + helper_count * 2),
        (matrices_at, matrices_at + helper_count * 64),
        (textures_at, textures_at + header[14] * 8),
    ]
    meshes = []
    for blend, count, offset in (
        (False, header[8], base + header[9]),
        (True, header[10], base + header[11]),
    ):
        for _ in range(count):
            _range(offset, 144, low, len(data), 16)
            words = struct.unpack_from("<36I", data, offset)
            if words[0] < 144 or words[0] % 16:
                raise CharacterMeshError("CM_SUBMESH_LENGTH")
            end = offset + words[0]
            _range(offset, words[0], low, len(data), 16)
            if words[5] and read_morph_refs is None:
                raise CharacterMeshError("CM_MORPH_UNSUPPORTED")
            ref_spans = read_morph_refs(offset, words) if read_morph_refs else ()
            bones = _palette(
                data, offset + words[8], words[7], len(skeleton.parents), offset + 144, end
            )
            if not bones:
                raise CharacterMeshError("CM_EMPTY_BONE_PALETTE")
            palette = _palette(data, offset + words[10], words[9], helper_count, offset + 144, end)
            texture_at = offset + words[14]
            _range(texture_at, 2, offset + 144, end, 2)
            texture = struct.unpack_from("<h", data, texture_at)[0]
            if not 0 <= texture < len(textures):
                raise CharacterMeshError("CM_TEXTURE_REFERENCE")
            vif_at, vif_size = offset + words[2], words[3] * 16
            _range(vif_at, vif_size, offset + 144, end, 16)
            _disjoint(
                [
                    *ref_spans,
                    (offset + words[8], offset + words[8] + 2 * len(bones)),
                    (offset + words[10], offset + words[10] + 2 * len(palette)),
                    (texture_at, texture_at + 2),
                    (vif_at, vif_at + vif_size),
                ]
            )
            packet = data[vif_at : vif_at + vif_size]
            meshes.append(_mesh(offset, blend, words, bones, palette, helpers, texture, packet))
            spans.append((offset, end))
            offset = end
    _disjoint(spans)
    return CharacterMesh(skeleton, helpers, tuple(matrix_words), textures, tuple(meshes))


def _mesh(offset, blend, words, bones, helper_palette, helpers, texture, packet):
    memory = load_vif(packet)
    address = words[4]
    head = memory.read(address) + memory.read(address + 1)
    count, _, vertex_start, matrix_start, _, _, strip_start, strip_end = head
    if not 1 <= count <= MAX_GROUPS or not 0 <= strip_start < strip_end <= 1024:
        raise CharacterMeshError("CM_VU_LAYOUT")
    vertices, groups = [], []
    for index in range(count):
        group = memory.read(address + 2 + index * 2)
        vertex_count, encoded_helpers, start, end = group
        if encoded_helpers not in (0, 2, 4, 6) or not 1 <= vertex_count <= 256:
            raise CharacterMeshError("CM_VERTEX_GROUP")
        if start != vertex_start + 4 * len(vertices) or end != start + 4 * vertex_count:
            raise CharacterMeshError("CM_VERTEX_RANGE")
        helper_count = encoded_helpers // 2
        addresses = memory.read(address + 3 + index * 2, helper_count + 1)
        local = []
        for bone_address in addresses:
            delta = bone_address - matrix_start
            if delta < 0 or delta % 4:
                raise CharacterMeshError("CM_BONE_ADDRESS")
            local.append(delta // 4)
        if local[0] >= len(bones):
            raise CharacterMeshError("CM_BONE_ADDRESS")
        primary = bones[local[0]]
        resolved, helper_indices = [primary], []
        for item in local[1:]:
            if not len(bones) <= item < len(bones) + len(helper_palette):
                raise CharacterMeshError("CM_BONE_ADDRESS")
            helper_index = helper_palette[item - len(bones)]
            source, target = helpers[helper_index]
            if source != primary or target in resolved:
                raise CharacterMeshError("CM_HELPER_BASE")
            resolved.append(target)
            helper_indices.append(helper_index)
        groups.append(VertexGroup(group, addresses, tuple(helper_indices)))
        for vertex in range(vertex_count):
            at = start + vertex * 4
            position = memory.read(at, 3, signed=True)
            normal = memory.read(at + 1, 3, signed=True)
            weights = memory.read(at + 2, len(resolved), signed=True) if helper_count else (4096,)
            # Observed sums: 4095 for two influences, 4094 for three. Preserve
            # the quantization deficit; how the VU uses it is not yet verified.
            if (
                any(weight < 0 or weight > 4096 for weight in weights)
                or not 4096 - helper_count <= sum(weights) <= 4096
            ):
                raise CharacterMeshError("CM_WEIGHTS")
            uv = memory.read(at + 3, 2, signed=True)
            vertices.append(Vertex(position, normal, uv, tuple(resolved), weights, primary))
    vertex_end = vertex_start + len(vertices) * 4
    matrix_end = matrix_start + 4 * (len(bones) + len(helper_palette))
    if matrix_end > 1024:
        raise CharacterMeshError("CM_BONE_ADDRESS")
    _disjoint(
        [
            (address, address + 2 + count * 2),
            (vertex_start, vertex_end),
            (strip_start, strip_end),
            (matrix_start, matrix_end),
        ]
    )
    strip = tuple(value for at in range(strip_start, strip_end) for value in memory.read(at))
    indices = []
    for command in strip:
        delta = (command & 0x7FFF) - vertex_start
        if command & ~0xFFFF or delta < 0 or delta % 4 or delta // 4 >= len(vertices):
            raise CharacterMeshError("CM_STRIP_ADDRESS")
        indices.append(delta // 4)
    triangles = []
    suppressed = degenerate = 0
    for index, command in enumerate(strip):
        if command & 0x8000:
            suppressed += 1
        elif index < 2:
            raise CharacterMeshError("CM_STRIP_PREFIX")
        else:
            triangle = tuple(indices[index - 2 : index + 1])
            if len(set(triangle)) < 3:
                degenerate += 1
            else:
                triangles.append(triangle if index % 2 == 0 else triangle[::-1])
    return Submesh(
        offset,
        blend,
        words,
        bones,
        helper_palette,
        texture,
        hashlib.sha256(packet).hexdigest(),
        head,
        tuple(groups),
        tuple(vertices),
        strip,
        tuple(triangles),
        suppressed,
        degenerate,
    )
