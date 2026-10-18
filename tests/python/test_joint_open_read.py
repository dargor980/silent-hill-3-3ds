"""Own combined catalog/pool/copy fixtures; no original game data or code."""

import hashlib
import json
import struct
import zipfile
from dataclasses import replace
from functools import lru_cache

import pytest
from test_buffer_copy import PROFILE as COPY
from test_buffer_copy import REQUEST, SECTOR_HASH, SOURCE
from test_buffer_copy import pause as cp_pause
from test_catalog_open import PROFILE as CA_PROFILE
from test_catalog_open import SOURCE as CA_SOURCE
from test_catalog_open import pause as ca_pause
from test_driver_transfer import BUFFER, DEST, OBJECT, POOL, ROOT
from test_observer_acquisition import CYCLE, PLAN, rejects
from test_observer_capture import packed
from test_pcsx2_state import CPU, own_archive

from tools.inspectors.joint_open_read import reconcile_joint_open_read
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.observer_series import SeriesPoint
from tools.inspectors.pcsx2_state import (
    INTERNALS_MEMBER,
    VERSION,
    VERSION_MEMBER,
    read_state_members,
)
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE

SHIFT = 0x300000
SEQUENCES = (1, 8, 13, 18, 26, 34, 42, 50, 58, 66, 74)
CATALOG = replace(CA_SOURCE, resource_sha256=SOURCE.resource_sha256)
wrapper = bytearray(CA_PROFILE.wrapper.data)
struct.pack_into("<I", wrapper, 0xB4, 3 << 26 | ((CA_PROFILE.target + SHIFT) >> 2))
OPENING = replace(
    CA_PROFILE,
    resolver=replace(CA_PROFILE.resolver, address=CA_PROFILE.resolver.address + SHIFT),
    wrapper=replace(
        CA_PROFILE.wrapper, address=CA_PROFILE.wrapper.address + SHIFT, data=bytes(wrapper)
    ),
    selected_pc=CA_PROFILE.selected_pc + SHIFT,
    open_pc=CA_PROFILE.open_pc + SHIFT,
    completed_pc=CA_PROFILE.completed_pc + SHIFT,
    target=CA_PROFILE.target + SHIFT,
    config_address=CA_PROFILE.config_address + SHIFT,
)


