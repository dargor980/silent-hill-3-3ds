"""Own nested dispatch and copy observations; no original code or payload."""

import hashlib
import json
import struct
from dataclasses import replace
from functools import lru_cache

import pytest
from test_backend_completion import PROFILE as BC_PROFILE
from test_backend_completion import SECTOR, SECTOR_HASH
from test_backend_completion import pause as bc_pause
from test_backend_sector import OLD, SOURCE
from test_driver_transfer import BUFFER, DEST, OBJECT, REQUEST, SP
from test_driver_transfer import PROFILE as DT_PROFILE
from test_driver_transfer import pause as dt_pause
from test_observer_acquisition import CYCLE, rejects

from tools.inspectors.buffer_copy import CopyProfile, reconcile_buffer_copy
from tools.inspectors.driver_transfer import DriverCode
from tools.inspectors.load_lineage import MAX_CYCLES

caller = bytearray(96)
caller[:64] = BC_PROFILE.backend.caller.data
struct.pack_into("<I", caller, 0, 0x27BDFF80)  # Own 128-byte frame.
struct.pack_into("<I", caller, 64, 3 << 26 | (0x180000 >> 2))
reader = bytearray(64)
struct.pack_into("<I", reader, 0, 0x27BDFF40)  # Own 192-byte frame.
struct.pack_into("<I", reader, 16, 3 << 26 | (0x150000 >> 2))
PROFILE = CopyProfile(
    replace(
        BC_PROFILE, backend=replace(BC_PROFILE.backend, caller=DriverCode(0x150000, bytes(caller)))
    ),
    replace(DT_PROFILE, reader=DriverCode(0x110000, bytes(reader))),
    DriverCode(0x180000, bytes(16)),
    0x110010,
    0x150040,
)
# Keep the copier away from the own driver-root range.
PROFILE = replace(PROFILE, copier=replace(PROFILE.copier, address=0x190000))
caller = bytearray(PROFILE.completion.backend.caller.data)
struct.pack_into("<I", caller, 64, 3 << 26 | (PROFILE.copier.address >> 2))
PROFILE = replace(
    PROFILE,
    completion=replace(
        PROFILE.completion,
        backend=replace(
            PROFILE.completion.backend,
            caller=replace(PROFILE.completion.backend.caller, data=bytes(caller)),
        ),
    ),
)
INNER = ("driver", "backend", "code", "copier", "args", "buffer", "destination", "return")


@lru_cache(maxsize=128)
def pause(
    index,
    *,
    source=SOURCE,
    request=REQUEST,
    words=(),
    values=(),
    addresses=(),
    physical=(),
    registers=(),
    **kwargs,
):
    if 1 <= index <= 3:
        return bc_pause(
            index - 1,
            source=source,
            request=request,
            words=words,
            values=(("code", PROFILE.completion.backend.caller.data),) + values,
            addresses=addresses,
            physical=physical,
            registers=registers,
            sequence=kwargs.pop("sequence", 1 + index * 8),
            slot=kwargs.pop("slot", index + 1),
            cycle=kwargs.pop("cycle", CYCLE + index + 1),
            **kwargs,
        )
    if index in (0, 6):
        seed = dt_pause(int(index == 6), request=request)
        labels = OLD
    else:
        seed = bc_pause(2, source=source, request=request)
        labels = INNER
    data = {p.label: p.packets[0][237:] for p in seed}
    loc = {p.label: p.plan.request.virtual_start for p in seed}
    if index in (0, 6):
        data["reader"] = PROFILE.driver.reader.data
        loc["args"] = SP + 320 + 48
        pc = PROFILE.driver.call_pc + (8 if index == 6 else 0)
        reg = (
            (29, SP + 320),
            (2, request.size if index == 6 else PROFILE.driver.reader.address),
            (31, PROFILE.driver.call_pc + 8),
        )
    else:
        row = list(struct.unpack("<12I", data["driver"]))
        row[11] = source.offset // 2048
        data.update(
            driver=struct.pack("<12I", *row),
            code=PROFILE.completion.backend.caller.data,
            copier=PROFILE.copier.data,
            destination=bytes(source.size)
            if index == 4
            else SECTOR[source.offset % 2048 : source.offset % 2048 + source.size],
            **{"return": struct.pack("<I", PROFILE.reader_call_pc + 8)},
        )
        loc.update(copier=PROFILE.copier.address, destination=DEST, **{"return": SP + 32})
        pc = PROFILE.copy_call_pc + (8 if index == 5 else 0)
        reg = (
            (29, SP),
            (4, DEST),
            (5, BUFFER + source.offset % 2048),
            (6, source.size),
            (17, source.size),
            (2, DEST),
            (31, PROFILE.copy_call_pc + 8),
        )
    for label, at, value in words:
        raw = bytearray(data[label])
        struct.pack_into("<I", raw, at * 4, value)
        data[label] = bytes(raw)
    data.update(values)
    loc.update(addresses)
    remap = dict(zip(labels, OLD, strict=True))
    points = dt_pause(
        0,
        request=request,
        pc=kwargs.pop("pc", pc),
        sequence=kwargs.pop("sequence", 1 + index * 8),
        slot=kwargs.pop("slot", index + 1),
        cycle=kwargs.pop("cycle", CYCLE + index + 1),
        values=tuple((remap[k], data[k]) for k in labels),
        addresses=tuple((remap[k], loc[k]) for k in labels),
        physical=tuple((remap[k], v) for k, v in physical),
        registers=reg + registers,
        **kwargs,
    )
    return tuple(replace(p, label=k) for p, k in zip(points, labels, strict=True))


