"""Bounded ELF32 LE MIPS file mapping, not a loader or complete ABI validator."""

import struct
from collections.abc import Callable
from dataclasses import dataclass

from tools.pipeline.profile import ProfileError

MAX_ELF_BYTES = 16 * 1024 * 1024
MAX_HEADERS = 128
ReadRange = Callable[[int, int], bytes]


def exact_read(read: ReadRange, offset: int, size: int) -> bytes:
    data = read(offset, size)
    if not isinstance(data, bytes) or len(data) != size:
        raise ProfileError("ELF_SHORT_READ", "Expected exact binary range")
    return data


@dataclass(frozen=True)
class Segment:
    index: int
    offset: int
    address: int
    file_size: int
    memory_size: int
    flags: int
    alignment: int


def _overlap(start: int, size: int, other: int, length: int) -> bool:
    return bool(size and length and start < other + length and other < start + size)


@dataclass(frozen=True)
class ElfMap:
    entry: int
    flags: int
    program_header_count: int
    segments: tuple[Segment, ...]

    def file_offset(self, address: int, size: int, *, executable: bool = False) -> int:
        if (
            type(address) is not int
            or type(size) is not int
            or address < 0
            or size <= 0
            or address + size > 1 << 32
        ):
            raise ProfileError("ELF_ADDRESS", "Invalid virtual range")
        hits = [
            segment
            for segment in self.segments
            if segment.address <= address
            and address + size <= segment.address + segment.file_size
            and (not executable or segment.flags & 1)
        ]
        if len(hits) != 1:
            raise ProfileError("ELF_UNBACKED_ADDRESS", "Range lacks a unique file mapping")
        segment = hits[0]
        return segment.offset + address - segment.address


def parse_elf(read: ReadRange, size: int) -> ElfMap:
    if type(size) is not int or not 52 <= size <= MAX_ELF_BYTES:
        raise ProfileError("ELF_BUDGET", "Executable exceeds inspection budget")
    header = struct.unpack("<16sHHIIIIIHHHHHH", exact_read(read, 0, 52))
    ident, kind, machine, version, entry, phoff, _, flags, ehsize, entsize, count, *_ = header
    if ident[:7] != b"\x7fELF\x01\x01\x01" or (kind, machine, version, ehsize) != (2, 8, 1, 52):
        raise ProfileError("ELF_HEADER", "Expected ELF32 LE MIPS executable version 1")
    if entsize != 32 or not 1 <= count <= MAX_HEADERS or phoff < 52 or phoff + count * 32 > size:
        raise ProfileError("ELF_TABLE", "Invalid or unsupported program table")
    segments = []
    for index in range(count):
        kind, offset, address, _, filesz, memsz, perm, align = struct.unpack(
            "<8I", exact_read(read, phoff + index * 32, 32)
        )
        if kind != 1:
            continue
        if filesz > memsz or offset + filesz > size or address + memsz > 1 << 32:
            raise ProfileError("ELF_SEGMENT_RANGE", "Invalid load segment bounds")
        if align > 1 and (align & (align - 1) or address % align != offset % align):
            raise ProfileError("ELF_ALIGNMENT", "Invalid load segment alignment")
        segment = Segment(index, offset, address, filesz, memsz, perm, align)
        for other in segments:
            if (
                _overlap(offset, filesz, other.offset, other.file_size)
                or _overlap(address, filesz, other.address, other.memory_size)
                or _overlap(address, memsz, other.address, other.file_size)
            ):
                raise ProfileError("ELF_OVERLAP", "Ambiguous file-backed load segment")
        segments.append(segment)
    mapping = ElfMap(entry, flags, count, tuple(segments))
    if entry % 4:
        raise ProfileError("ELF_ALIGNMENT", "Entry is not word aligned")
    mapping.file_offset(entry, 4, executable=True)
    return mapping
