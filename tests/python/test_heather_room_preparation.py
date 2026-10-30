"""Own geometry and custody failures; no original assets enter CI."""

import json
import os
import struct

import pytest

from tests.cld_polygon_wire_oracle import identical
from tests.heather_room_preparation_oracle import projection
from tests.python.helpers.heather_room_preparation_fixture import cld, configured, pin, wire
from tools.pipeline import heather_room_contacts as core
from tools.pipeline import prepare_heather_room_contacts as prep


@pytest.fixture
def source(tmp_path, monkeypatch):
    paths, profile, profile_pin = configured(tmp_path / "inputs")
    monkeypatch.setattr(core, "PROFILE_PIN", profile_pin)
    return paths, profile


def resign(paths, profile, monkeypatch):
    for name, key in (("catalog", "catalog_sha256"), ("receipt", "extraction_receipt_sha256")):
        profile[key] = pin(paths[name].read_bytes())["sha256"]
    paths["profile"].write_bytes(wire(profile))
    monkeypatch.setattr(core, "PROFILE_PIN", pin(wire(profile)))


def test_projection_preserves_every_word():
    raw = cld()
    view, contacts = core.convert_cld(raw)
    other, scene, roles = projection(raw)
    identical(view, other)
    assert contacts["scene"] == scene
    assert contacts["record_roles"] == roles
    assert len(scene["blockers"]) == 32
    assert len(roles) == 34


@pytest.mark.parametrize(
    "kind",
    [
        "origin",
        "selection",
        "reference",
        "other_cell",
        "variant",
        "bounds",
        "floor_y",
        "ceiling_y",
        "triangle",
        "empty_x",
        "empty_z",
    ],
)
def test_geometry_rejections(kind):
    raw = bytearray(cld())
    offsets = struct.unpack_from("<5I", raw, 352)
    floor = offsets[0]
    if kind == "origin":
        struct.pack_into("<f", raw, 0, 0)
    elif kind == "selection":
        struct.pack_into("<I", raw, 28, 1)
    elif kind == "reference":
        pointer = struct.unpack_from("<I", raw, 32 + 64)[0]
        struct.pack_into("<I", raw, pointer + 4, 0)
    elif kind == "other_cell":
        raw[36:40] = raw[32:36]
    elif kind == "variant":
        raw[offsets[1] + 1] = 0
    elif kind == "bounds":
        struct.pack_into("<f", raw, offsets[1] + 16, 1000001)
    elif kind == "floor_y":
        struct.pack_into("<f", raw, floor + 20, 1)
    elif kind == "ceiling_y":
        struct.pack_into("<f", raw, offsets[2] + 4 * 80 + 20, 0)
    elif kind == "triangle":
        raw[floor + 64 : floor + 80] = raw[floor + 16 : floor + 32]
    else:
        axis = 0 if kind == "empty_x" else 2
        for i in range(4):
            struct.pack_into("<f", raw, floor + 16 + 16 * i + 4 * axis, 100 if i in (0, 3) else 452)
    with pytest.raises(ValueError, match="HRC_PREP_"):
        core.convert_cld(bytes(raw))


def test_counts_rejection():
    from tests.cld_polygon_fixtures import resource

    raw = bytearray(resource((1, 3, 26, 3)))
    struct.pack_into("<2f", raw, 0, 100000, 140000)
    struct.pack_into("<I", raw, 28, 0)
    with pytest.raises(ValueError, match="HRC_PREP_COUNTS"):
        core.convert_cld(bytes(raw))


@pytest.mark.parametrize("kind", ["short", "nan", "infinite_w", "terminator"])
def test_wire_rejections(kind):
    raw = bytearray(cld())
    start = struct.unpack_from("<I", raw, 352)[0]
    if kind == "short":
        raw = raw[:-1]
    elif kind == "terminator":
        raw[start + 80] = 1
    else:
        struct.pack_into(
            "<I",
            raw,
            start + (16 if kind == "nan" else 28),
            0x7FC00000 if kind == "nan" else 0x7F800000,
        )
    with pytest.raises(ValueError):
        core.convert_cld(bytes(raw))


