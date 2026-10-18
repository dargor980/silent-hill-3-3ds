"""OS01-OS05 with independent synthetic state/wire values, no emulator assets."""

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

from tools.inspectors.observer_series import LABELS, SeriesPoint, validate_series
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE


@lru_cache(maxsize=16)
def point(index, alias=0, cycle=None, bad_base=False, bad_return=False):
    request = replace(PLAN.request, sequence=index + 3, expected_pc=0x100000 + index * 16)
    cycle = CYCLE + index if cycle is None else cycle
    internal = bytearray(own_internals(request.expected_pc)).ljust(CPU + 1160, b"\0")
    struct.pack_into("<I", internal, 292, PLAN.crc)
    entry_base = request.virtual_start if index != 3 else 0x55555555
    struct.pack_into("<I", internal, CPU + 4 * 16, entry_base + bad_base)
    struct.pack_into("<I", internal, CPU + 31 * 16, 0x100030 + 4 * bad_return)
    struct.pack_into("<Q", internal, CPU + 1088, cycle)
    packet = bytearray(packed(request, alias=alias))
    for start in [61, 149]:
        struct.pack_into("<Q", packet, start + 12, cycle)
    if index >= 2:
        packet[-1] ^= 1
    ram = bytearray(RAM_SIZE)
    offset = request.expected_offset + alias
    ram[offset : offset + request.size] = packet[237:]
    state = own_archive(
        [(VERSION_MEMBER, VERSION), (INTERNALS_MEMBER, bytes(internal)), (RAM_MEMBER, bytes(ram))],
        zipfile.ZIP_DEFLATED,
    )
    context = replace(
        PLAN.context, sequence=request.sequence, state_sha256=hashlib.sha256(state).hexdigest()
    )
    plan = replace(PLAN, request=request, context=context, slot=index + 1)
    return SeriesPoint(LABELS[index], plan, state, (bytes(packet),) * 3)


def series(**kwargs):
    return tuple(point(i, **kwargs) for i in range(4))


def swap(points, index, changed):
    return points[:index] + (changed,) + points[index + 1 :]


@pytest.mark.parametrize("alias", [0, 16])
def test_consistent_series_deterministic_differences_and_alias(alias):
    result = validate_series(series(alias=alias))
    assert result == validate_series(series(alias=alias))
    assert result["backing_continuous"] and result["matches_expected_backing"] == (alias == 0)
    assert result["entry_to_before"]["equal"]
    assert result["before_to_after"]["difference_ranges"] == [{"start": 31, "end": 32}]
    assert result["entry_to_returned"]["different_bytes"] == 1
    assert not result["live_acquisition_verified"] and result["resource_links"] == []
    encoded = json.dumps(result)
    assert all(
        key not in encoded for key in ['"pid"', '"pc"', '"crc"', '"cycle"', '"ee_main"', '"data"']
    )
    assert "state=" not in repr(point(0))


@pytest.mark.parametrize("points", [(), None, [], (None,) * 4])
def test_invalid_point_container(points):
    with rejects("SERIES_POINTS"):
        validate_series(points)


def test_wrong_labels_and_order():
    points = series()
    with rejects("SERIES_ORDER"):
        validate_series(points[::-1])


@pytest.mark.parametrize(
    "field",
    [
        "pid",
        "crc",
        "serial",
        "slot",
        "session",
        "environment",
        "process",
        "sequence",
        "base",
        "size",
        "offset",
    ],
)
def test_mixed_identity_or_range(field):
    points = series()
    p = points[1]
    plan = p.plan
    if field in ["pid", "crc", "slot"]:
        plan = replace(plan, **{field: 1 if field == "slot" else getattr(plan, field) + 1})
    elif field == "serial":
        plan = replace(plan, serial="SLES-99999")
    elif field == "session":
        plan = replace(
            plan,
            context=replace(plan.context, session_id="ab" * 16),
            request=replace(plan.request, session_id="ab" * 16),
        )
    elif field in ["environment", "process"]:
        plan = replace(plan, context=replace(plan.context, **{field + "_sha256": "d" * 64}))
    elif field == "sequence":
        plan = replace(
            plan,
            context=replace(plan.context, sequence=10),
            request=replace(plan.request, sequence=10),
        )
    else:
        name = {"base": "virtual_start", "size": "size", "offset": "expected_offset"}[field]
        plan = replace(
            plan, request=replace(plan.request, **{name: getattr(plan.request, name) + 1})
        )
    with rejects("SERIES_IDENTITY"):
        validate_series(swap(points, 1, replace(p, plan=plan)))


@pytest.mark.parametrize(
    "variant", ["state_type", "hash", "packet_count", "changed", "pid", "state_cycle"]
)
def test_replay_rejects_unbound_or_changed_point(variant):
    points = series()
    p = points[1]
    expected = {
        "state_type": "SERIES_STATE",
        "hash": "SERIES_STATE_HASH",
        "packet_count": "SERIES_PACKETS",
        "changed": "SERIES_CHANGED",
        "pid": "SERIES_IDENTITY",
        "state_cycle": "SERIES_STATE",
    }[variant]
    if variant == "state_type":
        p = replace(p, state=None)
    elif variant == "hash":
        p = replace(p, state=p.state + b"x")
    elif variant == "packet_count":
        p = replace(p, packets=p.packets[:2])
    else:
        packet = bytearray(p.packets[0])
        if variant == "changed":
            packet[-1] ^= 1
        else:
            for start in [61, 149]:
                struct.pack_into(
                    "<Q",
                    packet,
                    start + (12 if variant == "state_cycle" else 0),
                    CYCLE + 10 if variant == "state_cycle" else 99,
                )
        p = replace(
            p,
            packets=(bytes(packet),) + p.packets[1:]
            if variant == "changed"
            else (bytes(packet),) * 3,
        )
    with rejects(expected):
        validate_series(swap(points, 1, p))


@pytest.mark.parametrize("variant", ["mapping", "cycle_equal", "cycle_backwards", "base", "return"])
def test_cross_stop_continuity_and_register_checks(variant):
    points = series()
    index = 0 if variant in ["base", "return"] else 1
    kwargs = {
        "mapping": {"alias": 16},
        "cycle_equal": {"cycle": CYCLE},
        "cycle_backwards": {"cycle": CYCLE - 1},
        "base": {"bad_base": True},
        "return": {"bad_return": True},
    }[variant]
    expected = {
        "mapping": "SERIES_BACKING",
        "cycle_equal": "SERIES_CYCLE",
        "cycle_backwards": "SERIES_CYCLE",
        "base": "SERIES_BASE",
        "return": "SERIES_RETURN",
    }[variant]
    with rejects(expected):
        validate_series(swap(points, index, point(index, **kwargs)))


@pytest.mark.parametrize("field", ["ee_main", "vmap"])
def test_host_anchor_changes_rejected_even_with_same_physical_offset(field):
    points = series()
    p = points[1]
    packet = bytearray(p.packets[0])
    for start in [61, 149]:
        offsets = [20, 60, 76] if field == "ee_main" else [28]
        for offset in offsets:
            previous = struct.unpack_from("<Q", packet, start + offset)[0]
            struct.pack_into("<Q", packet, start + offset, previous + 4096)
    with rejects("SERIES_BACKING"):
        validate_series(swap(points, 1, replace(p, packets=(bytes(packet),) * 3)))
