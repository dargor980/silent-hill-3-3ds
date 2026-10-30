"""Pure SRM1 preparation: full MAP geometry, two verified glass shapes, original SRI2."""

import struct
import zlib

from tools.inspectors.map_probe import probe_map
from tools.inspectors.map_render_probe import probe_render_metadata
from tools.inspectors.texture_probe import probe_texture
from tools.pipeline.decoders.ps2_indexed8 import decode_indexed8, render_palette
from tools.pipeline.decoders.ps2_map_geometry import decode_shape, encode_vertices
from tools.pipeline.heather_room_contacts import equal, require
from tools.pipeline.intermediate_assets import sha, verify_file
from tools.pipeline.intermediate_json import encode_json
from tools.pipeline.material_inspection import PROFILE as GLASS_PROFILE

REFERENCE_SHA = "e4cdb9f7c55d17409d5b1da8b48f706dbfe51440ad0a69716351e305e41c1e37"
MAX_MAP_VERTICES = 27900
NEUTRAL_RGB = (0.55, 0.58, 0.62)
RENDER_PROFILE = {
    "schema_version": 1,
    "profile": "heather-hp34-render-v1",
    "room_profile_sha256": "5838c4b445a0da3f4a2636ac9c9e61edfe754dc89b33d25db33284581212e531",
    "basis": [1, -1, -1],
    "scale": 0.002,
    "viewport": [400, 240],
    "camera": {
        "eye_local": [275, -1000, -700],
        "target_local": [275, -300, 100],
        "vertical_fov_degrees": 80,
        "near_render_units": 0.02,
        "far_render_units": 12,
    },
    "camera_provenance": "authored_framing_refinement_HM_T4c_1_not_PS2",
    "opaque_order": "neutral_map_then_textured_actor",
    "transparent_order": "global_triangle_centroid_far_to_near_glass_and_hair",
    "transparent_depth_write": False,
    "glass_vertex_alpha_unorm8": 253,
    "hair_alpha_test_greater_unorm8": 100,
    "neutral_two_sided": True,
    "label": "CAMARA FIJA PROPIA / 29 FORMAS CON MATERIAL NEUTRO",
}


def glass_pixels(raw, reference):
    structure = probe_texture(len(raw), lambda o, n: raw[o : o + n])
    require(len(structure["blocks"]) == 1, "HRS_TEXTURE_BLOCKS")
    b = structure["blocks"][0]
    require(
        (b["width"], b["height"], b["bpp"], b["clut"]["declared_count"]) == (256, 256, 8, 4),
        "HRS_TEXTURE_PROFILE",
    )
    indices, clut = b["indices"], b["clut"]
    texture = decode_indexed8(
        256,
        256,
        raw[indices["offset"] : indices["offset"] + indices["size"]],
        raw[clut["data_offset"] : clut["data_offset"] + clut["size"]],
    )
    rgba = render_palette(texture, 0, normalize_alpha=False)
    require(
        sha(rgba) == reference["texture_rgba_sha256"] and max(rgba[3::4]) <= 128,
        "HRS_GLASS_REFERENCE",
    )
    normalized = bytearray(rgba)
    normalized[3::4] = bytes((a * 255 + 64) // 128 for a in rgba[3::4])
    return bytes(normalized)


def map_geometry(raw, reference, profile, glass_crc):
    structure = probe_map(len(raw), lambda o, n: raw[o : o + n])
    render = probe_render_metadata(len(raw), lambda o, n: raw[o : o + n])
    offset = render["base_transform"]["matrix_offset"]
    matrix = list(struct.unpack_from("<16f", raw, offset))
    origin = profile["coordinates"]["origin"]
    expected = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, *origin, 1]
    require(matrix == expected and reference["model_columns"] == expected, "HRS_SHARED_MODEL")
    equal(reference["profile"], GLASS_PROFILE, "HRS_GLASS_PROFILE")
    require(
        reference["scope"] == "mr_t4d_material_reference" and reference["schema_version"] == 1,
        "HRS_REFERENCE",
    )
    glass = {s["shape_offset"]: s for s in reference["shapes"]}
    selected = profile["render"]["verified_glass_shape_offsets"]
    require(
        len(glass) == len(reference["shapes"]) == 2 and set(glass) == set(selected),
        "HRS_GLASS_SHAPES",
    )
    require(
        len(reference["draw_order"]) == 2 and set(reference["draw_order"]) == set(glass),
        "HRS_GLASS_ORDER",
    )
    require(all(s["mode_word_20"] in (1, 2) for s in render["shape_words"]), "HRS_MAP_MODE")
    shapes, ranges, rows = [], [], []
    originals = triangles = glass_count = 0
    for group in structure["groups"]:
        for mesh in group["children"]:
            for submesh in mesh["children"]:
                for shape in submesh["children"]:
                    data = raw[shape["data_offset"] : shape["data_offset"] + shape["vertex_bytes"]]
                    decoded = decode_shape(data, shape["vertex_count"])
                    require(bool(decoded.triangles), "HRS_EMPTY_SHAPE")
                    first = len(rows)
                    is_glass = shape["offset"] in glass
                    colors = None
                    if is_glass:
                        ref = glass[shape["offset"]]
                        require(
                            sha(encode_vertices(decoded.vertices)) == ref["source_sha256"],
                            "HRS_GLASS_SOURCE",
                        )
                        colors = ref["rgba"]
                        require(
                            len(colors) == len(decoded.vertices)
                            and all(
                                len(c) == 4
                                and c[3] == 127
                                and all(type(x) is int and 0 <= x <= 128 for x in c)
                                for c in colors
                            ),
                            "HRS_GLASS_COLORS",
                        )
                    for triangle in decoded.triangles:
                        for i in triangle:
                            v = decoded.vertices[i]
                            rgb = (
                                tuple(c / 128 * 227 / 256 for c in colors[i][:3])
                                if colors
                                else NEUTRAL_RGB
                            )
                            rows.append((*v.position, 1, *rgb, *(x / 32768 for x in v.uv_words)))
                    count = len(rows) - first
                    if is_glass:
                        glass_count += count
                    ranges.append((shape["offset"], first, count, int(is_glass)))
                    originals += len(decoded.vertices)
                    triangles += len(decoded.triangles)
                    shapes.append(
                        dict(
                            group=group["offset"],
                            mesh=mesh["offset"],
                            submesh=submesh["offset"],
                            header=shape,
                            geometry=dict(
                                vertices=[
                                    dict(
                                        position=list(v.position),
                                        uv_words=list(v.uv_words),
                                        packed_attributes=list(v.packed_attributes),
                                    )
                                    for v in decoded.vertices
                                ],
                                triangles=[list(t) for t in decoded.triangles],
                                skipped_vertices=list(decoded.skipped_vertices),
                                degenerate_triangles=list(decoded.degenerate_triangles),
                            ),
                            source_sha256=sha(data),
                            material="verified_glass" if is_glass else "diagnostic_neutral",
                        )
                    )
    r = profile["render"]
    require(
        (len(shapes), originals, triangles)
        == (r["expected_shapes"], r["expected_vertices"], r["expected_triangles"]),
        "HRS_COUNTS",
    )
    require(
        len(shapes) <= 31 and len(rows) <= MAX_MAP_VERTICES and glass_count == 96, "HRS_CAPACITY"
    )
    payload = b"".join(struct.pack("<4I", *r) for r in ranges) + b"".join(
        struct.pack("<9f", *v) for v in rows
    )
    header = struct.pack(
        "<8s6I",
        b"S3RMv1\0\0",
        len(shapes),
        len(rows),
        len(payload),
        zlib.crc32(payload),
        glass_crc,
        1,
    )
    view = dict(
        schema_version=1,
        structure=structure,
        render_metadata=render,
        model_columns=matrix,
        shapes=shapes,
        neutral_material=dict(
            rgb=list(NEUTRAL_RGB), two_sided=True, label="29 FORMAS: MATERIAL NEUTRO"
        ),
        vertex_layout="local_xyzw_rgb_uv_f32",
        scene_transform="shared_origin_basis_scale_once",
    )
    return header + payload, encode_json(view)


