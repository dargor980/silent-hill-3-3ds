"""HM-T4d: authenticated inputs, code identity, deterministic SD layout and publication."""

import hashlib
import io
import json
import zipfile

import pytest

from tests.python.test_heather_room_runtime import sources  # noqa: F401
from tools.pipeline import prepare_heather_room_delivery as delivery
from tools.pipeline import prepare_heather_room_runtime as runtime
from tools.pipeline.inspection_archive import inspection_archive


def sums(build):
    names = [f"{delivery.STEM}.{ext}" for ext in ("elf", "3dsx", "smdh")] + [
        "build-id.txt",
        "toolchain-packages.txt",
        "sdk-image.txt",
    ]
    (build / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256((build / n).read_bytes()).hexdigest()}  {n}\n" for n in names)
    )


@pytest.fixture
def inputs(sources):  # noqa: F811 - imported pytest fixture
    root, a, b, repo = sources
    runtime.publish(a, b, root, repo, "runtime")
    for folder in ("engine", "toolchains", "docs/compatibility"):
        (repo / folder).mkdir(parents=True, exist_ok=True)
    (repo / "engine/main.cpp").write_bytes(b"own synthetic code")
    (repo / "CMakeLists.txt").write_bytes(b"own synthetic cmake")
    (repo / "toolchains/devkitpro-image.txt").write_bytes(b"own-test-image@sha256:0000\n")
    (repo / "docs/compatibility/heather-room.md").write_bytes(b"HM-T5: pending hardware tests\n")
    identity = hashlib.sha256(
        "".join(
            hashlib.sha256((repo / n).read_bytes()).hexdigest()
            for n in ("engine/main.cpp", "CMakeLists.txt")
        ).encode()
    ).hexdigest()[:12]
    build = root / "build"
    build.mkdir()
    elf = bytearray(64)
    elf[:6] = b"\x7fELF\x01\x01"
    elf[18:20] = b"\x28\0"
    files = {
        "sh3_heather_room.elf": bytes(elf) + identity.encode(),
        "sh3_heather_room.3dsx": b"3DSX" + identity.encode(),
        "sh3_heather_room.smdh": b"SMDH-own-test",
        "build-id.txt": (identity + "\n").encode(),
        "toolchain-packages.txt": b"own-test-sdk\n",
        "sdk-image.txt": (repo / "toolchains/devkitpro-image.txt").read_bytes(),
    }
    for n, raw in files.items():
        (build / n).write_bytes(raw)
    sums(build)
    return [a, b, root / "runtime-copy-a", root / "runtime-copy-b", build, root, repo, "delivery"]


def test_publish_and_zip(inputs):
    manifest = delivery.publish(*inputs)
    root = inputs[5]
    assert manifest["physical_validation"] is manifest["sd_installed"] is False
    left, right = [root / f"delivery-copy-{c}" for c in "ab"]
    assert {p.name: p.read_bytes() for p in left.iterdir()} == {
        p.name: p.read_bytes() for p in right.iterdir()
    }
    files = {r["file"]: (left / r["file"]).read_bytes() for r in manifest["files"]}
    assert len(files) == 21
    archive = files.pop("sd-card.zip")
    assert archive == inspection_archive(dict(reversed(list(files.items()))), delivery.STEM)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert z.testzip() is None and len(z.infolist()) == 21
        expected = {f"3ds/{delivery.STEM}/{n}" for n in files} | {"SHA256SUMS"}
        assert set(z.namelist()) == expected
        assert all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in z.infolist())
        assert all(i.external_attr >> 16 == 0o100600 for i in z.infolist())
        for line in z.read("SHA256SUMS").decode().splitlines():
            digest, name = line.split("  ")
            assert hashlib.sha256(z.read(name)).hexdigest() == digest
            assert z.read(name) == files[name.rsplit("/", 1)[1]]
    assert f"Build: {manifest['build_id']}".encode() in files["LEEME.txt"]
    assert left.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in left.iterdir())
    assert json.loads((left / "manifest.json").read_bytes()) == manifest
    with pytest.raises(FileExistsError):
        delivery.publish(*inputs)


@pytest.mark.parametrize(
    "name",
    [
        "scene.srr",
        "map.srm",
        "heather.sri",
        "texture-00.rgba",
        "source-scene-manifest.json",
        "manifest.json",
        ".manifest.pending.json",
    ],
)
def test_tampered_runtime(inputs, name):
    p = inputs[3] / name
    p.write_bytes(p.read_bytes() + b"changed")
    with pytest.raises(ValueError):
        delivery.publish(*inputs)
    assert not (inputs[5] / "delivery-copy-a").exists()


def test_inventory_and_symlink(inputs):
    p = inputs[3] / "extra"
    p.write_bytes(b"x")
    with pytest.raises(ValueError, match="HRD_RUNTIME_SET"):
        delivery.publish(*inputs)
    p.unlink()
    p = inputs[3] / "map.srm"
    p.unlink()
    p.symlink_to(inputs[2] / "map.srm")
    with pytest.raises(OSError):
        delivery.publish(*inputs)


