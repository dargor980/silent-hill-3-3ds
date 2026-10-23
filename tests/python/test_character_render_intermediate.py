"""Lossless render sidecars, independent texture expectations and private custody."""

import copy
import io
import json
import math
import shutil
import struct
import zipfile
from pathlib import Path

import pytest
import test_character_intermediate as base_tests
import test_character_lighting_inspection as lighting_tests
import test_character_material_inspection as material_tests
import test_character_world_inspection as world_tests

from tools.pipeline.character_intermediate import export_inspection, make_intermediate
from tools.pipeline.character_lighting_inspection import encode_lighting
from tools.pipeline.character_render_intermediate import (
    BLOB_LIMITS,
    CONVENTIONS,
    CONVERTER,
    OUTPUT_NAMES,
    PROFILE,
    SOURCES,
    export_render,
    sha,
)
from tools.pipeline.character_world_inspection import encode_world
from tools.pipeline.intermediate_json import encode_json
from tools.pipeline.prepare_character_render_intermediate import main, prepare_files
from tools.pipeline.preview_png import encode_rgba_png


def raw_json(value):
    return json.dumps(value).encode()


def manifest(files, **metadata):
    return dict(
        metadata, files=[dict(file=k, size=len(v), sha256=sha(v)) for k, v in files.items()]
    )


@pytest.fixture
def sample():
    docs, origin = base_tests.fixture()
    preset, mesh, _, _, _ = lighting_tests.fixture()
    _, _, materials, textures = material_tests.fixture()
    mesh["skeleton"] = docs["mesh"]["skeleton"]
    mesh["uninterpreted"] = [-0.0, True, 1, 1.0, "retained"]
    docs["mesh"] = mesh
    for name in origin:
        origin[name]["resources"]["model"].update(size=833712, sha256=sha(bytes(833712)))
        origin[name]["files"] = manifest(
            {k + ".json": raw_json(v) for k, v in docs.items() if (k == "mesh") == (name == "mesh")}
        )["files"]
    base_raw = make_intermediate(docs, origin)
    base = json.loads(base_raw)
    base_files = export_inspection(base_raw)
    old = manifest(
        base_files,
        schema_version=1,
        scope="private_character_intermediate",
        profile=base["profile"],
    )
    for s, b in zip(mesh["submeshes"], materials["bindings"], strict=True):
        b["header_words"] = s["header_words"][:]
    materials.update(schema_version=1, model_id=0x209, unknown_flags=[0xFFFFFFFF, -0.0])
    materials["textures"] = []
    blobs = {}
    for i, rgba in enumerate(textures):
        color = rgba[:4]
        preview = color[:3] + bytes([min(255, color[3] * 2)])
        blobs[f"image-{i}.indices"] = bytes(262144)
        for p in range(4):
            blobs[f"image-{i}-palette-{p}.bin"] = (color if p == 0 else bytes([p, 2, 3, 128])) * 256
        blobs[f"texture-{i}.rgba"] = rgba
        blobs[f"texture-{i}.png"] = encode_rgba_png(512, 512, preview * 262144)
        materials["textures"].append(
            dict(
                descriptor=i,
                image=i,
                palette=0,
                width=512,
                height=512,
                alpha_min=color[3],
                alpha_max=color[3],
                preview_rgba_sha256=sha(preview * 262144),
            )
        )
    mm = manifest(
        {"materials.json": raw_json(materials), **blobs},
        schema_version=1,
        scope="ps2_character_material_candidate",
        recipe=CONVENTIONS["materials_decoder"],
        resources=copy.deepcopy(origin["mesh"]["resources"]),
        opaque_metadata={"retained": True},
    )
    registers = {
        0: 0x3C,
        0x1A: 1,
        6: 0x2006D80665322800,
        8: 0x7FC007FC00A,
        0x14: 0x61,
        0x47: 0x50002,
        0x42: 0x44,
        0x4C: 0x80000,
        0x4E: 0x3A0001C0,
        0x4A: 0,
        0x49: 0,
        0x45: 0,
        0x46: 1,
        0x3D: 0,
        0x3B: 0x8000000080,
        0x22: 0,
    }
    ct = dict(
        schema_version=1,
        scope="ct_t4_character_material",
        status="pass",
        provenance=dict(
            guest_writes=False, mdl_sha256=origin["mesh"]["resources"]["model"]["sha256"]
        ),
        submeshes=[
            dict(
                submesh=i,
                image=b["image"],
                registers={f"{k:02x}": f"{v:016x}" for k, v in registers.items()},
            )
            for i, b in enumerate(materials["bindings"])
        ],
        draws=[dict(image=i, texture_sha256=sha(rgba)) for i, rgba in enumerate(textures)],
        unknown_register_words=[1, 0xFFFFFFFF],
    )
    pose = dict(
        input_sha256="b" * 64, output_sha256="c" * 64, draw_parameters_sha256="d" * 64, counter=0
    )
    li = dict(
        scope="li_mode2_type10_character_lighting",
        status="pass",
        poses=[copy.deepcopy(pose) for _ in range(4)],
        provenance=dict(
            new_guest_writes=False,
            mdl_sha256=ct["provenance"]["mdl_sha256"],
            mesh_sha256=sha(raw_json(mesh)),
        ),
    )
    preset.update(
        schema_version=1,
        scope="captured_character_lighting_preset",
        li_report_sha256=sha(raw_json(li)),
        **{k: v for k, v in pose.items() if k != "counter"},
        unknown_field=[1, 2, -0.0],
    )
    instances = world_tests.instances()
    for i, instance in enumerate(instances):
        instance["id"] = 398 + i
    gc = dict(
        schema_version=1,
        scope="gc_t4_character_world_bounded",
        status="pass",
        guest_writes=False,
        instance_observations=84,
        code_windows=[dict(address="0x100000", size=16, sha256=sha(bytes(16)))],
        continuous_snapshots=[
            dict(
                slot=8,
                sha256="e" * 64,
                actors=[
                    dict(
                        address=hex(0x44D630 + i * 0x320),
                        instance=s["id"],
                        position=s["model"][12:],
                        rotation=[0] * 4,
                        counter=66220,
                    )
                    for i, s in enumerate(instances)
                ],
            )
        ],
    )
    documents = dict(
        materials=materials,
        material_reference=ct,
        lighting_preset=preset,
        lighting_reference=li,
        world_reference=gc,
        world_placements=dict(instances=instances, reference_counter=66220),
    )
    pins = {k: "a" * 64 for k in SOURCES}
    pins.update(
        base=sha(raw_json(old)),
        materials=sha(raw_json(mm)),
        world_state="e" * 64,
        **{
            k: sha(raw_json(documents[k]))
            for k in (
                "material_reference",
                "lighting_preset",
                "lighting_reference",
                "world_reference",
            )
        },
    )
    value = dict(
        schema_version=1,
        profile=PROFILE,
        converter=CONVERTER,
        conventions=copy.deepcopy(CONVENTIONS),
        base=base,
        documents=documents,
        provenance=dict(base_manifest=old, materials_manifest=mm, source_sha256=pins),
    )
    return value, blobs


