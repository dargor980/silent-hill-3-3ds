"""PS01-PS07: self-authored states, no original BIOS, RAM or game registers."""

import hashlib
import os
import struct
import warnings
import zipfile
from contextlib import contextmanager
from io import BytesIO

import pytest
from test_camera_observation import observation as observation
from test_camera_observation import validate

from tools.inspectors import pcsx2_state as decoder
from tools.inspectors import state_files
from tools.pipeline.profile import ProfileError

CRC = 0x12345678
PC = 0x10203040
PATH = b"own.elf"
CPU = 301 + len(PATH) + 32


def own_internals(pc=PC, delay=0):
    data = bytearray(CPU + 684)
    data[:32] = b"BIOS".ljust(32, b"\0")
    struct.pack_into("<II", data, 292, CRC, len(PATH))
    data[300 : 300 + len(PATH)] = PATH
    data[300 + len(PATH)] = 1
    data[301 + len(PATH) : CPU] = b"cpuRegs".ljust(32, b"\0")
    for register in range(32):
        struct.pack_into("<4I", data, CPU + 16 * register, 0xDEAD0000 + register, 1, 2, 3)
    struct.pack_into("<II", data, CPU + 676, delay, pc)
    return bytes(data)


def own_archive(items=None, compression=zipfile.ZIP_STORED):
    if items is None:
        items = [
            (decoder.VERSION_MEMBER, decoder.VERSION),
            (decoder.INTERNALS_MEMBER, own_internals()),
        ]
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=compression) as archive:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            for name, data in items:
                archive.writestr(name, data)
    return stream.getvalue()


def test_low32_stride_endianness_selection_and_no_output(capsys):
    state = decoder.decode_ee_state(decoder.VERSION, own_internals(), CRC)
    assert state.pc == PC and not state.delay_slot
    assert state.gpr_low32 == tuple(0xDEAD0000 + r for r in range(32))
    assert state.registers_at(PC, [31, 0, 6]) == {
        "31": "dead001f",
        "0": "dead0000",
        "6": "dead0006",
    }
    assert "dead" not in repr(state) and str(PC) not in repr(state)
    assert not capsys.readouterr().out


@pytest.mark.parametrize(
    "pc,registers",
    [
        (PC + 4, [1]),
        (True, [1]),
        (PC, []),
        (PC, [0, 0]),
        (PC, [32]),
        (PC, [-1]),
        (PC, [True]),
        (PC, ["4"]),
        (PC, (1,)),
        (PC, None),
    ],
)
def test_invalid_point_selection(pc, registers):
    with pytest.raises(ProfileError):
        decoder.read_state_archive(own_archive(), CRC).registers_at(pc, registers)


def test_delay_slot_rejected_for_observation():
    state = decoder.decode_ee_state(decoder.VERSION, own_internals(delay=1), CRC)
    assert state.delay_slot
    with pytest.raises(ProfileError):
        state.registers_at(PC, [4])


def test_imported_synthetic_states_satisfy_existing_capture_contract(observation):
    plan, capture, *_ = observation
    for event in capture["events"]:
        point = next(p for p in plan["boundaries"][0]["points"] if p["id"] == event["point_id"])
        own = bytearray(own_internals(pc=point["pc"]))
        for register, value in event["registers"].items():
            struct.pack_into("<I", own, CPU + int(register) * 16, int(value, 16))
        raw = own_archive(
            [
                (decoder.VERSION_MEMBER, decoder.VERSION),
                (decoder.INTERNALS_MEMBER, bytes(own)),
            ]
        )
        event["registers"] = decoder.read_state_archive(raw, CRC).registers_at(
            point["pc"], point["registers"]
        )
    result = validate(observation)
    assert result["status"] == "validated_observations"
    assert result["comparisons"][0]["entry_copy_comparison"] == "equal"
    assert result["execution_authentication"] == "not_provided"


@pytest.mark.parametrize(
    "variant",
    [
        "version",
        "identity",
        "bool_crc",
        "bios_tag",
        "cpu_tag",
        "elf_not_executed",
        "zero_path",
        "long_path",
        "delay",
        "short_header",
        "short_registers",
        "large",
        "mutable",
    ],
)
def test_invalid_prefix(variant):
    data, version, crc = bytearray(own_internals()), decoder.VERSION, CRC
    if variant == "version":
        version = version[:-1] + b"x"
    elif variant == "identity":
        crc += 1
    elif variant == "bool_crc":
        crc = True
    elif variant in ("bios_tag", "cpu_tag", "elf_not_executed"):
        data[{"bios_tag": 0, "cpu_tag": CPU - 32, "elf_not_executed": CPU - 33}[variant]] = 0
    elif variant in ("zero_path", "long_path"):
        struct.pack_into("<I", data, 296, 0 if variant == "zero_path" else 1025)
    elif variant == "delay":
        struct.pack_into("<I", data, CPU + 676, 2)
    elif variant == "short_header":
        data = data[:300]
    elif variant == "short_registers":
        data = data[:-1]
    elif variant == "large":
        data = bytearray(decoder.MAX_INTERNALS + 1)
    with pytest.raises(ProfileError):
        decoder.decode_ee_state(version, data if variant == "mutable" else bytes(data), crc)


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_only_selected_members_are_read(compression, monkeypatch):
    original = zipfile.ZipFile.open
    calls = []

    def bounded(archive, info, *args, **kwargs):
        calls.append(info.filename)
        assert info.filename != "eeMemory.bin"
        return original(archive, info, *args, **kwargs)

    raw = own_archive(
        [
            (decoder.VERSION_MEMBER, decoder.VERSION),
            (decoder.INTERNALS_MEMBER, own_internals()),
            ("eeMemory.bin", b"own opaque data"),
        ],
        compression,
    )
    monkeypatch.setattr(zipfile.ZipFile, "open", bounded)
    assert decoder.read_state_archive(raw, CRC).pc == PC
    assert calls == [decoder.VERSION_MEMBER, decoder.INTERNALS_MEMBER]


