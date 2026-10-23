"""Synthetic world placements, custody links and deterministic SD packaging."""

import copy
import hashlib
import io
import json
import struct
import zipfile
import zlib

import pytest
import test_character_lighting_inspection as lighting_tests

from tools.pipeline.character_world_inspection import encode_world
from tools.pipeline.prepare_character_world_probe import extract_instances, main, prepare_files


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def instances():
    return [
        dict(
            id=i + 1,
            model=[0, 0, -1, 0, -1, 0, 0, 0, 0, 1, 0, 0, 100011 + i * 11, -100007, 200013, 1],
        )
        for i in range(3)
    ]


def test_wire_framing_and_determinism():
    _, _, scm, san, sct = lighting_tests.fixture()
    data = encode_world(instances(), 66220, scm, san, sct)
    assert len(data) == 264 and data == encode_world(instances(), 66220, scm, san, sct)
    assert struct.unpack_from("<8I", data, 8) == (
        1,
        3,
        *(zlib.crc32(x[32:]) for x in (scm, san, sct)),
        66220,
        224,
        zlib.crc32(data[40:]),
    )
    assert [struct.unpack_from("<I", data, 56 + i * 68)[0] for i in range(3)] == [1, 2, 3]
    assert data[-4:] == bytes(4)
    origin = struct.unpack_from("<3f", data, 40)
    assert all(abs(v) > 90000 for v in origin)
    assert 0 < struct.unpack_from("<f", data, 52)[0] < 1


@pytest.mark.parametrize(
    "change",
    [
        "count",
        "duplicate",
        "id",
        "counter",
        "nan",
        "reflection",
        "scale",
        "affine",
        "translation",
        "scm",
        "san",
        "sct",
        "profile",
        "model_scale",
        "origin",
    ],
)
def test_rejects_invalid_profile(change):
    _, _, scm, san, sct = lighting_tests.fixture()
    placed = instances()
    counter = 0
    if change == "count":
        placed.pop()
    elif change == "duplicate":
        placed[1]["id"] = 1
    elif change == "id":
        placed[0]["id"] = True
    elif change == "counter":
        counter = 98304
    elif change == "nan":
        placed[0]["model"][0] = float("nan")
    elif change == "reflection":
        placed[0]["model"][2] = 1
    elif change == "scale":
        placed[0]["model"][2] = 2
    elif change == "affine":
        placed[0]["model"][3] = 1
    elif change == "translation":
        placed[0]["model"][12] = 1000001
    elif change == "scm":
        scm = scm[:-1]
    elif change == "san":
        san = san[:-1]
    elif change == "sct":
        sct = sct[:-1]
    elif change == "profile":
        san = bytearray(san)
        struct.pack_into("<I", san, 16, 0x144A)
        san = bytes(san)
    else:
        scm = bytearray(scm)
        struct.pack_into(
            "<f",
            scm,
            44 if change == "model_scale" else 32,
            0 if change == "model_scale" else float("inf"),
        )
        struct.pack_into("<I", scm, 28, zlib.crc32(scm[32:]))
        scm = bytes(scm)
        sct = bytearray(sct)
        struct.pack_into("<I", sct, 20, zlib.crc32(scm[32:]))
        sct = bytes(sct)
    with pytest.raises(ValueError):
        encode_world(placed, counter, scm, san, sct)


@pytest.fixture
def bundle(tmp_path):
    old, _, mesh, _, _, _, _, _, build = lighting_tests.bundle.__wrapped__(tmp_path)
    for p in list(build.iterdir()):
        if "character_lighting" in p.name:
            p.rename(build / p.name.replace("lighting", "world"))
    (build / "SHA256SUMS").write_text(
        "".join(
            f"{sha(p.read_bytes())}  {p.name}\n"
            for p in sorted(build.iterdir())
            if p.name != "SHA256SUMS"
        )
    )
    ram = bytearray(32 * 1024 * 1024)
    actors = []
    for i, placement in enumerate(instances()):
        a = 0x44D630 + i * 0x320
        ident = 0x18E + i
        struct.pack_into("<HH", ram, a + 12, 0x209, ident)
        struct.pack_into("<4f", ram, a + 0x20, *placement["model"][12:])
        struct.pack_into("<16f", ram, a + 0x40, *placement["model"])
        struct.pack_into("<I", ram, a + 0x278, 66220)
        struct.pack_into("<I", ram, a + 0x308, 0x900000 + 96)
        struct.pack_into("<I", ram, a + 0x30C, 0xB00000)
        actors.append(
            dict(
                address=hex(a),
                instance=ident,
                position=placement["model"][12:],
                rotation=[0] * 4,
                counter=66220,
            )
        )
    raw_mesh = json.loads((mesh / "manifest.json").read_text())
    raw_mesh["resources"] = {
        name: dict(size=size, sha256=sha(bytes(size)))
        for name, size in [("model", 833712), ("animation", 3500)]
    }
    (mesh / "manifest.json").write_text(json.dumps(raw_mesh))
    old_manifest = json.loads((old / "manifest.json").read_text())
    old_manifest["mesh_manifest_sha256"] = sha((mesh / "manifest.json").read_bytes())
    (old / "manifest.json").write_text(json.dumps(old_manifest))
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("eeMemory.bin", ram)
        archive.writestr("synthetic.txt", "own fixture")
    state = tmp_path / "source.p2s"
    state.write_bytes(data.getvalue())
    reference = dict(
        schema_version=1,
        scope="gc_t4_character_world_bounded",
        status="pass",
        guest_writes=False,
        instance_observations=84,
        continuous_snapshots=[dict(slot=8, actors=actors, sha256=sha(data.getvalue()))],
        code_windows=[dict(address="0x100000", size=16, sha256=sha(bytes(16)))],
    )
    rp = tmp_path / "world-reference.json"
    rp.write_text(json.dumps(reference))
    return (
        old,
        sha((old / "manifest.json").read_bytes()),
        mesh,
        rp,
        sha(rp.read_bytes()),
        state,
        build,
    )


