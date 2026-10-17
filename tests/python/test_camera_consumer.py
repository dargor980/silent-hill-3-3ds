"""CE01-CE08: ELF and instruction fixtures created here, without original payloads."""

import hashlib
import json
import struct
from copy import deepcopy
from dataclasses import replace
from io import BytesIO

import pycdlib
import pytest

from tools.inspectors import camera_consumer as consumer
from tools.inspectors import mips_camera
from tools.inspectors.elf32 import MAX_ELF_BYTES, ElfMap, Segment, parse_elf
from tools.inspectors.mips_camera import STRIDE, match_loop, scan_loops
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def instruction(op, source, destination, immediate):
    return (op << 26) | (source << 21) | (destination << 16) | (immediate & 0xFFFF)


def own_loop(*, base=7, loaded=8, masked=9, step_op=9, displacement=-8, reverse=False):
    return struct.pack(
        "<6I",
        instruction(step_op, base, base, 128),
        0,
        instruction(35, base, loaded, 68),
        instruction(12, loaded, masked, 1),
        instruction(4, 0 if reverse else masked, masked if reverse else 0, displacement),
        0,
    )


def own_elf(payload=None, *, segments=None):
    payload = bytes(32) + own_loop() + bytes(8) if payload is None else payload
    if segments is None:
        segments = [(1, 256, 0x1000, 0x1000, len(payload), len(payload) + 64, 5, 16)]
    data = bytearray(256 + len(payload))
    struct.pack_into(
        "<16sHHIIIIIHHHHHH",
        data,
        0,
        b"\x7fELF\x01\x01\x01" + bytes(9),
        2,
        8,
        1,
        0x1000,
        52,
        0,
        0,
        52,
        32,
        len(segments),
        0,
        0,
        0,
    )
    for i, segment in enumerate(segments):
        struct.pack_into("<8I", data, 52 + i * 32, *segment)
    data[256:] = payload
    return bytes(data)


class ByteReader:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def __call__(self, offset, size):
        assert 0 <= size <= 4096
        assert 0 <= offset <= offset + size <= len(self.data)
        self.calls.append((offset, size))
        return self.data[offset : offset + size]


def parsed(data):
    reader = ByteReader(data)
    return reader, parse_elf(reader, len(data))


def test_mapping_and_metadata_candidate_do_not_grant_semantics():
    data = own_elf()
    reader, mapping = parsed(data)
    assert mapping.file_offset(0x1000, 4) == 256
    assert mapping.file_offset(0x103C, 4) == 316
    result = scan_loops(reader, mapping)
    assert result["scanned_file_bytes"] == 64
    assert result["candidate_count"] == 1
    candidate = result["candidates"][0]
    assert candidate["file_offset"] == 288
    assert candidate["branch_target_offset"] == 276
    assert candidate["window_sha256"] == digest(own_loop())
    assert candidate["state"] == "syntactic_candidate"
    assert candidate["resource_link"] == candidate["execution_reachability"] == "unproven"
    assert "instructions" not in candidate and "bytes" not in candidate


@pytest.mark.parametrize("size", [0, 51, MAX_ELF_BYTES + 1, True, "64"])
def test_file_budget_rejected_before_read(size):
    with pytest.raises(ProfileError, match="budget"):
        parse_elf(lambda *_: pytest.fail("must not read"), size)


