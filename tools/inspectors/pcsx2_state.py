"""PS01-PS04/PS06-PS07: bounded v2.8.2 EE state decoding; private values only."""

import struct
import zipfile
import zlib
from dataclasses import dataclass
from io import BytesIO

from tools.pipeline.profile import ProfileError

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_INTERNALS = 1024 * 1024
VERSION_MEMBER = "PCSX2 Savestate Version.id"
INTERNALS_MEMBER = "PCSX2 Internal Structures.dat"
VERSION = struct.pack("<I", 0x9A590000) + b"v2.8.2".ljust(32, b"\0")


def _require(condition, code="STATE_FORMAT"):
    if not condition:
        raise ProfileError(code, "State does not satisfy the pinned import contract")


@dataclass(frozen=True, repr=False)
class EEState:
    """Untrusted snapshot, not proof of execution; repr intentionally hides values."""

    pc: int
    delay_slot: bool
    gpr_low32: tuple[int, ...]

    def registers_at(self, pc: int, registers: list[int]) -> dict[str, str]:
        _require(type(pc) is int and self.pc == pc and not self.delay_slot, "STATE_POINT")
        _require(
            isinstance(registers, list)
            and 1 <= len(registers) <= 32
            and all(type(r) is int and 0 <= r < 32 for r in registers)
            and len(set(registers)) == len(registers),
            "STATE_REGISTERS",
        )
        return {str(r): f"{self.gpr_low32[r]:08x}" for r in registers}


def decode_ee_state(version: bytes, internals: bytes, expected_crc: int) -> EEState:
    """Decode the known little-endian x86_64 prefix, leaving the tail opaque."""
    _require(version == VERSION, "STATE_VERSION")
    _require(type(expected_crc) is int and 0 <= expected_crc <= 0xFFFFFFFF, "STATE_IDENTITY")
    _require(isinstance(internals, bytes) and 301 <= len(internals) <= MAX_INTERNALS)
    _require(internals[:32] == b"BIOS".ljust(32, b"\0"))
    crc, length = struct.unpack_from("<II", internals, 292)
    _require(crc == expected_crc, "STATE_IDENTITY")
    _require(1 <= length <= 1024, "STATE_BUDGET")
    tag = 301 + length
    cpu = tag + 32
    _require(len(internals) >= cpu + 684)
    _require(internals[300 + length] == 1, "STATE_ELF")
    _require(internals[tag:cpu] == b"cpuRegs".ljust(32, b"\0"))
    delay, pc = struct.unpack_from("<II", internals, cpu + 676)
    _require(delay in (0, 1))
    registers = tuple(struct.unpack_from("<I", internals, cpu + r * 16)[0] for r in range(32))
    return EEState(pc, bool(delay), registers)


def _zip_budget(raw: bytes) -> int:
    # Bound the central directory before ZipFile allocates its per-entry objects.
    _require(isinstance(raw, bytes) and 22 <= len(raw) <= MAX_ARCHIVE, "STATE_BUDGET")
    sig, disk, cd_disk, on_disk, count, size, offset, comment = struct.unpack("<4s4H2IH", raw[-22:])
    _require(sig == b"PK\x05\x06" and raw[:4] == b"PK\x03\x04")
    _require(disk == cd_disk == comment == 0 and on_disk == count)
    _require(2 <= count <= 64 and size <= 65536, "STATE_BUDGET")
    _require(offset + size == len(raw) - 22 and raw[offset : offset + 4] == b"PK\x01\x02")
    position, seen = offset, 0
    while position < offset + size:
        _require(seen < count and position + 46 <= offset + size, "STATE_BUDGET")
        _require(raw[position : position + 4] == b"PK\x01\x02")
        name_size, extra_size, comment_size, entry_disk = struct.unpack_from(
            "<4H", raw, position + 28
        )
        _require(entry_disk == 0)
        position += 46 + name_size + extra_size + comment_size
        _require(position <= offset + size)
        seen += 1
    _require(seen == count)
    return count


def read_state_members(raw: bytes, requests: tuple[tuple[str, int], ...]) -> list[bytes]:
    """Read explicit bounded members; callers define the pinned member contracts."""
    _require(
        isinstance(requests, tuple)
        and 1 <= len(requests) <= 3
        and all(
            isinstance(n, str) and type(limit) is int and 1 <= limit <= 32 * 1024 * 1024
            for n, limit in requests
        ),
        "STATE_BUDGET",
    )
    count = _zip_budget(raw)
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            entries = archive.infolist()
            _require(len(entries) == count)
            names = [e.filename for e in entries]
            _require(len(set(names)) == count, "STATE_DUPLICATE")
            _require(all(not e.flag_bits & 65 for e in entries), "STATE_ENCRYPTED")
            for info in entries:
                # This producer emits no extras. Reject ZIP64 even when a forged
                # central header hides a ZIP64 local header from ZipFile.
                _require(info.extract_version in (10, 20) and not info.extra)
                start = info.header_offset
                _require(0 <= start <= len(raw) - 30)
                _require(raw[start : start + 4] == b"PK\x03\x04")
                version, flags = struct.unpack_from("<HH", raw, start + 4)
                name_size, extra_size = struct.unpack_from("<HH", raw, start + 26)
                _require(version in (10, 20) and extra_size == 0)
                _require(not flags & 65, "STATE_ENCRYPTED")
                _require(start + 30 + name_size <= len(raw))
            values = []
            for name, limit in requests:
                _require(name in names, "STATE_MEMBER")
                info = archive.getinfo(name)
                _require(1 <= info.file_size <= limit, "STATE_BUDGET")
                with archive.open(info) as stream:
                    data = stream.read(limit + 1)
                _require(len(data) == info.file_size and len(data) <= limit, "STATE_BUDGET")
                values.append(data)
    except NotImplementedError as error:
        raise ProfileError("STATE_COMPRESSION", "Host cannot decode this compression") from error
    except (zipfile.BadZipFile, EOFError, zlib.error) as error:
        raise ProfileError("STATE_ZIP", "Invalid state archive") from error
    return values


def read_state_archive(raw: bytes, expected_crc: int) -> EEState:
    """Read only two bounded ZIP members. Never extract members to the filesystem."""
    values = read_state_members(raw, ((VERSION_MEMBER, 36), (INTERNALS_MEMBER, MAX_INTERNALS)))
    return decode_ee_state(*values, expected_crc)
