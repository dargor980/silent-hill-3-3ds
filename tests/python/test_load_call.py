"""LF02-08: independent synthetic code, registers, RAM and wire fixtures."""

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

from tools.inspectors.load_call import validate_call
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observer_series import SeriesPoint
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE

SITE, TARGET, DEST = 0x100FFC, 0x110000, 0x203FF0
DELAY = (16 << 21) | (6 << 11) | 0x2D


def instruction(delay=DELAY):
    return struct.pack("<III", (3 << 26) | (TARGET >> 2), delay, 0)


@lru_cache(maxsize=48)
def pause(
    index=0,
    *,
    size=32,
    site=SITE,
    delay=DELAY,
    cycle=None,
    pc=None,
    dest=DEST,
    physical=0x8FF0,
    code_physical=0x4FFC,
    changed=True,
    register=None,
    value=0,
    slot=None,
    sequence=None,
    code=None,
):
    pc = site + 8 * index if pc is None else pc
    cycle = CYCLE + 20 * index if cycle is None else cycle
    code = instruction(delay) if code is None else code
    internal = bytearray(own_internals(pc)).ljust(CPU + 1160, b"\0")
    struct.pack_into("<I", internal, 292, PLAN.crc)
    struct.pack_into("<Q", internal, CPU + 1088, cycle)
    registers = [0] * 32
    registers[2], registers[4], registers[5] = size, 7, dest
    registers[6], registers[16] = size if delay == 0 else 999, size
    registers[29], registers[31] = 0x300000, site + 8
    if register is not None:
        registers[register] = value
    for r, v in enumerate(registers):
        struct.pack_into("<I", internal, CPU + 16 * r, v)
    ram = bytearray(RAM_SIZE)
    ram[code_physical : code_physical + len(code)] = code
    data = bytes((i * 17 + index * changed) & 255 for i in range(size))
    ram[physical : physical + size] = data
    raw = own_archive(
        [(VERSION_MEMBER, VERSION), (INTERNALS_MEMBER, bytes(internal)), (RAM_MEMBER, bytes(ram))],
        zipfile.ZIP_DEFLATED,
    )
    points = []
    for i, (label, virtual, offset, payload) in enumerate(
        [("code", site, code_physical, code), ("destination", dest, physical, data)]
    ):
        seq = (1 + 2 * index if sequence is None else sequence) + i
        request = replace(
            PLAN.request,
            sequence=seq,
            expected_pc=pc,
            virtual_start=virtual,
            size=len(payload),
            expected_offset=offset,
        )
        context = replace(PLAN.context, sequence=seq, state_sha256=hashlib.sha256(raw).hexdigest())
        plan = replace(
            PLAN, request=request, context=context, slot=index + 1 if slot is None else slot
        )
        packet = bytearray(packed(request))
        for start in (61, 149):
            struct.pack_into("<Q", packet, start + 12, cycle)
        packet[237:] = payload
        points.append(SeriesPoint(label, plan, raw, (bytes(packet),) * 3))
    return tuple(points)


def run(before=None, after=None, **kwargs):
    return validate_call(
        pause() if before is None else before,
        pause(1) if after is None else after,
        kwargs.get("site", SITE),
        kwargs.get("code", instruction()),
        kwargs.get("target", TARGET),
    )


def swap(points, index, point):
    return points[:index] + (point,) + points[index + 1 :]


def packet_change(point, offset, fmt, value, one=False):
    packet = bytearray(point.packets[0])
    struct.pack_into("<" + fmt, packet, offset, value)
    return replace(
        point, packets=(bytes(packet),) + point.packets[1:] if one else (bytes(packet),) * 3
    )


@pytest.mark.parametrize(
    "size,delay,changed", [(1, 0, True), (32, DELAY, True), (4096, DELAY, False)]
)
def test_call_arguments_delay_and_complete_return(size, delay, changed):
    a, b = (pause(i, size=size, delay=delay, changed=changed) for i in (0, 1))
    result = run(a, b, code=instruction(delay))
    assert result == run(a, b, code=instruction(delay))
    assert result["requested_size"] == result["returned_size"] == size
    assert result["destination_unchanged"] == (not changed)
    assert result["code_and_destination_maps_checked"]
    assert not result["file_identity_verified"] and not result["disk_read_verified"]
    assert not result["live_acquisition_verified"] and result["read_events_produced"] == 0
    assert result["resource_links"] == result["capabilities"] == []
    assert result["points"][0]["pages"] == 2
    if size > 1:
        assert result["points"][1]["pages"] == 2
    public = json.dumps(result)
    assert all(k not in public for k in ['"pid"', '"pc"', '"cycle"', '"data"', '"virtual_start"'])
    assert "cpu=" not in repr(validate_pause(a))


