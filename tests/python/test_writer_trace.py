"""RW03-RW08: independently constructed states and wire with overlapping stores."""

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
from test_writer_sites import CODE, START

from tools.inspectors import writer_trace
from tools.inspectors.observer_series import SeriesPoint
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE

BASE, PHYSICAL, LINK = 0x120000, 0x220000, START + 0x100
ZERO = bytes(16)
ONE = b"\x01\x02\x03\x04" + bytes(12)
TWO = b"\x05\x06\x07\x08" + bytes(12)


@lru_cache(maxsize=128)
def frame(
    label,
    index,
    pc,
    data=ZERO,
    value=0,
    equal=False,
    alias=0,
    cycle=None,
    code=CODE,
    bad_base=False,
    bad_return=False,
):
    cycle = CYCLE + index if cycle is None else cycle
    request = replace(
        PLAN.request,
        sequence=index + 1,
        expected_pc=pc,
        virtual_start=BASE,
        size=16,
        expected_offset=PHYSICAL,
    )
    internal = bytearray(own_internals(pc)).ljust(CPU + 1160, b"\0")
    struct.pack_into("<I", internal, 292, PLAN.crc)
    struct.pack_into("<Q", internal, CPU + 1088, cycle)
    struct.pack_into("<Q", internal, CPU + 4 * 16, BASE + bad_base)
    struct.pack_into("<Q", internal, CPU + 5 * 16, value)
    struct.pack_into("<Q", internal, CPU + 1 * 16, 1)
    struct.pack_into("<Q", internal, CPU + 2 * 16, 1 if equal else 2)
    struct.pack_into("<Q", internal, CPU + 31 * 16, LINK + bad_return * 4)
    packet = bytearray(packed(request, alias=alias))
    for start in [61, 149]:
        struct.pack_into("<Q", packet, start + 12, cycle)
    packet[237:] = data
    ram = bytearray(RAM_SIZE)
    ram[PHYSICAL + alias : PHYSICAL + alias + 16] = data
    ram[START : START + len(code)] = code
    state = own_archive(
        [(VERSION_MEMBER, VERSION), (INTERNALS_MEMBER, bytes(internal)), (RAM_MEMBER, bytes(ram))],
        zipfile.ZIP_DEFLATED,
    )
    context = replace(
        PLAN.context, sequence=index + 1, state_sha256=hashlib.sha256(state).hexdigest()
    )
    return SeriesPoint(
        label,
        replace(PLAN, request=request, context=context, slot=index + 1),
        state,
        (bytes(packet),) * 3,
    )


def trace(alias=0):
    return (
        frame("entry", 0, START, alias=alias),
        frame("before", 1, START + 4, value=0x04030201, equal=True, alias=alias),
        frame("after", 2, START + 8, ONE, value=0x04030201, equal=True, alias=alias),
        frame("before", 3, START + 8, ONE, value=0x04030201, equal=True, alias=alias),
        frame("after", 4, START + 4, ONE, value=0x04030201, equal=True, alias=alias),
        frame("before", 5, START + 4, ONE, value=0x08070605, alias=alias),
        frame("after", 6, START + 8, TWO, value=0x08070605, alias=alias),
        frame("before", 7, START + 8, TWO, value=0x08070605, alias=alias),
        frame("after", 8, START + 16, TWO, value=0x08070605, alias=alias),
        frame("returned", 9, LINK, TWO, alias=alias),
    )


def run(points):
    return writer_trace.reconcile_trace(points, START, CODE)


@pytest.mark.parametrize("alias", [0, 16])
def test_reconcile_changed_no_change_and_overwritten_values_incrementally(alias):
    value = run(iter(trace(alias)))
    assert value == run(iter(trace(alias)))
    assert value["pair_count"] == 4 and value["no_change_pairs"] == 2
    assert (
        value["entry_to_returned"]["different_bytes"] == 4 and value["unexplained_net_bytes"] == 0
    )
    assert value["reconstructed_sha256"] == hashlib.sha256(TWO).hexdigest()
    assert value["matches_expected_backing"] == (alias == 0)
    assert (
        not value["live_acquisition_verified"] and not value["unobserved_transient_writes_excluded"]
    )
    assert all(k not in json.dumps(value) for k in ['"pid"', '"pc"', '"crc"', '"vmap"', '"data"'])