@pytest.mark.parametrize(
    "offset,fmt,value,code",
    [
        (0, "B", 0, "ELF_HEADER"),
        (4, "B", 2, "ELF_HEADER"),
        (5, "B", 2, "ELF_HEADER"),
        (6, "B", 0, "ELF_HEADER"),
        (16, "H", 3, "ELF_HEADER"),
        (18, "H", 3, "ELF_HEADER"),
        (20, "I", 2, "ELF_HEADER"),
        (40, "H", 51, "ELF_HEADER"),
        (28, "I", 0, "ELF_TABLE"),
        (28, "I", 310, "ELF_TABLE"),
        (42, "H", 31, "ELF_TABLE"),
        (44, "H", 0, "ELF_TABLE"),
        (44, "H", 129, "ELF_TABLE"),
        (44, "H", 65535, "ELF_TABLE"),
        (24, "I", 0x1001, "ELF_ALIGNMENT"),
        (24, "I", 0x1040, "ELF_UNBACKED_ADDRESS"),
        (56, "I", 320, "ELF_SEGMENT_RANGE"),
        (68, "I", 129, "ELF_SEGMENT_RANGE"),
        (72, "I", 63, "ELF_SEGMENT_RANGE"),
        (60, "I", 0xFFFFFFF0, "ELF_SEGMENT_RANGE"),
        (80, "I", 3, "ELF_ALIGNMENT"),
        (56, "I", 255, "ELF_ALIGNMENT"),
        (76, "I", 4, "ELF_UNBACKED_ADDRESS"),
    ],
)
def test_header_and_segment_failures(offset, fmt, value, code):
    data = bytearray(own_elf())
    struct.pack_into("<" + fmt, data, offset, value)
    with pytest.raises(ProfileError) as error:
        parsed(bytes(data))
    assert error.value.code == code


@pytest.mark.parametrize("bad", [b"", bytearray(52), None])
def test_malformed_reader_is_rejected(bad):
    with pytest.raises(ProfileError) as error:
        parse_elf(lambda *_: bad, 320)
    assert error.value.code == "ELF_SHORT_READ"


@pytest.mark.parametrize(
    "address,size,code",
    [
        (-1, 1, "ELF_ADDRESS"),
        (True, 1, "ELF_ADDRESS"),
        (0x1000, True, "ELF_ADDRESS"),
        (0x1000, 0, "ELF_ADDRESS"),
        (0xFFFFFFFF, 2, "ELF_ADDRESS"),
        (0x1040, 1, "ELF_UNBACKED_ADDRESS"),
        (0x103F, 2, "ELF_UNBACKED_ADDRESS"),
        (0x2000, 4, "ELF_UNBACKED_ADDRESS"),
    ],
)
def test_bss_holes_and_crossing_ranges_are_not_file_bytes(address, size, code):
    _, mapping = parsed(own_elf())
    with pytest.raises(ProfileError) as error:
        mapping.file_offset(address, size)
    assert error.value.code == code


def test_zero_byte_overlays_and_non_load_headers_are_not_scanned():
    load = (1, 256, 0x1000, 0, 64, 128, 5, 0)
    bss = (1, 320, 0x1080, 0, 0, 64, 7, 1)
    reader, mapping = parsed(own_elf(segments=[load, bss, bss, (0,) * 8]))
    assert mapping.program_header_count == 4 and len(mapping.segments) == 3
    assert scan_loops(reader, mapping)["scanned_segment_count"] == 1
    with pytest.raises(ProfileError):
        mapping.file_offset(0x1080, 4)