def test_preparation_exclusive_output_and_zip(bundle, tmp_path):
    a, report = prepare_files(*bundle)
    b, other = prepare_files(*bundle)
    assert a == b and report == other and report["draw_calls"] == 9
    assert report["instance_ids"] == [0x18E, 0x18F, 0x190]
    with zipfile.ZipFile(io.BytesIO(a["sd-card.zip"])) as z:
        assert len(z.namelist()) == 8
        assert z.read("3ds/sh3_character_world_probe/character.scw") == a["character.scw"]
    root = tmp_path / "private"
    root.mkdir()
    args = []
    for key, value in zip(
        (
            "material-source",
            "material-sha256",
            "mesh-source",
            "reference",
            "reference-sha256",
            "state",
            "build",
        ),
        bundle,
        strict=True,
    ):
        args.extend(("--" + key, str(value)))
    args += ["--private-root", str(root), "--run-id", "test-world"]
    assert main(args) == 0
    manifest = json.loads((root / "test-world/manifest.json").read_text())
    assert manifest["physical_2ds_xl"] == "pending"
    with pytest.raises(FileExistsError):
        main(args)


@pytest.mark.parametrize(
    "change",
    [
        "scope",
        "writes",
        "observations",
        "slot",
        "actors",
        "code",
        "address",
        "identity",
        "position",
        "rotation",
        "counter",
        "hash",
        "resource",
    ],
)
def test_rejects_reference_or_resident_mismatch(bundle, change):
    old, oh, mesh, rp, rh, state, build = bundle
    ref = json.loads(rp.read_text())
    actor = ref["continuous_snapshots"][0]["actors"][0]
    if change == "scope":
        ref["scope"] = "other"
    elif change == "writes":
        ref["guest_writes"] = True
    elif change == "observations":
        ref["instance_observations"] = 83
    elif change == "slot":
        ref["continuous_snapshots"][0]["slot"] = 9
    elif change == "actors":
        ref["continuous_snapshots"][0]["actors"].pop()
    elif change == "code":
        ref["code_windows"][0]["sha256"] = "a" * 64
    elif change == "address":
        actor["address"] = "0x44d631"
    elif change == "identity":
        actor["instance"] = 1
    elif change == "position":
        actor["position"][0] += 1
    elif change == "rotation":
        actor["rotation"][0] = 1
    elif change == "counter":
        actor["counter"] += 1
    elif change == "hash":
        ref["continuous_snapshots"][0]["sha256"] = "a" * 64
    else:
        resources = copy.deepcopy(json.loads((mesh / "manifest.json").read_text())["resources"])
        resources["model"]["sha256"] = "a" * 64
        with pytest.raises(ValueError):
            extract_instances(ref, state.read_bytes(), resources)
        return
    rp.write_text(json.dumps(ref))
    with pytest.raises(ValueError):
        prepare_files(old, oh, mesh, rp, sha(rp.read_bytes()), state, build)


@pytest.mark.parametrize("change", ["old_scope", "mesh_scope", "model", "code_extent", "short_ram"])
def test_custody_rejects_changed_dependencies(bundle, change):
    old, oh, mesh, rp, rh, state, build = bundle
    ref = json.loads(rp.read_text())
    old_manifest = json.loads((old / "manifest.json").read_text())
    if change == "old_scope":
        old_manifest["scope"] = "other"
    elif change == "mesh_scope":
        manifest = json.loads((mesh / "manifest.json").read_text())
        manifest["scope"] = "other"
        (mesh / "manifest.json").write_text(json.dumps(manifest))
        old_manifest["mesh_manifest_sha256"] = sha((mesh / "manifest.json").read_bytes())
    elif change == "model":
        path = old / "character.scm"
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 1
        path.write_bytes(raw)
        next(f for f in old_manifest["files"] if f["file"] == path.name)["sha256"] = sha(raw)
    elif change == "code_extent":
        ref["code_windows"][0]["size"] = 0
    else:
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("eeMemory.bin", bytes(1024))
            archive.writestr("synthetic.txt", "own fixture")
        state.write_bytes(data.getvalue())
        ref["continuous_snapshots"][0]["sha256"] = sha(data.getvalue())
    (old / "manifest.json").write_text(json.dumps(old_manifest))
    rp.write_text(json.dumps(ref))
    with pytest.raises(ValueError):
        prepare_files(
            old,
            sha((old / "manifest.json").read_bytes()),
            mesh,
            rp,
            sha(rp.read_bytes()),
            state,
            build,
        )


def test_extract_without_resource_manifest_for_readonly_diagnostic(bundle):
    _, _, _, rp, _, state, _ = bundle
    result, counter = extract_instances(json.loads(rp.read_text()), state.read_bytes())
    assert counter == 66220 and [r["id"] for r in result] == [398, 399, 400]
