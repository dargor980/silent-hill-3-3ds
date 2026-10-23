"""Synthetic SCT1 encoding, resource linkage and exclusive delivery checks."""

import copy
import hashlib
import io
import json
import struct
import zipfile
import zlib

import pytest
import test_animation_inspection as animation_tests
import test_character_inspection as character_tests

from tools.pipeline.character_inspection import inspection_character
from tools.pipeline.character_material_inspection import IMAGES, encode_material, material_ranges
from tools.pipeline.prepare_character_material_probe import main, prepare_files


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture():
    mesh, clip = character_tests.fixture()
    mesh["submeshes"] = [copy.deepcopy(mesh["submeshes"][0]) for _ in range(15)]
    bindings = []
    for i, (submesh, image) in enumerate(zip(mesh["submeshes"], IMAGES, strict=True)):
        submesh.update(texture_index=image, offset=128 * i, header_words=[i])
        submesh["vertices"][0]["uv_q12"] = [-1024, 3072]
        bindings.append(
            dict(
                submesh=i,
                image=image,
                descriptor=image,
                palette=0,
                blend_partition=False,
                offset=128 * i,
                header_words=[i],
            )
        )
    textures = [bytes([i * 43, 29, 71, (0, 64, 128)[i]]) * 512**2 for i in range(3)]
    return mesh, clip, {"bindings": bindings}, textures


def test_wire_and_mapping():
    mesh, clip, materials, textures = fixture()
    scm = inspection_character(mesh, clip)
    ranges = material_ranges(mesh, materials)
    assert ranges == [(0, 18, 0), (18, 9, 1), (27, 18, 2)]
    raw = encode_material(ranges, textures, scm)
    assert len(raw) == 3145796 and raw[:8] == b"S3CTv1\0\0"
    assert struct.unpack_from("<6I", raw, 8) == (
        3,
        512,
        3,
        zlib.crc32(scm[32:]),
        len(raw) - 32,
        zlib.crc32(raw[32:]),
    )
    assert raw[68:] == b"".join(textures)
    assert raw == encode_material(ranges, textures, scm)


@pytest.mark.parametrize(
    "change",
    [
        "magic",
        "crc",
        "short",
        "size",
        "ranges",
        "gap",
        "empty",
        "fraction",
        "order",
        "coverage",
        "texture_count",
        "texture_size",
        "alpha",
        "negative",
    ],
)
def test_encoder_rejects(change):
    mesh, clip, materials, textures = fixture()
    scm = inspection_character(mesh, clip)
    ranges = material_ranges(mesh, materials)
    if change == "magic":
        scm = b"XXXXXXXX" + scm[8:]
    elif change == "crc":
        scm = scm[:-1] + bytes([scm[-1] ^ 1])
    elif change == "short":
        scm = b"bad"
    elif change == "size":
        scm += b"x"
    elif change == "ranges":
        ranges.pop()
    elif change == "gap":
        ranges[1] = (0, 9, 1)
    elif change == "empty":
        ranges[0] = (0, 0, 0)
    elif change == "fraction":
        ranges[0] = (0, 17, 0)
    elif change == "negative":
        ranges[0] = (0, -3, 0)
    elif change == "order":
        ranges[0] = (0, 18, 1)
    elif change == "coverage":
        ranges[2] = (27, 15, 2)
    elif change == "texture_count":
        textures.pop()
    elif change == "texture_size":
        textures[0] = textures[0][:-1]
    else:
        textures[0] = bytes([0, 0, 0, 129]) + textures[0][4:]
    with pytest.raises(ValueError):
        encode_material(ranges, textures, scm)


@pytest.mark.parametrize(
    "change",
    [
        "count",
        "submesh",
        "image",
        "descriptor",
        "palette",
        "blend_partition",
        "offset",
        "header_words",
        "texture_index",
    ],
)
def test_binding_rejects(change):
    mesh, _, materials, _ = fixture()
    if change == "count":
        mesh["submeshes"].pop()
    elif change == "texture_index":
        mesh["submeshes"][0][change] = 1
    else:
        materials["bindings"][0][change] = [99] if change == "header_words" else 99
    with pytest.raises(ValueError):
        material_ranges(mesh, materials)


