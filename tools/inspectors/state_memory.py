"""RL02-RL03: bounded physical-offset hypotheses from a pinned EE state."""

from dataclasses import dataclass

from tools.inspectors.pcsx2_state import (
    INTERNALS_MEMBER,
    MAX_INTERNALS,
    VERSION_MEMBER,
    decode_ee_state,
    read_state_members,
)
from tools.pipeline.profile import ProfileError

RAM_SIZE = 32 * 1024 * 1024
RAM_MEMBER = "eeMemory.bin"


@dataclass(frozen=True, repr=False)
class MemorySample:
    data: bytes


def sample_state(raw: bytes, crc: int, event: dict, register: int, size: int) -> MemorySample:
    if (
        type(register) is not int
        or not 1 <= register <= 31
        or type(size) is not int
        or size not in (64, 256)
    ):
        raise ProfileError("MEMORY_REQUEST", "Invalid sample request")
    version, internals, memory = read_state_members(
        raw, ((VERSION_MEMBER, 36), (INTERNALS_MEMBER, MAX_INTERNALS), (RAM_MEMBER, RAM_SIZE))
    )
    state = decode_ee_state(version, internals, crc)
    expected = state.registers_at(event["pc"], [int(r) for r in event["registers"]])
    if expected != event["registers"] or str(register) not in expected:
        raise ProfileError("MEMORY_EVENT", "Snapshot does not match capture")
    if len(memory) != RAM_SIZE:
        raise ProfileError("MEMORY_SIZE", "Unsupported EE RAM size")
    address = state.gpr_low32[register]
    if not 0x100000 <= address < RAM_SIZE or address + size > RAM_SIZE:
        raise ProfileError("MEMORY_ADDRESS", "Unsupported physical-offset hypothesis")
    return MemorySample(memory[address : address + size])
