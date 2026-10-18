"""Own pool, code, states and packets; no original game material."""

import hashlib
import json
import struct
import zipfile
from dataclasses import replace
from functools import lru_cache

import pytest
from test_observer_acquisition import CYCLE, PLAN, rejects
from test_observer_capture import packed
from test_pcsx2_state import CPU, own_archive, own_internals

from tools.inspectors.driver_object import inspect_driver
from tools.inspectors.driver_transfer import (
    DriverCode,
    DriverProfile,
    DriverRequest,
    reconcile_driver_transfer,
)
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.observer_series import SeriesPoint
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE

ROOT, POOL, VTABLE, BUFFER, DEST, SP = 0x180000, 0x200000, 0x210000, 0x220000, 0x230000, 0x240000
OBJECT = POOL + 24 + 48
PAYLOAD = bytes(range(32))
REQUEST = DriverRequest(7, 65536, 8192, 32, 32, hashlib.sha256(PAYLOAD).hexdigest())
code = bytearray(32)
struct.pack_into(
    "<4I",
    code,
    8,
    35 << 26 | 16 << 21 | 2 << 16 | 4,
    35 << 26 | 2 << 21 | 2 << 16,
    2 << 21 | 31 << 11 | 9,
    0,
)
PROFILE = DriverProfile(
    ROOT, DriverCode(0x100000, bytes(code)), DriverCode(0x110000, bytes(32)), 0x100010
)


@lru_cache(maxsize=96)
def pause(
    index,
    *,
    request=REQUEST,
    pool=(),
    row=(),
    values=(),
    addresses=(),
    physical=(),
    registers=(),
    sequence=None,
    slot=None,
    cycle=None,
    pc=None,
    session=PLAN.request.session_id,
):
    pc = PROFILE.call_pc + 8 * index if pc is None else pc
    cycle = CYCLE + index + 1 if cycle is None else cycle
    seq = 1 + 8 * index if sequence is None else sequence
    header = [1, 22, 23, 16, 1, POOL + 24]
    for i, value in pool:
        header[i] = value
    words = [
        request.handle,
        VTABLE,
        0,
        5,
        4,
        0,
        request.file_size,
        0x250000,
        request.offset + index * request.size,
        0xFFFFFFFF,
        BUFFER,
        request.offset // 2048 if index else 0xFFFFFFFF,
    ]
    for i, value in row:
        words[i] = value
    args = bytearray(36)
    for at, value in ((0, request.handle), (16, DEST), (32, request.requested)):
        struct.pack_into("<I", args, at, value)
    regions = {
        "root": (ROOT, struct.pack("<I", POOL)),
        "pool": (POOL, struct.pack("<6I", *header)),
        "object": (OBJECT, struct.pack("<12I", *words)),
        "vtable": (VTABLE, struct.pack("<3I", PROFILE.reader.address, 0x120000, 0x130000)),
        "dispatch": (PROFILE.dispatch.address, PROFILE.dispatch.data),
        "reader": (PROFILE.reader.address, PROFILE.reader.data),
        "destination": (DEST, PAYLOAD if index else bytes(request.size)),
        "args": (SP + 48, bytes(args)),
    }
    for label, data in values:
        regions[label] = (regions[label][0], data)
    for label, address in addresses:
        regions[label] = (address, regions[label][1])
    gpr = [0] * 32
    for reg, value in {
        2: request.size if index else PROFILE.reader.address,
        4: OBJECT,
        5: DEST,
        6: request.requested,
        16: OBJECT,
        29: SP,
        31: PROFILE.call_pc + 8,
    }.items():
        gpr[reg] = value
    for reg, value in registers:
        gpr[reg] = value
    internal = bytearray(own_internals(pc)).ljust(CPU + 1160, b"\0")
    struct.pack_into("<I", internal, 292, PLAN.crc)
    struct.pack_into("<Q", internal, CPU + 1088, cycle)
    for reg, value in enumerate(gpr):
        struct.pack_into("<I", internal, CPU + 16 * reg, value)
    ram = bytearray(RAM_SIZE)
    backing = dict(physical)
    for label, (virtual, data) in regions.items():
        offset = backing.get(label, virtual)
        ram[offset : offset + len(data)] = data
    raw = own_archive(
        [(VERSION_MEMBER, VERSION), (INTERNALS_MEMBER, bytes(internal)), (RAM_MEMBER, bytes(ram))],
        zipfile.ZIP_DEFLATED,
    )
    points = []
    for i, (label, (virtual, data)) in enumerate(regions.items()):
        query = replace(
            PLAN.request,
            session_id=session,
            sequence=seq + i,
            expected_pc=pc,
            virtual_start=virtual,
            size=len(data),
            expected_offset=backing.get(label, virtual),
        )
        context = replace(
            PLAN.context,
            session_id=session,
            sequence=seq + i,
            state_sha256=hashlib.sha256(raw).hexdigest(),
        )
        plan = replace(
            PLAN, request=query, context=context, slot=index + 1 if slot is None else slot
        )
        packet = bytearray(packed(query))
        for start in (61, 149):
            struct.pack_into("<Q", packet, start + 12, cycle)
        packet[237:] = data
        points.append(SeriesPoint(label, plan, raw, (bytes(packet),) * 3))
    return tuple(points)