@pytest.mark.parametrize(
    "kind,error",
    [
        ("none", "TRACE_POINTS"),
        ("empty", "TRACE_INCOMPLETE"),
        ("point", "TRACE_ORDER"),
        ("plan", "TRACE_POINT"),
        ("hash", "TRACE_STATE_HASH"),
        ("packets", "TRACE_PACKETS"),
        ("packet_changed", "TRACE_CHANGED"),
        ("pid", "TRACE_IDENTITY"),
        ("state_cycle", "TRACE_STATE"),
        ("code", "TRACE_CODE"),
        ("entry", "TRACE_ENTRY"),
        ("base", "TRACE_BASE"),
        ("identity", "TRACE_IDENTITY"),
        ("sequence", "TRACE_IDENTITY"),
        ("slot", "TRACE_SLOT"),
        ("mapping", "TRACE_BACKING"),
        ("cycle", "TRACE_CYCLE"),
        ("site", "TRACE_SITE"),
        ("gap", "TRACE_GAP"),
        ("after_label", "TRACE_ORDER"),
        ("effect", "WRITER_EFFECT"),
        ("register", "WRITER_STEP"),
        ("missing_after", "TRACE_ORDER"),
        ("missing_return", "TRACE_INCOMPLETE"),
        ("early_return", "TRACE_ORDER"),
        ("return_pc", "TRACE_RETURN"),
        ("return_gap", "TRACE_RETURN_GAP"),
        ("extra", "TRACE_ORDER"),
    ],
)
def test_reject_incomplete_inconsistent_or_unexplained_trace(kind, error):
    points = list(trace())
    p = points[1]
    if kind == "none":
        points = None
    elif kind == "empty":
        points = []
    elif kind == "point":
        points[1] = None
    elif kind == "plan":
        points[1] = replace(p, plan=None)
    elif kind == "hash":
        points[1] = replace(p, state=p.state + b"x")
    elif kind == "packets":
        points[1] = replace(p, packets=p.packets[:2])
    elif kind in ["packet_changed", "state_cycle"]:
        packet = bytearray(p.packets[0])
        if kind == "packet_changed":
            packet[-1] ^= 1
            packets = (bytes(packet),) + p.packets[1:]
        else:
            for start in [61, 149]:
                struct.pack_into("<Q", packet, start + 12, CYCLE + 20)
            packets = (bytes(packet),) * 3
        points[1] = replace(p, packets=packets)
    elif kind == "pid":
        points[1] = replace(p, plan=replace(p.plan, pid=99))
    elif kind == "code":
        points[1] = frame("before", 1, START + 4, code=bytes(4) + CODE[4:-4] + b"xxxx")
    elif kind == "entry":
        points[0] = replace(points[0], label="before")
    elif kind == "base":
        points[0] = frame("entry", 0, START, bad_base=True)
    elif kind == "identity":
        points[1] = replace(p, plan=replace(p.plan, serial="SLES-99999"))
    elif kind == "sequence":
        points[1] = frame("before", 20, START + 4)
    elif kind == "slot":
        points[1] = replace(p, plan=replace(p.plan, slot=1))
    elif kind == "mapping":
        points[1] = frame("before", 1, START + 4, alias=16)
    elif kind == "cycle":
        points[1] = frame("before", 1, START + 4, cycle=CYCLE)
    elif kind == "site":
        points[1] = frame("before", 1, START + 16)
    elif kind == "gap":
        points[1] = frame("before", 1, START + 4, ONE)
    elif kind == "after_label":
        points[2] = replace(points[2], label="before")
    elif kind == "effect":
        points[2] = frame("after", 2, START + 8, TWO, value=0x04030201, equal=True)
    elif kind == "register":
        points[2] = frame("after", 2, START + 8, ONE, value=0x04030201)
    elif kind == "missing_after":
        points[2] = frame("returned", 2, LINK, ONE)
    elif kind == "missing_return":
        points.pop()
    elif kind == "early_return":
        points[1] = frame("returned", 1, LINK)
    elif kind == "return_pc":
        points[-1] = frame("returned", 9, LINK + 4, TWO)
    elif kind == "return_gap":
        points[-1] = frame("returned", 9, LINK, ONE)
    elif kind == "extra":
        points.append(points[-1])
    with rejects(error):
        run(points)


def test_bounded_iterator_stops_before_decoding_excess_point(monkeypatch):
    monkeypatch.setattr(writer_trace, "MAX_PAIRS", 1)
    points = list(trace())
    points[4] = None
    with rejects("TRACE_BUDGET"):
        run(iter(points))


def test_active_cycle_budget_and_inclusive_boundary():
    points = list(trace())
    points[-1] = frame("returned", 9, LINK, TWO, cycle=CYCLE + writer_trace.MAX_ACTIVE_CYCLES)
    assert run(points)["pair_count"] == 4
    points[-1] = frame("returned", 9, LINK, TWO, cycle=CYCLE + writer_trace.MAX_ACTIVE_CYCLES + 1)
    with rejects("TRACE_ACTIVE_BUDGET"):
        run(points)
