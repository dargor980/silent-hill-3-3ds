"""HRB02–06: bounded readers for prepared MAP materials and consumed GS strips.

Private source buffers stay in memory. The caller anchors their provenance.
This deliberately supports only the observed DMA/GIF subprofile.
"""

import math
import struct


def require(ok, code):
    if not ok:
        raise ValueError(code)


class Memory:
    def __init__(self, raw):
        require(type(raw) is bytes and 0 < len(raw) <= 32 * 1024 * 1024, "HRB_RAM")
        self.raw = raw

    def read(self, address, size):
        require(
            type(address) is int
            and type(size) is int
            and 0 < size <= len(self.raw)
            and 0 <= address <= len(self.raw) - size,
            "HRB_RANGE",
        )
        return self.raw[address : address + size]

    def words(self, address, count=4):
        return struct.unpack("<" + "I" * count, self.read(address, count * 4))

    def u32(self, address):
        return self.words(address, 1)[0]

    def pair(self, address):
        return struct.unpack("<QQ", self.read(address, 16))


def shape_chain(memory, start, return_to, payload, count, descriptor, primitive):
    """Validate CNT/REF/NEXT, complete source coverage and two-vertex overlap."""
    require(3 <= count <= 65536 and primitive in (0x3C, 0x7C), "HRB_SHAPE")
    address, covered, batches, tags, seen = start, 0, 0, 0, set()
    ranges = []
    while True:
        require(address % 16 == 0 and address not in seen and tags < 4096, "HRB_CHAIN")
        seen.add(address)
        tag, target, vif0, vif1 = memory.words(address)
        kind, qwc = tag >> 28, tag & 0xFFFF
        require(tag == (kind << 28) | qwc, "HRB_TAG_BITS")
        tags += 1
        if kind == 2:
            require(qwc == 0 and target == return_to and covered == count, "HRB_RETURN")
            require(vif0 == vif1 == 0 and batches > 0, "HRB_RETURN")
            return dict(
                tags=tags,
                batches=batches,
                vertices=count,
                primitive=primitive,
                source_ranges=ranges,
            )
        if kind == 1:
            require(qwc in (0, 3) and target == 0, "HRB_CNT")
            if qwc == 3:
                low, registers = memory.pair(address + 16)
                require(
                    registers == 0x412 and (low >> 46) & 1 and (low >> 47) & 2047 == primitive,
                    "HRB_PRIMITIVE",
                )
            address += (qwc + 1) * 16
        elif kind == 3:
            memory.read(target, qwc * 16)
            if vif1 >> 24 == 0x6D:
                first = 0 if batches == 0 else covered - 2
                require(
                    3 <= qwc <= 128
                    and target == payload + first * 16
                    and first + qwc <= count
                    and vif1 == 0x6D008006 | (qwc * 2 << 16),
                    "HRB_PAYLOAD",
                )
                covered = first + qwc
                batches += 1
                ranges.append([first, qwc])
            else:
                require(
                    qwc == 3 and target == descriptor + 0x60 and vif1 == 0x6C038003,
                    "HRB_PARAMETER_REF",
                )
            address += 16
        else:
            raise ValueError("HRB_DMA_KIND")


def prepared_mesh(memory, context, map_base, group_index, mesh_index, mesh, header_offset):
    """Cross-check original bank/manager, material setup and every shape pointer."""
    bank = memory.u32(context + 0x774)
    entry = bank + 0x40 + group_index * 16
    header, manager, _, _ = memory.words(entry)
    require(header == map_base + header_offset, "HRB_HEADER")
    require(memory.u32(manager + 0x20) == header, "HRB_MANAGER")
    selector = struct.unpack("<h", memory.read(map_base + mesh["mesh_offset"] + 16, 2))[0]
    require(selector == mesh["selector_candidate"] and 0 <= selector <= 15, "HRB_SELECTOR")
    mode = struct.unpack("<h", memory.read(map_base + mesh["mesh_offset"] + 22, 2))[0]
    require(mode in (0, 1, 3), "HRB_MODE")
    desc = memory.u32(context + 0x360 + group_index * 64 + mesh_index * 4)
    data = memory.read(desc, 32)
    setup = memory.u32(desc)
    require(
        struct.unpack_from("<h", data, 4)[0] == mode
        and data[6] == 9
        and data[23:26] == bytes((group_index, selector, 2))
        and data[9] == 7
        and struct.unpack_from("<H", data, 10)[0] == 7 + len(mesh["shape_offsets"]),
        "HRB_DESCRIPTOR",
    )
    texref = manager + 0x80 + selector * 48
    tex0, reg = memory.pair(texref)
    require(reg == 6, "HRB_TEX0")
    require(memory.words(setup - 0x90) == (0x30000002, texref - 16, 0, 0x50000002), "HRB_TEX_REF")
    for offset, vif0, vif1 in (
        (-0x70, 0x1000101, 0x6C01005B),
        (-0x50, 0, 0x6C01005F),
        (-0x30, 0, 0x6C010062),
        (-0x10, 0, 0x6C010065),
    ):
        require(memory.words(setup + offset) == (0x30000001, texref, vif0, vif1), "HRB_TEX_REF")
    pair = (0x44, 0x42) if mode == 1 else (0x5800D if mode == 3 else 0x5800C, 0x47)
    require(memory.pair(setup + 32) == pair, "HRB_SETUP_STATE")
    primitive = 0x7C if mode == 1 else 0x3C
    shapes = []
    for i, offset in enumerate(mesh["shape_offsets"]):
        call = setup + 112 + i * 16
        tag, chain, gate, unused = memory.words(call)
        require(tag in (0x20000000, 0x11000000) and unused == 0, "HRB_VISIBILITY")
        count = memory.u32(map_base + offset + 16)
        check = shape_chain(
            memory, chain, call + 16, map_base + offset + 64, count, desc, primitive
        )
        shapes.append(
            dict(
                shape_offset=offset,
                call_address=call,
                chain_address=chain,
                gate=gate,
                submitted=tag == 0x20000000,
                **check,
            )
        )
    return dict(
        group_index=group_index,
        mesh_offset=mesh["mesh_offset"],
        selector=selector,
        manager=manager,
        header=header,
        descriptor=desc,
        tex0=f"{tex0:016x}",
        mode=mode,
        setup_register=pair[1],
        setup_value=pair[0],
        shapes=shapes,
    )