def run(request=REQUEST, profile=PROFILE, stages=None):
    return reconcile_driver_transfer(request, profile, stages or (pause(0), pause(1)))


def changed(index, **kwargs):
    return tuple(pause(i, **kwargs) if i == index else pause(i) for i in range(2))


def test_supplied_pair_and_private_view():
    result = run()
    assert result == run() and len(result["points"]) == 16
    assert result["object_and_position_consistent"] and result["pinned_code_matches"]
    assert result["resource_size"] == 32 and result["read_events_produced"] == 0
    assert result["resource_links"] == result["capabilities"] == []
    for key in (
        "destination_preexisting",
        "initial_cache_index_matches",
        "source_anchor_reverified",
        "profile_semantics_authenticated",
        "open_generation_observed",
        "continuous_lifetime_verified",
        "file_identity_verified",
        "inner_route_verified",
        "cache_origin_verified",
        "disk_read_verified",
        "live_acquisition_verified",
    ):
        assert result[key] is False
    encoded = json.dumps(result)
    assert all(
        f'"{key}":' not in encoded for key in ("handle", "pc", "pid", "address", "path", "words")
    )
    view = inspect_driver(pause(0)[:4], 7, 65536, 8192, PROFILE.reader.address)
    assert view.pool[3:5] == (16, 1) and view.words[4] == 4
    for private in (view, REQUEST, PROFILE, PROFILE.reader):
        assert repr(private) == object.__repr__(private)


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"request": None}, "TRANSFER_INPUT"),
        ({"profile": None}, "TRANSFER_INPUT"),
        ({"stages": (pause(0),)}, "TRANSFER_STAGES"),
        ({"stages": [pause(0), pause(1)]}, "TRANSFER_STAGES"),
    ],
)
def test_input_structure(kwargs, error):
    with rejects(error):
        run(**kwargs)


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("handle", True, "DRIVER_HANDLE"),
        ("handle", -1, "DRIVER_HANDLE"),
        ("file_size", 0, "TRANSFER_RANGE"),
        ("file_size", 2**31, "TRANSFER_RANGE"),
        ("offset", -1, "TRANSFER_RANGE"),
        ("offset", 65536, "TRANSFER_RANGE"),
        ("size", 0, "TRANSFER_RANGE"),
        ("size", 4097, "TRANSFER_RANGE"),
        ("requested", 0, "TRANSFER_RANGE"),
        ("requested", 4097, "TRANSFER_RANGE"),
        ("size", 31, "TRANSFER_LENGTH"),
        ("requested", 33, "TRANSFER_LENGTH"),
        ("offset", 2040, "TRANSFER_SECTOR"),
        ("resource_sha256", "A" * 64, "TRANSFER_HASH"),
        ("resource_sha256", None, "TRANSFER_HASH"),
    ],
)
def test_request_validation(field, value, error):
    with rejects(error):
        run(request=replace(REQUEST, **{field: value}))


def test_signed_end_overflow():
    with rejects("TRANSFER_LENGTH"):
        run(request=replace(REQUEST, file_size=2**31 - 1, offset=2**31 - 16))


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("root_address", 0, "TRANSFER_ROOT"),
        ("root_address", ROOT + 1, "TRANSFER_ROOT"),
        ("dispatch", None, "TRANSFER_CODE"),
        ("reader", DriverCode(0, bytes(32)), "TRANSFER_CODE"),
        ("reader", DriverCode(0x110001, bytes(32)), "TRANSFER_CODE"),
        ("reader", DriverCode(0x110000, bytearray(32)), "TRANSFER_CODE"),
        ("reader", DriverCode(0x110000, bytes(16)), "TRANSFER_CODE"),
        ("reader", DriverCode(0x110000, bytes(21)), "TRANSFER_CODE"),
        ("reader", DriverCode(0x110000, bytes(4100)), "TRANSFER_CODE"),
        ("call_pc", True, "TRANSFER_PC"),
        ("call_pc", 0x100000, "TRANSFER_PC"),
        ("call_pc", 0x100011, "TRANSFER_PC"),
        ("call_pc", 0x100018, "TRANSFER_PC"),
        ("dispatch", DriverCode(0x100000, bytes(32)), "TRANSFER_CALL_SHAPE"),
    ],
)
def test_profile_validation(field, value, error):
    with rejects(error):
        run(profile=replace(PROFILE, **{field: value}))


