"""Pure SGM1 encoding and explicit inspection transform; no PS2 material inference."""

import math
import struct
import zlib

from tools.pipeline.decoders.ps2_map_geometry import MapGeometry

MAX_DRAW_VERTICES = 3072
COLORS = ((0.45, 0.9, 1.0), (1.0, 0.65, 0.3))
TARGET = (0.0, 0.75, -2.0)


def encode_sgm(vertices: list[tuple]) -> bytes:
    if not 3 <= len(vertices) <= MAX_DRAW_VERTICES or len(vertices) % 3:
        raise ValueError("SGM1 vertex budget")
    rows = []
    for vertex in vertices:
        if len(vertex) != 8 or any(
            type(value) not in (int, float) or not math.isfinite(value) for value in vertex
        ):
            raise ValueError("SGM1 finite float32 required")
        if (
            any(abs(x) > 4 for x in vertex[:3])
            or any(abs(x) > 2 for x in vertex[3:5])
            or any(not 0 <= x <= 1 for x in vertex[5:])
        ):
            raise ValueError("SGM1 numeric bounds")
        rows.append(struct.pack("<8f", *vertex))
    # Validate after float32 rounding, exactly as the native reader does.
    positions = [struct.unpack("<8f", row)[:3] for row in rows]
    for i in range(0, len(rows), 3):
        a, b, c = positions[i : i + 3]
        x, y, z = (b[j] - a[j] for j in range(3))
        u, v, w = (c[j] - a[j] for j in range(3))
        if y * w == z * v and z * u == x * w and x * v == y * u:
            raise ValueError("SGM1 degenerate triangle")
    payload = b"".join(rows)
    return (
        struct.pack("<8sIIII", b"S3GMv1\0\0", len(rows), 32, len(payload), zlib.crc32(payload))
        + payload
    )


def normalize_shapes(shapes: list[tuple[int, MapGeometry]]) -> tuple[bytes, dict]:
    count = sum(len(g.triangles) * 3 for _, g in shapes)
    if not 3 <= count <= MAX_DRAW_VERTICES:
        raise ValueError("SGM1 draw budget")
    points = [v.position for _, g in shapes for v in g.vertices]
    low = [min(p[j] for p in points) for j in range(3)]
    high = [max(p[j] for p in points) for j in range(3)]
    center = [(a + b) / 2 for a, b in zip(low, high, strict=True)]
    extent = max(b - a for a, b in zip(low, high, strict=True))
    if extent <= 0:
        raise ValueError("SGM1 empty extent")
    scale = 4 / extent
    vertices, ranges = [], []
    for ordinal, (offset, geometry) in enumerate(shapes):
        first = len(vertices)
        for triangle in geometry.triangles:
            for index in triangle:
                vertex = geometry.vertices[index]
                position = tuple(
                    (vertex.position[j] - center[j]) * scale + TARGET[j] for j in range(3)
                )
                vertices.append((*position, *vertex.uv_reference, *COLORS[ordinal % 2]))
        ranges.append({"shape_offset": offset, "first": first, "count": len(vertices) - first})
    return encode_sgm(vertices), {
        "center": center,
        "uniform_scale": scale,
        "target": list(TARGET),
        "axis_changes": "none",
        "draw_vertices": len(vertices),
        "ranges": ranges,
    }
