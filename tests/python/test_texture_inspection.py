"""Synthetic-only STX, delivery integrity and private-output contracts."""

import hashlib
import io
import json
import os
import struct
import zipfile
import zlib

import pytest

from tools.pipeline.prepare_texture_probe import BUILD_FILES, bounded_read, main, prepare_files
from tools.pipeline.private_texture_output import write_inspection_bundle
from tools.pipeline.profile import ProfileError
from tools.pipeline.texture_inspection import (
    PIXEL_BYTES,
    encode_stx,
    normalize_ps2_alpha,
    sd_archive,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def bundle(tmp_path):
    decoded, build, private = (tmp_path / name for name in ("decoded", "build", "private"))
    for path in (decoded, build, private):
        path.mkdir()
    rgba = bytes(range(256)) * 1024
    (decoded / "palette-0.rgba").write_bytes(rgba)
    manifest = {
        "schema_version": 1,
        "scope": "ps2_indexed_texture_decode",
        "recipe": "sh3-ps2-indexed8-four-cluts-v1",
        "status": "decoded_candidate",
        "orientation": "row_major_no_flip",
        "alpha": {"rgba": "original_ps2"},
        "block": {"width": 256, "height": 256},
        "files": [{"file": "palette-0.rgba", "size": len(rgba), "sha256": sha(rgba)}],
        "palettes": [{"ordinal": 0, "preview_rgba_sha256": sha(normalize_ps2_alpha(rgba))}],
        "resource": {"id": "synthetic-only"},
    }
    raw = json.dumps(manifest).encode()
    (decoded / "manifest.json").write_bytes(raw)
    values = {
        "build-id.txt": b"123456789abc\n",
        "sh3_texture_probe.3dsx": b"3DSXsynthetic",
        "sh3_texture_probe.smdh": b"SMDHsynthetic",
    }
    for name in BUILD_FILES:
        (build / name).write_bytes(values.get(name, b"synthetic only\n"))
    resums(build)
    return decoded, build, private, sha(raw)


def resums(build):
    (build / "SHA256SUMS").write_text(
        "".join(f"{sha((build / name).read_bytes())}  {name}\n" for name in sorted(BUILD_FILES))
    )


def test_encoder_and_all_alpha_values():
    raw = bytes(c for alpha in range(256) for c in (42, 87, 123, alpha)) * 256
    normalized = normalize_ps2_alpha(raw)
    assert normalized[0::4] == bytes([42]) * 65536
    assert normalized[1::4] == bytes([87]) * 65536
    assert normalized[2::4] == bytes([123]) * 65536
    assert normalized[3::4] == bytes(min(255, 2 * a) for a in range(256)) * 256
    encoded = encode_stx(normalized)
    assert struct.unpack("<8sHHIII", encoded[:24]) == (
        b"S3TXv1\0\0",
        256,
        256,
        1,
        PIXEL_BYTES,
        zlib.crc32(normalized),
    )
    assert encoded[24:] == normalized and len(encoded) == 262168


@pytest.mark.parametrize("value", [b"", b"x" * (PIXEL_BYTES - 1), bytearray(PIXEL_BYTES), None])
@pytest.mark.parametrize("function", [encode_stx, normalize_ps2_alpha])
def test_bad_pixel_input(value, function):
    with pytest.raises(ValueError):
        function(value)


def test_delivery_repeatable_and_zip_verified(bundle, tmp_path):
    decoded, build, private, digest = bundle
    files, report = prepare_files(decoded, digest, 0, build)
    assert (files, report) == prepare_files(decoded, digest, 0, build)
    assert report["physical_2ds_xl"] == "pending" and report["original_material"] == "pending"
    assert report["capabilities"] == []
    assert report["palette"] == 0
    with zipfile.ZipFile(io.BytesIO(files["sd-card.zip"])) as archive:
        assert archive.testzip() is None
        for line in archive.read("SHA256SUMS").decode().splitlines():
            checksum, name = line.split("  ")
            assert checksum == sha(archive.read(name))
        assert len(archive.namelist()) == 5
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
    checkout = tmp_path / "repo"
    checkout.mkdir()
    manifest = write_inspection_bundle(private, checkout, "run-a", files, report)
    assert manifest == write_inspection_bundle(private, checkout, "run-b", files, report)
    for name, data in files.items():
        assert (private / "run-a" / name).read_bytes() == data
        assert (private / "run-a" / name).stat().st_mode & 0o777 == 0o600
    assert (private / "run-a").stat().st_mode & 0o777 == 0o700
    with pytest.raises(FileExistsError):
        write_inspection_bundle(private, checkout, "run-a", files, report)
    with pytest.raises(ProfileError, match="external"):
        write_inspection_bundle(checkout, checkout, "run", files, report)
    with pytest.raises(ProfileError, match="output"):
        write_inspection_bundle(private, checkout, "run-c", {}, report)


@pytest.mark.parametrize("palette", [-1, 4, True, 0.0])
def test_explicit_palette_required(bundle, palette):
    decoded, build, _, digest = bundle
    with pytest.raises(ValueError):
        prepare_files(decoded, digest, palette, build)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 2),
        ("scope", "other"),
        ("recipe", "other"),
        ("status", "unknown"),
        ("orientation", "flipped"),
        ("alpha", {"rgba": "normalized"}),
        ("block", {"width": 128, "height": 256}),
        ("block", {"width": 256, "height": 128}),
        ("files", []),
        ("palettes", []),
    ],
)
def test_rejects_unrecognized_contract(bundle, field, value):
    decoded, build, _, _ = bundle
    path = decoded / "manifest.json"
    manifest = json.loads(path.read_bytes())
    manifest[field] = value
    raw = json.dumps(manifest).encode()
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        prepare_files(decoded, sha(raw), 0, build)


