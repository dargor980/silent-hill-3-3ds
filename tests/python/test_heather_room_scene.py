"""Own 31-shape preparation, material identity, corruption and exclusive publication."""

import copy
import json
import os
import struct
import zlib
from pathlib import Path

import pytest

from tests.python.helpers.heather_room_scene_fixture import (
    map_and_reference,
    pin,
    rig,
    scene_inputs,
    texture,
    wire,
)
from tools.pipeline import heather_room_contacts as contacts
from tools.pipeline import heather_room_scene as scene
from tools.pipeline import prepare_heather_room_scene as prep


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    paths, profile, a, b, ref = scene_inputs(tmp_path / "inputs")
    monkeypatch.setattr(contacts, "PROFILE_PIN", pin(paths["profile"].read_bytes()))
    monkeypatch.setattr(scene, "REFERENCE_SHA", pin(ref.read_bytes())["sha256"])
    monkeypatch.setattr(prep, "REFERENCE_SHA", pin(ref.read_bytes())["sha256"])
    return paths, profile, a, b, ref


def run(inputs):
    paths, _, a, b, ref = inputs
    return prep.prepare(paths, a, b, ref)


def test_inventory_lossless_and_common_local_basis(inputs):
    packages, report = run(inputs)
    files = packages["copy-a"]
    assert packages["copy-b"] == files
    assert prep.verify_files(files) == report["rig"]
    raw = files["map.srm"]
    magic, ns, nv, size, crc, glass_crc, version = struct.unpack_from("<8s6I", raw)
    assert (magic, ns, nv, size, version) == (b"S3RMv1\0\0", 31, 183, len(raw) - 32, 1)
    assert zlib.crc32(raw[32:]) == crc and zlib.crc32(files["glass.rgba"]) == glass_crc
    ranges = list(struct.iter_unpack("<4I", raw[32 : 32 + 31 * 16]))
    assert sum(r[3] for r in ranges) == 2
    assert sum(r[2] for r in ranges if r[3]) == 96
    vertices = list(struct.iter_unpack("<9f", raw[32 + 31 * 16 :]))
    assert all(v[3] == 1 for v in vertices)
    # No map origin or individual centering baked into local SRM1 vertices.
    assert vertices[0][:4] == (0, 0, 0, 1)
    assert vertices[0][4:7] == pytest.approx(
        (64 / 128 * 227 / 256, 96 / 128 * 227 / 256, 227 / 256)
    )
    assert vertices[96][4:7] == pytest.approx((0.55, 0.58, 0.62))
    view = json.loads(files["map-view.json"])
    for shape in view["shapes"]:
        old = shape["header"]
        rebuilt = b"".join(
            struct.pack(
                "<8h",
                *v["position"],
                v["packed_attributes"][0],
                *v["uv_words"],
                *v["packed_attributes"][1:],
            )
            for v in shape["geometry"]["vertices"]
        )
        assert (
            rebuilt
            == files["source.map"][old["data_offset"] : old["data_offset"] + old["vertex_bytes"]]
        )
    assert files["glass.rgba"][:4] == bytes([120, 100, 80, 128])


@pytest.mark.parametrize(
    "kind",
    [
        "matrix",
        "ref_matrix",
        "profile",
        "scope",
        "version",
        "duplicates",
        "glass_set",
        "order",
        "mode",
        "empty",
        "source",
        "colors_count",
        "colors_alpha",
        "colors_type",
        "counts",
        "capacity",
    ],
)
def test_map_rejections(inputs, kind):
    _, profile, _, _, _ = inputs
    raw, ref = map_and_reference()
    raw = bytearray(raw)
    profile = copy.deepcopy(profile)
    if kind == "matrix":
        struct.pack_into("<f", raw, 112, 2)
    elif kind == "ref_matrix":
        ref["model_columns"][12] += 1
    elif kind == "profile":
        ref["profile"]["fog"] = 226
    elif kind in ("scope", "version"):
        ref["scope" if kind == "scope" else "schema_version"] = "bad"
    elif kind == "duplicates":
        ref["shapes"].append(ref["shapes"][0])
    elif kind == "glass_set":
        ref["shapes"][0]["shape_offset"] += 16
    elif kind == "order":
        ref["draw_order"] *= 2
    elif kind == "mode":
        struct.pack_into("<I", raw, 448 + 20, 3)
    elif kind == "empty":
        for i in range(18):
            struct.pack_into("<h", raw, 448 + 64 + i * 16 + 8, 1)
    elif kind == "source":
        ref["shapes"][0]["source_sha256"] = "0" * 64
    elif kind == "colors_count":
        ref["shapes"][0]["rgba"].pop()
    elif kind == "colors_alpha":
        ref["shapes"][0]["rgba"][0][3] = 128
    elif kind == "colors_type":
        ref["shapes"][0]["rgba"][0][0] = True
    elif kind == "counts":
        profile["render"]["expected_vertices"] += 1
    else:
        # A valid third glass entry must still be rejected by the profile's two-shape rule.
        profile["render"]["verified_glass_shape_offsets"].append(1)
    with pytest.raises(ValueError):
        scene.map_geometry(bytes(raw), ref, profile, 0)