def test_lossless_roundtrip_and_known_bytes(sample):
    value, blobs = sample
    before = copy.deepcopy(sample)
    files = export_render(encode_json(value), blobs)
    assert set(files) == OUTPUT_NAMES and len(files) == 27
    assert files == export_render(files["intermediate.json"], {k: files[k] for k in BLOB_LIMITS})
    decoded = json.loads(files["intermediate.json"])
    assert encode_json(decoded) == encode_json(value)
    assert math.copysign(1, decoded["documents"]["materials"]["unknown_flags"][-1]) == -1
    assert all(files[k] == raw for k, raw in blobs.items())
    assert files["character.sct"][68:] == b"".join(blobs[f"texture-{i}.rgba"] for i in range(3))
    assert struct.unpack_from("<9I", files["character.sct"], 32) == (0, 18, 0, 18, 9, 1, 27, 18, 2)
    assert files["character.scl"] == encode_lighting(
        value["documents"]["lighting_preset"],
        value["base"]["documents"]["mesh"],
        files["character.scm"],
        files["animation.san"],
        files["character.sct"],
    )
    world = value["documents"]["world_placements"]
    assert files["character.scw"] == encode_world(
        world["instances"],
        66220,
        files["character.scm"],
        files["animation.san"],
        files["character.sct"],
    )
    assert [struct.unpack_from("<I", files["character.scw"], 56 + i * 68)[0] for i in range(3)] == [
        398,
        399,
        400,
    ]
    assert (value, blobs) == before


