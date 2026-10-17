"""M01-M08: generated metadata/payloads only; no candidate executable or game data."""

import hashlib
import json
import struct
from contextlib import contextmanager
from io import BytesIO

import pycdlib
import pytest

from tools.inspectors import mfa, mfa_probe
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile


def sector(names=("own/one.bin",), toc=0xD8, data_size=2048, ranges=None):
    result = bytearray(2048)
    struct.pack_into("<II", result, toc, len(names), data_size)
    cursor = toc + 8 + len(names) * 16
    for i, name in enumerate(names):
        raw = name.encode("ascii") + b"\0"
        offset, size = (i * 32, 16) if ranges is None else ranges[i]
        struct.pack_into("<IIII", result, toc + 8 + i * 16, cursor, offset, 0x1234, size)
        result[cursor : cursor + len(raw)] = raw
        cursor += len(raw)
    assert len(result) == 2048
    return bytes(result)


class Sectors:
    def __init__(self, sectors):
        self.sectors = sectors
        self.calls = []

    def read_at(self, offset, length):
        self.calls.append((offset, length))
        assert length == 2048
        # No payload sector is available: any accidental payload read fails.
        return self.sectors[offset]


def inspect(first=None, second=None):
    reader = Sectors({0: sector() if first is None else first})
    size = 4096
    if second is not None:
        reader.sectors[4096] = second
        size = 8192
    return mfa.inspect_d8(reader, size)


def changed(data, offset, value):
    result = bytearray(data)
    struct.pack_into("<I", result, offset, value)
    return bytes(result)


def test_valid_one_block_expected_ranges_and_no_payload_read():
    reader = Sectors({0: sector(("own/space name.bin", "empty.bin"), ranges=[(0, 16), (2048, 0)])})
    result = mfa.inspect_d8(reader, 4096)
    assert result == {
        "status": "structural_candidate",
        "layout": "mfa-d8-blocks-v1",
        "blocks": [
            {
                "offset": 0,
                "toc_offset": 216,
                "data_end": 4096,
                "entry_count": 2,
                "payload_bytes": 16,
                "unknown_word_values": [0x1234],
            }
        ],
        "block_count": 1,
        "entry_count": 2,
        "payload_bytes": 16,
        "metadata_bytes_read": 2048,
    }
    assert reader.calls == [(0, 2048)]
    assert "space name" not in json.dumps(result)


def test_multiblock_and_large_payload_do_not_allocate_or_read_payloads():
    data_size = 1024 * 1024 * 1024
    base = data_size + 2048
    reader = Sectors({0: sector(data_size=data_size), base: sector(("own/two.bin",), toc=8)})
    result = mfa.inspect_d8(reader, base + 4096)
    assert result["entry_count"] == result["block_count"] == 2
    assert result["blocks"][1]["toc_offset"] == base + 8
    assert reader.calls == [(0, 2048), (base, 2048)]


@pytest.mark.parametrize("size", [0, -1, 1, 2047, 4097, 1 << 63, True, 4096.0, "4096"])
def test_invalid_size_reads_nothing(size):
    reader = Sectors({})
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_d8(reader, size)
    assert error.value.code == "MFA_SIZE"
    assert reader.calls == []


@pytest.mark.parametrize(
    "offset,value,code",
    [
        (216, 0, "MFA_TABLE"),
        (216, 0xFFFFFFFF, "MFA_TABLE"),
        (220, 0, "MFA_BLOCK_RANGE"),
        (220, 1, "MFA_BLOCK_RANGE"),
        (220, 4096, "MFA_BLOCK_RANGE"),
        (224, 0, "MFA_NAME"),
        (224, 239, "MFA_NAME"),
        (224, 2048, "MFA_NAME"),
        (224, 0xFFFFFFFF, "MFA_NAME"),
        (228, 2049, "MFA_PAYLOAD_RANGE"),
        (236, 0xFFFFFFFF, "MFA_PAYLOAD_RANGE"),
    ],
)
def test_invalid_structure_has_typed_error(offset, value, code):
    with pytest.raises(mfa.MfaError) as error:
        inspect(changed(sector(), offset, value))
    assert error.value.code == code


@pytest.mark.parametrize(
    "name", ["", "/absolute", "../escape", "a/../b", "a//b", "a/./b", "a/", "C:/file", "a\\b"]
)
def test_unsafe_names_are_not_sanitized(name):
    with pytest.raises(mfa.MfaError) as error:
        inspect(sector((name,)))
    assert error.value.code == "MFA_PATH"


@pytest.mark.parametrize("change", ["unterminated", "control", "nonascii", "too_long"])
def test_name_encoding_and_termination_are_bounded(change):
    raw = bytearray(sector())
    if change == "unterminated":
        raw[240:] = b"a" * (2048 - 240)
    elif change == "control":
        raw[240] = 31
    elif change == "nonascii":
        raw[240] = 255
    else:
        raw[240:1266] = b"a" * 1025 + b"\0"
    with pytest.raises(mfa.MfaError) as error:
        inspect(bytes(raw))
    assert error.value.code == "MFA_NAME"


