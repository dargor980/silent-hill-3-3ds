"""RF01 / T01: own ISO fixtures, never the user's disc or extracted resources."""

import hashlib
import json
import struct
import zlib
from io import BytesIO

import pycdlib
import pytest

from tools.pipeline.disc import collect_disc, parse_boot_config
from tools.pipeline.inspect_iso import main
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile, verify_profile

CONFIG = b"BOOT2 = cdrom0:\\SLES_000.01;1\r\nVER = 1.02\r\nVMODE = PAL\r\n"
ELF = b"\x7fELF\x01\x01\x01" + b"\0" * 9 + struct.pack("<HHI", 2, 8, 1) + b"\0" * 28
FILES = {"SYSTEM.CNF": CONFIG, "SLES_000.01": ELF, "B0.MFA": b"synthetic container"}


def make_iso(path, files=None):
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident="SYNTHETIC")
    for name, data in (FILES if files is None else files).items():
        iso.add_fp(BytesIO(data), len(data), iso_path=f"/{name};1")
    iso.write(str(path))
    iso.close()
    return path


class MemoryDisc:
    def paths(self):
        return tuple(FILES)

    def read_prefix(self, path, limit):
        return FILES[path][:limit]

    def inspect(self, path):
        return len(FILES[path]), hashlib.sha256(FILES[path]).hexdigest()


def test_boot_config_does_not_equate_ver_to_disc_revision():
    boot = parse_boot_config(CONFIG)
    assert boot == {
        "executable": "SLES_000.01",
        "serial": "SLES-00001",
        "system_cnf_ver": "1.02",
        "video_mode": "PAL",
    }


@pytest.mark.parametrize(
    "config",
    [
        b"x" * 4097,
        b"\xff",
        b"",
        CONFIG + b"VER = 1.00\n",
        CONFIG.replace(b"cdrom0:", b"host:"),
        CONFIG.replace(b"SLES_000.01", b"../SLES_000.01"),
        CONFIG.replace(b"VMODE = PAL", b"VMODE = mystery"),
        CONFIG.replace(b"VER = 1.02", b"VER = invalid"),
        CONFIG.replace(b"BOOT2 =", b"BOOT2 "),
    ],
)
def test_bad_boot_config(config):
    with pytest.raises(ProfileError):
        parse_boot_config(config)


@pytest.mark.integration
def test_iso_and_memory_obey_same_contract(tmp_path):
    path = make_iso(tmp_path / "synthetic.iso")
    before = path.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    expected = collect_disc(MemoryDisc(), "test", digest)
    with IsoImage(path) as disc:
        assert disc.image_identity() == (len(before), digest)
        actual = collect_disc(disc, "test", digest)
        verify_profile(parse_profile(actual["profile"]), disc)
    assert actual == expected
    assert path.read_bytes() == before
    assert actual["profile"]["capabilities"] == []
    assert actual["profile"]["revision"] == "unverified"
    assert actual["profile"]["language"] == "unverified"
    assert actual["boot"]["system_cnf_ver"] == "1.02"
    assert actual["executable_format"] == "ELF32-little-endian-MIPS"


@pytest.mark.parametrize("missing", ["SYSTEM.CNF", "SLES_000.01", "B0.MFA"])
def test_missing_required_file_rejected(tmp_path, missing):
    path = make_iso(tmp_path / "missing.iso", {k: v for k, v in FILES.items() if k != missing})
    with IsoImage(path) as disc, pytest.raises(ProfileError, match="Missing"):
        collect_disc(disc, "test", "a" * 64)


@pytest.mark.parametrize(
    "elf",
    [
        b"invalid",
        ELF.replace(b"ELF", b"BAD"),
        ELF[:4] + b"\x02" + ELF[5:],
        ELF[:18] + b"\x03\0" + ELF[20:],
    ],
)
def test_invalid_boot_executable(tmp_path, elf):
    path = make_iso(tmp_path / "bad-elf.iso", {**FILES, "SLES_000.01": elf})
    with IsoImage(path) as disc, pytest.raises(ProfileError, match="ELF"):
        collect_disc(disc, "test", "a" * 64)


@pytest.mark.parametrize(
    "raw", [b"", b"not an iso", b"\0" * 40000], ids=["empty", "garbage", "zero-descriptors"]
)
def test_malformed_iso_is_typed(tmp_path, raw):
    path = tmp_path / "bad.iso"
    path.write_bytes(raw)
    with pytest.raises(ProfileError) as error, IsoImage(path):
        pytest.fail("Malformed input accepted")
    assert error.value.code == "INVALID_ISO"


