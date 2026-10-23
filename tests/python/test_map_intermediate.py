"""IR-T6: constructed panels/palettes, known wire values and private custody."""

import copy
import json
import math
import shutil
import struct
import zlib
from pathlib import Path

import pytest
from test_geometry_inspection import own_documents

from tools.pipeline.geometry_obj import encode_obj
from tools.pipeline.intermediate_assets import sha
from tools.pipeline.intermediate_json import encode_json
from tools.pipeline.map_intermediate import (
    BLOB_NAMES,
    CONVENTIONS,
    CONVERTER,
    OUTPUT_NAMES,
    PROFILE,
    export_map,
    make_map,
)
from tools.pipeline.material_inspection import PROFILE as MATERIAL_PROFILE
from tools.pipeline.prepare_map_intermediate import main, prepare_files
from tools.pipeline.preview_png import encode_rgba_png
from tools.pipeline.private_texture_output import write_map_intermediate_bundle
from tools.pipeline.profile import ProfileError


def raw_json(v):
    return json.dumps(v).encode()


def entries(files):
    return [dict(file=k, size=len(v), sha256=sha(v)) for k, v in files.items()]


@pytest.fixture(scope="module")
def source_sample():
    geometry, gm, decoded = own_documents()
    for doc in (geometry, gm):
        doc["shapes"].append(copy.deepcopy(doc["shapes"][0]))
        doc["shapes"][1]["shape_offset"] = 384
        doc["summary"].update(shapes=2, vertices=6, triangles=2)
        doc["resource"]["sha256"] = "1" * 64
        doc["opaque"] = [True, 1, 1.0, -0.0, None, "retained"]
    blobs = {"inspection.obj": encode_obj([(192, decoded), (384, decoded)])}
    gm["files"] = entries({"geometry.json": raw_json(geometry), **blobs})
    # Independent byte indexing; asymmetric rows, RGB and original PS2 alpha.
    indices = bytes((x + 3 * y) % 256 for y in range(256) for x in range(256))
    palettes = [
        b"".join(bytes([i, 255 - i, i // 2, (0, 64, 128)[i % 3]]) for i in range(256)),
        b"\xcc" * 1024,
        bytes(1024),
        bytes([3, 2, 1, 128]) * 256,
    ]
    tm = dict(
        schema_version=1,
        scope="ps2_indexed_texture_decode",
        recipe=CONVENTIONS["texture_decoder"],
        orientation="row_major_no_flip",
        alpha=dict(rgba="original_ps2", png="min(255,2*a)", loss="png_alpha_saturation"),
        resource=dict(sha256="2" * 64, unknown_word=0xFFFFFFFF),
        block=dict(width=256, height=256, bpp=8, clut=dict(declared_count=4)),
        palettes=[],
    )
    blobs["indices.bin"] = indices
    for p, palette in enumerate(palettes):
        rgba = b"".join(palette[i * 4 : i * 4 + 4] for i in indices)
        preview = bytearray(rgba)
        preview[3::4] = bytes(min(255, 2 * a) for a in rgba[3::4])
        blobs[f"palette-{p}.bin"] = palette
        blobs[f"palette-{p}.rgba"] = rgba
        blobs[f"palette-{p}.png"] = encode_rgba_png(256, 256, bytes(preview))
        tm["palettes"].append(
            dict(
                ordinal=p,
                alpha_min=min(rgba[3::4]),
                alpha_max=max(rgba[3::4]),
                normalized_saturated_pixels=sum(a >= 128 for a in rgba[3::4]),
                unique_rgba_colors=len({palette[j : j + 4] for j in range(0, 1024, 4)}),
                uniform_cc=p == 1,
                uniform_zero=p == 2,
                preview_rgba_sha256=sha(preview),
                uninterpreted=[-0.0, 1.0],
            )
        )
    tm["files"] = entries({k: v for k, v in blobs.items() if k != "inspection.obj"})
    model = [2, 0, 0, 0, 0, -3, 0, 0, 0, 0, -1, 0, 100, -40, 30, 1]
    gs = dict(
        schema_version=1,
        scope="mr_t4d_3_consumed_gif_and_gs",
        map_sha256=gm["resource"]["sha256"],
        texture_sha256=tm["resource"]["sha256"],
        dump_sha256="3" * 64,
        provenance=dict(gs_dump_packets_modified=False, model_or_asset_modified=False),
        conclusions=dict(
            both_shapes_consumed_by_gs=True,
            both_transforms_verified=True,
            blend_state_consumed=True,
            viewer_change_allowed=False,
        ),
        captures=[
            dict(
                state_sha256=str(i) * 64,
                model_matrix_sha256=sha(struct.pack("<16f", *model)),
                resources_unchanged=True,
            )
            for i in (4, 5)
        ],
        frames=[
            dict(
                vsync_interval=i,
                registers={
                    f"{k:02x}": f"{v:016x}"
                    for k, v in {
                        0: 0x7B,
                        0x42: 0x8000000044,
                        0x47: 0x53000,
                        0x3D: 0,
                        0x4E: 0x13A0001C0,
                    }.items()
                },
                stq_rgba_xyzf_match="exact",
                triangles_by_shape={"192": 1, "384": 1},
                triangles=2,
            )
            for i in (1, 3)
        ],
    )
    px = dict(
        schema_version=1,
        scope="mr_t4d_4_sw_replay_interior_pixels",
        input_gs_sha256=gs["dump_sha256"],
        texture_rgba_sha256=sha(blobs["palette-0.rgba"]),
        original_packets_modified=False,
        texture_rgba_exact_match=True,
        depth_buffer_unchanged=True,
        conclusions=dict(
            alpha_exact=True,
            fog_verified=True,
            texture_orientation_verified=True,
            transparency_verified_for_both_shapes=True,
            hardware_3ds=False,
        ),
        vsync_interval=1,
        triangles=[dict(shape_offset=384, triangle=0), dict(shape_offset=192, triangle=1)],
    )
    pins = dict(
        geometry=sha(raw_json(gm)),
        texture=sha(raw_json(tm)),
        gs_report=sha(raw_json(gs)),
        pixels_report=sha(raw_json(px)),
    )
    ref = dict(
        schema_version=1,
        scope="mr_t4d_material_reference",
        geometry_manifest_sha256=pins["geometry"],
        texture_manifest_sha256=pins["texture"],
        gs_report_sha256=pins["gs_report"],
        pixels_report_sha256=pins["pixels_report"],
        texture_rgba_sha256=px["texture_rgba_sha256"],
        profile=copy.deepcopy(MATERIAL_PROFILE),
        model_columns=model,
        draw_order=[384, 192],
        shapes=[
            dict(
                shape_offset=s["shape_offset"],
                source_sha256=s["source_sha256"],
                state_sha256=str(i + 4) * 64,
                rgba=[[128, 64, 32, 127], [16, 32, 64, 127], [8, 16, 32, 127]]
                if i == 0
                else [[0, 128, 0, 127]] * 3,
            )
            for i, s in enumerate(gm["shapes"])
        ],
    )
    pins["reference"] = sha(raw_json(ref))
    value = dict(
        schema_version=1,
        profile=PROFILE,
        converter=CONVERTER,
        conventions=copy.deepcopy(CONVENTIONS),
        documents=dict(geometry=geometry, material_reference=ref, gs_report=gs, pixels_report=px),
        provenance=dict(geometry_manifest=gm, texture_manifest=tm, source_sha256=pins),
    )
    return value, blobs


@pytest.fixture
def sample(source_sample):
    return copy.deepcopy(source_sample)


def test_lossless_roundtrip_known_geometry_and_alpha(sample):
    v, blobs = sample
    before = copy.deepcopy(sample)
    files = make_map(v["documents"], v["provenance"], blobs)
    assert set(files) == OUTPUT_NAMES and len(files) == 17
    assert files == export_map(files["intermediate.json"], {k: files[k] for k in BLOB_NAMES})
    decoded = json.loads(files["intermediate.json"])
    assert encode_json(decoded) == encode_json(v)
    assert math.copysign(1, decoded["documents"]["geometry"]["opaque"][3]) == -1
    assert [type(x) for x in decoded["documents"]["geometry"]["opaque"][:4]] == [
        bool,
        int,
        float,
        float,
    ]
    assert all(files[k] == raw for k, raw in blobs.items())
    rows = list(struct.iter_unpack("<8f", files["geometry.sgm"][24:]))
    assert len(rows) == 6
    for i, xyz in enumerate([(-2 / 3, -1.25, -2), (2 / 3, -1.25, -2), (-2 / 3, 2.75, -2)]):
        assert rows[i][:3] == pytest.approx(xyz)
        assert rows[i][5:] == pytest.approx((0, 227 / 256, 0))
    assert rows[3][5:] == pytest.approx((227 / 256, 227 / 512, 227 / 1024))
    assert [r[3:5] for r in rows[:3]] == [(1 / 32768, 0), (16385 / 32768, 32767 / 32768), (0, -1)]
    assert struct.unpack_from("<I", files["geometry.sgm"], 20)[0] == zlib.crc32(
        files["geometry.sgm"][24:]
    )
    pixels = files["texture.stx"][24:]
    assert pixels[:12] == bytes([0, 255, 0, 0, 1, 254, 0, 128, 2, 253, 1, 255])
    assert pixels[256 * 4 : 256 * 4 + 4] == bytes([3, 252, 1, 0])
    assert files["palette-1.bin"] == b"\xcc" * 1024
    assert files["palette-1.rgba"] == b"\xcc" * 262144
    assert (v, blobs) == before


@pytest.mark.parametrize(
    "path,bad",
    [
        ("schema_version", True),
        ("profile", "other"),
        ("converter", "other"),
        ("conventions.material_uv", "flip"),
        ("provenance.source_sha256.geometry", "X" * 64),
        ("provenance.source_sha256.texture", None),
        ("documents.geometry.schema_version", True),
        ("documents.geometry.scope", "other"),
        ("documents.geometry.shapes", []),
        ("documents.geometry.shapes.0.vertex_count", True),
        ("documents.geometry.shapes.0.triangles.0", [0, 1]),
        ("documents.geometry.shapes.0.triangles.0.0", False),
        ("documents.geometry.shapes.0.vertices.0.position.0", 7),
        ("documents.geometry.shapes.0.triangles.0", [2, 1, 0]),
        ("provenance.geometry_manifest.files", []),
        ("provenance.geometry_manifest.files.0", None),
        ("provenance.geometry_manifest.files.0.file", "../outside"),
        ("provenance.geometry_manifest.files.0.file", "inspection.obj"),
        ("provenance.geometry_manifest.files.0.size", True),
        ("provenance.geometry_manifest.files.0.size", 8 * 1024 * 1024 + 1),
        ("provenance.texture_manifest.files.0.size", 65535),
        ("provenance.texture_manifest.alpha.png", "a"),
        ("provenance.texture_manifest.block.width", 128),
        ("provenance.texture_manifest.block.bpp", 8.0),
        ("provenance.texture_manifest.block.clut.declared_count", 4.0),
        ("provenance.texture_manifest.palettes.1.alpha_max", 128),
        ("documents.material_reference.geometry_manifest_sha256", "0" * 64),
        ("documents.material_reference.profile.depth_write", True),
        ("documents.material_reference.texture_rgba_sha256", "0" * 64),
        ("documents.material_reference.model_columns.12", 99),
        ("documents.material_reference.model_columns.0", True),
        ("documents.material_reference.shapes", []),
        ("documents.material_reference.shapes.0.source_sha256", "0" * 64),
        ("documents.material_reference.shapes.0.state_sha256", "5" * 64),
        ("documents.material_reference.shapes.0.rgba.0.3", 128),
        ("documents.material_reference.draw_order", [192, 192]),
        ("documents.material_reference.draw_order", [192, 384]),
        ("documents.gs_report.map_sha256", "0" * 64),
        ("documents.gs_report.provenance.model_or_asset_modified", True),
        ("documents.gs_report.conclusions.both_shapes_consumed_by_gs", False),
        ("documents.gs_report.captures.0.resources_unchanged", False),
        ("documents.gs_report.captures.0.state_sha256", "5" * 64),
        ("documents.gs_report.frames", []),
        ("documents.gs_report.frames.0.vsync_interval", 3),
        ("documents.gs_report.frames.0.vsync_interval", True),
        ("documents.gs_report.frames.0.registers", []),
        ("documents.gs_report.frames.0.registers.0", "000000000000007b"),
        ("documents.gs_report.frames.0.registers.42", "0000008000000045"),
        ("documents.gs_report.frames.0.registers.4e", "000000003a0001c0"),
        ("documents.gs_report.frames.0.registers.00", "0X7B"),
        ("documents.gs_report.frames.0.stq_rgba_xyzf_match", "approximate"),
        ("documents.gs_report.frames.0.triangles_by_shape.192", True),
        ("documents.pixels_report.vsync_interval", 2),
        ("documents.pixels_report.vsync_interval", True),
        ("documents.pixels_report.triangles.0.triangle", False),
        ("documents.pixels_report.triangles.0.shape_offset", 192),
        ("documents.pixels_report.conclusions.alpha_exact", False),
        ("documents.pixels_report.depth_buffer_unchanged", False),
        ("documents.pixels_report.triangles", None),
    ],
)
def test_rejects_mixed_or_unsupported_documents(sample, path, bad):
    v, blobs = sample
    parts = path.split(".")
    parent = v
    for key in parts[:-1]:
        parent = parent[int(key) if isinstance(parent, list) else key]
    parent[int(parts[-1]) if isinstance(parent, list) else parts[-1]] = bad
    with pytest.raises(ValueError):
        export_map(encode_json(v), blobs)


@pytest.mark.parametrize(
    "change", ["missing", "extra", "truncated", "type", "hash", "obj", "palette", "rgba"]
)
def test_rejects_changed_sidecars(sample, change):
    v, blobs = sample
    if change == "missing":
        del blobs["indices.bin"]
    elif change == "extra":
        blobs["unknown"] = b"a"
    elif change == "truncated":
        blobs["palette-0.png"] = b"x"
    elif change == "type":
        blobs["indices.bin"] = bytearray(blobs["indices.bin"])
    elif change == "hash":
        blobs["indices.bin"] = bytes(65536)
    else:
        name, manifest = (
            ("inspection.obj", "geometry_manifest")
            if change == "obj"
            else ("palette-0.bin" if change == "palette" else "palette-2.rgba", "texture_manifest")
        )
        blobs[name] = b"x" * len(blobs[name])
        next(e for e in v["provenance"][manifest]["files"] if e["file"] == name)["sha256"] = sha(
            blobs[name]
        )
    with pytest.raises(ValueError):
        export_map(encode_json(v), blobs)


@pytest.mark.parametrize("change", ["opaque", "summary", "skipped", "degenerate"])
def test_rejects_bool_numeric_aliases(sample, change):
    v, blobs = sample
    doc = v["documents"]["geometry"]
    manifest = v["provenance"]["geometry_manifest"]
    if change == "opaque":
        manifest["opaque"][1] = True
    elif change == "summary":
        doc["summary"]["degenerate_triangles"] = False
        manifest["summary"]["degenerate_triangles"] = False
    else:
        doc["shapes"][0][change + ("_vertices" if change == "skipped" else "_triangles")] = [
            False,
            True,
        ]
    with pytest.raises(ValueError):
        export_map(encode_json(v), blobs)


@pytest.fixture
def inputs(sample, tmp_path):
    v, blobs = sample
    source = tmp_path / "sources"
    source.mkdir()
    config = {}
    for key in ("geometry", "texture"):
        path = source / key
        path.mkdir()
        raw = raw_json(v["provenance"][key + "_manifest"])
        (path / "manifest.json").write_bytes(raw)
        config[key] = dict(path=str(path), sha256=sha(raw))
    (source / "geometry/geometry.json").write_bytes(raw_json(v["documents"]["geometry"]))
    for name, raw in blobs.items():
        (source / ("geometry" if name == "inspection.obj" else "texture") / name).write_bytes(raw)
    for key in ("reference", "gs_report", "pixels_report"):
        raw = raw_json(v["documents"]["material_reference" if key == "reference" else key])
        path = source / (key + ".json")
        path.write_bytes(raw)
        config[key] = dict(path=str(path), sha256=sha(raw))
    return config


def test_publish_exclusive_and_rebuild_after_removing_synthetic_sources(inputs, tmp_path):
    files, report = prepare_files(inputs)
    assert report["original_sidecars_preserved"] == 14
    assert report["logical_roundtrip"] and report["inspection_regeneration_identical"]
    assert not report["original_map_rebuild"] and not report["new_ps2_or_hardware_execution"]
    assert report["capabilities"] == []
    config = tmp_path / "config.json"
    config.write_bytes(raw_json(inputs))
    private, repo = tmp_path / "private", tmp_path / "repo"
    private.mkdir()
    repo.mkdir()
    args = ["--inputs", str(config), "--private-root", str(private), "--run-id", "map-test"]
    assert main(args) == 0
    output = private / "map-test"
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert main(args) == 1
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    manifest = json.loads((output / "manifest.json").read_bytes())
    for entry in manifest["files"]:
        path = output / entry["file"]
        assert sha(path.read_bytes()) == entry["sha256"]
        assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ProfileError):
        write_map_intermediate_bundle(repo, repo, "bad", files, report)
    with pytest.raises(ProfileError):
        write_map_intermediate_bundle(private, repo, "bad", {}, report)
    shutil.rmtree(tmp_path / "sources")
    assert export_map(before["intermediate.json"], {k: before[k] for k in BLOB_NAMES}) == files
    assert main(args) == 1


@pytest.mark.parametrize(
    "change", ["hash", "relative", "extra", "blob", "symlink", "json_duplicate", "oversized"]
)
def test_rejects_input_custody(inputs, tmp_path, change):
    if change == "hash":
        inputs["reference"]["sha256"] = "0" * 64
    elif change == "relative":
        inputs["texture"]["path"] = "relative"
    elif change == "extra":
        inputs["extra"] = {}
    elif change in ("blob", "symlink"):
        path = Path(inputs["texture"]["path"]) / "indices.bin"
        if change == "blob":
            path.write_bytes(b"bad")
        else:
            path.rename(tmp_path / "target")
            path.symlink_to(tmp_path / "target")
    else:
        path = Path(inputs["reference"]["path"])
        path.write_bytes(
            b'{"schema_version":1,"schema_version":1}'
            if change == "json_duplicate"
            else b" " * 131073
        )
        inputs["reference"]["sha256"] = sha(path.read_bytes())
    with pytest.raises((ValueError, OSError)):
        prepare_files(inputs)
