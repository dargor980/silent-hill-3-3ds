"""Pure, lossless MAP glass sidecar and the verified MI inspection recipes."""

import struct

from tools.pipeline.decoders.ps2_indexed8 import IndexedTexture, render_palette
from tools.pipeline.decoders.ps2_map_geometry import encode_vertices
from tools.pipeline.geometry_obj import encode_obj
from tools.pipeline.geometry_transform import MapAffine
from tools.pipeline.intermediate_assets import digest, fields, inventory, sha, verify_file
from tools.pipeline.intermediate_json import decode_json, encode_json
from tools.pipeline.material_inspection import PROFILE as MATERIAL_PROFILE
from tools.pipeline.material_inspection import material_geometry, material_texture
from tools.pipeline.prepare_geometry_probe import GEOMETRY_FIELDS, verified_shapes

PROFILE = "ps2-map-glass-v1"
CONVERTER = "decoded-map-glass-intermediate-v1"
CONVENTIONS = {
    "geometry_decoder": "sh3-ps2-map-local-geometry-v1",
    "texture_decoder": "sh3-ps2-indexed8-four-cluts-v1",
    "positions": "local_i16_original_units_not_metres",
    "topology": "strip_parity_by_vertex_position_skips_preserved",
    "packed_attributes": "opaque_original_i16",
    "model": "column_major_affine_once_before_basis",
    "inspection": "basis_1_minus1_minus1_then_center_uniform_scale_target_0_0.75_minus2",
    "material_uv": "signed_U_V_div_32768_control_bit_retained_no_flip",
    "obj_uv": "historical_U_div_32768_1_minus_V_div_32768",
    "vertex_rgb": "captured_rgb_div_128_times_fog_227_div_256",
    "rgba": "original_bytes_all_four_palettes_only_zero_drawn",
    "png": "preserved_preview_min_255_2a_alpha_saturation",
    "stx_alpha": "floor_alpha_times_255_plus_64_div_128",
    "material": (
        "source_alpha_blend_vertex_alpha_253_div_255_no_depth_write_linear_clamp_front_planar"
    ),
    "precision": "host_double_to_sgm_f32_no_VU_GS_PICA_equivalence",
    "unrepresented": "all_decoded_metadata_and_14_sidecars_retained_no_original_MAP_rebuild",
}
SOURCES = ("geometry", "texture", "reference", "gs_report", "pixels_report")
DOCUMENTS = ("geometry", "material_reference", "gs_report", "pixels_report")
GEOMETRY_LIMITS = {"geometry.json": 8 * 1024 * 1024, "inspection.obj": 4 * 1024 * 1024}
TEXTURE_LIMITS = {"indices.bin": 65536}
for _palette in range(4):
    TEXTURE_LIMITS.update(
        {
            f"palette-{_palette}.bin": 1024,
            f"palette-{_palette}.rgba": 262144,
            f"palette-{_palette}.png": 1024 * 1024,
        }
    )
TEXTURE_EXACT = {k for k in TEXTURE_LIMITS if not k.endswith(".png")}
BLOB_NAMES = {"inspection.obj"} | set(TEXTURE_LIMITS)
OUTPUT_NAMES = BLOB_NAMES | {"intermediate.json", "geometry.sgm", "texture.stx"}


def _schema(document, scope):
    if (
        type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or document["scope"] != scope
    ):
        raise ValueError("Unsupported map source schema")


def _geometry(document, manifest):
    _schema(document, "ps2_map_group_geometry")
    _schema(manifest, "ps2_map_group_geometry")
    if len(document["shapes"]) != 2:
        raise ValueError("Expected two verified map shapes")
    if encode_json({k: v for k, v in manifest.items() if k not in {"files", "shapes"}}) != (
        encode_json({k: v for k, v in document.items() if k != "shapes"})
    ) or encode_json(manifest["shapes"]) != encode_json(
        [{k: v for k, v in s.items() if k not in GEOMETRY_FIELDS} for s in document["shapes"]]
    ):
        raise ValueError("Map metadata types or values differ")
    if any(type(count) is not int for count in document["summary"].values()):
        raise ValueError("Invalid map summary types")
    for shape in document["shapes"]:
        for name in (
            "vertex_count",
            "triangle_count",
            "skipped_count",
            "degenerate_count",
            "data_bytes",
        ):
            if type(shape[name]) is not int:
                raise ValueError("Invalid map count type")
        for triangle in shape["triangles"]:
            if len(triangle) != 3 or any(type(i) is not int for i in triangle):
                raise ValueError("Invalid map triangle type")
        if any(
            type(i) is not int
            for key in ("skipped_vertices", "degenerate_triangles")
            for i in shape[key]
        ):
            raise ValueError("Invalid map omitted vertex/triangle type")
    return verified_shapes(document, manifest)


