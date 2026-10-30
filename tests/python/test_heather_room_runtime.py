"""SRR1 preserves contact bits and rejects altered source pairs/publication failures."""

import json
import struct
import zlib

import pytest

from tests.python.helpers.heather_room_scene_fixture import pin, scene_inputs
from tools.pipeline import heather_room_contacts as contact
from tools.pipeline import heather_room_scene as scene
from tools.pipeline import prepare_heather_room_runtime as runtime
from tools.pipeline import prepare_heather_room_scene as preparation


@pytest.fixture
def sources(tmp_path, monkeypatch):
    paths, _, a, b, ref = scene_inputs(tmp_path / "inputs")
    monkeypatch.setattr(contact, "PROFILE_PIN", pin(paths["profile"].read_bytes()))
    monkeypatch.setattr(scene, "REFERENCE_SHA", pin(ref.read_bytes())["sha256"])
    monkeypatch.setattr(preparation, "REFERENCE_SHA", pin(ref.read_bytes())["sha256"])
    root = tmp_path / "private"
    root.mkdir()
    preparation.publish(paths, a, b, ref, root, tmp_path / "repo", "scene")
    return root, root / "scene-copy-a", root / "scene-copy-b", tmp_path / "repo"


def test_descriptor_preserves_contact_bits(sources):
    _, a, _, _ = sources
    files, _ = preparation.read_bundle(a)
    raw = runtime.runtime_descriptor(files)
    assert len(raw) == 596
    magic, length, crc, map_crc, rig_crc, glass_crc, version = struct.unpack_from("<8s6I", raw)
    assert (magic, length, version) == (b"S3RRv1\0\0", 564, 1)
    assert crc == zlib.crc32(raw[32:])
    assert [map_crc, rig_crc, glass_crc] == [
        zlib.crc32(files[k]) for k in ("map.srm", "heather.sri", "glass.rgba")
    ]
    contacts = json.loads(files["contacts.json"])["scene"]
    boxes = struct.unpack_from("<128I", raw, 84)
    assert boxes == tuple(int(v[4:], 16) for box in contacts["blockers"] for v in box)
    assert struct.unpack_from("<4f", raw, 68) == (100275, 0, 140000, 0)


@pytest.mark.parametrize(
    "name", ["contacts.json", "room-profile.json", "heather.sri", "map.srm", "render-profile.json"]
)
def test_source_changes_rejected(sources, name):
    _, a, _, _ = sources
    files, _ = preparation.read_bundle(a)
    files[name] += b"corruption"
    with pytest.raises(ValueError):
        runtime.runtime_descriptor(files)


def test_publication_and_existing_directory(sources):
    root, a, b, repo = sources
    reports = runtime.publish(a, b, root, repo, "runtime")
    assert reports[0] == reports[1]
    source, _ = preparation.read_bundle(a)
    for copy in ("copy-a", "copy-b"):
        path = root / ("runtime-" + copy)
        assert path.stat().st_mode & 0o777 == 0o700
        assert (path / "scene.srr").read_bytes() == runtime.runtime_descriptor(source)
        assert all((path / n).read_bytes() == v for n, v in source.items())
        assert all(f.stat().st_mode & 0o777 == 0o600 for f in path.iterdir())
    with pytest.raises(FileExistsError):
        runtime.publish(a, b, root, repo, "runtime")


def test_source_change_during_publication(sources, monkeypatch):
    root, a, b, repo = sources
    original = runtime._write_bundle

    def changed(*args, **kwargs):
        (b / "map.srm").write_bytes(b"changed")
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime, "_write_bundle", changed)
    with pytest.raises(ValueError):
        runtime.publish(a, b, root, repo, "runtime")
    assert not (root / "runtime-copy-a/manifest.json").exists()


def test_pair_mismatch_rejected(sources, monkeypatch):
    root, a, b, repo = sources
    read = runtime.read_bundle

    def altered(path):
        files, manifest = read(path)
        if path == b:
            manifest["task"] = "different"
        return files, manifest

    monkeypatch.setattr(runtime, "read_bundle", altered)
    with pytest.raises(ValueError, match="HRR_AB"):
        runtime.publish(a, b, root, repo, "runtime")


def test_cli(sources, capsys):
    root, a, b, _ = sources
    args = [
        "--scene-a",
        str(a),
        "--scene-b",
        str(b),
        "--private-root",
        str(root),
        "--run-prefix",
        "cli",
    ]
    assert runtime.main(args) == 0
    assert json.loads(capsys.readouterr().out)["descriptor_bytes"] == 596
    assert runtime.main(args) == 1
    assert json.loads(capsys.readouterr().out)["error_type"] == "FileExistsError"