@lru_cache(maxsize=96)
def pause(
    index,
    *,
    words=(),
    values=(),
    addresses=(),
    physical=(),
    registers=(),
    sequence=None,
    slot=None,
    cycle=None,
    session=PLAN.request.session_id,
    host_shift=0,
):
    seq = SEQUENCES[index] if sequence is None else sequence
    slot = index + 1 if slot is None else slot
    cycle = CYCLE + index + 1 if cycle is None else cycle
    if index >= 4:
        points = cp_pause(
            index - 4,
            words=words,
            values=values,
            addresses=addresses,
            physical=physical,
            registers=registers,
            sequence=seq,
            slot=slot,
            cycle=cycle,
            session=session,
        )
    else:
        seed = ca_pause(index)
        pc = seed[0].plan.request.expected_pc + SHIFT
        loc = {p.label: p.plan.request.virtual_start + SHIFT for p in seed}
        data = {p.label: p.packets[0][237:] for p in seed}
        data["code"] = OPENING.resolver.data if index == 0 else OPENING.wrapper.data
        for label, fields in (("config", (1, 2)), ("directory", (1,)), ("record", (0, 1))):
            if label in data:
                raw = bytearray(data[label])
                for word in fields:
                    at = word * 4
                    struct.pack_into("<I", raw, at, struct.unpack_from("<I", raw, at)[0] + SHIFT)
                data[label] = bytes(raw)
        if index == 3:
            driver = cp_pause(0)
            block = bytearray(24 + 48 * 16)
            block[:24] = driver[1].packets[0][237:]
            block[OBJECT - POOL : OBJECT - POOL + 48] = driver[2].packets[0][237:]
            for label, point in (("driver_root", driver[0]), ("driver_vtable", driver[3])):
                data[label] = point.packets[0][237:]
                loc[label] = point.plan.request.virtual_start
            data["driver_pool"] = bytes(block)
            loc["driver_pool"] = POOL
            labels = (*data.keys(),)
            data = {
                label: data[label]
                for label in (*labels[:5], "driver_root", "driver_pool", "driver_vtable")
            }
        for label, word, value in words:
            raw = bytearray(data[label])
            struct.pack_into("<I", raw, word * 4, value)
            data[label] = bytes(raw)
        data.update(values)
        loc.update(addresses)
        (raw_internal,) = read_state_members(seed[0].state, ((INTERNALS_MEMBER, 1024 * 1024),))
        internal = bytearray(raw_internal)
        struct.pack_into("<I", internal, CPU + 680, pc)
        struct.pack_into("<Q", internal, CPU + 1088, cycle)
        for reg in range(32):
            at = CPU + 16 * reg
            value = struct.unpack_from("<I", internal, at)[0]
            if 0x100000 <= value < 0x240000:
                struct.pack_into("<I", internal, at, value + SHIFT)
        for reg, value in registers:
            struct.pack_into("<I", internal, CPU + 16 * reg, value)
        ram = bytearray(RAM_SIZE)
        backing = dict(physical)
        for label, raw in data.items():
            at = backing.get(label, loc[label])
            ram[at : at + len(raw)] = raw
        state = own_archive(
            [
                (VERSION_MEMBER, VERSION),
                (INTERNALS_MEMBER, bytes(internal)),
                (RAM_MEMBER, bytes(ram)),
            ],
            zipfile.ZIP_DEFLATED,
        )
        points = []
        for i, (label, raw) in enumerate(data.items()):
            request = replace(
                PLAN.request,
                session_id=session,
                sequence=seq + i,
                expected_pc=pc,
                virtual_start=loc[label],
                size=len(raw),
                expected_offset=backing.get(label, loc[label]),
            )
            context = replace(
                PLAN.context,
                session_id=session,
                sequence=seq + i,
                state_sha256=hashlib.sha256(state).hexdigest(),
            )
            plan = replace(PLAN, request=request, context=context, slot=slot)
            packet = bytearray(packed(request))
            for start in (61, 149):
                struct.pack_into("<Q", packet, start + 12, cycle)
            packet[237:] = raw
            points.append(SeriesPoint(label, plan, state, (bytes(packet),) * 3))
    if host_shift:
        moved = []
        for point in points:
            packet = bytearray(point.packets[0])
            for start in (61, 149):
                for at in (start + 20, start + 60):
                    struct.pack_into(
                        "<Q", packet, at, struct.unpack_from("<Q", packet, at)[0] + host_shift
                    )
                if struct.unpack_from("<I", packet, start + 48)[0] == 2:
                    at = start + 76
                    struct.pack_into(
                        "<Q", packet, at, struct.unpack_from("<Q", packet, at)[0] + host_shift
                    )
            moved.append(replace(point, packets=(bytes(packet),) * 3))
        points = moved
    return tuple(points)


def run(
    *,
    catalog=CATALOG,
    opening=OPENING,
    source=SOURCE,
    request=REQUEST,
    copy=COPY,
    sector_sha256=SECTOR_HASH,
    stages=None,
    **kwargs,
):
    return reconcile_joint_open_read(
        catalog,
        opening,
        source,
        request,
        copy,
        sector_sha256,
        tuple(pause(i) for i in range(11)) if stages is None else stages,
        **kwargs,
    )


def changed(index, **kwargs):
    return tuple(pause(i, **kwargs) if i == index else pause(i) for i in range(11))


def test_default_fails_closed_even_when_all_endpoints_match():
    with rejects("JOINT_LIFETIME_UNPROVEN"):
        run()