def test_truncated_file_extent_is_rejected(tmp_path):
    path = make_iso(tmp_path / "truncated.iso")
    with path.open("r+b") as stream:
        stream.truncate(24 * 2048)
    with pytest.raises(ProfileError), IsoImage(path) as disc:
        collect_disc(disc, "test", "a" * 64)


def test_iso_symlink_and_absent_input(tmp_path):
    path = make_iso(tmp_path / "synthetic.iso")
    link = tmp_path / "link.iso"
    link.symlink_to(path)
    for candidate in (link, tmp_path / "missing", tmp_path):
        with pytest.raises(ProfileError), IsoImage(candidate):
            pytest.fail("Non-regular input accepted")


def test_changed_input_rejected(tmp_path):
    path = make_iso(tmp_path / "changed.iso")
    with pytest.raises(ProfileError, match="changed"), IsoImage(path) as disc:
        disc.image_identity()
        with path.open("ab") as stream:
            stream.write(b"changed")


def test_missing_iso_member_and_prefix_limit(tmp_path):
    with IsoImage(make_iso(tmp_path / "synthetic.iso")) as disc:
        for operation in (
            lambda: disc.inspect("absent"),
            lambda: disc.read_prefix("SYSTEM.CNF", 4097),
        ):
            with pytest.raises(ProfileError):
                operation()