def project_vertices(raw, matrix):
    require(len(raw) % 16 == 0 and 3 <= len(raw) // 16 <= 65536, "HRB_VERTICES")
    require(len(matrix) == 4 and all(len(row) == 4 for row in matrix), "HRB_MATRIX")
    require(all(math.isfinite(v) for row in matrix for v in row), "HRB_MATRIX")
    out = []
    for words in struct.iter_unpack("<8h", raw):
        point = (*words[:3], 1)
        hp = [sum(matrix[j][k] * point[j] for j in range(4)) for k in range(4)]
        require(all(math.isfinite(v) for v in hp) and hp[3] > 0, "HRB_PROJECTION")
        out.append((words[4:6], tuple(math.trunc(v / hp[3] * 16) for v in hp[:3])))
    return out


def match_strip(payload, lookup, sequence=None):
    """Return the unique source shape from all vertices, independent of its material."""
    require(len(payload) % 48 == 0 and len(payload) >= 3 * 48, "HRB_STRIP")
    require(sequence is None or len(sequence) == len(payload) // 48, "HRB_SEQUENCE_LENGTH")
    candidates, max_error = None, 0
    for at in range(0, len(payload), 48):
        s, t, q = struct.unpack_from("<3f", payload, at)
        require(all(math.isfinite(v) for v in (s, t, q)) and q > 0, "HRB_STQ")
        values = (s / q * 32768, t / q * 32768)
        uv = tuple(round(v) for v in values)
        require(max(abs(a - b) for a, b in zip(values, uv, strict=True)) <= 0.25, "HRB_UV")
        xyz = struct.unpack_from("<3I", payload, at + 32)
        if sequence is not None:
            expected_uv, expected_xyz = sequence[at // 48]
            require(
                uv == expected_uv
                and max(abs(a - b) for a, b in zip(xyz, expected_xyz, strict=True)) <= 2,
                "HRB_ORDERED_VERTEX",
            )
        matches = {}
        for shape, expected in lookup.get(uv, []):
            error = max(abs(a - b) for a, b in zip(xyz, expected, strict=True))
            if error <= 2:
                matches[shape] = min(error, matches.get(shape, 2))
        require(matches, "HRB_VERTEX_MATCH")
        candidates = set(matches) if candidates is None else candidates & matches.keys()
        require(candidates, "HRB_STRIP_MATCH")
        max_error = max(max_error, max(matches[s] for s in candidates))
    require(len(candidates) == 1, "HRB_AMBIGUOUS")
    return next(iter(candidates)), max_error


def initial_gs_state(raw):
    require(len(raw) == 4194813 and struct.unpack_from("<I", raw)[0] == 9, "HRB_GS_STATE")
    state = {}
    for i, r in enumerate(
        (0, 0x1A, 0x1C, 0x22, 0x3B, 0x3D, 0x44, 0x45, 0x46, 0x49, 0x50, 0x53, 0x51, 0x52)
    ):
        state[r] = struct.unpack_from("<Q", raw, 4 + i * 8)[0]
    for c in range(2):
        for i, r in enumerate((0x18, 6, 0x14, 8, 0x34, 0x36, 0x40, 0x42, 0x47, 0x4A, 0x4C, 0x4E)):
            state[r + c] = struct.unpack_from("<Q", raw, 124 + c * 96 + i * 8)[0]
    return state


def apply_packet(state, packet):
    """Update effective state, preserving a TEX2 marker until the next TEX0."""
    f = packet.fields
    if not f["nloop"] or f["flag"] >= 2:
        return
    if f["flag"] == 0 and f["pre"]:
        state[0] = f["prim"]
    step = 16 if f["flag"] == 0 else 8
    for j in range(f["nloop"] * f["nreg"]):
        reg = (f["regs"] >> ((j % f["nreg"]) * 4)) & 15
        value = struct.unpack_from("<Q", packet.payload, j * step)[0]
        if f["flag"] == 0 and reg == 14:
            reg = struct.unpack_from("<Q", packet.payload, j * step + 8)[0] & 127
        elif reg not in (0, 6, 7, 8, 9):
            continue
        state[reg] = value
        if reg in (6, 7):
            state[0x100 + reg - 6] = False
        elif reg in (0x16, 0x17):
            state[0x100 + reg - 0x16] = True