def _texture(manifest, blobs):
    _schema(manifest, "ps2_indexed_texture_decode")
    if (
        manifest["recipe"] != CONVENTIONS["texture_decoder"]
        or manifest["orientation"] != "row_major_no_flip"
        or encode_json(manifest["alpha"])
        != encode_json(
            {"rgba": "original_ps2", "png": "min(255,2*a)", "loss": "png_alpha_saturation"}
        )
        or type(manifest["block"]["width"]) is not int
        or manifest["block"]["width"] != 256
        or type(manifest["block"]["height"]) is not int
        or manifest["block"]["height"] != 256
        or type(manifest["block"]["bpp"]) is not int
        or manifest["block"]["bpp"] != 8
        or type(manifest["block"]["clut"]["declared_count"]) is not int
        or manifest["block"]["clut"]["declared_count"] != 4
        or len(manifest["palettes"]) != 4
    ):
        raise ValueError("Unsupported map texture profile")
    image = IndexedTexture(
        256, 256, blobs["indices.bin"], tuple(blobs[f"palette-{i}.bin"] for i in range(4))
    )
    for i, row in enumerate(manifest["palettes"]):
        rgba = render_palette(image, i, normalize_alpha=False)
        palette = image.palettes[i]
        expected = dict(
            ordinal=i,
            alpha_min=min(rgba[3::4]),
            alpha_max=max(rgba[3::4]),
            normalized_saturated_pixels=sum(a >= 128 for a in rgba[3::4]),
            unique_rgba_colors=len({palette[j : j + 4] for j in range(0, 1024, 4)}),
            uniform_cc=palette == b"\xcc" * 1024,
            uniform_zero=palette == bytes(1024),
            preview_rgba_sha256=sha(render_palette(image, i, normalize_alpha=True)),
        )
        if rgba != blobs[f"palette-{i}.rgba"] or encode_json(
            {k: row[k] for k in expected}
        ) != encode_json(expected):
            raise ValueError("Map palette semantics differ")
    return blobs["palette-0.rgba"]