@pytest.mark.parametrize(
    "change",
    [
        "schema",
        "profile",
        "converter",
        "convention",
        "extra",
        "documents",
        "provenance",
        "pins",
        "digest",
        "base_scope",
        "base_file",
        "material_schema",
        "material_recipe",
        "resource",
        "ct_status",
        "ct_guest",
        "ct_binding",
        "ct_alpha",
        "li_link",
        "li_identity",
        "li_mesh",
        "li_pose",
        "li_count",
        "gc_state",
        "gc_status",
        "gc_slot",
        "gc_ids",
        "gc_position",
        "gc_counter",
        "inventory_extra",
        "inventory_duplicate",
        "inventory_size",
        "inventory_digest",
        "missing_blob",
        "extra_blob",
        "blob_size",
        "blob_hash",
        "texture_count",
        "texture_metadata",
        "texture_draw",
        "palette_semantics",
        "binding",
        "light_type",
        "world_scale",
        "malformed",
        "register_type",
        "register_alias",
        "ct_image_type",
        "texture_type",
        "binding_type",
    ],
)
def test_rejects_mixed_or_invalid_inputs(sample, change):
    v, blobs = sample
    d, p = v["documents"], v["provenance"]
    ct, li, gc = d["material_reference"], d["lighting_reference"], d["world_reference"]
    mm = p["materials_manifest"]
    if change == "schema":
        v["schema_version"] = True
    elif change == "profile":
        v["profile"] = "unknown"
    elif change == "converter":
        v["converter"] = "v2"
    elif change == "convention":
        v["conventions"]["composition"] = "combined"
    elif change == "extra":
        v["extra"] = 1
    elif change == "documents":
        del d["materials"]
    elif change == "provenance":
        p["extra"] = 1
    elif change == "pins":
        del p["source_sha256"]["base"]
    elif change == "digest":
        p["source_sha256"]["base"] = "z" * 64
    elif change == "base_scope":
        p["base_manifest"]["scope"] = "other"
    elif change == "base_file":
        p["base_manifest"]["files"][0]["size"] += 1
    elif change == "material_schema":
        mm["schema_version"] = True
    elif change == "material_recipe":
        mm["recipe"] = "other"
    elif change == "resource":
        mm["resources"]["model"]["sha256"] = "0" * 64
    elif change == "ct_status":
        ct["status"] = "fail"
    elif change == "ct_guest":
        ct["provenance"]["guest_writes"] = True
    elif change == "ct_binding":
        ct["submeshes"][0]["image"] = 2
    elif change == "ct_alpha":
        ct["submeshes"][0]["registers"]["00"] = "000000000000007c"
    elif change == "li_link":
        d["lighting_preset"]["li_report_sha256"] = "0" * 64
    elif change == "li_identity":
        li["provenance"]["mdl_sha256"] = "0" * 64
    elif change == "li_mesh":
        li["provenance"]["mesh_sha256"] = "0" * 64
    elif change == "li_pose":
        li["poses"][-1]["output_sha256"] = "0" * 64
    elif change == "li_count":
        li["poses"].pop()
    elif change == "gc_state":
        gc["continuous_snapshots"][0]["sha256"] = "0" * 64
    elif change == "gc_status":
        gc["status"] = "fail"
    elif change == "gc_slot":
        gc["continuous_snapshots"][0]["slot"] = 9
    elif change == "gc_ids":
        d["world_placements"]["instances"][0]["id"] = 399
    elif change == "gc_position":
        d["world_placements"]["instances"][0]["model"][12] += 1
    elif change == "gc_counter":
        d["world_placements"]["reference_counter"] += 1
    elif change == "inventory_extra":
        mm["files"][1]["file"] = "../outside"
    elif change == "inventory_duplicate":
        mm["files"][1] = mm["files"][2]
    elif change == "inventory_size":
        mm["files"][1]["size"] = True
    elif change == "inventory_digest":
        mm["files"][1]["sha256"] = "z" * 64
    elif change == "missing_blob":
        blobs.pop("image-0.indices")
    elif change == "extra_blob":
        blobs["extra"] = b"x"
    elif change == "blob_size":
        blobs["texture-0.rgba"] += b"x"
    elif change == "blob_hash":
        blobs["texture-0.rgba"] = b"x" * 1048576
    elif change == "texture_count":
        d["materials"]["textures"].pop()
    elif change == "texture_metadata":
        d["materials"]["textures"][0]["preview_rgba_sha256"] = "0" * 64
    elif change == "texture_draw":
        ct["draws"][0]["texture_sha256"] = "0" * 64
    elif change == "palette_semantics":
        name = "image-0-palette-0.bin"
        blobs[name] = bytes(1024)
        next(e for e in mm["files"] if e["file"] == name)["sha256"] = sha(blobs[name])
    elif change == "binding":
        d["materials"]["bindings"][0]["palette"] = 1
    elif change == "light_type":
        d["lighting_preset"]["spot"]["type"] = 17
    elif change == "world_scale":
        d["world_placements"]["instances"][0]["model"][2] = 2
    elif change == "malformed":
        ct["submeshes"] = None
    elif change == "register_type":
        ct["submeshes"][0]["registers"] = []
    elif change == "register_alias":
        ct["submeshes"][0]["registers"]["0"] = ct["submeshes"][0]["registers"]["00"]
    elif change == "ct_image_type":
        ct["submeshes"][0]["image"] = False
    elif change == "texture_type":
        d["materials"]["textures"][0]["palette"] = False
    elif change == "binding_type":
        d["materials"]["bindings"][0]["palette"] = False
    with pytest.raises(ValueError):
        export_render(encode_json(v), blobs)


