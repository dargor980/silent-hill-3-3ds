"""Synthetic full upload/draw trace, with deliberately reused video addresses."""

import copy
import struct
from collections import defaultdict

import pytest

from tests.heather_room_material_binding_audit import consume
from tests.python.test_map_material_binding import gs_state
from tests.python.test_texture_probe import own_block, own_file
from tools.inspectors.pcsx2_gs_dump import Packet


def gif(frame, low, regs, payload):
    return Packet(3, frame, 0, struct.pack("<QQ", low, regs), payload)


def ad(frame, values):
    return gif(
        frame, len(values) | 1 << 60, 14, b"".join(struct.pack("<QQ", v, r) for r, v in values)
    )


def fixture(change=None):
    blocks, transfers, meshes, lookup, packets = [], [], [], defaultdict(list), []
    first_draw = None
    state = bytearray(4194813)
    struct.pack_into("<I", state, 0, 9)
    for i in range(7):
        block = bytearray(own_block(width=512, height=512))
        block[80 : 80 + 262144] = bytes([i + 1]) * 262144
        block[-4096:] = bytes([i + 31]) * 4096
        blocks.append(bytes(block))
        transfers.append((bytes(block[80 : 80 + 262144]), bytes(block[-4096:])))
        meshes.append(
            dict(
                group_index=i,
                selector=0,
                mode=0,
                shapes=[dict(shape_offset=i, submitted=True, vertices=3, batches=1)],
            )
        )
        for j in range(3):
            lookup[(j * 100, j * 200)].append((i, (i * 100 + j * 10, 100 + j * 10, 200 + j * 10)))
    for frame in (1, 3):
        packets.append(ad(frame, list(gs_state().items())))
        for i in range(7):
            for role, content in enumerate(transfers[i]):
                base = 0x3000 if role == 0 else 0x3780
                bitblt = base << 32 | (4 if role == 0 else 1) << 48
                extent = 0x10000000100 if role == 0 else 0x4000000040
                values = [(0x50, bitblt), (0x51, 0), (0x52, extent), (0x53, 0)]
                if frame == 1 and i == 0:
                    if change == "direction":
                        values[-1] = (0x53, 1)
                    if change == "position":
                        values[1] = (0x51, 1)
                    if change == "width":
                        values[0] = (0x50, base << 32 | 2 << 48)
                    if change == "extent":
                        values[2] = (0x52, 0)
                    if change == "psm":
                        values[0] = (0x50, bitblt | 19 << 56)
                    if change == "indices" and role == 0:
                        content = transfers[1][0]
                    if change == "clut" and role == 1:
                        content = transfers[1][1]
                    if change == "bytes" and role == 0:
                        content = b"X" + content[1:]
                packets.append(ad(frame, values))
                # Two chunks exercise continuation without a second TRXDIR.
                for chunk in (content[: len(content) // 2], content[len(content) // 2 :]):
                    packets.append(gif(frame, len(chunk) // 16 | 2 << 58, 0, chunk))
            if change == "overwrite" and frame == 1 and i == 0:
                packets.extend(
                    [
                        ad(
                            frame,
                            [
                                (0x50, 0x3000 << 32 | 4 << 48),
                                (0x51, 0),
                                (0x52, 0x10000000100),
                                (0x53, 0),
                            ],
                        ),
                        gif(frame, 1 | 2 << 58, 0, bytes(16)),
                    ]
                )
            tex0 = 0x2006F00665323000
            if change == "selector" and frame == 1 and i == 0:
                tex0 += 4 << 37
            packets.append(ad(frame, [(6, tex0)]))
            data = b"".join(
                struct.pack(
                    "<4f4I4I",
                    j * 100 / 32768,
                    j * 200 / 32768,
                    1,
                    0,
                    90,
                    80,
                    70,
                    0,
                    i * 100 + j * 10,
                    100 + j * 10,
                    200 + j * 10,
                    0,
                )
                for j in range(3)
            )
            prim = 60
            if frame == 1 and i == 0:
                if change == "prim":
                    prim = 124
                if change == "color":
                    data = bytearray(data)
                    struct.pack_into("<I", data, 16, 256)
                    data = bytes(data)
                if change == "geometry":
                    data = bytearray(data)
                    struct.pack_into("<I", data, 32, 10000)
                    data = bytes(data)
            p = gif(frame, 3 | 1 << 46 | prim << 47 | 3 << 60, 0x412, data)
            if change == "frame" and frame == 1 and i == 0:
                p = gif(2, 3 | 1 << 46 | prim << 47 | 3 << 60, 0x412, data)
            packets.append(p)
            if frame == 1 and i == 0:
                first_draw = p
            if change == "interleave" and frame == 1 and i == 1:
                packets.extend(
                    [
                        ad(
                            frame,
                            [
                                (0x50, 0x3000 << 32 | 4 << 48),
                                (0x51, 0),
                                (0x52, 0x10000000100),
                                (0x53, 0),
                            ],
                        ),
                        gif(frame, 16384 | 2 << 58, 0, transfers[0][0]),
                        ad(
                            frame,
                            [
                                (0x50, 0x3780 << 32 | 1 << 48),
                                (0x51, 0),
                                (0x52, 0x4000000040),
                                (0x53, 0),
                            ],
                        ),
                        gif(frame, 256 | 2 << 58, 0, transfers[0][1]),
                        first_draw,
                    ]
                )
            if change in ("duplicate", "state") and frame == 1 and i == 0:
                if change == "state":
                    packets.append(ad(frame, [(0x4C, 0x80000)]))
                packets.append(p)
    if change == "hidden":
        meshes[0]["shapes"][0]["submitted"] = False

    class FakeDump:
        def __init__(self):
            self.state = bytes(state)

        def packets(self):
            return iter(packets)

    sequences = {
        i: [((j * 100, j * 200), (i * 100 + j * 10, 100 + j * 10, 200 + j * 10)) for j in range(3)]
        for i in range(7)
    }
    if change in ("state", "duplicate"):
        sequences[0] *= 2
    return FakeDump(), lookup, meshes, bytes(258048) + own_file(*blocks), sequences


def test_consumption_reuses_addresses_and_checks_exact_upload_bytes():
    args = fixture()
    before = copy.deepcopy(args[2])
    out = consume(*args)
    assert args[2] == before
    assert (
        out["submitted_shapes"] == 7 and out["frames"] == 2 and out["matched_vertex_records"] == 42
    )
    assert out["order"] == {1: list(range(7)), 3: list(range(7))}
    assert len(out["transfers"]) == 28
    assert all(r["vertices"] == 3 and r["max_xyz_error"] == 0 for r in out["draws"])
    assert len({t["sha256"] for t in out["transfers"]}) == 14
    assert len({t["base"] for t in out["transfers"]}) == 2


@pytest.mark.parametrize(
    "change,code",
    [
        ("direction", "TRANSFER"),
        ("position", "UPLOAD_MATCH"),
        ("psm", "UPLOAD_MATCH"),
        ("width", "UPLOAD_WIDTH"),
        ("extent", "UPLOAD_EXTENT"),
        ("indices", "GS_BINDING"),
        ("clut", "GS_CLUT"),
        ("selector", "GS_CLUT"),
        ("bytes", "DRAW_ORDER"),
        ("overwrite", "DRAW_ORDER"),
        ("prim", "GS_PRIM"),
        ("color", "COLOR"),
        ("geometry", "VERTEX_MATCH"),
        ("frame", "GS_FRAME"),
        ("duplicate", "GS_COVERAGE"),
        ("state", "STATE_CHANGED"),
        ("hidden", "GS_BINDING"),
        ("interleave", "DRAW_INTERLEAVE"),
    ],
)
def test_wrong_binding_or_state_cannot_produce_acceptance(change, code):
    with pytest.raises(ValueError, match="HRB_" + code):
        consume(*fixture(change))