def test_explicit_diagnostic_preserves_original_81_observations():
    stages = tuple(pause(i) for i in range(11))
    result = run(stages=stages, require_continuity=False)
    assert result == run(require_continuity=False)
    assert result["joint_catalog_open_copy_consistent"]
    assert result["catalog_entry_and_open_consistent"]
    assert result["copy_and_driver_return_consistent"]
    assert result["post_open_position_and_generation_consistent"]
    assert (
        result["read_events_produced"] == 0
        and result["resource_links"] == result["capabilities"] == []
    )
    assert [p["sequence"] for p in result["points"]] == list(range(1, 82))
    assert len({p["state_sha256"] for p in result["points"]}) == 11
    for metadata, point in zip(
        result["points"], (p for pause in stages for p in pause), strict=True
    ):
        assert metadata["packet_sha256"] == [hashlib.sha256(p).hexdigest() for p in point.packets]
    for key in (
        "continuous_lifetime_verified",
        "source_anchor_reverified",
        "profile_semantics_authenticated",
        "opening_observed",
        "live_acquisition_verified",
        "disk_read_verified",
        "buffer_fill_verified",
        "inner_copy_verified",
        "discovery_budget_included",
        "file_identity_verified",
    ):
        assert result[key] is False
    assert result["execution_authentication"] == "not_provided"
    encoded = json.dumps(result)
    assert all(
        text not in encoded for text in ("own.bin", "pack.dat", '"pc":', '"pid":', '"address":')
    )


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"catalog": None}, "CATALOG_INPUT"),
        ({"copy": None}, "COPY_INPUT"),
        ({"source": None}, "BACKEND_INPUT"),
        ({"request": None}, "BACKEND_INPUT"),
        ({"require_continuity": 0}, "JOINT_POLICY"),
        ({"require_continuity": None}, "JOINT_POLICY"),
        ({"stages": ()}, "JOINT_STAGES"),
        ({"stages": [()] * 11}, "JOINT_STAGES"),
        ({"stages": ((),) * 10}, "JOINT_STAGES"),
    ],
)
def test_input_rejections(kwargs, error):
    with rejects(error):
        run(**kwargs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("container_sha256", "d" * 64),
        ("resource_sha256", "e" * 64),
        ("file_size", SOURCE.file_size + 1),
        ("offset", SOURCE.offset + 1),
        ("size", SOURCE.size + 1),
    ],
)
def test_cross_source_mismatch(field, value):
    with rejects("JOINT_SOURCE"):
        run(catalog=replace(CATALOG, **{field: value}))