@pytest.fixture
def bundle(tmp_path):
    _, _, _, _, build = animation_tests.bundle.__wrapped__(tmp_path)
    for p in list(build.iterdir()):
        if p.name.startswith("sh3_animation"):
            p.rename(build / p.name.replace("animation", "character_material"))
    (build / "SHA256SUMS").write_text(
        "".join(
            f"{sha(p.read_bytes())}  {p.name}\n"
            for p in sorted(build.iterdir())
            if p.name != "SHA256SUMS"
        )
    )
    mesh, clip, materials, textures = fixture()
    resources = dict(model=dict(sha256="a" * 64), animation=dict(sha256="b" * 64))

    def source(name, files, **metadata):
        path = tmp_path / name
        path.mkdir()
        inventory = []
        for name, raw in files.items():
            (path / name).write_bytes(raw)
            inventory.append(dict(file=name, size=len(raw), sha256=sha(raw)))
        raw = json.dumps(dict(metadata, files=inventory)).encode()
        (path / "manifest.json").write_bytes(raw)
        return path, sha(raw)

    ms, mh = source(
        "mesh-material",
        {"mesh.json": json.dumps(mesh).encode()},
        scope="ps2_character_mesh_candidate",
        resources=resources,
    )
    cs, ch = source(
        "old-viewer",
        {"animation.san": clip, "character.scm": inspection_character(mesh, clip)},
        scope="private_character_inspection",
        clip="0x1449",
        mesh_manifest_sha256=mh,
    )
    ts, th = source(
        "textures",
        {
            "materials.json": json.dumps(materials).encode(),
            **{f"texture-{i}.rgba": raw for i, raw in enumerate(textures)},
        },
        scope="ps2_character_material_candidate",
        resources=resources,
    )
    # Registers are synthetic and sufficient for the supported opaque profile.
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
    ref = tmp_path / "ct4.json"
    ref.write_text(
        json.dumps(
            dict(
                schema_version=1,
                scope="ct_t4_character_material",
                status="pass",
                provenance=dict(guest_writes=False, mdl_sha256="a" * 64),
                submeshes=[
                    dict(
                        submesh=i,
                        image=image,
                        registers={f"{k:02x}": f"{v:016x}" for k, v in registers.items()},
                    )
                    for i, image in enumerate(IMAGES)
                ],
                draws=[dict(image=i, texture_sha256=sha(raw)) for i, raw in enumerate(textures)],
            )
        )
    )
    return [cs, ch, ms, mh, ts, th, ref, sha(ref.read_bytes()), build]


def test_delivery(bundle, tmp_path):
    files, report = prepare_files(*bundle)
    assert (files, report) == prepare_files(*bundle)
    assert report["draw_calls"] == 3 and report["physical_2ds_xl"] == "pending"
    assert files["character.scm"] == (bundle[0] / "character.scm").read_bytes()
    assert files["animation.san"] == (bundle[0] / "animation.san").read_bytes()
    with zipfile.ZipFile(io.BytesIO(files["sd-card.zip"])) as z:
        assert z.read("3ds/sh3_character_material_probe/character.sct") == files["character.sct"]
    private = tmp_path / "private"
    private.mkdir()
    names = (
        "character-source",
        "character-sha256",
        "mesh-source",
        "mesh-sha256",
        "materials-source",
        "materials-sha256",
        "reference",
        "reference-sha256",
        "build",
    )
    args = [x for n, v in zip(names, bundle, strict=True) for x in ("--" + n, str(v))]
    args += ["--private-root", str(private), "--run-id", "material-fixture"]
    assert main(args) == 0
    with pytest.raises(FileExistsError):
        main(args)


@pytest.mark.parametrize(
    "change",
    [
        "hash",
        "status",
        "writes",
        "model",
        "count",
        "binding",
        "state",
        "texture",
        "tamper",
        "old_mesh",
    ],
)
def test_provenance_rejects(bundle, change):
    args = list(bundle)
    ref = json.loads(args[6].read_text())
    if change == "hash":
        args[7] = "0" * 64
    elif change == "status":
        ref["status"] = "fail"
    elif change == "writes":
        ref["provenance"]["guest_writes"] = True
    elif change == "model":
        ref["provenance"]["mdl_sha256"] = "c" * 64
    elif change == "count":
        ref["submeshes"].pop()
    elif change == "binding":
        ref["submeshes"][0]["image"] = 1
    elif change == "state":
        ref["submeshes"][0]["registers"]["00"] = "000000000000007c"
    elif change == "texture":
        ref["draws"][0]["texture_sha256"] = "c" * 64
    elif change == "tamper":
        (args[4] / "texture-0.rgba").write_bytes(b"x")
    else:
        (args[0] / "character.scm").write_bytes(b"x")
    if change != "hash":
        args[6].write_text(json.dumps(ref))
        args[7] = sha(args[6].read_bytes())
    with pytest.raises(ValueError):
        prepare_files(*args)


@pytest.mark.parametrize("change", ["duplicate", "size", "resource", "scm_binding"])
def test_manifest_cross_checks(bundle, change):
    args = list(bundle)
    index = 0 if change == "scm_binding" else 4
    path = args[index] / "manifest.json"
    manifest = json.loads(path.read_text())
    if change == "duplicate":
        manifest["files"].append(manifest["files"][0])
    elif change == "size":
        manifest["files"][0]["size"] += 1
    elif change == "resource":
        manifest["resources"]["animation"]["sha256"] = "c" * 64
    else:
        scm = args[0] / "character.scm"
        raw = bytearray(scm.read_bytes())
        struct.pack_into("<f", raw, 32, 123.0)
        struct.pack_into("<I", raw, 28, zlib.crc32(raw[32:]))
        scm.write_bytes(raw)
        for item in manifest["files"]:
            if item["file"] == "character.scm":
                item["sha256"] = sha(raw)
    path.write_text(json.dumps(manifest))
    args[index + 1] = sha(path.read_bytes())
    with pytest.raises(ValueError):
        prepare_files(*args)
