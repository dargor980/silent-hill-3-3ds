"""AC01/07: pinned x86_64 cpuRegisters and a bounded physical EE RAM window."""

import struct
from dataclasses import dataclass

from tools.inspectors.effective_mapping import integer
from tools.inspectors.observation_capture import require
from tools.inspectors.pcsx2_state import (
    INTERNALS_MEMBER,
    VERSION_MEMBER,
    EEState,
    decode_ee_state,
    read_state_members,
)
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE

CPU_BYTES = 1160
CYCLE_OFFSET = 1088
MAX_ACQUISITION_INTERNALS = 4 * 1024 * 1024
# BIOS/ELF header, maximum path, tag and complete pinned cpuRegisters.
MAX_CPU_PREFIX = 333 + 1024 + CPU_BYTES


@dataclass(frozen=True, repr=False)
class AcquisitionState:
    cpu: EEState
    cycle: int
    data: bytes


def read_acquisition_state(raw: bytes, crc: int, offset: int, size: int) -> AcquisitionState:
    integer(size, 1, 4096, "ACQUIRE_RANGE")
    integer(offset, 0, RAM_SIZE - size, "ACQUIRE_RANGE")
    version, internals, ram = read_state_members(
        raw,
        (
            (VERSION_MEMBER, 36),
            (INTERNALS_MEMBER, MAX_ACQUISITION_INTERNALS),
            (RAM_MEMBER, RAM_SIZE),
        ),
    )
    # The full member was read/CRC-checked; only its known prefix has semantics here.
    cpu = decode_ee_state(version, internals[:MAX_CPU_PREFIX], crc)
    start = 333 + struct.unpack_from("<I", internals, 296)[0]
    require(len(internals) >= start + CPU_BYTES, "ACQUIRE_CPU_TRUNCATED")
    require(not cpu.delay_slot, "ACQUIRE_DELAY_SLOT")
    require(len(ram) == RAM_SIZE, "ACQUIRE_RAM_SIZE")
    cycle = struct.unpack_from("<Q", internals, start + CYCLE_OFFSET)[0]
    return AcquisitionState(cpu, cycle, ram[offset : offset + size])