def _registers(words):
    if type(words) is not dict:
        raise ValueError("Invalid map GS register map")
    result = {}
    for key, value in words.items():
        if (
            len(key) != 2
            or any(c not in "0123456789abcdef" for c in key)
            or type(value) is not str
            or len(value) != 16
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("Invalid map GS register word")
        result[int(key, 16)] = int(value, 16)
    return result


def _references(value, shapes, rgba):
    docs, provenance = value["documents"], value["provenance"]
    ref, gs, px = (docs[k] for k in ("material_reference", "gs_report", "pixels_report"))
    gm, tm, pins = (
        provenance[k] for k in ("geometry_manifest", "texture_manifest", "source_sha256")
    )
    _schema(ref, "mr_t4d_material_reference")
    _schema(gs, "mr_t4d_3_consumed_gif_and_gs")
    _schema(px, "mr_t4d_4_sw_replay_interior_pixels")
    for key, target in (
        ("geometry_manifest_sha256", "geometry"),
        ("texture_manifest_sha256", "texture"),
        ("gs_report_sha256", "gs_report"),
        ("pixels_report_sha256", "pixels_report"),
    ):
        if ref[key] != pins[target]:
            raise ValueError("Map reference source differs")
    if (
        encode_json(ref["profile"]) != encode_json(MATERIAL_PROFILE)
        or gs["map_sha256"] != digest(gm["resource"]["sha256"])
        or gs["texture_sha256"] != digest(tm["resource"]["sha256"])
        or px["input_gs_sha256"] != digest(gs["dump_sha256"])
        or ref["texture_rgba_sha256"] != sha(rgba)
        or px["texture_rgba_sha256"] != sha(rgba)
        or gs["provenance"]["gs_dump_packets_modified"] is not False
        or gs["provenance"]["model_or_asset_modified"] is not False
        or px["original_packets_modified"] is not False
        or px["texture_rgba_exact_match"] is not True
        or px["depth_buffer_unchanged"] is not True
    ):
        raise ValueError("Unsupported map material evidence")
    for conclusions, keys in (
        (
            gs["conclusions"],
            ("both_shapes_consumed_by_gs", "both_transforms_verified", "blend_state_consumed"),
        ),
        (
            px["conclusions"],
            (
                "alpha_exact",
                "fog_verified",
                "texture_orientation_verified",
                "transparency_verified_for_both_shapes",
            ),
        ),
    ):
        if any(conclusions[k] is not True for k in keys):
            raise ValueError("Incomplete map evidence")
    model = MapAffine(ref["model_columns"]).columns
    model_sha = sha(struct.pack("<16f", *model))
    by_offset = dict(shapes)
    if len(ref["shapes"]) != 2 or len(gs["captures"]) != 2:
        raise ValueError("Incomplete map captures")
    captures = {c["state_sha256"]: c for c in gs["captures"]}
    if len(captures) != 2 or {s["state_sha256"] for s in ref["shapes"]} != set(captures):
        raise ValueError("Duplicate map capture")
    for state in captures:
        digest(state)
    for shape in ref["shapes"]:
        offset = shape["shape_offset"]
        if (
            type(offset) is not int
            or offset not in by_offset
            or shape["source_sha256"] != sha(encode_vertices(by_offset[offset].vertices))
        ):
            raise ValueError("Map captured shape differs")
        capture = captures[shape["state_sha256"]]
        if (
            capture["model_matrix_sha256"] != model_sha
            or capture["resources_unchanged"] is not True
        ):
            raise ValueError("Map captured model differs")
    expected_counts = {str(offset): len(g.triangles) for offset, g in shapes}
    if len(gs["frames"]) != 2 or len({frame["vsync_interval"] for frame in gs["frames"]}) != 2:
        raise ValueError("Incomplete GS frame evidence")
    for frame in gs["frames"]:
        if type(frame["vsync_interval"]) is not int or frame["vsync_interval"] < 1:
            raise ValueError("Invalid GS frame interval")
        r = _registers(frame["registers"])
        if (
            r[0] != MATERIAL_PROFILE["prim"]
            or r[0x42] != MATERIAL_PROFILE["alpha"]
            or r[0x47] != MATERIAL_PROFILE["test"]
            or r[0x3D] != 0
            or r[0x4E] >> 32 != 1
            or frame["stq_rgba_xyzf_match"] != "exact"
            or encode_json(frame["triangles_by_shape"]) != encode_json(expected_counts)
            or type(frame["triangles"]) is not int
            or frame["triangles"] != sum(expected_counts.values())
        ):
            raise ValueError("Consumed map state differs")
    if type(px["vsync_interval"]) is not int or px["vsync_interval"] not in {
        f["vsync_interval"] for f in gs["frames"]
    }:
        raise ValueError("Pixel replay frame differs")
    order = ref["draw_order"]
    if (
        type(order) is not list
        or any(type(o) is not int for o in order)
        or len(order) != 2
        or set(order) != set(by_offset)
    ):
        raise ValueError("Map draw order differs")
    offsets = [o for o in order for _ in by_offset[o].triangles]
    if any(
        type(t[k]) is not int for t in px["triangles"] for k in ("shape_offset", "triangle")
    ) or [(t["shape_offset"], t["triangle"]) for t in px["triangles"]] != list(
        zip(offsets, range(len(offsets)), strict=True)
    ):
        raise ValueError("Pixel replay topology/order differs")


def export_map(raw, blobs):
    """Regenerate from the owned JSON and fourteen sidecars, with no source I/O."""
    value = decode_json(raw)
    fields(
        value, ("schema_version", "profile", "converter", "conventions", "documents", "provenance")
    )
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["profile"] != PROFILE
        or value["converter"] != CONVERTER
        or encode_json(value["conventions"]) != encode_json(CONVENTIONS)
    ):
        raise ValueError("Unsupported map intermediate profile")
    fields(value["documents"], DOCUMENTS)
    fields(value["provenance"], ("geometry_manifest", "texture_manifest", "source_sha256"))
    fields(value["provenance"]["source_sha256"], SOURCES)
    for pin in value["provenance"]["source_sha256"].values():
        digest(pin)
    fields(blobs, BLOB_NAMES)
    try:
        docs, provenance = value["documents"], value["provenance"]
        gm, tm = provenance["geometry_manifest"], provenance["texture_manifest"]
        geometry_entries = inventory(gm, GEOMETRY_LIMITS)
        texture_entries = inventory(tm, TEXTURE_LIMITS, TEXTURE_EXACT)
        verify_file(blobs["inspection.obj"], geometry_entries["inspection.obj"])
        for name in TEXTURE_LIMITS:
            verify_file(blobs[name], texture_entries[name])
        shapes = _geometry(docs["geometry"], gm)
        if encode_obj(shapes) != blobs["inspection.obj"]:
            raise ValueError("Historical OBJ differs")
        rgba = _texture(tm, blobs)
        _references(value, shapes, rgba)
        sgm, _ = material_geometry(shapes, docs["material_reference"])
        stx = material_texture(rgba)
    except (KeyError, TypeError, IndexError, OverflowError) as error:
        raise ValueError("Malformed map intermediate") from error
    return {
        **blobs,
        "intermediate.json": encode_json(value),
        "geometry.sgm": sgm,
        "texture.stx": stx,
    }


def make_map(documents, provenance, blobs):
    raw = encode_json(
        dict(
            schema_version=1,
            profile=PROFILE,
            converter=CONVERTER,
            conventions=CONVENTIONS,
            documents=documents,
            provenance=provenance,
        )
    )
    return export_map(raw, blobs)