@pytest.fixture
def inputs(sample, tmp_path):
    v, blobs = sample
    source = tmp_path / "sources"
    source.mkdir()
    config = {}

    def put(key, raw, filename=None):
        target = source / key
        if filename:
            target.mkdir(exist_ok=True)
            path = target / filename
        else:
            path = target
        path.write_bytes(raw)
        config[key] = dict(path=str(target), sha256=sha(raw))
        return target

    base_files = export_inspection(encode_json(v["base"]))
    bs = put("base", raw_json(v["provenance"]["base_manifest"]), "manifest.json")
    for name, raw in base_files.items():
        (bs / name).write_bytes(raw)
    ms = put("materials", raw_json(v["provenance"]["materials_manifest"]), "manifest.json")
    for name, raw in {"materials.json": raw_json(v["documents"]["materials"]), **blobs}.items():
        (ms / name).write_bytes(raw)
    for key in ("material_reference", "lighting_preset", "lighting_reference"):
        put(key, raw_json(v["documents"][key]))
    ram = bytearray(32 * 1024 * 1024)
    for actor, placement in zip(
        v["documents"]["world_reference"]["continuous_snapshots"][0]["actors"],
        v["documents"]["world_placements"]["instances"],
        strict=True,
    ):
        a = int(actor["address"], 16)
        struct.pack_into("<HH", ram, a + 12, 0x209, actor["instance"])
        struct.pack_into("<4f", ram, a + 0x20, *actor["position"])
        struct.pack_into("<16f", ram, a + 0x40, *placement["model"])
        struct.pack_into("<I", ram, a + 0x278, 66220)
        struct.pack_into("<I", ram, a + 0x308, 0x900000 + 96)
        struct.pack_into("<I", ram, a + 0x30C, 0xB00000)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("eeMemory.bin", ram)
        z.writestr("synthetic.txt", "own fixture")
    put("world_state", buffer.getvalue())
    v["documents"]["world_reference"]["continuous_snapshots"][0]["sha256"] = sha(buffer.getvalue())
    put("world_reference", raw_json(v["documents"]["world_reference"]))
    return config


def test_import_publish_then_rebuild_without_sources(inputs, tmp_path):
    first, report = prepare_files(inputs)
    assert report["original_blobs_preserved"] == 21 and report["logical_roundtrip"]
    assert first == prepare_files(inputs)[0]
    config_path = tmp_path / "inputs.json"
    config_path.write_bytes(raw_json(inputs))
    root = tmp_path / "private"
    root.mkdir()
    argv = ["--inputs", str(config_path), "--private-root", str(root), "--run-id", "render-test"]
    assert main(argv) == 0
    dest = root / "render-test"
    before = {p.name: p.read_bytes() for p in dest.iterdir()}
    assert main(argv) == 1
    assert before == {p.name: p.read_bytes() for p in dest.iterdir()}
    shutil.rmtree(tmp_path / "sources")
    assert (
        export_render(
            (dest / "intermediate.json").read_bytes(),
            {name: (dest / name).read_bytes() for name in BLOB_LIMITS},
        )
        == first
    )
    assert main(argv) == 1


@pytest.mark.parametrize(
    "change", ["hash", "blob", "json_duplicate", "state", "relative", "extra", "symlink"]
)
def test_import_rejects_custody(inputs, tmp_path, change):
    if change == "hash":
        inputs["base"]["sha256"] = "0" * 64
    elif change == "relative":
        inputs["base"]["path"] = "relative"
    elif change == "extra":
        inputs["extra"] = {}
    elif change == "blob":
        (Path(inputs["materials"]["path"]) / "texture-0.rgba").write_bytes(b"bad")
    elif change == "json_duplicate":
        p = Path(inputs["material_reference"]["path"])
        p.write_bytes(b'{"schema_version":1,"schema_version":1}')
        inputs["material_reference"]["sha256"] = sha(p.read_bytes())
    elif change == "state":
        inputs["world_state"]["sha256"] = "0" * 64
    elif change == "symlink":
        p = Path(inputs["materials"]["path"]) / "texture-0.rgba"
        p.rename(tmp_path / "target")
        p.symlink_to(tmp_path / "target")
    with pytest.raises((ValueError, OSError)):
        prepare_files(inputs)
