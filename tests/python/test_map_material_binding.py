"""Invented RAM/GIF fixtures; no private game data."""

import struct

import pytest

from tests.heather_room_material_binding_audit import check_profile
from tools.inspectors.map_material_binding import (
    Memory,
    apply_packet,
    initial_gs_state,
    match_strip,
    prepared_mesh,
    project_vertices,
    shape_chain,
)
from tools.inspectors.pcsx2_gs_dump import Packet


def fixture(mode=0, selector=0, visible=True):
    raw = bytearray(65536)

    def words(at, *values):
        struct.pack_into("<" + "I" * len(values), raw, at, *values)

    words(0x1774, 0x3000)
    words(0x3040, 0x8400, 0x4000, 123, 0)
    words(0x4020, 0x8400)
    words(0x1360, 0x5000)
    words(0x5000, 0x6000)
    struct.pack_into("<h", raw, 0x5004, mode)
    raw[0x5006] = 9
    raw[0x5009] = 7
    struct.pack_into("<H", raw, 0x500A, 8)
    raw[0x5017:0x501A] = bytes((0, selector, 2))
    texref = 0x4080 + selector * 48
    struct.pack_into("<QQ", raw, texref, 0x2006F00665323000, 6)
    words(0x5F70, 0x30000002, texref - 16, 0, 0x50000002)
    for off, v0, v1 in (
        (-0x70, 0x1000101, 0x6C01005B),
        (-0x50, 0, 0x6C01005F),
        (-0x30, 0, 0x6C010062),
        (-0x10, 0, 0x6C010065),
    ):
        words(0x6000 + off, 0x30000001, texref, v0, v1)
    pair = (0x44, 0x42) if mode == 1 else (0x5800D if mode == 3 else 0x5800C, 0x47)
    struct.pack_into("<QQ", raw, 0x6020, *pair)
    words(0x6070, 0x20000000 if visible else 0x11000000, 0x7000, 0, 0)
    struct.pack_into("<h", raw, 0x8090, selector)
    struct.pack_into("<h", raw, 0x8096, mode)
    words(0x8110, 7)
    prim = 0x7C if mode == 1 else 0x3C
    for at, count, payload in ((0x7000, 5, 0x8140), (0x7070, 4, 0x8170)):
        words(at, 0x10000003, 0, 0x1000101, 0x6C038000)
        struct.pack_into("<QQ", raw, at + 16, count | 1 << 46 | prim << 47 | 3 << 60, 0x412)
        words(at + 64, 0x30000003, 0x5060, 0, 0x6C038003)
        words(at + 80, 0x30000000 | count, payload, 0, 0x6D008006 | count * 2 << 16)
        words(at + 96, 0x10000000, 0, 0, 0x17000000)
    words(0x70E0, 0x20000000, 0x6080, 0, 0)
    mesh = dict(mesh_offset=128, selector_candidate=selector, shape_offsets=[256])
    return raw, mesh


def inspect(raw, mesh):
    return prepared_mesh(Memory(bytes(raw)), 0x1000, 0x8000, 0, 0, mesh, 1024)


@pytest.mark.parametrize(
    "mode,selector,visible", [(0, 0, True), (1, 14, True), (3, 1, True), (0, 0, False)]
)
def test_prepared_binding_complete_ranges_and_visibility(mode, selector, visible):
    raw, mesh = fixture(mode, selector, visible)
    before = bytes(raw)
    out = inspect(raw, mesh)
    assert bytes(raw) == before
    assert out["mode"] == mode and out["selector"] == selector
    assert out["header"] == 0x8400 and out["manager"] == 0x4000
    assert out["shapes"] == [
        dict(
            shape_offset=256,
            call_address=0x6070,
            chain_address=0x7000,
            gate=0,
            submitted=visible,
            tags=9,
            batches=2,
            vertices=7,
            primitive=0x7C if mode == 1 else 0x3C,
            source_ranges=[[0, 5], [3, 4]],
        )
    ]


