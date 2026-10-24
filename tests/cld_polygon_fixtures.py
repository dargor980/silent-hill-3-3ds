"""Own synthetic CLD writer; no production or oracle imports/constants.

This only constructs test inputs, including intentionally invalid counts.
Expected errors and views belong to the tests, not to this writer.
"""

import struct


def polygon(group=0, index=0):
    """Nonconstant opaque fields, finite W, two variants and distinct groups."""
    return struct.pack(
        "<BBHIII16f",
        1,
        index % 2,
        0x1234 + group,
        0xABC00000 + index,
        0x80000021 + group,
        0xDEADBEEF,
        *[float(group * 100 + index * 16 + component - 8) for component in range(16)],
    )


def resource(counts=(2, 2, 2, 2), *, lists=None, aliases=None, data_start=None, group4_count=0):
    """Assemble four polygon groups, index lists/aliases and an optional fifth group.

    lists maps (group, cell) to indices. aliases maps a cell to (target, suffix)
    where suffix is a word offset within an already assigned target list.
    Unassigned cells share the empty sentinel at 372. Padding is nonzero.
    """
    if len(counts) != 4:
        raise ValueError("four polygon counts required")
    header = bytearray(372)
    header.extend(struct.pack("<I", 0xFFFFFFFF))
    pointers = {(g, c): 372 for g in range(5) for c in range(16)}
    for key, indices in (lists or {}).items():
        pointers[key] = len(header)
        header.extend(struct.pack(f"<{len(indices) + 1}I", *indices, 0xFFFFFFFF))
    for key, (target, suffix) in (aliases or {}).items():
        pointers[key] = pointers[target] + suffix * 4
    first = (len(header) + 15) // 16 * 16 if data_start is None else data_start
    if first < len(header) or first % 16:
        raise ValueError("data start must fit lists and align to 16")
    header.extend(b"\xa5" * (first - len(header)))
    struct.pack_into("<2I", header, 0, 0x80000000, 0x40200000)
    struct.pack_into("<I", header, 28, 0xDEADBEEF)
    for (group, cell), pointer in pointers.items():
        struct.pack_into("<I", header, 32 + group * 64 + cell * 4, pointer)
    blocks = [
        b"".join(polygon(group, i) for i in range(count)) + bytes(80)
        for group, count in enumerate(counts)
    ]
    blocks.append((b"\x01" + bytes(47)) * group4_count + bytes(48))
    offset = first
    for group, block in enumerate(blocks):
        struct.pack_into("<I", header, 8 + group * 4, len(block))
        struct.pack_into("<I", header, 352 + group * 4, offset)
        offset += len(block)
    return bytes(header) + b"".join(blocks)


def multigroup():
    return resource(
        lists={(0, 0): [1, 0, 1], (2, 0): [0, 1], (3, 0): [1, 1]},
        aliases={(0, 1): ((0, 0), 0), (0, 2): ((0, 0), 2), (1, 15): ((0, 0), 0)},
    )