@pytest.mark.parametrize("field,value", [(3, 0), (3, 257), (4, 32), (5, POOL + 32)])
def test_invalid_pool(field, value):
    with rejects("DRIVER_POOL"):
        run(stages=tuple(pause(i, pool=((field, value),)) for i in range(2)))


@pytest.mark.parametrize(
    "field,value,error",
    [
        (0, 0xFFFFFFFF, "DRIVER_CLOSED_OR_FOREIGN"),
        (0, 9, "DRIVER_CLOSED_OR_FOREIGN"),
        (4, 0, "DRIVER_GENERATION"),
        (4, 5, "DRIVER_GENERATION"),
        (4, 2**31 + 4, "DRIVER_GENERATION"),
        (3, 0xFFFFFFFF, "DRIVER_STATE"),
        (5, 2, "DRIVER_STATE"),
        (6, 65535, "DRIVER_POSITION"),
        (8, 8191, "DRIVER_POSITION"),
        (7, 0, "DRIVER_REFERENCE"),
        (1, VTABLE + 4, "DRIVER_VTABLE"),
        (10, 0, "TRANSFER_BUFFER"),
        (10, 2**32 - 2047, "TRANSFER_BUFFER"),
        (11, 32, "TRANSFER_CACHE"),
    ],
)
def test_object_fail_closed(field, value, error):
    with rejects(error):
        run(stages=tuple(pause(i, row=((field, value),)) for i in range(2)))


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"pool": ((3, 1),)}, "DRIVER_OBJECT"),
        ({"addresses": (("object", OBJECT + 48),)}, "DRIVER_OBJECT"),
        ({"values": (("root", struct.pack("<I", POOL + 16)),)}, "DRIVER_POOL"),
        ({"values": (("vtable", struct.pack("<3I", 0x120000, 0, 0)),)}, "DRIVER_VTABLE"),
        ({"values": (("pool", bytes(20)),)}, "DRIVER_LAYOUT"),
        ({"values": (("args", bytes(32)),)}, "TRANSFER_LAYOUT"),
        ({"values": (("destination", bytes(31)),)}, "TRANSFER_LAYOUT"),
        ({"values": (("args", bytes(36)),)}, "TRANSFER_SAVED_ARGS"),
        ({"values": (("dispatch", bytes(32)),)}, "TRANSFER_CODE"),
        ({"values": (("reader", bytes([1]) * 32),)}, "TRANSFER_CODE"),
        ({"addresses": (("root", ROOT + 4),)}, "TRANSFER_ROOT"),
    ],
)
def test_layout_and_pointers(kwargs, error):
    with rejects(error):
        run(stages=tuple(pause(i, **kwargs) for i in range(2)))


@pytest.mark.parametrize(
    "index,kwargs,error",
    [
        (0, {"pc": PROFILE.call_pc + 4}, "TRANSFER_PC"),
        (1, {"slot": 1}, "TRANSFER_SLOT"),
        (1, {"sequence": 10}, "TRANSFER_IDENTITY"),
        (1, {"cycle": CYCLE + 1}, "TRANSFER_CYCLE"),
        (1, {"cycle": CYCLE + MAX_CYCLES + 2}, "TRANSFER_CYCLE"),
        (1, {"physical": (("destination", DEST + 4096),)}, "TRANSFER_BACKING"),
        (1, {"pool": ((1, 24),)}, "TRANSFER_CHANGED"),
        (1, {"row": ((7, 0x260000),)}, "TRANSFER_OBJECT_CHANGED"),
        (1, {"row": ((11, 0),)}, "TRANSFER_CACHE"),
        (1, {"row": ((8, 8192),)}, "DRIVER_POSITION"),
        (1, {"values": (("destination", bytes(32)),)}, "TRANSFER_PAYLOAD"),
    ],
)
def test_pair_invariants(index, kwargs, error):
    with rejects(error):
        run(stages=changed(index, **kwargs))