def run(*, source=SOURCE, request=REQUEST, profile=PROFILE, sector_sha256=SECTOR_HASH, stages=None):
    return reconcile_buffer_copy(
        source,
        request,
        profile,
        sector_sha256,
        tuple(pause(i) for i in range(7)) if stages is None else stages,
    )


def changed(index, **kwargs):
    return tuple(pause(i, **kwargs) if i == index else pause(i) for i in range(7))


def test_complete_supplied_route_is_not_live_execution():
    result = run()
    assert result == run() and len(result["points"]) == 56
    assert result["copy_and_driver_return_consistent"]
    assert result["driver_generation_matches_at_endpoints"]
    assert not result["destination_preexisting"]
    assert result["read_events_produced"] == 0
    assert result["resource_links"] == result["capabilities"] == []
    for key in (
        "inner_copy_verified",
        "backend_completion_verified",
        "buffer_fill_verified",
        "continuous_lifetime_verified",
        "opening_observed",
        "source_anchor_reverified",
        "profile_semantics_authenticated",
        "disk_read_verified",
        "live_acquisition_verified",
        "writes_outside_destination_verified",
    ):
        assert result[key] is False
    assert result["execution_authentication"] == "not_provided"
    assert repr(PROFILE) == object.__repr__(PROFILE)
    assert all(
        f'"{key}":' not in json.dumps(result) for key in ("address", "pc", "pid", "path", "words")
    )


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("completion", None, "COMPLETION_INPUT"),
        ("driver", None, "TRANSFER_INPUT"),
        ("copier", None, "COPY_CODE"),
        ("copier", DriverCode(True, bytes(16)), "COPY_CODE"),
        ("copier", DriverCode(3, bytes(16)), "COPY_CODE"),
        ("copier", DriverCode(0x190000, bytes(7)), "COPY_CODE"),
        ("copier", DriverCode(0x190000, bytearray(16)), "COPY_CODE"),
        ("copy_call_pc", True, "COPY_CALL"),
        ("copy_call_pc", 0x150041, "COPY_CALL"),
        ("copy_call_pc", 0x150058, "COPY_CALL"),
        ("copy_call_pc", 0x150020, "COPY_CALL"),
        ("reader_call_pc", 0x110014, "COPY_CALL"),
    ],
)
def test_profile_input(field, value, error):
    with rejects(error):
        run(profile=replace(PROFILE, **{field: value}))


def test_bad_profile_and_stages():
    with rejects("COPY_INPUT"):
        run(profile=None)
    for stages in ((), ((),) * 6, [()] * 7):
        with rejects("COPY_STAGES"):
            run(stages=stages)


@pytest.mark.parametrize("word", [0, 0x27BD0000, 0x27BDFFF1, 0x27BDE000])
def test_invalid_stack_frame(word):
    code = bytearray(PROFILE.driver.reader.data)
    struct.pack_into("<I", code, 0, word)
    profile = replace(
        PROFILE,
        driver=replace(PROFILE.driver, reader=replace(PROFILE.driver.reader, data=bytes(code))),
    )
    with rejects("COPY_FRAME"):
        run(profile=profile)


@pytest.mark.parametrize("at,word", [(64, 0), (68, 1)])
def test_copy_call_shape(at, word):
    code = bytearray(PROFILE.completion.backend.caller.data)
    struct.pack_into("<I", code, at, word)
    profile = replace(
        PROFILE,
        completion=replace(
            PROFILE.completion,
            backend=replace(
                PROFILE.completion.backend,
                caller=replace(PROFILE.completion.backend.caller, data=bytes(code)),
            ),
        ),
    )
    with rejects("COPY_CALL"):
        run(profile=profile)


