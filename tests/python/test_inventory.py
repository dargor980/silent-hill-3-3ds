"""F02.01: deterministic metadata, conservative signatures and fail-closed custody."""

import hashlib
import json
import struct
from dataclasses import replace
from io import BytesIO

import pycdlib
import pytest

from tools.inspectors import catalog
from tools.inspectors.inventory import collect_inventory, entry_id
from tools.inspectors.signatures import PREFIX_LIMIT, classify
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile

CONFIG = b"BOOT2 = cdrom0:\\SLES_000.01;1\r\nVER = 1.02\r\nVMODE = PAL\r\n"
ELF = bytearray(52)
ELF[:7] = b"\x7fELF\x01\x01\x01"
struct.pack_into("<HHI", ELF, 16, 2, 8, 1)
struct.pack_into("<H", ELF, 40, 52)
ELF = bytes(ELF)
FILES = {
    "SYSTEM.CNF": CONFIG,
    "SLES_000.01": ELF,
    "B0.MFA": b"own unknown container bytes",
    "FAKE.AFS": b"not an archive despite extension",
    "REAL.DAT": b"AFS\0" + struct.pack("<I", 0),
    "EMPTY.DAT": b"",
    "SAME.DAT": b"own unknown container bytes",
}


def profile_for(files):
    return parse_profile(
        {
            "schema_version": 1,
            "id": "ps2-synthetic-disc",
            "platform": "ps2",
            "region": "Europe",
            "revision": "synthetic",
            "serial": "SLES-00001",
            "language": "synthetic",
            "extractor_version": "none",
            "capabilities": [],
            "files": [
                {"path": path, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for path, data in files.items()
            ],
        }
    )


class MemoryReader:
    def __init__(self, files=None, offsets=None):
        self.files = FILES.copy() if files is None else files
        self.offsets = offsets or {path: index * 2048 for index, path in enumerate(self.files)}
        self.inspected = []
        self.prefixes = []

    def paths(self):
        return tuple(self.files)

    def inspect(self, path):
        self.inspected.append(path)
        data = self.files[path]
        return len(data), hashlib.sha256(data).hexdigest()

    def file_offset(self, path):
        return self.offsets[path]

    def read_prefix(self, path, limit):
        assert set(self.inspected) == set(self.files), "All hashes must be checked first"
        assert 0 <= limit <= PREFIX_LIMIT
        self.prefixes.append(path)
        return self.files[path][:limit]


def inventory(reader=None, profile=None):
    return collect_inventory(
        reader or MemoryReader(), profile or profile_for(FILES), 65536, "a" * 64
    )


def test_complete_deterministic_inventory_and_known_dependency():
    report = inventory()
    reverse = MemoryReader(dict(reversed(list(FILES.items()))), MemoryReader().offsets)
    assert inventory(reverse) == report
    assert report["summary"]["file_count"] == len(FILES)
    assert report["summary"]["type_counts"] == {
        "afs_candidate": 1,
        "elf32_le_mips": 1,
        "ps2_boot_config": 1,
        "unknown": 4,
    }
    assert report["capabilities"] == []
    assert report["extraction"] == report["nested_inventory"] == "not_performed"
    entries = {e["path"]: e for e in report["entries"]}
    assert list(entries) == sorted(FILES)
    assert len({e["id"] for e in entries.values()}) == len(FILES)
    assert entries["SAME.DAT"]["sha256"] == entries["B0.MFA"]["sha256"]
    assert entries["SAME.DAT"]["id"] != entries["B0.MFA"]["id"]
    assert entries["SYSTEM.CNF"]["dependencies"] == {
        "status": "partial",
        "known": [
            {
                "target_id": entries["SLES_000.01"]["id"],
                "relation": "boot_executable",
                "evidence": "SYSTEM.CNF:BOOT2",
            }
        ],
    }
    for entry in report["entries"]:
        assert entry["origin"] == {
            "profile_id": "ps2-synthetic-disc",
            "image_id": "iso:" + "a" * 64,
        }
        assert entry["container_id"] == report["source"]["id"]
        assert entry["support"] == "inventory_only"
        if entry["path"] != "SYSTEM.CNF":
            assert entry["dependencies"] == {"status": "not_inspected", "known": []}
    encoded = json.dumps(report)
    assert "own unknown container bytes" not in encoded
    assert "not an archive despite extension" not in encoded


def test_ids_bind_image_profile_and_path():
    base = entry_id("a" * 64, "profile", "one")
    assert base != entry_id("b" * 64, "profile", "one")
    assert base != entry_id("a" * 64, "other", "one")
    assert base != entry_id("a" * 64, "profile", "two")


@pytest.mark.parametrize("path", ["FILE.MFA", "FILE.AFS", "FILE.IRX", "FILE.BIN", "FILE.ELF"])
def test_extensions_do_not_grant_format(path):
    result = classify(path, b"synthetic unknown", 17)
    assert result["type"] == result["recognition"] == "unknown"


@pytest.mark.parametrize(
    "data,reason",
    [
        (b"", "empty"),
        (b"\x7fELF", "truncated_elf_header"),
        (b"AFS\0", "truncated_afs_header"),
        (b"AFS!xxxx", "no_registered_signature"),
    ],
)
def test_unknown_reason_is_explicit(data, reason):
    result = classify("ANY.DAT", data, len(data))
    assert result["type"] == "unknown"
    assert result["reason"] == reason


@pytest.mark.parametrize("offset,value", [(4, 2), (5, 2), (6, 0), (18, 40), (20, 0), (40, 0)])
def test_elf_unsupported_variants_remain_unknown(offset, value):
    data = bytearray(ELF)
    data[offset] = value
    assert classify("ANY.DAT", bytes(data), len(data))["reason"] == "unsupported_elf_header"


def test_signatures_do_not_depend_on_extension_or_claim_full_validation():
    assert classify("OTHER.MFA", ELF, len(ELF))["recognition"] == "header_checked"
    afs = b"AFS\0" + b"\xff" * 4  # Count is deliberately not interpreted in this task.
    assert classify("OTHER.BIN", afs, len(afs))["recognition"] == "signature_only"


@pytest.mark.parametrize("prefix,size", [(b"a", 2), (b"a", 0), (b"a" * 4097, 4097)])
def test_short_or_excess_prefix_is_error(prefix, size):
    with pytest.raises(ProfileError) as error:
        classify("ANY.DAT", prefix, size)
    assert error.value.code == "PREFIX_SIZE_MISMATCH"


def test_oversized_boot_config_rejected():
    with pytest.raises(ProfileError) as error:
        classify("SYSTEM.CNF", b"a" * 4096, 4097)
    assert error.value.code == "INVALID_BOOT_CONFIG"


@pytest.mark.parametrize("change", ["missing", "extra", "duplicate", "hash", "size", "platform"])
def test_profile_must_match_all_entries_before_prefix_read(change):
    reader = MemoryReader()
    profile = profile_for(FILES)
    if change == "missing":
        reader.files.pop("B0.MFA")
    elif change == "extra":
        reader.files["EXTRA.DAT"] = b"extra"
    elif change == "duplicate":
        reader.paths = lambda: tuple(FILES) + ("B0.MFA",)
    elif change in {"hash", "size"}:
        # Mutate the last entry so earlier entries are checked but never classified.
        reader.files["SAME.DAT"] = b"X" * len(FILES["SAME.DAT"]) if change == "hash" else b"short"
    else:
        profile = replace(profile, platform="synthetic")
    with pytest.raises(ProfileError):
        inventory(reader, profile)
    assert reader.prefixes == []


@pytest.mark.parametrize("offset", [-1, True, 1.5, 65536, 1 << 64])
def test_invalid_offsets_rejected(offset):
    reader = MemoryReader()
    reader.offsets["B0.MFA"] = offset
    with pytest.raises(ProfileError) as error:
        inventory(reader)
    assert error.value.code == "INVALID_OFFSET"


@pytest.mark.parametrize("size", [0, -1, True, 1 << 64])
def test_invalid_image_size(size):
    with pytest.raises(ProfileError) as error:
        collect_inventory(MemoryReader(), profile_for(FILES), size, "a" * 64)
    assert error.value.code == "INVALID_SIZE"


@pytest.mark.parametrize("digest", [None, "a" * 63, "A" * 64, "invalid"])
def test_invalid_image_identity(digest):
    with pytest.raises(ProfileError) as error:
        collect_inventory(MemoryReader(), profile_for(FILES), 65536, digest)
    assert error.value.code == "INVALID_IMAGE_HASH"


@pytest.mark.parametrize("change", ["no_config", "no_executable", "serial", "bad_executable"])
def test_boot_relation_requires_matching_target(change):
    files = FILES.copy()
    if change == "no_config":
        del files["SYSTEM.CNF"]
    elif change == "no_executable":
        del files["SLES_000.01"]
    elif change == "serial":
        files["SYSTEM.CNF"] = CONFIG.replace(b"SLES_000.01", b"SLES_000.02")
    else:
        files["SLES_000.01"] = b"unknown"
    with pytest.raises(ProfileError):
        inventory(MemoryReader(files), profile_for(files))


@pytest.fixture
def synthetic_disc(tmp_path):
    path = tmp_path / "synthetic.iso"
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident="SYNTHETIC")
    for name, data in FILES.items():
        iso.add_fp(BytesIO(data), len(data), iso_path=f"/{name};1")
    iso.write(str(path))
    iso.close()
    return path


