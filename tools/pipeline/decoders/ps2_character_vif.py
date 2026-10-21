"""Pure, fail-closed loader for the unmasked MDL VIF subset (CM03).

This only unpacks data into VU memory. It never executes VU microcode.
Missing lanes remain unknown instead of inheriting another packet's memory.
"""

import struct
from dataclasses import dataclass

RAM_QWORDS = 1024
MAX_PACKET_BYTES = 65536
FORMATS = {0x6C: (4, 4), 0x6D: (4, 2), 0x69: (3, 2), 0x65: (2, 2)}


class CharacterVifError(ValueError):
    pass


@dataclass(frozen=True)
class Unpack:
    offset: int
    command: int
    immediate: int
    count: int
    cycle_length: int
    write_length: int


@dataclass(frozen=True)
class VifMemory:
    words: tuple[tuple[int | None, ...], ...]
    unpacks: tuple[Unpack, ...]

    def read(self, address: int, count: int = 4, *, signed: bool = False) -> tuple[int, ...]:
        if not 0 <= address < RAM_QWORDS or not 1 <= count <= 4:
            raise CharacterVifError("CM_VU_ADDRESS")
        values = self.words[address][:count]
        if any(value is None for value in values):
            raise CharacterVifError("CM_VU_UNINITIALIZED")
        return tuple(
            value - (1 << 32) if signed and value >= (1 << 31) else value for value in values
        )


def load_vif(data: bytes) -> VifMemory:
    if type(data) is not bytes or not 4 <= len(data) <= MAX_PACKET_BYTES or len(data) % 4:
        raise CharacterVifError("CM_VIF_SIZE")
    words = [[None] * 4 for _ in range(RAM_QWORDS)]
    offset = 0
    cycle = write = 1
    unpacks = []
    while offset < len(data):
        command_at = offset
        immediate, encoded_count, command = struct.unpack_from("<HBB", data, offset)
        offset += 4
        if command == 0:
            if immediate or encoded_count:
                raise CharacterVifError("CM_VIF_NOP")
            continue
        if command == 1:
            cycle, write = immediate & 255, immediate >> 8
            if encoded_count or not 1 <= write <= cycle:
                raise CharacterVifError("CM_VIF_CYCLE")
            continue
        if command not in FORMATS or immediate & ~0x43FF:
            raise CharacterVifError("CM_VIF_UNSUPPORTED")
        lanes, width = FORMATS[command]
        count = encoded_count or 256
        address = immediate & 0x3FF
        unsigned = bool(immediate & 0x4000)
        payload_size = count * lanes * width
        padded_end = (offset + payload_size + 3) & ~3
        if padded_end > len(data):
            raise CharacterVifError("CM_VIF_TRUNCATED")
        if any(data[offset + payload_size : padded_end]):
            raise CharacterVifError("CM_VIF_PADDING")
        final_address = address + cycle * ((count - 1) // write) + (count - 1) % write
        if final_address >= RAM_QWORDS:
            raise CharacterVifError("CM_VIF_RANGE")
        code = "I" if width == 4 else ("H" if unsigned else "h")
        for index in range(count):
            destination = address + cycle * (index // write) + index % write
            values = struct.unpack_from("<" + code * lanes, data, offset + index * lanes * width)
            # V2/V3 unspecified lanes are deliberately not made readable.
            words[destination] = [value & 0xFFFFFFFF for value in values] + [None] * (4 - lanes)
        unpacks.append(Unpack(command_at, command, immediate, count, cycle, write))
        offset = padded_end
    return VifMemory(tuple(tuple(row) for row in words), tuple(unpacks))