def test_optional_pending(inputs):
    for path in inputs[2:4]:
        (path / ".manifest.pending.json").unlink()
    assert delivery.publish(*inputs)["build_id"]


@pytest.mark.parametrize("fault", ["hash", "identity", "source", "sdk", "elf", "embedded"])
def test_invalid_build(inputs, fault):
    build, repo = inputs[4], inputs[6]
    if fault == "identity":
        (build / "build-id.txt").write_bytes(b"111111111111\n")
    elif fault == "source":
        (repo / "engine/extra.cpp").write_bytes(b"new source")
    elif fault == "sdk":
        (build / "sdk-image.txt").write_bytes(b"other-image\n")
    elif fault == "elf":
        (build / "sh3_heather_room.elf").write_bytes(b"not an ARM elf")
    else:
        (build / "sh3_heather_room.3dsx").write_bytes(b"3DSX without embedded identity")
    if fault != "hash":
        sums(build)
    with pytest.raises(ValueError):
        delivery.publish(*inputs)
    assert not (inputs[5] / "delivery-copy-a").exists()


def test_missing_and_unexpected_archive_files(inputs):
    files, _ = delivery.prepare(inputs[0], inputs[2], inputs[4], inputs[6], delivery.PinnedInputs())
    files.pop("sd-card.zip")
    for change in ("missing", "extra"):
        bad = dict(files)
        if change == "missing":
            bad.pop("scene.srr")
        else:
            bad["source.cld"] = b"unneeded source"
        with pytest.raises(ValueError):
            inspection_archive(bad, delivery.STEM)


def test_source_changes_before_manifest(inputs, monkeypatch):
    original = delivery._write_bundle

    def change(*args, **kwargs):
        (inputs[6] / "engine/main.cpp").write_bytes(b"changed while publishing")
        return original(*args, **kwargs)

    monkeypatch.setattr(delivery, "_write_bundle", change)
    with pytest.raises(ValueError):
        delivery.publish(*inputs)
    assert not (inputs[5] / "delivery-copy-a/manifest.json").exists()


def test_completed_a_rechecked_after_b(inputs, monkeypatch):
    original = delivery._write_bundle

    def change(*args, **kwargs):
        report = original(*args, **kwargs)
        (inputs[5] / "delivery-copy-a/scene.srr").write_bytes(b"changed")
        return report

    monkeypatch.setattr(delivery, "_write_bundle", change)
    with pytest.raises(ValueError):
        delivery.publish(*inputs)


def test_b_failure_keeps_complete_a(inputs):
    (inputs[5] / "delivery-copy-b").mkdir()
    with pytest.raises(FileExistsError):
        delivery.publish(*inputs)
    assert (inputs[5] / "delivery-copy-a/manifest.json").is_file()
    assert not (inputs[5] / "delivery-copy-b/manifest.json").exists()


def test_cli(inputs, monkeypatch, capsys):
    publish = delivery.publish

    def repository(*args):
        return publish(*args[:6], inputs[6], args[7])

    monkeypatch.setattr(delivery, "publish", repository)
    args = []
    for key, value in zip(
        ["scene-a", "scene-b", "runtime-a", "runtime-b", "build", "private-root"],
        inputs[:6],
        strict=True,
    ):
        args += ["--" + key, str(value)]
    args += ["--run-prefix", "cli"]
    assert delivery.main(args) == 0
    assert json.loads(capsys.readouterr().out)["copies"] == 2
    assert delivery.main(args) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"


def test_materials_archive_and_delivery_dispatch(inputs, monkeypatch):
    from tools.pipeline import prepare_heather_room_materials as materials
    from tools.pipeline.collision_polygon_inputs import PinnedInputs

    a, b, ra, rb, build, root, repo, prefix = inputs
    original, manifest = delivery.read_runtime(a, ra, PinnedInputs())
    original["material-profile.json"] = b"{}"
    original.update(
        {name: bytes([i + 1]) * 32 for i, name in enumerate(sorted(materials.TEXTURES))}
    )
    monkeypatch.setattr(materials, "read_runtime", lambda *args: (original, manifest))
    for directory in (ra, rb):
        (directory / "material-profile.json").write_bytes(b"{}")
    report = delivery.publish(*inputs)
    assert report["accounted_bytes"] == 51726136
    assert report["label"] == "MATERIALES ORIGINALES / LUZ FIJA"
    output = root / (prefix + "-copy-a")
    with zipfile.ZipFile(output / "sd-card.zip") as z:
        assert len(z.infolist()) == 30 and z.testzip() is None
        for name in materials.TEXTURES:
            assert z.read(f"3ds/{delivery.STEM}/{name}") == original[name]
    data = {name: original[name] for name in delivery.RUNTIME_NAMES | materials.TEXTURES}
    data.update({f"{delivery.STEM}.3dsx": b"x", f"{delivery.STEM}.smdh": b"x", "LEEME.txt": b"x"})
    del data["room-texture-08.rgba"]
    with pytest.raises(ValueError, match="Unexpected inspection archive files"):
        inspection_archive(data, delivery.STEM)