@pytest.mark.integration
def test_cli_report_and_profile_verification(tmp_path, capsys):
    path = make_iso(tmp_path / "synthetic.iso")
    report = tmp_path / "report.json"
    args = ["--iso", str(path), "--region", "Europe", "--output", str(report)]
    assert main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "observed"
    assert summary["extraction"] == "not_performed"
    data = json.loads(report.read_text())
    assert data["image"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert data["file_count"] == 3
    assert str(tmp_path) not in report.read_text()
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps(data["profile"]))
    report2 = tmp_path / "verified.json"
    assert main(args[:-1] + [str(report2), "--profile", str(profile)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "matched_local_profile"
    altered = json.loads(profile.read_text())
    altered["files"][0]["sha256"] = "0" * 64
    profile.write_text(json.dumps(altered))
    assert main(args[:-1] + [str(tmp_path / "fail.json"), "--profile", str(profile)]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "HASH_MISMATCH"
    assert not (tmp_path / "fail.json").exists()


def test_cli_does_not_overwrite_existing_output(tmp_path, capsys):
    path = make_iso(tmp_path / "synthetic.iso")
    before = path.read_bytes()
    assert main(["--iso", str(path), "--output", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "OUTPUT_EXISTS"
    assert path.read_bytes() == before


def test_cli_input_and_output_errors(tmp_path, capsys):
    args = ["--iso", str(tmp_path / "missing.iso"), "--output", str(tmp_path / "out")]
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "ISO_READ_ERROR"
    args[1] = str(make_iso(tmp_path / "synthetic.iso"))
    args[-1] = str(tmp_path / "missing-dir/out")
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "REPORT_WRITE_ERROR"


@pytest.mark.parametrize(
    "field,value",
    [
        ("serial", "SLES-99999"),
        ("platform", "synthetic"),
        ("region", "Japan"),
        ("files", "partial"),
    ],
)
def test_cli_rejects_inconsistent_or_partial_profile(tmp_path, capsys, field, value):
    path = make_iso(tmp_path / "synthetic.iso")
    profile = collect_disc(MemoryDisc(), "Europe", "a" * 64)["profile"]
    profile[field] = profile["files"][:1] if value == "partial" else value
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile))
    output = tmp_path / "report.json"
    assert (
        main(
            [
                "--iso",
                str(path),
                "--region",
                "Europe",
                "--profile",
                str(profile_path),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["code"] == "PROFILE_MISMATCH"
    assert not output.exists()


@pytest.mark.parametrize("data,expected", [(b"truncated", 10), (b"excess", 5)])
def test_stream_hash_rejects_size_mismatch(data, expected):
    with pytest.raises(ProfileError) as error:
        IsoImage._hash(BytesIO(data), expected)
    assert error.value.code == "SIZE_MISMATCH"


def test_unsupported_iso_file_version(tmp_path):
    path = tmp_path / "v2.iso"
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(BytesIO(b"test"), 4, iso_path="/TEST.;2")
    iso.write(str(path))
    iso.close()
    with pytest.raises(ProfileError) as error, IsoImage(path):
        pytest.fail("Unexpected file version accepted")
    assert error.value.code == "UNSUPPORTED_ISO"


def test_declared_extent_beyond_image_rejected(tmp_path):
    path = make_iso(tmp_path / "bad-extent.iso")
    # Corrupt only the synthetic directory record's extent, in both byte orders.
    data = bytearray(path.read_bytes())
    name_offset = data.index(b"B0.MFA;1", 16 * 2048)
    record_start = name_offset - 33
    beyond = len(data) // 2048 + 1
    data[record_start + 2 : record_start + 10] = struct.pack("<I", beyond) + struct.pack(
        ">I", beyond
    )
    path.write_bytes(data)
    with pytest.raises(ProfileError) as error, IsoImage(path):
        pytest.fail("Out-of-bounds extent accepted")
    assert error.value.code == "INVALID_ISO"


def synthetic_reference(path):
    data = path.read_bytes()
    return {
        "schema_version": 1,
        "id": "synthetic-catalog",
        "source_url": "https://example.invalid/synthetic",
        "retrieved_on": "2026-10-16",
        "serial": "SLES-00001",
        "region": "Europe",
        "revision": "1.02",
        "languages": ["en", "es"],
        "image": {
            "size": len(data),
            "sha1": hashlib.sha1(data).hexdigest(),
            "md5": hashlib.md5(data).hexdigest(),
            "crc32": f"{zlib.crc32(data):08x}",
        },
    }


@pytest.mark.integration
def test_cli_applies_catalog_after_matching_image_and_profile(tmp_path, capsys):
    iso = make_iso(tmp_path / "synthetic.iso")
    reference = tmp_path / "reference.json"
    reference.write_text(json.dumps(synthetic_reference(iso)))
    output = tmp_path / "matched.json"
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps(collect_disc(MemoryDisc(), "Europe", "a" * 64)["profile"]))
    args = [
        "--iso",
        str(iso),
        "--output",
        str(output),
        "--catalog",
        str(reference),
        "--profile",
        str(profile),
    ]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "matched_catalog"
    report = json.loads(output.read_text())
    assert report["profile"]["revision"] == "1.02"
    assert report["profile"]["language"] == "en,es"
    assert report["profile"]["capabilities"] == []
    assert report["catalog"]["language_runtime_verified"] is False
    assert report["compatibility"] == "unverified"
    assert report["image"]["sha256"] == hashlib.sha256(iso.read_bytes()).hexdigest()
    # A confirmed profile can be checked again without silently reverting metadata.
    profile.write_text(json.dumps(report["profile"]))
    args[3] = str(tmp_path / "repeat.json")
    assert main(args) == 0
    capsys.readouterr()
    # Metadata contradictions reject the report even when the file hashes match.
    bad = {**report["profile"], "revision": "9.99"}
    profile.write_text(json.dumps(bad))
    args[3] = str(tmp_path / "bad.json")
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "PROFILE_MISMATCH"
    assert not (tmp_path / "bad.json").exists()


@pytest.mark.integration
def test_catalog_rejects_modified_disc_with_unchanged_serial(tmp_path, capsys):
    iso = make_iso(tmp_path / "synthetic.iso")
    reference = tmp_path / "reference.json"
    reference.write_text(json.dumps(synthetic_reference(iso)))
    make_iso(iso, {**FILES, "B0.MFA": b"MODIFIED container"})
    output = tmp_path / "out.json"
    assert main(["--iso", str(iso), "--output", str(output), "--catalog", str(reference)]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "CATALOG_MISMATCH"
    assert not output.exists()


@pytest.mark.parametrize(
    "raw",
    [b"bad json", b"\xff", b"x" * 65537, None],
    ids=["bad-json", "encoding", "too-large", "absent"],
)
def test_cli_invalid_catalog(tmp_path, capsys, raw):
    path = tmp_path / "catalog.json"
    if raw is not None:
        path.write_bytes(raw)
    assert (
        main(
            [
                "--iso",
                str(tmp_path / "never-opened.iso"),
                "--output",
                str(tmp_path / "out"),
                "--catalog",
                str(path),
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["code"] in {"INVALID_CATALOG", "CATALOG_READ_ERROR"}