@pytest.mark.parametrize("entry", ["files", "palettes"])
def test_rejects_duplicate_metadata(bundle, entry):
    decoded, build, _, _ = bundle
    path = decoded / "manifest.json"
    manifest = json.loads(path.read_bytes())
    manifest[entry] *= 2
    raw = json.dumps(manifest).encode()
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        prepare_files(decoded, sha(raw), 0, build)


@pytest.mark.parametrize("target", ["manifest", "pixels", "build", "preview"])
def test_rejects_digest_mismatch(bundle, target):
    decoded, build, _, digest = bundle
    if target == "manifest":
        digest = "0" * 64
    elif target == "pixels":
        (decoded / "palette-0.rgba").write_bytes(bytes(PIXEL_BYTES))
    elif target == "build":
        (build / "sh3_texture_probe.3dsx").write_bytes(b"changed")
    else:
        path = decoded / "manifest.json"
        manifest = json.loads(path.read_bytes())
        manifest["palettes"][0]["preview_rgba_sha256"] = "0" * 64
        raw = json.dumps(manifest).encode()
        path.write_bytes(raw)
        digest = sha(raw)
    with pytest.raises(ValueError, match="SHA-256"):
        prepare_files(decoded, digest, 0, build)


@pytest.mark.parametrize("variant", ["duplicate", "missing", "traversal", "malformed"])
def test_rejects_invalid_build_inventory(bundle, variant):
    decoded, build, _, digest = bundle
    path = build / "SHA256SUMS"
    lines = path.read_text().splitlines()
    if variant == "duplicate":
        lines += lines[:1]
    elif variant == "missing":
        lines = lines[1:]
    elif variant == "traversal":
        lines[0] = "0" * 64 + "  ../outside"
    else:
        lines[0] = "bad"
    path.write_text("\n".join(lines))
    with pytest.raises(ValueError, match="inventory"):
        prepare_files(decoded, digest, 0, build)


@pytest.mark.parametrize(
    "name", ["build-id.txt", "sh3_texture_probe.3dsx", "sh3_texture_probe.smdh"]
)
def test_rejects_invalid_build_type(bundle, name):
    decoded, build, _, digest = bundle
    (build / name).write_bytes(b"invalid")
    resums(build)
    with pytest.raises(ValueError):
        prepare_files(decoded, digest, 0, build)


@pytest.mark.parametrize("kind", ["empty", "oversize", "directory", "symlink", "fifo"])
def test_bounded_regular_input_only(tmp_path, kind):
    path = tmp_path / "input"
    if kind == "directory":
        path.mkdir()
    elif kind == "symlink":
        path.symlink_to(tmp_path / "absent")
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.write_bytes(b"" if kind == "empty" else b"too large")
    with pytest.raises((OSError, ValueError)):
        bounded_read(path, 4)


def test_archive_names_are_fixed():
    with pytest.raises(ValueError):
        sd_archive({"../escape": b"data"})


def test_cli_private_delivery(bundle, capsys):
    decoded, build, private, digest = bundle
    assert (
        main(
            [
                "--decoded",
                str(decoded),
                "--build",
                str(build),
                "--private-root",
                str(private),
                "--manifest-sha256",
                digest,
                "--palette",
                "0",
                "--run-id",
                "cli",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "prepared"
    assert (private / "cli" / "manifest.json").is_file()