@pytest.mark.parametrize(
    "index,kwargs,error",
    [
        (4, {"slot": 1}, "COPY_SLOTS"),
        (0, {"sequence": 2}, "COPY_IDENTITY"),
        (6, {"session": "b" * 32}, "COPY_IDENTITY"),
        (6, {"cycle": CYCLE + 6}, "COPY_CYCLE"),
        (6, {"cycle": CYCLE + MAX_CYCLES + 2}, "COPY_CYCLE"),
        (4, {"physical": (("copier", 0x191000),)}, "COPY_PAGE"),
        (6, {"addresses": (("destination", DEST + 4),)}, "COPY_BACKING"),
        (4, {"values": (("destination", bytes(31)),)}, "COPY_LAYOUT"),
        (4, {"pc": PROFILE.copy_call_pc + 8}, "COPY_PC"),
        (6, {"pc": PROFILE.driver.call_pc}, "COPY_PC"),
        (6, {"registers": ((29, SP + 336),)}, "COPY_STACK"),
        (4, {"registers": ((29, SP + 16),)}, "COPY_STACK"),
        (0, {"addresses": (("args", SP + 384),)}, "COPY_BACKING"),
        (0, {"registers": ((4, OBJECT + 48),)}, "COPY_OUTER_ABI"),
        (6, {"registers": ((2, 31),)}, "COPY_OUTER_ABI"),
        (6, {"registers": ((2, DEST),)}, "COPY_OUTER_ABI"),
        (6, {"registers": ((31, 0),)}, "COPY_OUTER_ABI"),
        (4, {"registers": ((4, DEST + 4),)}, "COPY_ABI"),
        (4, {"registers": ((5, BUFFER + 1),)}, "COPY_ABI"),
        (4, {"registers": ((6, 31),)}, "COPY_ABI"),
        (4, {"registers": ((17, 31),)}, "COPY_ABI"),
        (5, {"registers": ((2, 32),)}, "COPY_ABI"),
        (5, {"registers": ((31, 0),)}, "COPY_ABI"),
        (4, {"words": (("return", 0, PROFILE.reader_call_pc),)}, "COPY_INNER_CHANGED"),
        (4, {"words": (("backend", 8, 0),)}, "COPY_INNER_CHANGED"),
        (4, {"words": (("driver", 10, BUFFER + 2048),)}, "COPY_DRIVER_CHANGED"),
        (4, {"words": (("driver", 11, 3),)}, "COPY_DRIVER_POSITION"),
        (5, {"words": (("driver", 8, 8193),)}, "COPY_DRIVER_POSITION"),
        (6, {"words": (("object", 4, 5),)}, "DRIVER_GENERATION"),
        (6, {"words": (("object", 8, 8223),)}, "DRIVER_POSITION"),
        (3, {"words": (("backend", 8, 0),)}, "COMPLETION_PROGRESS"),
        (5, {"values": (("destination", bytes(32)),)}, "COPY_PAYLOAD"),
        (6, {"values": (("destination", bytes(32)),)}, "COPY_PAYLOAD"),
        (4, {"values": (("destination", b"x" * 32),)}, "COPY_PAYLOAD"),
        (6, {"words": (("pool", 1, 99),)}, "COPY_OUTER_CHANGED"),
        (5, {"values": (("buffer", SECTOR[:32] + bytes(2016)),)}, "COPY_INNER_CHANGED"),
        (5, {"values": (("copier", b"x" * 16),)}, "COPY_INNER_CHANGED"),
    ],
)
def test_foreign_partial_stale_and_mapped_observations(index, kwargs, error):
    with rejects(error):
        run(stages=changed(index, **kwargs))


def test_destination_already_matches_is_declared_without_new_write():
    stages = tuple(
        pause(i, values=(("destination", SECTOR[:32]),)) if i in (0, 4) else pause(i)
        for i in range(7)
    )
    result = run(stages=stages)
    assert result["destination_preexisting"] and not result["inner_copy_verified"]


def test_saved_parent_and_copier_must_match_profile():
    with rejects("COPY_PARENT"):
        run(
            stages=tuple(
                pause(i, words=(("return", 0, 0),)) if i in (4, 5) else pause(i) for i in range(7)
            )
        )
    with rejects("COPY_CODE"):
        run(
            stages=tuple(
                pause(i, values=(("copier", b"x" * 16),)) if i in (4, 5) else pause(i)
                for i in range(7)
            )
        )