def cli_arguments(tmp_path, disc):
    profile = tmp_path / "profile.json"
    # Keep the on-disk schema separate from the frozen domain value.
    data = {
        "schema_version": 1,
        "id": "ps2-synthetic-disc",
        "platform": "ps2",
        "region": "Europe",
        "revision": "synthetic",
        "serial": "SLES-00001",
        "language": "synthetic",
        "extractor_version": "none",
        "capabilities": [],
        "files": [
            {"path": p, "size": len(b), "sha256": hashlib.sha256(b).hexdigest()}
            for p, b in FILES.items()
        ],
    }
    profile.write_text(json.dumps(data))
    return [
        "--iso",
        str(disc),
        "--profile",
        str(profile),
        "--image-sha256",
        hashlib.sha256(disc.read_bytes()).hexdigest(),
        "--output",
        str(tmp_path / "catalog.json"),
    ]


def test_iso_and_memory_contract_offsets_match_actual_bytes(synthetic_disc):
    image_bytes = synthetic_disc.read_bytes()
    with IsoImage(synthetic_disc) as iso:
        size, digest = iso.image_identity()
        offsets = {path: iso.file_offset(path) for path in iso.paths()}
        actual = collect_inventory(iso, profile_for(FILES), size, digest)
    expected = collect_inventory(MemoryReader(offsets=offsets), profile_for(FILES), size, digest)
    assert actual == expected
    for entry in actual["entries"]:
        start = entry["offset"]
        assert image_bytes[start : start + entry["size"]] == FILES[entry["path"]]
    assert synthetic_disc.read_bytes() == image_bytes