@pytest.mark.parametrize("points", [None, [], (), (None,), (None,) * 9])
def test_pause_container(points):
    with rejects("PAUSE_POINTS"):
        validate_pause(points)


@pytest.mark.parametrize("label", [None, "", "../../private", "x" * 25, "code", 1])
def test_unique_bounded_labels(label):
    a = pause()
    with rejects("PAUSE_LABELS"):
        validate_pause(swap(a, 1, replace(a[1], label=label)))


@pytest.mark.parametrize(
    "field", ["pid", "crc", "serial", "slot", "environment", "process", "sequence"]
)
def test_same_pause_identity(field):
    a = pause()
    p = a[1]
    plan = p.plan
    if field in ("pid", "crc", "slot"):
        plan = replace(plan, **{field: getattr(plan, field) + 1})
    elif field == "serial":
        plan = replace(plan, serial="SLES-99999")
    elif field == "sequence":
        plan = replace(
            plan,
            request=replace(plan.request, sequence=10),
            context=replace(plan.context, sequence=10),
        )
    else:
        plan = replace(plan, context=replace(plan.context, **{field + "_sha256": "e" * 64}))
    with rejects("PAUSE_IDENTITY"):
        validate_pause(swap(a, 1, replace(p, plan=plan)))


@pytest.mark.parametrize(
    "variant",
    ["raw_type", "raw_changed", "hash", "packets_type", "packets_count", "changed", "data", "pid"],
)
def test_state_and_packet_binding(variant):
    a = pause()
    p = a[0]
    expected = {
        "raw_type": "PAUSE_STATE",
        "raw_changed": "PAUSE_STATE_HASH",
        "hash": "PAUSE_STATE_HASH",
        "packets_type": "PAUSE_PACKETS",
        "packets_count": "PAUSE_PACKETS",
        "changed": "PAUSE_CHANGED",
        "data": "PAUSE_DATA",
        "pid": "PAUSE_IDENTITY",
    }[variant]
    if variant == "raw_type":
        p = replace(p, state=None)
    elif variant == "raw_changed":
        p = replace(p, state=p.state + b"changed")
    elif variant == "hash":
        p = replace(p, plan=replace(p.plan, context=replace(p.plan.context, state_sha256="e" * 64)))
    elif variant == "packets_type":
        p = replace(p, packets=list(p.packets))
    elif variant == "packets_count":
        p = replace(p, packets=p.packets[:2])
    elif variant in ("changed", "data"):
        p = packet_change(p, 237, "B", p.packets[0][237] ^ 1, one=variant == "changed")
    else:
        p = packet_change(packet_change(p, 61, "Q", 43), 149, "Q", 43)
    with rejects(expected):
        validate_pause(swap(a, 0, p))


@pytest.mark.parametrize("variant", ["cycle", "host", "vmap", "alias", "page"])
def test_cpu_mapping_and_overlapping_pages(variant):
    if variant == "page":
        with rejects("PAUSE_PAGE"):
            validate_pause(pause(dest=SITE + 0x100))
        return
    a = pause()
    p = a[1]
    packet = bytearray(p.packets[0])
    for start in (61, 149):
        offsets = {"cycle": [12], "host": [20, 60, 76], "vmap": [28], "alias": [60, 76]}[variant]
        for off in offsets:
            v = struct.unpack_from("<Q", packet, start + off)[0]
            struct.pack_into("<Q", packet, start + off, v + (1 if variant == "cycle" else 4096))
    if variant == "alias":
        struct.pack_into("<II", packet, 53, p.plan.request.expected_offset + 4096, 0)
    expected = {
        "cycle": "PAUSE_CPU",
        "host": "PAUSE_BACKING",
        "vmap": "PAUSE_BACKING",
        "alias": "PAUSE_EXPECTED_BACKING",
    }[variant]
    with rejects(expected):
        validate_pause(swap(a, 1, replace(p, packets=(bytes(packet),) * 3)))


def test_later_region_must_reuse_identical_state():
    a = pause()
    with rejects("PAUSE_STATE_HASH"):
        validate_pause(swap(a, 1, replace(a[1], state=pause(1)[1].state)))