def test_maximum_name_length_is_supported():
    assert inspect(sector(("a" * 1024,)))["entry_count"] == 1


@pytest.mark.parametrize("names", [("a", "A"), ("a", "a/b"), ("a/b", "a"), ("a/b", "A/B")])
def test_duplicates_and_file_directory_collisions(names):
    with pytest.raises(mfa.MfaError) as error:
        inspect(sector(names))
    assert error.value.code == "MFA_DUPLICATE_PATH"


def test_collisions_across_blocks_are_rejected():
    with pytest.raises(mfa.MfaError) as error:
        inspect(second=sector(("OWN/ONE.BIN",), toc=8))
    assert error.value.code == "MFA_DUPLICATE_PATH"


def test_overlap_rejected_but_adjacency_and_out_of_order_are_valid():
    names = ("a", "b")
    with pytest.raises(mfa.MfaError) as error:
        inspect(sector(names, ranges=[(0, 16), (15, 1)]))
    assert error.value.code == "MFA_OVERLAP"
    assert inspect(sector(names, ranges=[(16, 16), (0, 16)]))["payload_bytes"] == 32


@pytest.mark.parametrize("limit", ["MAX_BLOCKS", "MAX_ENTRIES"])
def test_resource_budgets_stop_before_reading_or_allocating_unbounded(monkeypatch, limit):
    monkeypatch.setattr(mfa, limit, 1)
    reader = Sectors({0: sector(), 4096: sector(("other",), toc=8)})
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_d8(reader, 8192)
    assert error.value.code == "MFA_LIMIT"
    assert len(reader.calls) == (1 if limit == "MAX_BLOCKS" else 2)


def test_incomplete_following_block_cannot_accept_first_block():
    with pytest.raises(mfa.MfaError) as error:
        inspect(second=bytes(2048))
    assert error.value.code == "MFA_TABLE"


def test_b8_and_unknown_remain_unknown_under_d8_policy():
    for data in (sector(toc=0xB8), bytes(2048)):
        with pytest.raises(mfa.MfaError):
            inspect(data)


def test_short_read_is_transport_error_not_format_unknown():
    with pytest.raises(ProfileError) as error:
        mfa.inspect_d8(Sectors({0: b"short"}), 4096)
    assert type(error.value) is ProfileError
    assert error.value.code == "SHORT_READ"


def own_files():
    elf = bytearray(52)
    elf[:7] = b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHI", elf, 16, 2, 8, 1)
    struct.pack_into("<H", elf, 40, 52)
    return {
        "SYSTEM.CNF": b"BOOT2 = cdrom0:\\SLES_000.01;1\nVER = 1.02\nVMODE = PAL\n",
        "SLES_000.01": bytes(elf),
        "B0.MFA": sector() + b"own payload!".ljust(2048, b"!"),
        "ALT.MFA": sector(toc=0xB8) + bytes(2048),
        "BAD.MFA": b"own unknown format",
    }


def profile_data(files):
    return {
        "schema_version": 1,
        "id": "synthetic-mfa-probe",
        "platform": "ps2",
        "region": "Europe",
        "revision": "synthetic",
        "serial": "SLES-00001",
        "language": "synthetic",
        "extractor_version": "none",
        "capabilities": [],
        "files": [
            {"path": p, "size": len(d), "sha256": hashlib.sha256(d).hexdigest()}
            for p, d in files.items()
        ],
    }


class MemoryDisc:
    def __init__(self, files, offsets):
        self.files = files
        self.offsets = offsets
        self.hashed = set()

    def paths(self):
        return tuple(reversed(self.files))

    def inspect(self, path):
        self.hashed.add(path)
        data = self.files[path]
        return len(data), hashlib.sha256(data).hexdigest()

    def read_prefix(self, path, limit):
        assert self.hashed == set(self.files)
        return self.files[path][:limit]

    def file_offset(self, path):
        return self.offsets[path]

    def read_range(self, path, offset, length):
        assert self.hashed == set(self.files)
        return self.files[path][offset : offset + length]


@pytest.fixture
def source(tmp_path):
    files = own_files()
    image = pycdlib.PyCdlib()
    image.new(interchange_level=3, vol_ident="OWNTEST")
    for path, data in files.items():
        image.add_fp(BytesIO(data), len(data), iso_path=f"/{path};1")
    path = tmp_path / "own.iso"
    image.write(str(path))
    image.close()
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps(profile_data(files)))
    return path, profile


def arguments(source, tmp_path):
    iso, profile = source
    return [
        "--iso",
        str(iso),
        "--profile",
        str(profile),
        "--image-sha256",
        hashlib.sha256(iso.read_bytes()).hexdigest(),
        "--output",
        str(tmp_path / "out.json"),
    ]


