"""Lossless local MAP vertices and reference strip topology, without material inference."""

import struct
from dataclasses import dataclass

RECIPE = "sh3-ps2-map-local-geometry-v1"
MAX_VERTICES = 65536


class GeometryDecodeError(ValueError):
    pass


@dataclass(frozen=True)
class MapVertex:
    position: tuple[int, int, int]
    uv_words: tuple[int, int]
    packed_attributes: tuple[int, int, int]

    @property
    def uv_reference(self) -> tuple[float, float]:
        return self.uv_words[0] / 32768, 1 - self.uv_words[1] / 32768


@dataclass(frozen=True)
class MapGeometry:
    vertices: tuple[MapVertex, ...]
    triangles: tuple[tuple[int, int, int], ...]
    skipped_vertices: tuple[int, ...]
    degenerate_triangles: tuple[int, ...]


def encode_vertices(vertices: tuple[MapVertex, ...]) -> bytes:
    """Reconstruct original records, retaining all bits of packed words."""
    return b"".join(
        struct.pack(
            "<8h",
            *v.position,
            v.packed_attributes[0],
            *v.uv_words,
            *v.packed_attributes[1:],
        )
        for v in vertices
    )


def decode_shape(data: bytes, count: int) -> MapGeometry:
    if type(count) is not int or not 3 <= count <= MAX_VERTICES:
        raise GeometryDecodeError("MG_VERTEX_COUNT")
    if type(data) is not bytes or len(data) != count * 16:
        raise GeometryDecodeError("MG_PAYLOAD_SIZE")
    vertices, triangles, skipped, degenerate = [], [], [], []
    for i, words in enumerate(struct.iter_unpack("<8h", data)):
        vertex = MapVertex(words[:3], words[4:6], (words[3], words[6], words[7]))
        vertices.append(vertex)
        if words[4] & 1:
            skipped.append(i)
            continue
        if i < 2:
            raise GeometryDecodeError("MG_STRIP_START")
        face = (i, i - 1, i - 2) if i % 2 else (i - 2, i - 1, i)
        a, b, c = (vertices[j].position for j in face)
        ab = tuple(b[j] - a[j] for j in range(3))
        ac = tuple(c[j] - a[j] for j in range(3))
        if (
            ab[1] * ac[2] == ab[2] * ac[1]
            and ab[2] * ac[0] == ab[0] * ac[2]
            and ab[0] * ac[1] == ab[1] * ac[0]
        ):
            degenerate.append(len(triangles))
        triangles.append(face)
    result = MapGeometry(tuple(vertices), tuple(triangles), tuple(skipped), tuple(degenerate))
    if encode_vertices(result.vertices) != data:
        raise GeometryDecodeError("MG_ROUNDTRIP")
    return result
