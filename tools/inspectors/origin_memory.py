"""OR02-OR04: preserve a validated entry base across states of one capture."""

from dataclasses import dataclass

from tools.inspectors.observation_capture import require
from tools.inspectors.pcsx2_state import (
    INTERNALS_MEMBER,
    MAX_INTERNALS,
    VERSION_MEMBER,
    decode_ee_state,
    read_state_archive,
    read_state_members,
)
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE, MemorySample

MAX_RANGE = 4096


@dataclass(frozen=True, repr=False)
class EntryBase:
    address: int
    session: str
    environment: str
    sequence: int


def validate_event(state, event):
    require(
        state.registers_at(event["pc"], [int(r) for r in event["registers"]]) == event["registers"],
        "ORIGIN_EVENT",
    )


def entry_base(raw: bytes, crc: int, event: dict, register: int) -> EntryBase:
    require(type(register) is int and 1 <= register <= 31, "ORIGIN_REGISTER")
    state = read_state_archive(raw, crc)
    validate_event(state, event)
    require(str(register) in event["registers"], "ORIGIN_REGISTER")
    address = state.gpr_low32[register]
    require(0x100000 <= address < RAM_SIZE, "ORIGIN_RANGE")
    return EntryBase(address, event["session_id"], event["environment_sha256"], event["sequence"])


def preserved_range(raw: bytes, crc: int, event: dict, base: EntryBase, size: int) -> MemorySample:
    require(type(size) is int and 1 <= size <= MAX_RANGE, "ORIGIN_RANGE")
    require(
        event["session_id"] == base.session
        and event["environment_sha256"] == base.environment
        and type(event["sequence"]) is int
        and event["sequence"] >= base.sequence,
        "ORIGIN_SESSION",
    )
    require(0x100000 <= base.address < RAM_SIZE and base.address + size <= RAM_SIZE, "ORIGIN_RANGE")
    version, internals, memory = read_state_members(
        raw, ((VERSION_MEMBER, 36), (INTERNALS_MEMBER, MAX_INTERNALS), (RAM_MEMBER, RAM_SIZE))
    )
    validate_event(decode_ee_state(version, internals, crc), event)
    require(len(memory) == RAM_SIZE, "ORIGIN_MEMORY_SIZE")
    return MemorySample(memory[base.address : base.address + size])