@pytest.mark.parametrize("kind", ["blocks", "dimensions", "palette", "reference", "alpha"])
def test_texture_rejections(kind):
    raw = bytearray(texture())
    _, ref = map_and_reference()
    if kind == "blocks":
        struct.pack_into("<I", raw, 20, 0)
    elif kind == "dimensions":
        struct.pack_into("<H", raw, 40, 128)
    elif kind == "palette":
        raw[112 + 65536 + 12] = 3
    elif kind == "reference":
        ref["texture_rgba_sha256"] = "0" * 64
    else:
        for i in range(1024):
            raw[-4096 + i * 4 + 3] = 200
        ref["texture_rgba_sha256"] = pin(bytes([120, 100, 80, 200]) * 256 * 256)["sha256"]
    with pytest.raises(ValueError):
        scene.glass_pixels(bytes(raw), ref)


@pytest.mark.parametrize(
    "kind",
    [
        "pin",
        "magic",
        "bones",
        "clips",
        "source",
        "reserved",
        "length",
        "crc",
        "count",
        "files",
        "texture",
        "budget",
        "staging",
    ],
)
def test_rig_rejections(inputs, kind):
    _, profile, _, _, _ = inputs
    profile = copy.deepcopy(profile)
    files = rig()
    raw = bytearray(files["heather.sri"])
    mutations = {
        "magic": (0, 0),
        "bones": (8, 35),
        "clips": (32, 2),
        "source": (48, 523),
        "reserved": (64, 1),
        "length": (56, 1),
        "crc": (60, 0),
        "count": (28, 12),
    }
    if kind in mutations:
        at, value = mutations[kind]
        struct.pack_into("<I", raw, at, value)
    files["heather.sri"] = bytes(raw)
    if kind != "pin":
        profile["heather"]["sri_sha256"] = pin(bytes(raw))["sha256"]
    else:
        profile["heather"]["sri_sha256"] = "0" * 64
    if kind == "files":
        del files["texture-12.rgba"]
    if kind == "texture":
        files["texture-12.rgba"] += b"x"
    if kind == "budget":
        profile["budgets"]["resident_texture_bytes"] = 1
    if kind == "staging":
        profile["budgets"]["texture_staging_bytes"] = 1
    with pytest.raises(ValueError):
        scene.rig_metadata(files, profile)


@pytest.mark.parametrize(
    "key",
    [
        "map.srm",
        "map-view.json",
        "source.map",
        "source.tex",
        "glass-reference.json",
        "glass.rgba",
        "heather.sri",
        "texture-12.rgba",
        "heather-source-manifest.json",
        "room-profile.json",
        "contacts.json",
        "render-profile.json",
    ],
)
def test_package_tampering(inputs, key):
    files = run(inputs)[0]["copy-a"]
    files[key] += b" "
    with pytest.raises(ValueError):
        prep.verify_files(files)


def test_unknown_output(inputs):
    files = run(inputs)[0]["copy-a"]
    files["unknown"] = b"x"
    with pytest.raises(ValueError):
        prep.verify_files(files)


@pytest.mark.parametrize("copy", [2, 3])
@pytest.mark.parametrize(
    "name", ["manifest.json", "heather.sri", "texture-00.rgba", "texture-12.rgba"]
)
def test_every_rig_copy_authenticated(inputs, copy, name):
    path = inputs[copy] / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        run(inputs)


@pytest.mark.parametrize(
    "kind", ["appearance", "model", "animation", "clips", "inventory", "duplicate"]
)
def test_rig_manifest_semantics(inputs, monkeypatch, kind):
    paths, profile, a, b, _ = inputs
    manifest = json.loads((a / "manifest.json").read_bytes())
    if kind == "appearance":
        manifest["appearance"] = "extra_game"
    elif kind == "model":
        manifest["model_resource"] = 523
    elif kind == "animation":
        manifest["animation_resource"] = 526
    elif kind == "clips":
        manifest["clips"][0]["clip_id"] = 102
    elif kind == "inventory":
        manifest["files"].pop()
    else:
        manifest["files"].append(manifest["files"][0])
    for root in (a, b):
        (root / "manifest.json").write_bytes(wire(manifest))
    profile["heather"]["package_manifest_sha256"] = pin(wire(manifest))["sha256"]
    paths["profile"].write_bytes(wire(profile))
    monkeypatch.setattr(contacts, "PROFILE_PIN", pin(wire(profile)))
    with pytest.raises(ValueError):
        run(inputs)