def test_destination_cannot_alias_sector_even_if_bytes_match():
    stages = []
    for i in range(7):
        if i in (0, 4, 5, 6):
            stages.append(
                pause(
                    i, physical=(("destination", BUFFER),), values=(("destination", SECTOR[:32]),)
                )
            )
        else:
            stages.append(pause(i))
    with rejects("COPY_OVERLAP"):
        run(stages=tuple(stages))


def test_labels_and_state_bytes_are_not_substitutable():
    stages = list(pause(i) for i in range(7))
    stages[4] = tuple(replace(p, label="other") if p.label == "return" else p for p in stages[4])
    with rejects("COPY_REGIONS"):
        run(stages=tuple(stages))
    stages[4] = (replace(pause(4)[0], state=pause(4)[0].state + b"x"), *pause(4)[1:])
    with rejects("PAUSE_STATE_HASH"):
        run(stages=tuple(stages))


def test_last_region_and_cycle_budget():
    stages = tuple(
        pause(i, sequence=201 + i * 8, cycle=CYCLE + 1 + (MAX_CYCLES if i == 6 else i))
        for i in range(7)
    )
    assert run(stages=stages)["points"][-1]["sequence"] == 256
    with rejects("MAPPING_CONTEXT"):
        run(stages=tuple(pause(i, sequence=202 + i * 8) for i in range(7)))


@pytest.mark.parametrize(
    "size,offset,file_size", [(2048, 8192, 65536), (31, 8201, 8232), (1, 8192, 8193)]
)
def test_full_unaligned_and_last_partial_sector(size, offset, file_size):
    payload = SECTOR[offset % 2048 : offset % 2048 + size]
    digest = hashlib.sha256(payload).hexdigest()
    source = replace(SOURCE, size=size, offset=offset, file_size=file_size, resource_sha256=digest)
    request = replace(
        REQUEST,
        size=size,
        requested=size,
        offset=offset,
        file_size=file_size,
        resource_sha256=digest,
    )
    stages = tuple(
        pause(i, source=source, request=request, values=(("destination", payload),))
        if i == 6
        else pause(i, source=source, request=request)
        for i in range(7)
    )
    valid = min(2048, file_size - offset // 2048 * 2048)
    assert (
        run(
            source=source,
            request=request,
            sector_sha256=hashlib.sha256(SECTOR[:valid]).hexdigest(),
            stages=stages,
        )["resource_size"]
        == size
    )


def test_host_anchor_changed_only_in_outer_return():
    points = []
    for p in pause(6):
        packets = []
        for raw in p.packets:
            data = bytearray(raw)
            for at in (61, 149):
                struct.pack_into(
                    "<Q", data, at + 28, struct.unpack_from("<Q", data, at + 28)[0] + 4096
                )
            packets.append(bytes(data))
        points.append(replace(p, packets=tuple(packets)))
    with rejects("COPY_BACKING"):
        run(stages=(*tuple(pause(i) for i in range(6)), tuple(points)))


def test_helper_frame_must_contain_captured_locals():
    code = bytearray(PROFILE.completion.backend.caller.data)
    struct.pack_into("<I", code, 0, 0x27BDFFF0)
    profile = replace(
        PROFILE,
        completion=replace(
            PROFILE.completion,
            backend=replace(
                PROFILE.completion.backend,
                caller=replace(PROFILE.completion.backend.caller, data=bytes(code)),
            ),
        ),
    )
    with rejects("COPY_FRAME"):
        run(profile=profile)


def test_buffer_cannot_alias_copier_only_observed_at_copy():
    profile = replace(PROFILE, copier=replace(PROFILE.copier, data=SECTOR[:16]))
    stages = []
    for i in range(7):
        kwargs = {}
        if i in (2, 3, 4, 5):
            kwargs["physical"] = (("buffer", PROFILE.copier.address),)
        if i in (4, 5):
            kwargs["values"] = (("copier", SECTOR[:16]),)
        stages.append(pause(i, **kwargs))
    with rejects("COPY_OVERLAP"):
        run(profile=profile, stages=tuple(stages))


@pytest.mark.parametrize(
    "indices,kwargs,error",
    [
        ((0, 6), {"words": (("args", 0, 8),)}, "COPY_OUTER_ARGS"),
        ((0, 6), {"addresses": (("root", PROFILE.driver.root_address + 4),)}, "COPY_ROOT"),
        ((4, 5), {"addresses": (("return", SP + 36),)}, "COPY_PARENT"),
    ],
)
def test_consistent_but_foreign_outer_and_parent_data(indices, kwargs, error):
    with rejects(error):
        run(stages=tuple(pause(i, **kwargs) if i in indices else pause(i) for i in range(7)))