def rig_metadata(files, profile):
    raw = files["heather.sri"]
    require(sha(raw) == profile["heather"]["sri_sha256"] and len(raw) >= 96, "HRS_SRI_PIN")
    magic, *h = struct.unpack_from("<8s22I", raw)
    require(
        magic == b"S3RIv2\0\0"
        and h[:2] == [36, 58]
        and h[6:12] == [3, 2, 25, 1, 522, 525]
        and h[14:] == [0] * 8,
        "HRS_SRI_PROFILE",
    )
    require(
        h[5] == 13 and h[12] == len(raw) - 96 and zlib.crc32(raw[96:]) == h[13], "HRS_SRI_LENGTH"
    )
    require(
        set(files) == {"heather.sri"} | {f"texture-{i:02}.rgba" for i in range(13)}, "HRS_SRI_FILES"
    )
    materials = list(struct.iter_unpack("<7I", raw[-13 * 28 :]))
    total = 256 * 256 * 4
    staging = 0
    for i, m in enumerate(materials):
        pixels = files[f"texture-{i:02}.rgba"]
        require(
            m[2] == i and len(pixels) == m[3] * m[4] * 4 and zlib.crc32(pixels) == m[6],
            "HRS_SRI_TEXTURE",
        )
        total += len(pixels)
        staging = max(staging, len(pixels))
    require(
        total <= profile["budgets"]["resident_texture_bytes"]
        and staging <= profile["budgets"]["texture_staging_bytes"],
        "HRS_TEXTURE_BUDGET",
    )
    return dict(
        bones=h[0],
        samples=h[1],
        helpers=h[2],
        vertices=h[3],
        indices=h[4],
        materials=h[5],
        texture_resident_bytes=total,
        texture_staging_bytes=staging,
    )


def make_scene(raw_map, raw_texture, reference_raw, profile, rig_files):
    from tools.pipeline.intermediate_json import decode_json

    verify_file(raw_map, profile["resources"]["map"])
    verify_file(raw_texture, profile["resources"]["external_texture"])
    require(sha(reference_raw) == REFERENCE_SHA, "HRS_REFERENCE_PIN")
    reference = decode_json(reference_raw)
    pixels = glass_pixels(raw_texture, reference)
    binary, view = map_geometry(raw_map, reference, profile, zlib.crc32(pixels))
    rig = rig_metadata(rig_files, profile)
    return {
        "render-profile.json": encode_json(RENDER_PROFILE),
        "map.srm": binary,
        "map-view.json": view,
        "source.map": raw_map,
        "source.tex": raw_texture,
        "glass-reference.json": reference_raw,
        "glass.rgba": pixels,
        **rig_files,
    }, rig
