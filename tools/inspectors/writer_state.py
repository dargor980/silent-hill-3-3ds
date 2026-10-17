"""WR04: extend the pinned state prefix with low64 GPRs and a bounded RAM window."""

import struct
from dataclasses import dataclass

from tools.inspectors.observation_capture import require
from tools.inspectors.pcsx2_state import (
    INTERNALS_MEMBER,
    MAX_INTERNALS,
    VERSION_MEMBER,
    EEState,
    decode_ee_state,
    read_state_members,
)
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE


@dataclass(frozen=True, repr=False)
class WriterState:
    cpu: EEState
    gpr_low64: tuple[int, ...]
    data: bytes


def read_writer_state(raw: bytes, crc: int, base: int | None, size: int) -> WriterState:
    version, internals, memory = read_state_members(
        raw, ((VERSION_MEMBER, 36), (INTERNALS_MEMBER, MAX_INTERNALS), (RAM_MEMBER, RAM_SIZE))
    )
    cpu = decode_ee_state(version, internals, crc)
    offset = 333 + struct.unpack_from("<I", internals, 296)[0]
    registers = tuple(struct.unpack_from("<Q", internals, offset + r * 16)[0] for r in range(32))
    if base is None:
        base = cpu.gpr_low32[4]
    require(
        type(size) is int
        and 4 <= size <= 4096
        and type(base) is int
        and 0x100000 <= base < RAM_SIZE
        and base + size <= RAM_SIZE
        and len(memory) == RAM_SIZE,
        "WRITER_RANGE",
    )
    return WriterState(cpu, registers, memory[base : base + size])
