"""Synthetic SCL1 dependencies, coefficient mapping and private packaging."""

import copy
import hashlib
import io
import json
import struct
import zipfile
import zlib

import pytest
import test_animation_inspection as animation_tests
import test_character_material_inspection as material_tests

from tools.pipeline.character_inspection import inspection_character
from tools.pipeline.character_lighting_inspection import encode_lighting
from tools.pipeline.character_material_inspection import encode_material, material_ranges
from tools.pipeline.prepare_character_lighting_probe import main, prepare_files


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fixture():
    mesh, clip, materials, textures = material_tests.fixture()
    for i, s in enumerate(mesh["submeshes"]):
        raw = bytearray(144)
        raw[0x40] = 2
        struct.pack_into("<3f", raw, 0x60, 2 + i, 3 + i, 4 + i)
        struct.pack_into("<3f", raw, 0x70, 5 + i, 6 + i, 7 + i)
        s["header_words"] = list(struct.unpack("<36I", raw))
        materials["bindings"][i]["header_words"] = s["header_words"][:]
    scm = inspection_character(mesh, clip)
    sct = encode_material(material_ranges(mesh, materials), textures, scm)
    preset = dict(
        reference_counter=0,
        model_to_capture=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 2, 3, 4, 1],
        ambient=[0.1, 0.2, 0.3, 120],
        directionals=[dict(direction=[1, 2, 3], color=[4, 5, 6, 7]) for _ in range(3)],
        spot=dict(
            type=16,
            position=[1, 2, 3],
            direction=[0, 0, 1],
            color=[2, 3, 4, 5],
            attenuation=[100, -0.5, 4, -3],
        ),
    )
    return preset, mesh, scm, clip, sct


def test_wire_layout_and_coefficients():
    args = fixture()
    raw = encode_lighting(*args)
    assert len(raw) == 872 and raw == encode_lighting(*args)
    assert struct.unpack_from("<10I", raw, 8) == (
        1,
        15,
        3,
        *(zlib.crc32(x[32:]) for x in args[2:]),
        45,
        45,
        824,
        zlib.crc32(raw[48:]),
    )
    assert struct.unpack_from("<16f", raw, 52) == tuple(args[0]["model_to_capture"])
    for i in range(15):
        assert struct.unpack_from("<4I6f", raw, 272 + i * 40) == (
            i * 3,
            3,
            i * 3,
            3,
            2 + i,
            3 + i,
            4 + i,
            5 + i,
            6 + i,
            7 + i,
        )


@pytest.mark.parametrize(
    "change",
    [
        "scm",
        "san",
        "sct",
        "short",
        "large_count",
        "shape",
        "clip_id",
        "sct_binding",
        "counter",
        "nan",
        "nonaffine",
        "scale",
        "reflection",
        "ambient",
        "directions",
        "spot_type",
        "spot_direction",
        "attenuation",
        "mode",
        "blend",
        "vertices",
        "triangles",
        "cross_range",
        "material_nan",
        "material_high",
        "coverage",
    ],
)
def test_encoder_rejects(change):
    p, m, scm, san, sct = fixture()
    if change in ("scm", "san", "sct"):
        inputs = [scm, san, sct]
        i = ("scm", "san", "sct").index(change)
        inputs[i] = inputs[i][:-1] + bytes([inputs[i][-1] ^ 1])
        scm, san, sct = inputs
    elif change == "short":
        scm = b""
    elif change == "large_count":
        scm = bytearray(scm)
        struct.pack_into("<I", scm, 8, 2049)
        scm = bytes(scm)
    elif change == "shape":
        m["submeshes"].pop()
    elif change == "clip_id":
        san = bytearray(san)
        struct.pack_into("<I", san, 16, 0x144A)
        san = bytes(san)
    elif change == "sct_binding":
        sct = bytearray(sct)
        struct.pack_into("<I", sct, 20, 0)
        sct = bytes(sct)
    elif change == "counter":
        p["reference_counter"] = True
    elif change == "nan":
        p["model_to_capture"][0] = float("nan")
    elif change == "nonaffine":
        p["model_to_capture"][3] = 1
    elif change == "scale":
        p["model_to_capture"][0] = 2
    elif change == "reflection":
        p["model_to_capture"][0] = -1
    elif change == "ambient":
        p["ambient"][0] = 17
    elif change == "directions":
        p["directionals"].pop()
    elif change == "spot_type":
        p["spot"]["type"] = 10
    elif change == "spot_direction":
        p["spot"]["direction"] = [0, 1]
    elif change == "attenuation":
        p["spot"]["attenuation"][0] = 1000001
    elif change == "mode":
        m["submeshes"][0]["header_words"][16] = 4
    elif change == "blend":
        m["submeshes"][0]["blend_partition"] = True
    elif change == "vertices":
        m["submeshes"][0]["vertices"].pop()
    elif change == "triangles":
        m["submeshes"][0]["triangles"] = []
    elif change == "cross_range":
        scm = bytearray(scm)
        struct.pack_into("<H", scm, len(scm) - 90, 3)
        struct.pack_into("<I", scm, 28, zlib.crc32(scm[32:]))
        scm = bytes(scm)
        sct = bytearray(sct)
        struct.pack_into("<I", sct, 20, zlib.crc32(scm[32:]))
        sct = bytes(sct)
    elif change in ("material_nan", "material_high"):
        m["submeshes"][0]["header_words"][24] = struct.unpack(
            "<I", struct.pack("<f", float("nan") if change == "material_nan" else 129)
        )[0]
    else:
        m["submeshes"][-1]["vertices"].append(copy.deepcopy(m["submeshes"][-1]["vertices"][0]))
    with pytest.raises(ValueError):
        encode_lighting(p, m, scm, san, sct)


