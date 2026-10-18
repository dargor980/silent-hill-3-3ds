"""Own table, generation and mapped-state fixtures for DA02-04."""

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

from tools.inspectors.archive_descriptor import inspect_descriptor, reconcile_descriptors
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.observer_series import SeriesPoint
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE

TOKEN, OFFSET, SIZE = 35, 8192, 1536


@lru_cache(maxsize=48)
def points(
    index=0,
    *,
    count=16,
    base=0x8000,
    row_index=3,
    generation=2,
    underlying=7,
    offset=OFFSET,
    size=SIZE,
    table_cut=12,
    row_cut=16,
    physical=0xA030,
    cycle=None,
    sequence=None,
    slot=None,
    root=0x40000,
):
    cycle = CYCLE + index if cycle is None else cycle
    pc = 0x100000 + 4 * index
    table = struct.pack("<3I", count, root, base)[:table_cut]
    row = struct.pack("<4I", underlying, generation, offset, size)[:row_cut]
    ram = bytearray(RAM_SIZE)
    ram[0x7000 : 0x7000 + len(table)] = table
    ram[physical : physical + len(row)] = row
    internal = bytearray(own_internals(pc)).ljust(CPU + 1160, b"\0")
    struct.pack_into("<I", internal, 292, PLAN.crc)
    struct.pack_into("<Q", internal, CPU + 1088, cycle)
    raw = own_archive(
        [(VERSION_MEMBER, VERSION), (INTERNALS_MEMBER, bytes(internal)), (RAM_MEMBER, bytes(ram))],
        zipfile.ZIP_DEFLATED,
    )
    result = []
    for i, (label, virtual, backing, data) in enumerate(
        [("table", 0x3000, 0x7000, table), ("descriptor", base + 16 * row_index, physical, row)]
    ):
        seq = (1 + 2 * index if sequence is None else sequence) + i
        request = replace(
            PLAN.request,
            expected_pc=pc,
            sequence=seq,
            virtual_start=virtual,
            size=len(data),
            expected_offset=backing,
        )
        context = replace(PLAN.context, sequence=seq, state_sha256=hashlib.sha256(raw).hexdigest())
        packet = bytearray(packed(request))
        for start in (61, 149):
            struct.pack_into("<Q", packet, start + 12, cycle)
        packet[237:] = data
        plan = replace(
            PLAN, request=request, context=context, slot=index + 1 if slot is None else slot
        )
        result.append(SeriesPoint(label, plan, raw, (bytes(packet),) * 3))
    return tuple(result)


def run(a=None, b=None, token=TOKEN, offset=OFFSET, size=SIZE):
    return reconcile_descriptors(
        points() if a is None else a, points(1) if b is None else b, token, offset, size
    )