def test_memory_and_iso_substitution_and_repeat_output(source, tmp_path, capsys):
    iso, profile = source
    original = iso.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    parsed = parse_profile(json.loads(profile.read_text()))
    with IsoImage(iso) as image:
        offsets = {p: image.file_offset(p) for p in image.paths()}
        actual = mfa_probe.collect_probe(image, parsed, len(original), digest)
    expected = mfa_probe.collect_probe(
        MemoryDisc(own_files(), offsets), parsed, len(original), digest
    )
    assert actual == expected
    assert actual["summary"] == {
        "candidate_count": 3,
        "status_counts": {"structural_candidate": 1, "unknown": 2},
        "structural_entry_count": 1,
        "structural_block_count": 1,
    }
    assert actual["capabilities"] == []
    assert actual["extraction"] == actual["payload_validation"] == "not_performed"
    args = arguments(source, tmp_path)
    assert mfa_probe.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "probed"
    result = (tmp_path / "out.json").read_bytes()
    assert b"own payload" not in result and b"own/one.bin" not in result
    assert str(tmp_path).encode() not in result
    args[-1] = str(tmp_path / "repeat.json")
    assert mfa_probe.main(args) == 0
    assert (tmp_path / "repeat.json").read_bytes() == result
    assert mfa_probe.main(args) == 1
    assert (tmp_path / "repeat.json").read_bytes() == result
    assert iso.read_bytes() == original


def test_non_mfa_members_not_selected():
    files = own_files()
    files = {p: d for p, d in files.items() if not p.endswith(".MFA")}
    reader = MemoryDisc(files, {p: 0 for p in files})
    result = mfa_probe.collect_probe(reader, parse_profile(profile_data(files)), 65536, "a" * 64)
    assert result["summary"]["candidate_count"] == 0


@pytest.mark.parametrize(
    "change",
    [
        "hash",
        "profile_hash",
        "absent_iso",
        "absent_profile",
        "output_link",
        "output_dir",
        "invalid_hash",
    ],
)
def test_cli_rejects_without_report(source, tmp_path, capsys, change):
    args = arguments(source, tmp_path)
    if change == "hash":
        args[5] = "0" * 64
    elif change == "invalid_hash":
        args[5] = "not a hash"
    elif change == "profile_hash":
        raw = json.loads(source[1].read_text())
        raw["files"][-1]["sha256"] = "0" * 64
        source[1].write_text(json.dumps(raw))
    elif change == "absent_iso":
        args[1] += "absent"
    elif change == "absent_profile":
        args[3] += "absent"
    elif change == "output_link":
        (tmp_path / "out.json").symlink_to(tmp_path / "absent")
    else:
        args[-1] = str(tmp_path / "absent/out.json")
    assert mfa_probe.main(args) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"
    assert not (tmp_path / "out.json").exists()


@pytest.mark.parametrize("operation", ["image_identity", "inspect", "read_prefix", "read_range"])
def test_transport_failure_aborts_entire_probe(source, tmp_path, capsys, monkeypatch, operation):
    def fail(*args):
        raise ProfileError("ISO_READ_ERROR", "Own failure injection")

    monkeypatch.setattr(IsoImage, operation, fail)
    assert mfa_probe.main(arguments(source, tmp_path)) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "ISO_READ_ERROR"
    assert not (tmp_path / "out.json").exists()


def test_input_mutation_before_close_prevents_report(source, tmp_path, monkeypatch, capsys):
    collect = mfa_probe.collect_probe

    def mutate(*args):
        result = collect(*args)
        with source[0].open("ab") as out:
            out.write(b"own mutation")
        return result

    monkeypatch.setattr(mfa_probe, "collect_probe", mutate)
    assert mfa_probe.main(arguments(source, tmp_path)) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "INPUT_CHANGED"
    assert not (tmp_path / "out.json").exists()


@pytest.mark.parametrize(
    "offset,length,code",
    [
        (-1, 1, "READ_RANGE"),
        (4096, 1, "READ_RANGE"),
        (1, 4096, "READ_RANGE"),
        (True, 1, "READ_RANGE"),
        (0.0, 1, "READ_RANGE"),
        (0, True, "READ_LIMIT"),
        (0, -1, "READ_LIMIT"),
        (0, 4097, "READ_LIMIT"),
        (0, 1.0, "READ_LIMIT"),
    ],
)
def test_iso_ranges_confined_before_io(source, offset, length, code):
    with IsoImage(source[0]) as image, pytest.raises(ProfileError) as error:
        image.read_range("B0.MFA", offset, length)
    assert error.value.code == code


def test_exact_iso_range_and_eof(source):
    with IsoImage(source[0]) as image:
        assert image.read_range("B0.MFA", 2048, 12) == b"own payload!"
        assert image.read_range("B0.MFA", 4096, 0) == b""


@pytest.mark.parametrize("short", [True, False])
def test_iso_read_failure_is_typed(source, monkeypatch, short):
    @contextmanager
    def broken(self, **kwargs):
        if not short:
            raise OSError("own read failure")
        yield BytesIO(b"short")

    with IsoImage(source[0]) as image:
        monkeypatch.setattr(pycdlib.PyCdlib, "open_file_from_iso", broken)
        with pytest.raises(ProfileError) as error:
            image.read_range("B0.MFA", 0, 2048)
    assert error.value.code == ("SHORT_READ" if short else "ISO_READ_ERROR")
