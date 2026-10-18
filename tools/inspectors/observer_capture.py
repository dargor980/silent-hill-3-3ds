"""OB02/04/08: strict private wire codec; no socket, file or emulator access."""

import struct
from dataclasses import dataclass

from tools.inspectors.effective_mapping import (
    EE_RAM_SIZE,
    MappingContext,
    MappingResult,
    MappingSnapshot,
    PageEntry,
    integer,
    validate_context,
    validate_mapping,
)
from tools.inspectors.observation_capture import require

HEADER = struct.Struct("<4sBBH16s8I")
SNAPSHOT = struct.Struct("<QIQQQIIIIIIQIIQI")
ERRORS = (
    "OK",
    "REQUEST",
    "PAUSE",
    "SAVE_PENDING",
    "ANCHORS",
    "PC",
    "HANDLER",
    "OUTSIDE_RAM",
    "NONCONTIGUOUS",
    "UNSTABLE",
    "READ",
    "CONTENT",
    "TIMEOUT",
)


@dataclass(frozen=True, repr=False)
class ObserverRequest:
    session_id: str
    sequence: int
    expected_pc: int
    virtual_start: int
    size: int
    expected_offset: int

    def validate(self):
        # Context syntax is shared; no claim that an echo authenticates a session.
        validate_context(
            MappingContext(self.session_id, "0" * 64, "0" * 64, self.sequence, "0" * 64)
        )
        require(self.session_id != "0" * 32, "OBSERVER_SESSION")
        integer(self.expected_pc, 0, 2**32 - 1, "OBSERVER_PC")
        require(self.expected_pc % 4 == 0, "OBSERVER_PC")
        integer(self.virtual_start, 0, 2**32 - 1, "OBSERVER_RANGE")
        integer(self.size, 1, 4096, "OBSERVER_RANGE")
        require(self.virtual_start + self.size <= 2**32, "OBSERVER_RANGE")
        integer(self.expected_offset, 0, EE_RAM_SIZE - self.size, "OBSERVER_RANGE")

    def encode(self) -> bytes:
        self.validate()
        return struct.pack(
            "<IBBH16s5I",
            44,
            0xE0,
            1,
            0,
            bytes.fromhex(self.session_id),
            self.sequence,
            self.expected_pc,
            self.virtual_start,
            self.size,
            self.expected_offset,
        )


@dataclass(frozen=True, repr=False)
class Observation:
    pid: int
    pc: int
    cycle: int
    game_crc: int
    before: MappingSnapshot
    after: MappingSnapshot
    mapping: MappingResult
    data: bytes

    def metadata(self) -> dict:
        return {
            **self.mapping.metadata(),
            "observer_protocol": 1,
            "state_binding_verified": False,
            "content_size": len(self.data),
        }


def _snapshot(raw, context, request):
    values = SNAPSHOT.unpack(raw)
    (
        pid,
        pc,
        cycle,
        base,
        vmap,
        ram,
        flags,
        crc,
        count,
        page0,
        reserved0,
        bias0,
        page1,
        reserved1,
        bias1,
        reserved2,
    ) = values
    require(reserved0 == reserved1 == reserved2 == 0, "OBSERVER_RESERVED")
    require(flags == 1, "OBSERVER_FLAGS")
    require(pid > 0 and pc == request.expected_pc, "OBSERVER_IDENTITY")
    require(count in (1, 2), "OBSERVER_COVERAGE")
    require(count == 2 or (page1 == bias1 == 0), "OBSERVER_COVERAGE")
    pages = (PageEntry(page0, bias0), PageEntry(page1, bias1))[:count]
    sample = MappingSnapshot(context, True, base, ram, vmap, pages)
    return (pid, pc, cycle, crc), sample


def decode_reply(packet: bytes, request: ObserverRequest, context: MappingContext) -> Observation:
    """Validate supplied bytes only. Context/state hashes require later external binding."""
    require(type(request) is ObserverRequest, "OBSERVER_REQUEST")
    request.validate()
    validate_context(context)
    require(
        context.session_id == request.session_id and context.sequence == request.sequence,
        "OBSERVER_CONTEXT",
    )
    require(type(packet) is bytes and 5 <= len(packet) <= 4333, "OBSERVER_LENGTH")
    length, pine = struct.unpack_from("<IB", packet)
    require(length == len(packet), "OBSERVER_LENGTH")
    if pine == 255:
        require(len(packet) == 5, "OBSERVER_LENGTH")
        require(False, "OBSERVER_PINE_REJECTED")
    require(pine == 0 and len(packet) >= 237, "OBSERVER_ENVELOPE")
    (
        magic,
        version,
        status,
        reserved,
        session,
        seq,
        pc,
        start,
        size,
        expected,
        data_size,
        offset,
        matches,
    ) = HEADER.unpack_from(packet, 5)
    require(magic == b"SH3O" and version == 1, "OBSERVER_VERSION")
    require(reserved == 0, "OBSERVER_RESERVED")
    require(status < len(ERRORS), "OBSERVER_STATUS")
    require(
        (session.hex(), seq, pc, start, size, expected)
        == (
            request.session_id,
            request.sequence,
            request.expected_pc,
            request.virtual_start,
            request.size,
            request.expected_offset,
        ),
        "OBSERVER_ECHO",
    )
    if status:
        require(
            len(packet) == 237
            and data_size == offset == matches == 0
            and packet[61:] == bytes(176),
            "OBSERVER_ERROR_PAYLOAD",
        )
        require(False, "OBSERVER_" + ERRORS[status])
    require(data_size == size and len(packet) == 237 + size, "OBSERVER_LENGTH")
    require(matches in (0, 1), "OBSERVER_MATCH")
    first, before = _snapshot(packet[61:149], context, request)
    second, after = _snapshot(packet[149:237], context, request)
    require(first == second, "OBSERVER_IDENTITY")
    mapping = validate_mapping(before, after, context, start, size, expected)
    require(
        mapping.physical_offset == offset and mapping.matches_expected_backing == bool(matches),
        "OBSERVER_MAPPING",
    )
    return Observation(*first, before, after, mapping, packet[237:])