@pytest.mark.parametrize(
    "other",
    [
        (1, 272, 0x2000, 0, 16, 16, 4, 0),
        (1, 304, 0x1000, 0, 16, 16, 4, 0),
        (1, 320, 0x1000, 0, 0, 16, 7, 0),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_backed_overlap_with_another_memory_or_file_range_rejected(other, reverse):
    load = (1, 256, 0x1000, 0, 48, 48, 5, 0)
    segments = [load, other]
    with pytest.raises(ProfileError) as error:
        parsed(own_elf(segments=segments[::-1] if reverse else segments))
    assert error.value.code == "ELF_OVERLAP"


@pytest.mark.parametrize("step_op", [9, 25])
@pytest.mark.parametrize("reverse", [False, True])
def test_own_pattern_and_signed_branch(step_op, reverse):
    assert match_loop(own_loop(step_op=step_op, reverse=reverse), 0x1020) == 0x1014
    assert match_loop(own_loop(displacement=-5), 0x1020) == 0x1020
    assert match_loop(own_loop(displacement=-32768), 0x40000) == 0x20014


@pytest.mark.parametrize(
    "changes",
    [
        {"base": 0},
        {"loaded": 0},
        {"loaded": 7},
        {"masked": 0},
        {"masked": 7},
        {"step_op": 8},
        {"displacement": 0},
        {"displacement": 32767},
    ],
)
def test_pattern_wrong_registers_or_forward_target(changes):
    assert match_loop(own_loop(**changes), 0x1020) is None


@pytest.mark.parametrize(
    "index,word",
    [
        (0, instruction(9, 7, 6, 128)),
        (0, instruction(9, 7, 7, 127)),
        (1, instruction(9, 7, 7, 1)),
        (2, instruction(35, 6, 8, 68)),
        (2, instruction(35, 7, 8, 92)),
        (2, instruction(37, 7, 8, 68)),
        (3, instruction(12, 6, 9, 1)),
        (3, instruction(12, 8, 9, 2)),
        (3, instruction(13, 8, 9, 1)),
        (4, instruction(5, 9, 0, -8)),
        (4, instruction(20, 9, 0, -8)),
        (4, instruction(4, 9, 8, -8)),
        (5, instruction(9, 7, 7, 128)),
    ],
)
def test_pattern_rejects_near_matches_and_non_nop_delay(index, word):
    data = bytearray(own_loop())
    struct.pack_into("<I", data, index * 4, word)
    assert match_loop(bytes(data), 0x1020) is None


@pytest.mark.parametrize(
    "data,address",
    [
        (bytes(23), 0),
        (bytearray(24), 0),
        (None, 0),
        (bytes(24), 1),
        (bytes(24), -4),
        (bytes(24), True),
        (bytes(24), 0xFFFFFFF0),
    ],
)
def test_invalid_pattern_window(data, address):
    with pytest.raises(ProfileError) as error:
        match_loop(data, address)
    assert error.value.code == "MIPS_WINDOW"


def test_big_endian_and_target_underflow_not_matched():
    big = struct.pack(">6I", *struct.unpack("<6I", own_loop()))
    assert match_loop(big, 0x1020) is None
    assert match_loop(own_loop(), 0) is None


@pytest.mark.parametrize("position", [STRIDE - 4, STRIDE, STRIDE + 4, 4092, 4096, 8188])
def test_pattern_at_block_boundaries_is_found_exactly_once(position):
    data = own_elf(bytes(position) + own_loop() + bytes(12))
    reader, mapping = parsed(data)
    report = scan_loops(reader, mapping)
    assert report["candidate_count"] == 1
    assert report["candidates"][0]["file_offset"] == 256 + position
    assert max(size for _, size in reader.calls) <= 4096


def test_final_pattern_and_no_match_are_complete():
    reader, mapping = parsed(own_elf(bytes(32) + own_loop()))
    assert scan_loops(reader, mapping)["candidate_count"] == 1
    reader, mapping = parsed(own_elf(bytes(12)))
    assert scan_loops(reader, mapping)["candidate_count"] == 0


def test_pattern_cannot_cross_segment_boundary_or_jump_to_other_segment():
    loop = own_loop()
    data = own_elf(bytes(32) + loop)
    first = Segment(0, 256, 0x1000, 44, 44, 5, 1)
    second = Segment(1, 300, 0x102C, 12, 12, 5, 1)
    assert (
        scan_loops(ByteReader(data), ElfMap(0x1000, 0, 2, (first, second)))["candidate_count"] == 0
    )
    reader, mapping = parsed(own_elf(loop))
    assert scan_loops(reader, mapping)["candidate_count"] == 0  # target before segment


@pytest.mark.parametrize("field", ["offset", "address", "file_size"])
def test_scan_rejects_misalignment(field):
    _, mapping = parsed(own_elf())
    segment = replace(mapping.segments[0], **{field: getattr(mapping.segments[0], field) + 1})
    with pytest.raises(ProfileError) as error:
        scan_loops(lambda *_: pytest.fail("must not read"), replace(mapping, segments=(segment,)))
    assert error.value.code == "MIPS_ALIGNMENT"


def test_scan_budget_and_candidate_limit_abort(monkeypatch):
    reader, mapping = parsed(own_elf())
    segment = replace(mapping.segments[0], file_size=MAX_ELF_BYTES + 4)
    with pytest.raises(ProfileError) as error:
        scan_loops(lambda *_: pytest.fail("must not read"), replace(mapping, segments=(segment,)))
    assert error.value.code == "MIPS_BUDGET"
    monkeypatch.setattr(mips_camera, "MAX_CANDIDATES", 0)
    with pytest.raises(ProfileError) as error:
        scan_loops(reader, mapping)
    assert error.value.code == "MIPS_BUDGET"


def test_late_read_failure_never_returns_partial_candidates():
    reader, mapping = parsed(own_elf(bytes(32) + own_loop() + bytes(8192)))

    def broken(offset, size):
        if offset > 256 + STRIDE:
            raise ProfileError("OWN_IO_ERROR", "Synthetic read failure")
        return reader(offset, size)

    with pytest.raises(ProfileError) as error:
        scan_loops(broken, mapping)
    assert error.value.code == "OWN_IO_ERROR"


CONFIG = b"BOOT2 = cdrom0:\\SLES_000.01;1\nVER = 1.02\nVMODE = PAL\n"


class OwnDisc:
    def __init__(self, files):
        self.files = files
        self.inspected = []

    def paths(self):
        return tuple(self.files)

    def inspect(self, path):
        self.inspected.append(path)
        data = self.files[path]
        return len(data), digest(data)

    def read_range(self, path, offset, size):
        return ByteReader(self.files[path])(offset, size)


@pytest.fixture
def evidence(tmp_path):
    files = {"SYSTEM.CNF": CONFIG, "SLES_000.01": own_elf(), "OWN.BIN": b"own data"}
    path = tmp_path / "own.iso"
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident="OWN")
    for name, data in files.items():
        iso.add_fp(BytesIO(data), len(data), iso_path=f"/{name};1")
    iso.write(str(path))
    iso.close()
    profile = {
        "schema_version": 1,
        "id": "own-ps2-test",
        "platform": "ps2",
        "serial": "SLES-00001",
        "region": "Europe",
        "revision": "unverified",
        "language": "unverified",
        "extractor_version": "own",
        "capabilities": [],
        "files": [{"path": p, "size": len(b), "sha256": digest(b)} for p, b in files.items()],
    }
    source = {
        "id": "iso:" + digest(path.read_bytes()),
        "sha256": digest(path.read_bytes()),
        "size": path.stat().st_size,
        "profile": {
            k: profile[k] for k in ("id", "platform", "serial", "region", "revision", "language")
        },
    }
    probe = {
        "schema_version": 1,
        "source": source,
        "scope": "camera_hypothesis_survey",
        "method": "sh2-road128-reference-v1",
        "capabilities": [],
        "f02_07_status": "pending",
    }
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile))
    q = tmp_path / "probe.json"
    q.write_text(json.dumps(probe))
    args = [
        "--iso",
        str(path),
        "--profile",
        str(p),
        "--camera-probe",
        str(q),
        "--image-sha256",
        source["sha256"],
        "--profile-sha256",
        digest(p.read_bytes()),
        "--camera-probe-sha256",
        digest(q.read_bytes()),
    ]
    return files, path, profile, probe, args