def test_cli_repeat_is_identical_without_payloads_or_absolute_paths(
    tmp_path, synthetic_disc, capsys
):
    args = cli_arguments(tmp_path, synthetic_disc)
    assert catalog.main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "catalogued"
    assert summary["file_count"] == len(FILES)
    output = tmp_path / "catalog.json"
    original = output.read_bytes()
    assert str(tmp_path).encode() not in original
    assert FILES["B0.MFA"] not in original
    args[-1] = str(tmp_path / "repeat.json")
    assert catalog.main(args) == 0
    assert (tmp_path / "repeat.json").read_bytes() == original
    assert catalog.main(args) == 1
    assert (tmp_path / "repeat.json").read_bytes() == original


@pytest.mark.parametrize("change", ["hash", "absent", "profile", "output_dir", "output_link"])
def test_cli_failure_does_not_accept_report(tmp_path, synthetic_disc, capsys, change):
    args = cli_arguments(tmp_path, synthetic_disc)
    if change == "hash":
        args[5] = "0" * 64
    elif change == "absent":
        args[1] = str(tmp_path / "absent.iso")
    elif change == "profile":
        args[3] = str(tmp_path / "absent.json")
    elif change == "output_dir":
        args[-1] = str(tmp_path / "absent/out.json")
    else:
        (tmp_path / "catalog.json").symlink_to(tmp_path / "absent")
    assert catalog.main(args) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"
    assert not (tmp_path / "catalog.json").exists()


def test_changed_iso_is_rejected_before_report_write(tmp_path, synthetic_disc, monkeypatch):
    args = cli_arguments(tmp_path, synthetic_disc)
    collect = catalog.collect_inventory

    def change(*params):
        report = collect(*params)
        with synthetic_disc.open("ab") as stream:
            stream.write(b"synthetic mutation")
        return report

    monkeypatch.setattr(catalog, "collect_inventory", change)
    assert catalog.main(args) == 1
    assert not (tmp_path / "catalog.json").exists()


@pytest.mark.parametrize("operation", ["image_identity", "inspect", "read_prefix", "file_offset"])
def test_reader_failures_never_create_success_report(
    tmp_path, synthetic_disc, monkeypatch, capsys, operation
):
    args = cli_arguments(tmp_path, synthetic_disc)

    def fail(*args):
        raise ProfileError("ISO_READ_ERROR", "Synthetic read failure")

    monkeypatch.setattr(IsoImage, operation, fail)
    assert catalog.main(args) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "ISO_READ_ERROR"
    assert not (tmp_path / "catalog.json").exists()


def test_large_member_prefix_is_bounded():
    reader = MemoryReader({**FILES, "LARGE.DAT": b"x" * (PREFIX_LIMIT + 100)})
    report = inventory(reader, profile_for(reader.files))
    entry = next(e for e in report["entries"] if e["path"] == "LARGE.DAT")
    assert entry["size"] == PREFIX_LIMIT + 100
    assert entry["classification"]["type"] == "unknown"


@pytest.mark.parametrize("field_offset", [1, 26, 27])
def test_extended_or_interleaved_extent_is_not_claimed_contiguous(synthetic_disc, field_offset):
    data = bytearray(synthetic_disc.read_bytes())
    record_start = data.index(b"B0.MFA;1", 16 * 2048) - 33
    data[record_start + field_offset] = 1
    synthetic_disc.write_bytes(data)
    with pytest.raises(ProfileError), IsoImage(synthetic_disc):
        pytest.fail("Unsupported member layout accepted")


def test_missing_offset_member_is_typed(synthetic_disc):
    with IsoImage(synthetic_disc) as iso, pytest.raises(ProfileError) as error:
        iso.file_offset("MISSING.DAT")
    assert error.value.code == "MISSING_FILE"
