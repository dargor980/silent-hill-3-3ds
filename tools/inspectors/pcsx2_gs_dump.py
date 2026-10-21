"""Bounded read-only reader for uncompressed PCSX2 GS v9 dumps.

No renderer or asset exporter. GIF framing follows the pinned GSState::Transfer;
partial packets remain attached to their own path across transfer records.
"""

import struct
from dataclasses import dataclass

MAX_DUMP = 256 * 1024 * 1024
STATE_SIZE = 4194813
REG_SIZE = 8192


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class Record:
    offset: int
    frame: int
    kind: int
    path: int | None
    data: bytes


@dataclass(frozen=True)
class Packet:
    path: int
    frame: int
    offset: int
    tag: bytes
    payload: bytes

    @property
    def fields(self):
        low, regs = struct.unpack("<QQ", self.tag)
        return dict(
            nloop=low & 32767,
            pre=(low >> 46) & 1,
            prim=(low >> 47) & 2047,
            flag=(low >> 58) & 3,
            nreg=((low >> 60) & 15) or 16,
            regs=regs,
        )


class Dump:
    def __init__(self, raw):
        require(44 <= len(raw) <= MAX_DUMP, "dump size")
        fake, header_size = struct.unpack_from("<II", raw)
        require(fake == 0xFFFFFFFF, "new header required")
        require(36 <= header_size <= 32 * 1024 * 1024, "header size")
        require(8 + header_size <= len(raw), "truncated header")
        (version, size, serial_off, serial_size, crc, width, height, image_off, image_size) = (
            struct.unpack_from("<9I", raw, 8)
        )
        require(version == 9 and size == STATE_SIZE, "unsupported state")
        require(serial_off == 36 and 0 < serial_size <= 32, "serial extent")
        require(image_off == serial_off + serial_size, "image offset")
        require(image_size == width * height * 4, "image extent")
        require(image_off + image_size == header_size, "header extent")
        self.serial = raw[8 + serial_off : 8 + serial_off + serial_size].decode("ascii")
        self.crc = crc
        self.image_size = (width, height)
        self.image = raw[8 + image_off : 8 + image_off + image_size]
        start = 8 + header_size
        require(start + size + REG_SIZE <= len(raw), "truncated state")
        self.state = raw[start : start + size]
        require(struct.unpack_from("<I", self.state)[0] == version, "state version mismatch")
        # Freeze serializes four GIFPath tag/position pairs followed by m_q.
        for i in range(4):
            tag, reg = struct.unpack_from("<16sI", self.state, size - 84 + i * 20)
            low = struct.unpack_from("<Q", tag)[0]
            require(low & 32767 == 0 and reg == 0, "initial GIF path is active")
        self.registers = raw[start + size : start + size + REG_SIZE]
        self.raw = raw
        self.records_offset = start + size + REG_SIZE

    def records(self):
        pos = self.records_offset
        frame = 0
        while pos < len(self.raw):
            offset = pos
            kind = self.raw[pos]
            pos += 1
            path = None
            if kind == 0:
                require(pos + 5 <= len(self.raw), "truncated transfer header")
                path, size = struct.unpack_from("<BI", self.raw, pos)
                pos += 5
                require(path <= 3 and size > 0 and size % 16 == 0, "transfer shape")
            elif kind == 1:
                size = 1
            elif kind == 2:
                size = 4
            elif kind == 3:
                size = REG_SIZE
            else:
                raise ValueError("unknown record")
            require(pos + size <= len(self.raw), "truncated record")
            data = self.raw[pos : pos + size]
            pos += size
            if kind == 1:
                require(data[0] in (0, 1), "field")
            yield Record(offset, frame, kind, path, data)
            if kind == 1:
                frame += 1

    def packets(self):
        pending = [None] * 4
        for record in self.records():
            if record.kind != 0:
                continue
            path = record.path
            pos = 0
            while pos < len(record.data):
                entry = pending[path]
                if entry is None:
                    tag = record.data[pos : pos + 16]
                    pos += 16
                    low = struct.unpack_from("<Q", tag)[0]
                    loops, flag, nreg = low & 32767, (low >> 58) & 3, ((low >> 60) & 15) or 16
                    if flag == 0:
                        length = loops * nreg * 16
                    elif flag == 1:
                        length = ((loops * nreg * 8 + 15) // 16) * 16
                    else:
                        length = loops * 16
                    entry = [record.frame, record.offset, tag, length, bytearray()]
                    pending[path] = entry
                count = min(entry[3] - len(entry[4]), len(record.data) - pos)
                entry[4].extend(record.data[pos : pos + count])
                pos += count
                if len(entry[4]) == entry[3]:
                    yield Packet(path, entry[0], entry[1], entry[2], bytes(entry[4]))
                    pending[path] = None
        require(all(p is None for p in pending), "incomplete GIF packet")