@pytest.fixture
def bundle(tmp_path):
    _, _, _, _, build = animation_tests.bundle.__wrapped__(tmp_path)
    for path in list(build.iterdir()):
        if path.name.startswith("sh3_animation"):
            path.rename(build / path.name.replace("animation", "character_lighting"))
    (build / "SHA256SUMS").write_text(
        "".join(
            f"{sha(p.read_bytes())}  {p.name}\n"
            for p in sorted(build.iterdir())
            if p.name != "SHA256SUMS"
        )
    )
    preset, mesh, scm, san, sct = fixture()

    def source(name, files, **metadata):
        path = tmp_path / name
        path.mkdir()
        for name, data in files.items():
            (path / name).write_bytes(data)
        raw = json.dumps(
            dict(
                metadata, files=[dict(file=n, size=len(b), sha256=sha(b)) for n, b in files.items()]
            )
        ).encode()
        (path / "manifest.json").write_bytes(raw)
        return path, sha(raw)

    mesh_raw = json.dumps(mesh).encode()
    ms, mh = source(
        "mesh",
        {"mesh.json": mesh_raw},
        scope="ps2_character_mesh_candidate",
        resources={"model": {"sha256": "a" * 64}},
    )
    old, oh = source(
        "material",
        {"character.scm": scm, "animation.san": san, "character.sct": sct},
        scope="private_character_material_inspection",
        mesh_manifest_sha256=mh,
        gpu_vertex_bytes_per_frame=45 * 36,
        gpu_texture_bytes=3 * 1048576,
    )
    pose = dict(
        input_sha256="b" * 64, output_sha256="c" * 64, draw_parameters_sha256="d" * 64, counter=0
    )
    ref = dict(
        status="pass",
        scope="li_mode2_type10_character_lighting",
        poses=[pose] * 4,
        provenance=dict(new_guest_writes=False, mdl_sha256="a" * 64, mesh_sha256=sha(mesh_raw)),
    )
    rp = tmp_path / "reference.json"
    rp.write_text(json.dumps(ref))
    rh = sha(rp.read_bytes())
    preset.update(
        schema_version=1,
        scope="captured_character_lighting_preset",
        li_report_sha256=rh,
        **{k: v for k, v in pose.items() if k != "counter"},
    )
    pp = tmp_path / "preset.json"
    pp.write_text(json.dumps(preset))
    ph = sha(pp.read_bytes())
    return (old, oh, ms, mh, pp, ph, rp, rh, build)


def test_preparation_and_exclusive_output(bundle, tmp_path):
    files, report = prepare_files(*bundle)
    assert files == prepare_files(*bundle)[0] and len(files["character.scl"]) == 872
    assert (
        report["physical_2ds_xl"] == "pending"
        and report["lighting"] == "fixed_capture_preset_recomputed_per_pose"
    )
    with zipfile.ZipFile(io.BytesIO(files["sd-card.zip"])) as z:
        assert len(z.namelist()) == 8
        assert z.read("3ds/sh3_character_lighting_probe/character.scl") == files["character.scl"]
    private = tmp_path / "private"
    private.mkdir()
    argv = []
    for k, v in zip(
        (
            "material-source",
            "material-sha256",
            "mesh-source",
            "mesh-sha256",
            "preset",
            "preset-sha256",
            "reference",
            "reference-sha256",
            "build",
        ),
        bundle,
        strict=True,
    ):
        argv += ["--" + k, str(v)]
    argv += ["--private-root", str(private), "--run-id", "lighting-test"]
    assert main(argv) == 0
    with pytest.raises((FileExistsError, ValueError)):
        main(argv)


@pytest.mark.parametrize(
    "field",
    ["identity", "status", "capture", "counter", "mesh", "preset_hash", "reference_hash", "mode"],
)
def test_preparer_rejects_provenance(bundle, field):
    args = list(bundle)
    if field == "preset_hash":
        args[5] = "0" * 64
    elif field == "reference_hash":
        args[7] = "0" * 64
    elif field in ("capture", "counter", "mode"):
        p = json.loads(args[4].read_text())
        if field == "capture":
            p["output_sha256"] = "0" * 64
        elif field == "counter":
            p["reference_counter"] = 1
        else:
            p["spot"]["type"] = 10
        args[4].write_text(json.dumps(p))
        args[5] = sha(args[4].read_bytes())
    else:
        ref = json.loads(args[6].read_text())
        if field == "identity":
            ref["provenance"]["mdl_sha256"] = "0" * 64
        elif field == "mesh":
            ref["provenance"]["mesh_sha256"] = "0" * 64
        else:
            ref["status"] = "failed"
        args[6].write_text(json.dumps(ref))
        args[7] = sha(args[6].read_bytes())
        p = json.loads(args[4].read_text())
        p["li_report_sha256"] = args[7]
        args[4].write_text(json.dumps(p))
        args[5] = sha(args[4].read_bytes())
    with pytest.raises(ValueError):
        prepare_files(*args)