def test_one_and_eight_regions_and_first_excess():
    p = pause()[0]
    assert len(validate_pause((p,)).regions) == 1
    points = []
    for i in range(8):
        request = replace(p.plan.request, sequence=i + 1)
        plan = replace(p.plan, request=request, context=replace(p.plan.context, sequence=i + 1))
        packet = bytearray(p.packets[0])
        struct.pack_into("<I", packet, 29, i + 1)
        points.append(replace(p, label=chr(97 + i), plan=plan, packets=(bytes(packet),) * 3))
    assert len(validate_pause(tuple(points)).regions) == 8
    with rejects("PAUSE_POINTS"):
        validate_pause(tuple(points) + (p,))


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"site": True}, "CALL_SITE"),
        ({"site": -4}, "CALL_SITE"),
        ({"site": 2**32 - 8}, "CALL_SITE"),
        ({"target": True}, "CALL_TARGET"),
        ({"target": 2**32}, "CALL_TARGET"),
        ({"site": SITE + 1}, "CALL_ALIGNMENT"),
        ({"target": TARGET + 1}, "CALL_ALIGNMENT"),
        ({"code": None}, "CALL_CODE"),
        ({"code": bytes(4)}, "CALL_CODE"),
        ({"code": bytes(8)}, "CALL_CODE"),
        ({"code": bytes(12)}, "CALL_OPCODE"),
        ({"target": TARGET + 4}, "CALL_OPCODE"),
        ({"code": instruction(1)}, "CALL_DELAY"),
        ({"code": instruction(31 << 21 | 6 << 11 | 0x2D)}, "CALL_DELAY"),
    ],
)
def test_pinned_call_shape(kwargs, error):
    with rejects(error):
        run(**kwargs)


@pytest.mark.parametrize(
    "variant",
    [
        "labels",
        "sequence",
        "slot",
        "cycle_equal",
        "cycle_backwards",
        "cycle_over",
        "pc",
        "sp",
        "ra",
        "size",
        "destination",
        "short",
        "error",
        "mapping",
        "code",
    ],
)
def test_call_pair_rejections(variant):
    kwargs = {
        "sequence": {"sequence": 10},
        "slot": {"slot": 1},
        "cycle_equal": {"cycle": CYCLE},
        "cycle_backwards": {"cycle": CYCLE - 1},
        "cycle_over": {"cycle": CYCLE + MAX_CYCLES + 1},
        "pc": {"pc": SITE + 12},
        "sp": {"register": 29, "value": 0x300004},
        "ra": {"register": 31, "value": SITE + 12},
        "short": {"register": 2, "value": 31},
        "error": {"register": 2, "value": 0xFFFFFFFF},
        "mapping": {"physical": 0x9FF0},
        "code": {"code": instruction(0)},
    }.get(variant, {})
    a, b = pause(), pause(1, **kwargs)
    if variant == "labels":
        a = tuple(replace(p, label="other" if i == 0 else p.label) for i, p in enumerate(a))
    if variant == "size":
        a = pause(register=16, value=33)
    if variant == "destination":
        a = pause(register=5, value=DEST + 4)
    error = {
        "labels": "CALL_REGIONS",
        "sequence": "CALL_IDENTITY",
        "slot": "CALL_SLOT",
        "cycle_equal": "CALL_CYCLE",
        "cycle_backwards": "CALL_CYCLE",
        "cycle_over": "CALL_CYCLE",
        "pc": "CALL_PC",
        "sp": "CALL_FRAME",
        "ra": "CALL_FRAME",
        "size": "CALL_ARGUMENTS",
        "destination": "CALL_ARGUMENTS",
        "short": "CALL_SHORT_OR_ERROR",
        "error": "CALL_SHORT_OR_ERROR",
        "mapping": "CALL_BACKING",
        "code": "CALL_CODE",
    }[variant]
    with rejects(error):
        run(a, b)


def test_pair_process_mixing_and_exact_active_budget():
    b = tuple(
        replace(p, plan=replace(p.plan, context=replace(p.plan.context, process_sha256="f" * 64)))
        for p in pause(1)
    )
    with rejects("CALL_IDENTITY"):
        run(after=b)
    assert run(after=pause(1, cycle=CYCLE + MAX_CYCLES))["returned_size"] == 32


def test_zero_source_is_architectural_zero_not_stored_gpr_zero():
    delay = 6 << 11 | 0x2D
    a, b = pause(delay=delay, register=0, value=32), pause(1, delay=delay)
    with rejects("CALL_ARGUMENTS"):
        run(a, b, code=instruction(delay))


def test_return_instruction_on_next_page_requires_that_page():
    site = SITE - 4
    a, b = (pause(i, site=site, code_physical=0x4FF8) for i in (0, 1))
    assert run(a, b, site=site)["points"][0]["pages"] == 2
    p = a[0]
    packet = bytearray(p.packets[0])
    for start in (61, 149):
        struct.pack_into("<I", packet, start + 48, 1)
        packet[start + 68 : start + 84] = bytes(16)
    with rejects("MAPPING_COVERAGE"):
        run(swap(a, 0, replace(p, packets=(bytes(packet),) * 3)), b, site=site)