@pytest.mark.parametrize(
    "index,kwargs,error",
    [
        (4, {"slot": 4}, "JOINT_SLOTS"),
        (4, {"sequence": 23}, "JOINT_IDENTITY"),
        (4, {"session": "02" * 16}, "JOINT_IDENTITY"),
        (4, {"cycle": CYCLE + 4}, "JOINT_CYCLE"),
        (10, {"cycle": CYCLE + MAX_CYCLES + 5}, "JOINT_CYCLE"),
        (4, {"host_shift": 4096}, "JOINT_BACKING"),
        (3, {"physical": (("driver_root", ROOT + 4096),)}, "JOINT_PAGE"),
        (3, {"addresses": (("driver_root", ROOT + 4),)}, "JOINT_DRIVER_BACKING"),
        (3, {"values": (("driver_root", struct.pack("<I", POOL + 16)),)}, "JOINT_DRIVER_CHANGED"),
        (3, {"words": (("driver_vtable", 1, 123),)}, "JOINT_DRIVER_CHANGED"),
        (3, {"values": (("driver_pool", bytes(24)),)}, "JOINT_POOL_SIZE"),
        (3, {"addresses": (("driver_pool", POOL + 16),)}, "JOINT_POOL_BACKING"),
        (3, {"words": (("driver_pool", 0, 9),)}, "JOINT_POOL_CHANGED"),
        (3, {"words": (("driver_pool", (OBJECT - POOL) // 4, 9),)}, "JOINT_POOL_CHANGED"),
        (3, {"words": (("driver_pool", (OBJECT - POOL) // 4 + 8, 0),)}, "JOINT_POOL_CHANGED"),
        (3, {"words": (("driver_pool", (OBJECT - POOL) // 4 + 11, 4),)}, "JOINT_POOL_CHANGED"),
        (0, {"registers": ((9, 123),)}, "CATALOG_SELECTION"),
        (9, {"registers": ((2, 32),)}, "COPY_ABI"),
    ],
)
def test_joint_rejections(index, kwargs, error):
    with rejects(error):
        run(stages=changed(index, **kwargs), require_continuity=False)


def test_final_open_regions_must_include_pool_block():
    stages = list(pause(i) for i in range(11))
    stages[3] = stages[3][:5]
    with rejects("JOINT_REGIONS"):
        run(stages=tuple(stages))


def test_foreign_handle_consistent_with_its_catalog_still_rejected():
    stages = []
    for i in range(11):
        kwargs = {"registers": ((2, 8),)} if i == 2 else {}
        if i == 3:
            kwargs = {"registers": ((16, 8),), "words": (("descriptor", 0, 8),)}
        stages.append(pause(i, **kwargs))
    with rejects("JOINT_HANDLE"):
        run(stages=tuple(stages))


@pytest.mark.parametrize("word,value", [(5, 1), (9, 123), (11, 3)])
def test_consistent_but_not_initial_object_rejected(word, value):
    stages = []
    for i in range(11):
        changes = ()
        if i == 3:
            changes = (("driver_pool", (OBJECT - POOL) // 4 + word, value),)
        elif i >= 4 and (word != 11 or i < 8):
            changes = (("object" if i in (4, 10) else "driver", word, value),)
        stages.append(pause(i, words=changes))
    with rejects("JOINT_INITIAL"):
        run(stages=tuple(stages))


@pytest.mark.parametrize("target", [DEST, BUFFER])
def test_copy_targets_cannot_alias_prior_catalog_controls(target):
    # Relocate only the catalog query physically, with coherent own packets/RAM.
    query = ca_pause(0)[-1].plan.request.virtual_start + SHIFT
    stages = tuple(
        pause(i, physical=(("request", target),)) if i == 0 else pause(i) for i in range(11)
    )
    assert query != target
    with rejects("JOINT_OVERLAP"):
        run(stages=stages)


def test_other_pool_rows_need_not_remain_equal():
    result = run(stages=changed(3, words=(("driver_pool", 6, 123),)), require_continuity=False)
    assert result["joint_catalog_open_copy_consistent"]


def test_global_sequence_and_cycle_boundaries():
    stages = tuple(
        pause(i, sequence=SEQUENCES[i] + 175, cycle=CYCLE + 1 + MAX_CYCLES if i == 10 else None)
        for i in range(11)
    )
    assert run(stages=stages, require_continuity=False)["points"][-1]["sequence"] == 256
    with pytest.raises(ValueError):
        run(stages=tuple(pause(i, sequence=SEQUENCES[i] + 176) for i in range(11)))


def test_raw_state_from_a_different_pause_is_not_repaired():
    stages = list(pause(i) for i in range(11))
    stages[3] = stages[3][:5] + tuple(replace(p, state=pause(2)[0].state) for p in stages[3][5:])
    with rejects("PAUSE_STATE_HASH"):
        run(stages=tuple(stages))


@pytest.mark.parametrize("count", [84, 85])
def test_full_pool_observation_size_boundary(count):
    original = pause(3)[6].packets[0][237:]
    block = bytearray(original).ljust(24 + 48 * count, b"\0")
    struct.pack_into("<I", block, 12, count)
    stages = tuple(
        pause(i, values=(("driver_pool", bytes(block)),))
        if i == 3
        else pause(i, words=(("pool", 3, count),))
        if i in (4, 10)
        else pause(i)
        for i in range(11)
    )
    if count == 84:
        assert run(stages=stages, require_continuity=False)["joint_catalog_open_copy_consistent"]
    else:
        with pytest.raises(ValueError):
            run(stages=stages, require_continuity=False)


def test_async_flag_matches_open_and_all_driver_observations():
    stages = []
    for i in range(11):
        registers = ((18, 0x2001),) if 1 <= i <= 3 else ()
        words = ()
        if i == 3:
            words = (("driver_pool", (OBJECT - POOL) // 4 + 5, 1),)
        elif i >= 4:
            words = (("object" if i in (4, 10) else "driver", 5, 1),)
        stages.append(pause(i, words=words, registers=registers))
    result = run(
        opening=replace(OPENING, flags=0x2001), stages=tuple(stages), require_continuity=False
    )
    assert result["post_open_position_and_generation_consistent"]


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"session": "03" * 16}, "JOINT_IDENTITY"),
        ({"host_shift": 4096}, "JOINT_BACKING"),
    ],
)
def test_individually_consistent_halves_cannot_be_joined(kwargs, error):
    stages = tuple(pause(i, **kwargs) if i >= 4 else pause(i) for i in range(11))
    with rejects(error):
        run(stages=stages, require_continuity=False)