def collect(evidence, *, disc=None, profile=None, probe=None):
    files, _, p, q, args = evidence
    return consumer.survey_consumer(
        disc or OwnDisc(files),
        parse_profile(p if profile is None else profile),
        q if probe is None else probe,
        q["source"]["size"],
        args[7],
        args[9],
        args[11],
    )


def test_memory_and_iso_agree_and_unrelated_member_not_individually_hashed(evidence):
    files, path, _, _, _ = evidence
    disc = OwnDisc(files)
    expected = collect(evidence, disc=disc)
    assert disc.inspected == ["SYSTEM.CNF", "SLES_000.01"]
    with IsoImage(path) as iso:
        assert collect(evidence, disc=iso) == expected
    assert expected["confirmed_camera_consumers"] == 0
    assert expected["capabilities"] == [] and expected["f02_07_status"] == "pending"
    # Own data can look like instructions; structural matching cannot identify camera input.
    assert expected["scan"]["candidate_count"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("source", {}),
        ("scope", "other"),
        ("method", "other"),
        ("capabilities", ["camera"]),
        ("f02_07_status", "complete"),
    ],
)
def test_mixed_probe_evidence_rejected(evidence, field, value):
    probe = deepcopy(evidence[3])
    probe[field] = value
    with pytest.raises(ProfileError) as error:
        collect(evidence, probe=probe)
    assert error.value.code == "CONSUMER_EVIDENCE"


