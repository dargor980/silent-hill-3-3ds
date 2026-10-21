"""Pure conversion of a captured, bounded glass material; not a general GS renderer."""

from tools.pipeline.geometry_inspection import TARGET, encode_sgm
from tools.pipeline.geometry_transform import MapAffine, inspection_basis, material_uv
from tools.pipeline.texture_inspection import PIXEL_BYTES, encode_stx

PROFILE = {
    "prim": 0x7B,
    "alpha": 0x8000000044,
    "test": 0x53000,
    "vertex_alpha": 127,
    "fog": 227,
    "fog_color": [0, 0, 0],
    "depth_write": False,
    "filter": "linear",
    "wrap": "clamp",
}


def material_geometry(shapes, reference):
    if reference["profile"] != PROFILE:
        raise ValueError("Unsupported material state")
    model = reference["model_columns"]
    transform = MapAffine(model)
    refs = reference["shapes"]
    by_offset = dict(shapes)
    order = reference["draw_order"]
    if (
        not shapes
        or len(by_offset) != len(shapes)
        or len(refs) != len(shapes)
        or {r["shape_offset"] for r in refs} != set(by_offset)
        or len(order) != len(shapes)
        or set(order) != set(by_offset)
    ):
        raise ValueError("Material shape inventory differs")
    world, colors = {}, {}
    for ref in refs:
        offset = ref["shape_offset"]
        geometry = by_offset[offset]
        rgba = ref["rgba"]
        if len(rgba) != len(geometry.vertices) or any(
            len(row) != 4
            or any(type(x) is not int or not 0 <= x <= 128 for x in row)
            or row[3] != 127
            for row in rgba
        ):
            raise ValueError("Unsupported captured vertex color")
        colors[offset] = [tuple(x / 128 * PROFILE["fog"] / 256 for x in row[:3]) for row in rgba]
        world[offset] = []
        for vertex in geometry.vertices:
            world[offset].append(inspection_basis(transform.transform_point(vertex.position)))
    points = [p for group in world.values() for p in group]
    low = [min(p[j] for p in points) for j in range(3)]
    high = [max(p[j] for p in points) for j in range(3)]
    center = [(a + b) / 2 for a, b in zip(low, high, strict=True)]
    extent = max(b - a for a, b in zip(low, high, strict=True))
    if extent <= 0:
        raise ValueError("Empty material extent")
    scale = 4 / extent
    rows, ranges = [], []
    for offset in order:
        geometry = by_offset[offset]
        first = len(rows)
        for triangle in geometry.triangles:
            for index in triangle:
                p = tuple(
                    (world[offset][index][j] - center[j]) * scale + TARGET[j] for j in range(3)
                )
                uv = material_uv(geometry.vertices[index].uv_words)
                rows.append((*p, *uv, *colors[offset][index]))
        ranges.append({"shape_offset": offset, "first": first, "count": len(rows) - first})
    # This inspector's backdrop and camera require a front-facing planar sample.
    # Refuse to silently reuse this policy for arbitrary scene geometry.
    for i in range(0, len(rows), 3):
        a, b, c = rows[i : i + 3]
        normal_z = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if normal_z <= 0 or any(abs(v[2] + 2) > 1e-5 for v in (a, b, c)):
            raise ValueError("Expected front-facing planar inspection geometry")
    return encode_sgm(rows), {
        "model_columns": model,
        "basis": [1, -1, -1],
        "world_center_after_basis": center,
        "uniform_scale": scale,
        "target": list(TARGET),
        "ranges": ranges,
        "uv": "raw_UV_div_32768_no_flip",
        "lighting": "captured_rgb_div_128_times_fog_227_div_256",
    }


def material_texture(rgba):
    if type(rgba) is not bytes or len(rgba) != PIXEL_BYTES or max(rgba[3::4]) > 128:
        raise ValueError("Expected bounded PS2 alpha")
    output = bytearray(rgba)
    # Round to nearest UNORM8, not the preview's saturating multiply-by-two.
    output[3::4] = bytes((alpha * 255 + 64) // 128 for alpha in rgba[3::4])
    return encode_stx(bytes(output))