@pytest.mark.parametrize(
    "index,reg,value",
    [
        (0, 2, 0),
        (0, 4, OBJECT + 48),
        (0, 5, DEST + 4),
        (0, 6, 31),
        (0, 16, OBJECT + 48),
        (0, 29, SP + 16),
        (1, 29, SP + 16),
        (1, 16, OBJECT + 48),
        (1, 31, PROFILE.call_pc + 4),
        (1, 2, 31),
        (1, 2, 0xFFFFFFFF),
    ],
)
def test_abi(index, reg, value):
    with rejects("TRANSFER_ARGUMENTS"):
        run(stages=changed(index, registers=((reg, value),)))


def test_region_order_and_driver_interface():
    with rejects("TRANSFER_REGIONS"):
        run(
            stages=(
                tuple(replace(p, label="other") if p.label == "root" else p for p in pause(0)),
                pause(1),
            )
        )
    with rejects("DRIVER_REGIONS"):
        inspect_driver(pause(0)[1:5], 7, 65536, 8192, PROFILE.reader.address)
    for target in (0, PROFILE.reader.address + 1):
        with rejects("DRIVER_TARGET"):
            inspect_driver(pause(0)[:4], 7, 65536, 8192, target)
    with rejects("DRIVER_SIZE"):
        inspect_driver(pause(0)[:4], 7, 0, 8192, PROFILE.reader.address)
    with rejects("DRIVER_POSITION"):
        inspect_driver(pause(0)[:4], 7, 65536, 65537, PROFILE.reader.address)


def test_session_mixing():
    with rejects("TRANSFER_IDENTITY"):
        run(stages=changed(1, session="f" * 32))


def test_process_mixing():
    points = tuple(
        replace(p, plan=replace(p.plan, context=replace(p.plan.context, process_sha256="f" * 64)))
        for p in pause(1)
    )
    with rejects("TRANSFER_IDENTITY"):
        run(stages=(pause(0), points))


def test_cached_preexisting_payload_never_becomes_read():
    result = run(stages=changed(0, row=((11, 4),), values=(("destination", PAYLOAD),)))
    assert result["initial_cache_index_matches"] and result["destination_preexisting"]
    assert not result["cache_origin_verified"] and not result["disk_read_verified"]
    assert result["read_events_produced"] == 0


def test_eof_clamp_and_last_partial_sector():
    request = replace(REQUEST, file_size=8224, requested=64)
    result = run(request=request, stages=tuple(pause(i, request=request) for i in range(2)))
    assert result["requested_size"] == 64 and result["resource_size"] == 32


@pytest.mark.parametrize(
    "shift,count,handle,counter,index", [(0, 1, 7, 8, 0), (1, 16, 7, 4, 1), (31, 256, 0, 1, 0)]
)
def test_observed_shift_not_derived_from_capacity(shift, count, handle, counter, index):
    object_at = POOL + 24 + 48 * index
    request = replace(REQUEST, handle=handle)
    stages = tuple(
        pause(
            i,
            request=request,
            pool=((3, count), (4, shift)),
            row=((4, counter),),
            addresses=(("object", object_at),),
            registers=((4, object_at), (16, object_at)),
        )
        for i in range(2)
    )
    assert run(request=request, stages=stages)["object_and_position_consistent"]


def test_budget_boundaries():
    stages = (pause(0, sequence=241), pause(1, sequence=249, cycle=CYCLE + 1 + MAX_CYCLES))
    assert run(stages=stages)["points"][-1]["sequence"] == 256
    with rejects("MAPPING_CONTEXT"):
        run(stages=(pause(0, sequence=242), pause(1, sequence=250)))


def test_full_sector_and_maximum_request_with_eof_clamp():
    payload = bytes(range(256)) * 8
    request = replace(
        REQUEST,
        size=2048,
        requested=4096,
        file_size=10240,
        resource_sha256=hashlib.sha256(payload).hexdigest(),
    )
    stages = tuple(pause(i, request=request, values=(("destination", payload),)) for i in range(2))
    assert run(request=request, stages=stages)["resource_size"] == 2048


def test_previous_valid_cache_index_is_not_provenance():
    result = run(stages=changed(0, row=((11, 3),)))
    assert not result["initial_cache_index_matches"] and not result["cache_origin_verified"]


def test_async_flag_is_preserved_without_claiming_completion():
    result = run(stages=tuple(pause(i, row=((5, 1),)) for i in range(2)))
    assert not result["inner_route_verified"]


def test_matching_arbitrary_reader_pin_does_not_authenticate_semantics():
    reader = DriverCode(PROFILE.reader.address, bytes([7]) * 32)
    profile = replace(PROFILE, reader=reader)
    stages = tuple(pause(i, values=(("reader", reader.data),)) for i in range(2))
    result = run(profile=profile, stages=stages)
    assert result["pinned_code_matches"] and not result["profile_semantics_authenticated"]