@pytest.mark.parametrize(
    "at,fmt,value,code",
    [
        (0x3040, "I", 0x8404, "HEADER"),
        (0x4020, "I", 0x8404, "MANAGER"),
        (0x8090, "h", 1, "SELECTOR"),
        (0x8096, "h", 9, "MODE"),
        (0x5004, "h", 3, "DESCRIPTOR"),
        (0x5006, "B", 10, "DESCRIPTOR"),
        (0x5009, "B", 8, "DESCRIPTOR"),
        (0x500A, "H", 9, "DESCRIPTOR"),
        (0x5018, "B", 1, "DESCRIPTOR"),
        (0x4088, "Q", 7, "TEX0"),
        (0x5F74, "I", 0x4080, "TEX_REF"),
        (0x5F94, "I", 0x4090, "TEX_REF"),
        (0x6020, "Q", 0x5800D, "SETUP_STATE"),
        (0x6070, "I", 0x10000000, "VISIBILITY"),
        (0x607C, "I", 1, "VISIBILITY"),
        (0x7000, "I", 0x10000002, "CNT"),
        (0x7004, "I", 16, "CNT"),
        (0x7018, "Q", 0x413, "PRIMITIVE"),
        (0x7044, "I", 0x5070, "PARAMETER_REF"),
        (0x7054, "I", 0x8150, "PAYLOAD"),
        (0x70C4, "I", 0x8180, "PAYLOAD"),
        (0x70E4, "I", 0x6070, "RETURN"),
        (0x70E8, "I", 1, "RETURN"),
        (0x7000, "I", 0x10010003, "TAG_BITS"),
        (0x7000, "I", 0x50000000, "DMA_KIND"),
        (0x6074, "I", 0x7001, "CHAIN"),
        (0x8110, "I", 2, "SHAPE"),
        (0x7054, "I", 0x10000, "RANGE"),
    ],
)
def test_reject_corrupt_prepared_chain(at, fmt, value, code):
    raw, mesh = fixture()
    struct.pack_into("<" + fmt, raw, at, value)
    with pytest.raises(ValueError, match="HRB_" + code):
        inspect(raw, mesh)


@pytest.mark.parametrize("raw", [b"", bytearray(10), None, b"x" * (32 * 1024 * 1024 + 1)])
def test_ram_type_and_limit(raw):
    with pytest.raises(ValueError, match="HRB_RAM"):
        Memory(raw)


@pytest.mark.parametrize("at,n", [(-1, 1), (True, 1), (0, True), (0, 0), (1, 4), (0, 5)])
def test_ranges(at, n):
    with pytest.raises(ValueError, match="HRB_RANGE"):
        Memory(b"abcd").read(at, n)


def test_chain_budget(monkeypatch):
    class Endless:
        def words(self, _):
            return (0x10000000, 0, 0, 0)

    with pytest.raises(ValueError, match="HRB_CHAIN"):
        shape_chain(Endless(), 0, 16, 64, 3, 128, 0x3C)


def projected():
    words = [
        (1, 2, 3, 0, 100, 200, 0, 0),
        (4, 5, 6, 0, 300, 400, 0, 0),
        (7, 8, 9, 0, 500, 600, 0, 0),
    ]
    raw = b"".join(struct.pack("<8h", *w) for w in words)
    matrix = [[int(i == j) for j in range(4)] for i in range(4)]
    return raw, matrix


def strip():
    raw, matrix = projected()
    pts = project_vertices(raw, matrix)
    lookup = {uv: [(123, xyz)] for uv, xyz in pts}
    packet = b"".join(
        struct.pack("<4f4I4I", uv[0] / 32768, uv[1] / 32768, 1, 0, 90, 80, 70, 127, *xyz, 0)
        for uv, xyz in pts
    )
    return packet, lookup


def test_projection_and_geometry_only_strip_match():
    raw, matrix = projected()
    assert project_vertices(raw, matrix) == [
        ((100, 200), (16, 32, 48)),
        ((300, 400), (64, 80, 96)),
        ((500, 600), (112, 128, 144)),
    ]
    payload, lookup = strip()
    # Shared vertices don't create ambiguity when the whole strip identifies one shape.
    lookup[(100, 200)].append((456, (16, 32, 48)))
    assert match_strip(payload, lookup) == (123, 0)
    points = project_vertices(raw, matrix)
    assert match_strip(payload, lookup, points) == (123, 0)
    with pytest.raises(ValueError, match="HRB_ORDERED_VERTEX"):
        match_strip(payload, lookup, list(reversed(points)))
    with pytest.raises(ValueError, match="HRB_SEQUENCE_LENGTH"):
        match_strip(payload, lookup, points[:-1])
    p = bytearray(payload)
    struct.pack_into("<I", p, 32, 18)
    assert match_strip(bytes(p), lookup) == (123, 2)
    struct.pack_into("<I", p, 32, 19)
    with pytest.raises(ValueError, match="HRB_VERTEX_MATCH"):
        match_strip(bytes(p), lookup)


@pytest.mark.parametrize(
    "case,code",
    [("short", "VERTICES"), ("matrix", "MATRIX"), ("nan", "MATRIX"), ("behind", "PROJECTION")],
)
def test_projection_errors(case, code):
    raw, matrix = projected()
    if case == "short":
        raw = raw[:-1]
    if case == "matrix":
        matrix.pop()
    if case == "nan":
        matrix[0][0] = float("nan")
    if case == "behind":
        matrix[3][3] = -1
    with pytest.raises(ValueError, match="HRB_" + code):
        project_vertices(raw, matrix)