def test_signed_zero_and_filter_are_preserved():
    raw = bytearray(cld())
    offset = struct.unpack_from("<I", raw, 356)[0]
    struct.pack_into("<I", raw, offset + 8, 4096)
    for i in range(4):
        struct.pack_into("<I", raw, offset + 16 + i * 16, 0x80000000 if i == 0 else 0)
    view, contacts = core.convert_cld(bytes(raw))
    assert view["groups"][1]["records"][0]["filter_word"] == 4096
    assert contacts["scene"]["blockers"][0][:2] == ["f32:80000000"] * 2
    assert contacts["scene"] == projection(bytes(raw))[1]


def test_floor_erosion_uses_exact_dyadics():
    raw = bytearray(cld())
    offset = struct.unpack_from("<I", raw, 352)[0]
    for i in range(4):
        struct.pack_into("<I", raw, offset + 16 + i * 16, 0x80000001 if i in (0, 3) else 0x43B00000)
    # Width is exactly 352 plus the smallest binary32 subnormal.
    core.convert_cld(bytes(raw))


def test_pair_and_reconstruction(source):
    paths, _ = source
    packages, report = prep.prepare_files(paths)
    assert packages["copy-a"] == packages["copy-b"]
    assert report["counts"] == dict(records=34, floor=1, ceiling_excluded=1, blockers=32)
    assert not report["runtime_integration"]
    files = packages["copy-a"]
    assert files["source.cld"] == cld()
    assert files["room-profile.json"] == paths["profile"].read_bytes()
    assert core.verify_package(files) == report


@pytest.mark.parametrize("key", ["profile", "schema_version", "coordinates", "budgets", "contacts"])
def test_profile_semantics(source, monkeypatch, key):
    paths, profile = source
    profile[key] = (
        0
        if key == "schema_version"
        else {}
        if key in ("coordinates", "budgets", "contacts")
        else "wrong"
    )
    resign(paths, profile, monkeypatch)
    with pytest.raises((ValueError, KeyError)):
        prep.prepare_files(paths)


@pytest.mark.parametrize("name", core.LIMITS)
def test_reconstruction_corruption(source, name):
    packages, _ = prep.prepare_files(source[0])
    files = packages["copy-a"]
    files[name] += b" "
    with pytest.raises(ValueError):
        core.verify_package(files)


@pytest.mark.parametrize("kind", ["missing", "extra", "empty", "oversize", "not_bytes"])
def test_package_limits(source, kind):
    files = prep.prepare_files(source[0])[0]["copy-a"]
    if kind == "missing":
        del files["source.cld"]
    elif kind == "extra":
        files["extra"] = b"x"
    else:
        files["source.cld"] = {"empty": b"", "oversize": b"x" * 65537, "not_bytes": "x"}[kind]
    with pytest.raises(ValueError):
        core.verify_package(files)


@pytest.mark.parametrize("role", ["map", "collision", "external_texture"])
@pytest.mark.parametrize("copy", ["copy-a", "copy-b"])
def test_all_sources_verified_before_decoder(source, monkeypatch, role, copy):
    paths, profile = source
    target = paths["copies"] / copy / (profile["resources"][role]["id"][6:] + ".bin")
    raw = target.read_bytes()
    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    monkeypatch.setattr(
        core, "decode_polygons", lambda _: pytest.fail("decoder called before custody")
    )
    with pytest.raises(ValueError):
        prep.prepare_files(paths)


@pytest.mark.parametrize("key", ["profile", "catalog", "receipt"])
def test_anchor_corruption(source, monkeypatch, key):
    paths, _ = source
    paths[key].write_bytes(paths[key].read_bytes() + b" ")
    monkeypatch.setattr(
        core, "decode_polygons", lambda _: pytest.fail("decoder called before custody")
    )
    with pytest.raises(ValueError):
        prep.prepare_files(paths)


@pytest.mark.parametrize("kind", ["missing", "symlink", "fifo", "directory"])
def test_nonregular_sources(source, kind):
    paths, profile = source
    path = paths["copies"] / "copy-a" / (profile["resources"]["collision"]["id"][6:] + ".bin")
    path.unlink()
    if kind == "symlink":
        path.symlink_to(paths["profile"])
    elif kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    with pytest.raises((ValueError, OSError)):
        prep.prepare_files(paths)