def test_reference_must_be_pinned(inputs):
    inputs[4].write_bytes(inputs[4].read_bytes() + b" ")
    with pytest.raises(ValueError):
        run(inputs)


@pytest.mark.parametrize("kind", ["missing", "symlink", "directory", "fifo"])
def test_rig_regular_files_only(inputs, kind):
    p = inputs[3] / "texture-12.rgba"
    p.unlink()
    if kind == "symlink":
        p.symlink_to(inputs[2] / "texture-12.rgba")
    elif kind == "directory":
        p.mkdir()
    elif kind == "fifo":
        os.mkfifo(p)
    with pytest.raises((ValueError, OSError)):
        run(inputs)


def test_publish_pair_and_exclusivity(inputs, tmp_path):
    paths, _, a, b, ref = inputs
    root = tmp_path / "private"
    root.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    result = prep.publish(paths, a, b, ref, root, repo, "own")
    assert result["copy-a"] == result["copy-b"]
    for copy_name in ("copy-a", "copy-b"):
        directory = root / ("own-" + copy_name)
        files = {name: (directory / name).read_bytes() for name in prep.OUTPUT_NAMES}
        assert prep.verify_files(files) == result[copy_name]["rig"]
        assert prep.read_bundle(directory) == (files, result[copy_name])
        assert directory.stat().st_mode & 0o777 == 0o700
        assert all(p.stat().st_mode & 0o777 == 0o600 for p in directory.iterdir())
    with pytest.raises(FileExistsError):
        prep.publish(paths, a, b, ref, root, repo, "own")


def test_publication_input_change_no_manifest(inputs, tmp_path, monkeypatch):
    original = prep._write_bundle

    def changed(*args, **kwargs):
        inputs[4].write_bytes(b"changed")
        return original(*args, **kwargs)

    monkeypatch.setattr(prep, "_write_bundle", changed)
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(ValueError):
        prep.publish(inputs[0], inputs[2], inputs[3], inputs[4], root, tmp_path / "repo", "own")
    assert not (root / "own-copy-a/manifest.json").exists()


def test_partial_second_copy_never_succeeds(inputs, tmp_path, monkeypatch):
    original = prep._write_bundle

    def failed(*args, **kwargs):
        if args[2].endswith("copy-b"):
            raise OSError("injected")
        return original(*args, **kwargs)

    monkeypatch.setattr(prep, "_write_bundle", failed)
    root = tmp_path / "private"
    root.mkdir()
    with pytest.raises(OSError):
        prep.publish(inputs[0], inputs[2], inputs[3], inputs[4], root, tmp_path / "repo", "own")
    assert (root / "own-copy-a/manifest.json").exists()


def test_cli(inputs, tmp_path, capsys):
    root = tmp_path / "private"
    root.mkdir()
    args = [v for k, p in inputs[0].items() for v in ("--" + k, str(p))]
    args += [
        "--heather-a",
        str(inputs[2]),
        "--heather-b",
        str(inputs[3]),
        "--reference",
        str(inputs[4]),
        "--private-root",
        str(root),
        "--run-prefix",
        "own",
    ]
    assert prep.main(args) == 0
    assert json.loads(capsys.readouterr().out)["shapes"] == 31
    assert prep.main(args) == 1
    assert json.loads(capsys.readouterr().out) == dict(
        status="rejected", error_type="FileExistsError"
    )


def test_render_profile_matches_schema():
    root = Path(__file__).resolve().parents[2]
    assert (
        json.loads((root / "schemas/heather-room-render-v1.json").read_bytes())
        == scene.RENDER_PROFILE
    )


@pytest.mark.parametrize("kind", ["missing", "extra", "manifest", "pending", "symlink", "data"])
def test_readback_rejects_corruption(inputs, tmp_path, kind):
    root = tmp_path / "private"
    root.mkdir()
    prep.publish(inputs[0], inputs[2], inputs[3], inputs[4], root, tmp_path / "repo", "own")
    folder = root / "own-copy-a"
    if kind == "missing":
        (folder / "source.map").unlink()
    elif kind == "extra":
        (folder / "unexpected").write_bytes(b"x")
    elif kind == "manifest":
        manifest = json.loads((folder / "manifest.json").read_bytes())
        manifest["triangles"] += 1
        (folder / "manifest.json").write_bytes(wire(manifest))
    elif kind == "pending":
        (folder / ".manifest.pending.json").write_bytes(b"different")
    elif kind == "symlink":
        (folder / "map.srm").unlink()
        (folder / "map.srm").symlink_to(root / "own-copy-b/map.srm")
    else:
        (folder / "map.srm").write_bytes(b"changed")
    with pytest.raises((ValueError, OSError)):
        prep.read_bundle(folder)
