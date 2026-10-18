"""DT02-03: private driver-pool view; distinct from archive descriptors."""

import struct
from dataclasses import dataclass

from tools.inspectors.effective_mapping import integer
from tools.inspectors.mapped_pause import MappedPause, validate_pause
from tools.inspectors.observation_capture import require


@dataclass(frozen=True, repr=False)
class DriverView:
    pause: MappedPause
    pool: tuple
    words: tuple


def inspect_driver(points, handle, file_size, position, target):
    integer(handle, 0, 2**31 - 1, "DRIVER_HANDLE")
    integer(file_size, 1, 2**31 - 1, "DRIVER_SIZE")
    integer(position, 0, file_size, "DRIVER_POSITION")
    integer(target, 4, 2**32 - 4, "DRIVER_TARGET")
    require(target % 4 == 0, "DRIVER_TARGET")
    pause = validate_pause(points)
    require(
        tuple(r[0] for r in pause.regions) == ("root", "pool", "object", "vtable"),
        "DRIVER_REGIONS",
    )
    require(tuple(len(r[2].data) for r in pause.regions) == (4, 24, 48, 12), "DRIVER_LAYOUT")
    root, pool, obj, vtable = pause.regions
    address = struct.unpack("<I", root[2].data)[0]
    words = struct.unpack("<6I", pool[2].data)
    count, shift, base = words[3:]
    require(
        16 <= address == pool[1].virtual_start
        and address % 16 == 0
        and 1 <= count <= 256
        and 0 <= shift <= 31
        and base == address + 24
        and base + 48 * count <= 2**32,
        "DRIVER_POOL",
    )
    index = handle & ((1 << shift) - 1)
    require(index < count and obj[1].virtual_start == base + 48 * index, "DRIVER_OBJECT")
    row = struct.unpack("<12I", obj[2].data)
    require(row[0] == handle, "DRIVER_CLOSED_OR_FOREIGN")
    require(row[4] > 0 and ((row[4] - 1) << shift) + index == handle, "DRIVER_GENERATION")
    require(row[3] < 2**31 and row[5] in (0, 1), "DRIVER_STATE")
    require(row[6] == file_size and row[8] == position, "DRIVER_POSITION")
    require(row[7] != 0, "DRIVER_REFERENCE")
    require(
        row[1] >= 4
        and row[1] % 4 == 0
        and row[1] == vtable[1].virtual_start
        and struct.unpack_from("<I", vtable[2].data)[0] == target,
        "DRIVER_VTABLE",
    )
    return DriverView(pause, words, row)