@pytest.mark.parametrize(
    "variant",
    [
        "short",
        "trailing",
        "multidisk",
        "count",
        "directory_size",
        "offset",
        "duplicate",
        "missing",
        "empty_member",
        "oversize_member",
        "crc",
        "encrypted",
        "zip64_local",
        "zip64_central",
        "local_extra",
        "central_extra",
        "local_offset",
        "local_magic",
        "local_name_size",
        "local_encrypted",
        "bad_compression",
        "entry_count",
    ],
)
def test_archive_rejections(variant):
    raw = bytearray(own_archive())
    cd = struct.unpack_from("<I", raw, len(raw) - 6)[0]
    if variant == "short":
        raw = raw[:21]
    elif variant == "trailing":
        raw += b"x"
    elif variant == "multidisk":
        struct.pack_into("<H", raw, len(raw) - 18, 1)
    elif variant in ("count", "entry_count"):
        count = 65 if variant == "count" else 3
        struct.pack_into("<HH", raw, len(raw) - 14, count, count)
    elif variant == "directory_size":
        struct.pack_into("<I", raw, len(raw) - 10, 65537)
    elif variant == "offset":
        struct.pack_into("<I", raw, len(raw) - 6, 0)
    elif variant == "duplicate":
        raw = own_archive([(decoder.VERSION_MEMBER, decoder.VERSION)] * 2)
    elif variant == "missing":
        raw = own_archive([(decoder.VERSION_MEMBER, decoder.VERSION), ("other", b"x")])
    elif variant == "empty_member":
        raw = own_archive(
            [(decoder.VERSION_MEMBER, b""), (decoder.INTERNALS_MEMBER, own_internals())]
        )
    elif variant == "oversize_member":
        struct.pack_into("<I", raw, cd + 24, 37)
    elif variant == "crc":
        raw[30 + len(decoder.VERSION_MEMBER)] ^= 1
    elif variant == "encrypted":
        struct.pack_into("<H", raw, cd + 8, 1)
    elif variant == "zip64_local":
        struct.pack_into("<H", raw, 4, 45)
    elif variant == "zip64_central":
        struct.pack_into("<H", raw, cd + 6, 45)
    elif variant == "local_extra":
        struct.pack_into("<H", raw, 28, 20)
    elif variant == "central_extra":
        struct.pack_into("<H", raw, cd + 30, 20)
    elif variant == "local_offset":
        struct.pack_into("<I", raw, cd + 42, 0xFFFFFF00)
    elif variant == "local_magic":
        raw[30 + len(decoder.VERSION_MEMBER) + len(decoder.VERSION)] = 0
    elif variant == "local_name_size":
        struct.pack_into("<H", raw, 26, 65535)
    elif variant == "local_encrypted":
        struct.pack_into("<H", raw, 6, 1)
    elif variant == "bad_compression":
        struct.pack_into("<H", raw, 8, 99)
        struct.pack_into("<H", raw, cd + 10, 99)
    with pytest.raises(ProfileError):
        decoder.read_state_archive(bytes(raw), CRC)


def test_budget_precedes_zip_allocation(monkeypatch):
    raw = own_archive()
    monkeypatch.setattr(decoder, "MAX_ARCHIVE", len(raw) - 1)
    monkeypatch.setattr(zipfile, "ZipFile", lambda *a: pytest.fail("must reject before ZIP"))
    with pytest.raises(ProfileError):
        decoder.read_state_archive(raw, CRC)


def test_unavailable_compression_error(monkeypatch):
    raw = own_archive()

    def unavailable(*args):
        raise NotImplementedError("own host fixture")

    monkeypatch.setattr(zipfile.ZipFile, "open", unavailable)
    with pytest.raises(ProfileError) as raised:
        decoder.read_state_archive(raw, CRC)
    assert raised.value.code == "STATE_COMPRESSION"