@pytest.mark.parametrize(
    "kind",
    [
        "status",
        "source",
        "selection",
        "inventory",
        "duplicate",
        "copies",
        "copy_row",
        "path",
        "offset",
    ],
)
def test_receipt_mismatches(source, monkeypatch, kind):
    paths, profile = source
    receipt = json.loads(paths["receipt"].read_bytes())
    if kind in ("status", "source", "selection"):
        receipt[kind] = "wrong"
    elif kind == "inventory":
        receipt["resources"].pop()
    elif kind == "duplicate":
        receipt["resources"].append(receipt["resources"][0])
    elif kind == "copies":
        receipt["copies"]["copy-b"].pop()
    elif kind == "copy_row":
        receipt["copies"]["copy-a"][0]["size"] += 1
    elif kind == "path":
        receipt["resources"][0]["file"] = "../escape.bin"
    else:
        receipt["resources"][0]["container_offset"] += 1
    paths["receipt"].write_bytes(wire(receipt))
    resign(paths, profile, monkeypatch)
    with pytest.raises(ValueError):
        prep.prepare_files(paths)


def publish(source, tmp_path):
    root, repository = tmp_path / "private", tmp_path / "repo"
    root.mkdir()
    repository.mkdir()
    result = prep.prepare_and_write(source[0], root, repository, "own")
    return root, repository, result


def test_exclusive_pair_publish_and_readback(source, tmp_path):
    root, repo, manifests = publish(source, tmp_path)
    expected = prep.prepare_files(source[0])[0]
    assert manifests["copy-a"] == manifests["copy-b"]
    for name in expected:
        path = root / ("own-" + name)
        assert path.stat().st_mode & 0o777 == 0o700
        assert prep.read_bundle(path)[0] == expected[name]
        assert all(p.stat().st_mode & 0o777 == 0o600 for p in path.iterdir())
        (path / ".manifest.pending.json").unlink()
        assert prep.read_bundle(path)[0] == expected[name]
    with pytest.raises(FileExistsError):
        prep.prepare_and_write(source[0], root, repo, "own")


@pytest.mark.parametrize("kind", ["extra", "source", "manifest", "pending", "symlink"])
def test_readback_rejects_tampering(source, tmp_path, kind):
    root, _, _ = publish(source, tmp_path)
    path = root / "own-copy-a"
    if kind == "extra":
        (path / "unexpected").write_bytes(b"x")
    elif kind == "symlink":
        (path / "source.cld").unlink()
        (path / "source.cld").symlink_to(source[0]["profile"])
    elif kind == "source":
        (path / "source.cld").write_bytes(b"bad")
    elif kind == "pending":
        (path / ".manifest.pending.json").unlink()
        (path / ".manifest.pending.json").write_bytes(b"{}")
    else:
        (path / "manifest.json").write_bytes(b"{}")
    with pytest.raises((ValueError, OSError)):
        prep.read_bundle(path)


def test_input_change_prevents_manifest(source, tmp_path, monkeypatch):
    original = prep._write_bundle

    def changed(*args, **kwargs):
        source[0]["receipt"].write_bytes(b"changed")
        return original(*args, **kwargs)

    monkeypatch.setattr(prep, "_write_bundle", changed)
    with pytest.raises(ValueError):
        publish(source, tmp_path)
    assert not (tmp_path / "private/own-copy-a/manifest.json").exists()


def test_partial_pair_is_not_accepted(source, tmp_path, monkeypatch):
    original = prep._write_bundle

    def failed(*args, **kwargs):
        if args[2].endswith("copy-b"):
            raise OSError("injected")
        return original(*args, **kwargs)

    monkeypatch.setattr(prep, "_write_bundle", failed)
    with pytest.raises(OSError):
        publish(source, tmp_path)
    assert (tmp_path / "private/own-copy-a/manifest.json").exists()
    assert not (tmp_path / "private/own-copy-b/manifest.json").exists()


def test_private_destination_and_absolute_inputs(source, tmp_path):
    with pytest.raises(ValueError):
        prep.prepare_and_write(source[0], tmp_path / "private", tmp_path, "own")
    with pytest.raises(ValueError):
        prep.prepare_files({**source[0], "copies": "relative"})


def test_cli(source, tmp_path, capsys):
    root = tmp_path / "private"
    root.mkdir()
    args = [v for key, path in source[0].items() for v in ("--" + key, str(path))]
    args += ["--private-root", str(root), "--run-prefix", "own"]
    assert prep.main(args) == 0
    assert json.loads(capsys.readouterr().out) == dict(status="prepared", copies=2, blockers=32)
    assert prep.main(args) == 1
    assert json.loads(capsys.readouterr().out) == dict(
        status="rejected", error_type="FileExistsError"
    )