@pytest.mark.parametrize(
    "count,index,generation", [(2, 1, 1), (3, 2, 2), (16, 3, 2), (255, 254, 3), (256, 255, 1)]
)
def test_capacity_generation_and_unmodified_pair(count, index, generation):
    token = generation * (1 << (count - 1).bit_length()) + index
    a, b = (points(i, count=count, row_index=index, generation=generation) for i in (0, 1))
    result = run(a, b, token=token)
    assert result == run(a, b, token=token)
    assert result["candidate_size"] == SIZE and result["read_events_produced"] == 0
    assert not any(
        result[k]
        for k in [
            "file_identity_verified",
            "open_observed",
            "code_checked",
            "disk_read_verified",
            "live_acquisition_verified",
        ]
    )
    assert result["resource_links"] == result["capabilities"] == []
    assert all(k not in json.dumps(result) for k in ['"token"', '"base"', '"generation"', '"row"'])
    assert "table=" not in repr(inspect_descriptor(a, token, OFFSET, SIZE))


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"token": True}, "DESCRIPTOR_TOKEN"),
        ({"token": -1}, "DESCRIPTOR_TOKEN"),
        ({"token": 2**31}, "DESCRIPTOR_TOKEN"),
        ({"offset": -1}, "DESCRIPTOR_RANGE"),
        ({"offset": True}, "DESCRIPTOR_RANGE"),
        ({"size": 0}, "DESCRIPTOR_RANGE"),
        ({"size": True}, "DESCRIPTOR_RANGE"),
        ({"size": 2**31 - OFFSET}, "DESCRIPTOR_RANGE"),
    ],
)
def test_scalar_inputs(kwargs, error):
    with rejects(error):
        run(**kwargs)


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"count": 0}, "DESCRIPTOR_CAPACITY"),
        ({"count": 1}, "DESCRIPTOR_CAPACITY"),
        ({"count": 257}, "DESCRIPTOR_CAPACITY"),
        ({"table_cut": 11}, "DESCRIPTOR_LAYOUT"),
        ({"row_cut": 15}, "DESCRIPTOR_LAYOUT"),
        ({"base": 0}, "DESCRIPTOR_TABLE"),
        ({"base": 0x8001}, "DESCRIPTOR_TABLE"),
        ({"base": 0xFFFFFFF0, "row_index": 0}, "DESCRIPTOR_TABLE"),
        ({"count": 3}, "DESCRIPTOR_TABLE"),
        ({"row_index": 4}, "DESCRIPTOR_ROW"),
        ({"underlying": 0xFFFFFFFF}, "DESCRIPTOR_CLOSED_OR_RESERVED"),
        ({"underlying": 0xFFFFFFFE}, "DESCRIPTOR_CLOSED_OR_RESERVED"),
        ({"underlying": 0x80000000}, "DESCRIPTOR_CLOSED_OR_RESERVED"),
        ({"generation": 0}, "DESCRIPTOR_GENERATION"),
        ({"generation": 3}, "DESCRIPTOR_GENERATION"),
        ({"generation": 0x10000002}, "DESCRIPTOR_GENERATION"),
        ({"offset": OFFSET + 1}, "DESCRIPTOR_RANGE"),
        ({"size": SIZE - 1}, "DESCRIPTOR_RANGE"),
        ({"offset": 0xFFFFFFFF}, "DESCRIPTOR_RANGE"),
        ({"size": 0}, "DESCRIPTOR_RANGE"),
    ],
)
def test_layout_lifecycle_and_range(kwargs, error):
    with rejects(error):
        run(a=points(**kwargs))


def test_labels_are_not_a_success_flag():
    a = points()
    a = (replace(a[0], label="other"), a[1])
    with rejects("DESCRIPTOR_REGIONS"):
        run(a=a)


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"sequence": 10}, "DESCRIPTOR_IDENTITY"),
        ({"slot": 1}, "DESCRIPTOR_SLOT"),
        ({"cycle": CYCLE}, "DESCRIPTOR_CYCLE"),
        ({"cycle": CYCLE - 1}, "DESCRIPTOR_CYCLE"),
        ({"cycle": CYCLE + MAX_CYCLES + 1}, "DESCRIPTOR_CYCLE"),
        ({"underlying": 8}, "DESCRIPTOR_CHANGED"),
        ({"root": 0x40010}, "DESCRIPTOR_CHANGED"),
        ({"physical": 0xB030}, "DESCRIPTOR_BACKING"),
    ],
)
def test_pair_continuity(kwargs, error):
    with rejects(error):
        run(b=points(1, **kwargs))


def test_process_mixing_and_exact_cycle_budget():
    b = tuple(
        replace(p, plan=replace(p.plan, context=replace(p.plan.context, process_sha256="e" * 64)))
        for p in points(1)
    )
    with rejects("DESCRIPTOR_IDENTITY"):
        run(b=b)
    assert run(b=points(1, cycle=CYCLE + MAX_CYCLES))["candidate_size"] == SIZE


def test_reused_index_requires_new_generation_token():
    new = points(1, generation=3)
    with rejects("DESCRIPTOR_GENERATION"):
        inspect_descriptor(new, TOKEN, OFFSET, SIZE)
    assert (
        inspect_descriptor(new, 51, OFFSET, SIZE).row
        != inspect_descriptor(points(), TOKEN, OFFSET, SIZE).row
    )