@pytest.mark.parametrize(
    "case,code",
    [
        ("short", "STRIP"),
        ("nan", "STQ"),
        ("zero_q", "STQ"),
        ("uv", "UV"),
        ("missing", "VERTEX_MATCH"),
        ("mixed", "STRIP_MATCH"),
        ("ambiguous", "AMBIGUOUS"),
    ],
)
def test_bad_or_ambiguous_strip(case, code):
    payload, lookup = strip()
    p = bytearray(payload)
    if case == "short":
        p.pop()
    if case == "nan":
        struct.pack_into("<f", p, 0, float("nan"))
    if case == "zero_q":
        struct.pack_into("<f", p, 8, 0)
    if case == "uv":
        struct.pack_into("<f", p, 0, 100.5 / 32768)
    if case == "missing":
        lookup.clear()
    if case == "mixed":
        lookup[(300, 400)] = [(456, (64, 80, 96))]
    if case == "ambiguous":
        for v in lookup.values():
            v.append((456, v[0][1]))
    with pytest.raises(ValueError, match="HRB_" + code):
        match_strip(bytes(p), lookup)


def packet(regs, values, flag=0, pre=0, prim=0):
    n = len(regs)
    tag = struct.pack(
        "<QQ",
        1 | pre << 46 | prim << 47 | flag << 58 | n << 60,
        sum(r << (i * 4) for i, r in enumerate(regs)),
    )
    return Packet(
        3,
        1,
        0,
        tag,
        b"".join(struct.pack("<QQ", *v) if flag == 0 else struct.pack("<Q", v[0]) for v in values),
    )


def test_state_initialization_and_mutations_include_tex2_invalidation():
    raw = bytearray(4194813)
    struct.pack_into("<I", raw, 0, 9)
    struct.pack_into("<Q", raw, 12, 1)
    state = initial_gs_state(bytes(raw))
    assert state[0x1A] == 1
    apply_packet(state, packet([14, 14], [(0x123, 6), (0x456, 0x16)], pre=1, prim=60))
    assert state[0] == 60 and state[6] == 0x123 and state[0x100]
    apply_packet(state, packet([6, 7, 2], [(0x789, 0), (0xABC, 0), (555, 0)]))
    assert state[6] == 0x789 and state[7] == 0xABC and not state[0x100] and not state[0x101]
    assert 2 not in state
    apply_packet(state, packet([14], [(0x123, 0x17)]))
    assert state[0x101]
    apply_packet(state, packet([8, 9], [(11, 0), (12, 0)], flag=1))
    assert state[8] == 11
    assert state[9] == 12
    before = state.copy()
    apply_packet(state, packet([0], [(1, 0)], flag=2))
    assert state == before
    apply_packet(state, Packet(3, 1, 0, bytes(16), b""))
    assert state == before
    with pytest.raises(ValueError, match="HRB_GS_STATE"):
        initial_gs_state(bytes(4194813))


def gs_state(mode=0):
    raw = bytearray(4194813)
    struct.pack_into("<I", raw, 0, 9)
    s = initial_gs_state(bytes(raw))
    s.update(
        {
            0: 0x7C if mode == 1 else 0x3C,
            6: 0x2006F00665323000,
            0x14: 0x60,
            0x47: 0x5800D if mode == 3 else 0x5800C,
            0x42: 0x44,
            0x4E: 0x3A0001C0,
            0x4C: 0x80100,
            0x3B: 0x8000000040,
            0x1A: 1,
            0x46: 1,
        }
    )
    return s


@pytest.mark.parametrize("mode", [0, 1, 3])
def test_effective_original_profiles(mode):
    d = check_profile(gs_state(mode), mode)
    assert d["primitive"]["abe"] == int(mode == 1)
    assert d["test"]["ate"] == int(mode == 3) and d["test"]["aref"] == 0 and d["test"]["atst"] == 6
    assert d["depth"]["mask"] == 0 and d["clamp"]["wms"] == d["clamp"]["wmt"] == 0


@pytest.mark.parametrize(
    "reg,value,code",
    [
        (0x100, True, "TEX2"),
        (0, 0x7C, "GS_PRIM"),
        (0x14, 0, "FILTER_WRAP"),
        (8, 5, "FILTER_WRAP"),
        (0x47, 0x5800D, "GS_TEST"),
        (0x42, 0x48, "BLEND_DEPTH"),
        (0x4E, 0x13A0001C0, "BLEND_DEPTH"),
        (0x4C, 0, "FRAME"),
        (0x3B, 0, "TEXA_FOG"),
        (0x3D, 1, "TEXA_FOG"),
        (0x49, 1, "GLOBAL"),
        (6, 0, "TEXTURE"),
    ],
)
def test_profile_rejects_material_state_changes(reg, value, code):
    s = gs_state()
    s[reg] = value
    with pytest.raises(ValueError, match="HRB_" + code):
        check_profile(s, 0)