@pytest.fixture
def private_state(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    path = root / "own.p2s"
    raw = own_archive()
    path.write_bytes(raw)
    path.chmod(0o600)
    return root, path.name, hashlib.sha256(raw).hexdigest(), CRC, tmp_path / "repo"


def test_private_success(private_state):
    assert state_files.read_private_state(*private_state).pc == PC


@pytest.mark.parametrize(
    "name", ["", "../own.p2s", "/own.p2s", "x\\y.p2s", "x\0.p2s", "x.zip", "a" * 129, None]
)
def test_private_filename(private_state, name):
    args = list(private_state)
    args[1] = name
    with pytest.raises(ProfileError):
        state_files.read_private_state(*args)


@pytest.mark.parametrize(
    "variant",
    [
        "inside",
        "same",
        "ancestor",
        "mode",
        "directory_mode",
        "empty",
        "large",
        "hash",
        "symlink",
        "parent_symlink",
        "hardlink",
        "fifo",
    ],
)
def test_custody_rejections(private_state, variant, monkeypatch):
    root, name, sha, crc, repo = private_state
    path = root / name
    if variant in ("inside", "same", "ancestor"):
        repo = {"inside": root.parent, "same": root, "ancestor": root / "repo"}[variant]
    elif variant == "mode":
        path.chmod(0o644)
    elif variant == "directory_mode":
        root.chmod(0o755)
    elif variant == "empty":
        path.write_bytes(b"")
    elif variant == "large":
        monkeypatch.setattr(state_files, "MAX_ARCHIVE", path.stat().st_size - 1)
    elif variant == "hash":
        sha = "f" * 64
    elif variant == "parent_symlink":
        alias = root.with_name("alias")
        alias.symlink_to(root)
        root = alias
    else:
        original = root / "original"
        path.rename(original)
        if variant == "symlink":
            path.symlink_to(original)
        elif variant == "hardlink":
            os.link(original, path)
        else:
            os.mkfifo(path, 0o600)
    with pytest.raises((ProfileError, OSError)):
        state_files.read_private_state(root, name, sha, crc, repo)


@pytest.mark.parametrize("mutation", ["file", "directory", "mode"])
def test_late_changes(private_state, monkeypatch, mutation):
    root, name, *_ = private_state
    original = state_files.read_state_archive

    def change(*args):
        result = original(*args)
        if mutation == "file":
            (root / name).write_bytes(b"changed")
        elif mutation == "directory":
            root.rename(root.with_name("moved"))
            root.mkdir(mode=0o700)
        else:
            root.chmod(0o755)
        return result

    monkeypatch.setattr(state_files, "read_state_archive", change)
    with pytest.raises(ProfileError) as raised:
        state_files.read_private_state(*private_state)
    assert raised.value.code == "STATE_CHANGED"


def test_change_during_read(private_state, monkeypatch):
    root, name, *_ = private_state
    original = state_files._owned_stream

    @contextmanager
    def changed(fd, mode):
        with original(fd, mode) as stream:

            class Changing:
                def fileno(self):
                    return stream.fileno()

                def read(self, count):
                    data = stream.read(count)
                    (root / name).write_bytes(b"changed")
                    return data

            yield Changing()

    monkeypatch.setattr(state_files, "_owned_stream", changed)
    with pytest.raises(ProfileError) as raised:
        state_files.read_private_state(*private_state)
    assert raised.value.code == "STATE_CHANGED"


def test_close_failure_prevents_success(private_state, monkeypatch):
    original = state_files.os.close
    active = False
    decode = state_files.read_state_archive

    def decoded(*args):
        nonlocal active
        value = decode(*args)
        active = True
        return value

    def close(fd):
        original(fd)
        if active:
            raise OSError("own close failure after release")

    monkeypatch.setattr(state_files, "read_state_archive", decoded)
    monkeypatch.setattr(state_files.os, "close", close)
    with pytest.raises(OSError):
        state_files.read_private_state(*private_state)


@pytest.mark.parametrize(
    "variant", ["hidden_entries", "entry_disk", "oversize_name", "truncated_header"]
)
def test_central_directory_checked_before_zip_allocation(monkeypatch, variant):
    raw = bytearray(
        own_archive(
            [
                (decoder.VERSION_MEMBER, decoder.VERSION),
                (decoder.INTERNALS_MEMBER, own_internals()),
                ("own third member", b"own"),
            ]
        )
    )
    cd = struct.unpack_from("<I", raw, len(raw) - 6)[0]
    if variant == "hidden_entries":
        struct.pack_into("<HH", raw, len(raw) - 14, 2, 2)
    elif variant == "entry_disk":
        struct.pack_into("<H", raw, cd + 34, 1)
    elif variant == "oversize_name":
        struct.pack_into("<H", raw, cd + 28, 65535)
    else:
        end = len(raw) - 22
        struct.pack_into("<H", raw, cd + 28, end - cd - 47)
    monkeypatch.setattr(zipfile, "ZipFile", lambda *a: pytest.fail("preflight must reject first"))
    with pytest.raises(ProfileError):
        decoder.read_state_archive(bytes(raw), CRC)