@pytest.mark.parametrize(
    "mutation", ["size", "hash", "paths", "missing_config", "boot_serial", "missing_boot"]
)
def test_source_identity_and_boot_mismatches(evidence, mutation):
    files, _, profile, _, _ = evidence
    files, profile = deepcopy(files), deepcopy(profile)
    if mutation == "size":
        files["SLES_000.01"] += b"x"
    elif mutation == "hash":
        files["SLES_000.01"] = b"x" + files["SLES_000.01"][1:]
    elif mutation == "paths":
        files["NEW.BIN"] = b"x"
    elif mutation == "missing_config":
        del files["SYSTEM.CNF"]
    else:
        config = CONFIG.replace(b"000.01", b"999.01")
        files["SYSTEM.CNF"] = config
        profile["files"][0].update(size=len(config), sha256=digest(config))
        if mutation == "missing_boot":
            profile["serial"] = "SLES-99901"
            evidence[3]["source"]["profile"]["serial"] = "SLES-99901"
    with pytest.raises(ProfileError):
        collect(evidence, disc=OwnDisc(files), profile=profile)


@pytest.mark.parametrize("config", [b"", bytes(4097)])
def test_config_budget(evidence, config):
    files, _, profile, _, _ = evidence
    files["SYSTEM.CNF"] = config
    profile["files"][0].update(size=len(config), sha256=digest(config))
    with pytest.raises(ProfileError) as error:
        collect(evidence)
    assert error.value.code == "INVALID_BOOT_CONFIG"


def test_short_config_read(evidence):
    disc = OwnDisc(evidence[0])
    disc.read_range = lambda *_: b""
    with pytest.raises(ProfileError) as error:
        collect(evidence, disc=disc)
    assert error.value.code == "ELF_SHORT_READ"


def test_cli_repeat_exclusive_output_and_pinned_input(evidence, tmp_path, capsys):
    args = evidence[-1]
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    assert consumer.main(args + ["--output", str(a)]) == 0
    assert consumer.main(args + ["--output", str(b)]) == 0
    assert a.read_bytes() == b.read_bytes()
    assert consumer.main(args + ["--output", str(a)]) == 1
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["code"] == "OUTPUT_EXISTS"


@pytest.mark.parametrize("arg", ["--image-sha256", "--profile-sha256", "--camera-probe-sha256"])
def test_cli_hash_mismatch_leaves_no_output(evidence, tmp_path, capsys, arg):
    args = list(evidence[-1])
    args[args.index(arg) + 1] = "f" * 64
    output = tmp_path / "rejected.json"
    assert consumer.main(args + ["--output", str(output)]) == 1
    assert not output.exists()
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"


def test_cli_late_source_change_prevents_publication(evidence, tmp_path, monkeypatch, capsys):
    class ChangedIso(IsoImage):
        def __exit__(self, *args):
            super().__exit__(*args)
            raise ProfileError("INPUT_CHANGED", "Synthetic late failure")

    monkeypatch.setattr(consumer, "IsoImage", ChangedIso)
    output = tmp_path / "rejected.json"
    assert consumer.main(evidence[-1] + ["--output", str(output)]) == 1
    assert not output.exists()
    assert json.loads(capsys.readouterr().out)["code"] == "INPUT_CHANGED"


def test_cli_write_error_is_sanitized(evidence, tmp_path, monkeypatch, capsys):
    def broken(*_):
        raise OSError("PRIVATE ORIGINAL DATA")

    monkeypatch.setattr(consumer, "publish_report", broken)
    assert consumer.main(evidence[-1] + ["--output", str(tmp_path / "fail.json")]) == 1
    assert json.loads(capsys.readouterr().out) == {
        "status": "rejected",
        "code": "CONSUMER_IO_ERROR",
    }
