"""Own sector contents, state transitions and code; no original game material."""

import hashlib
import json
import struct
from dataclasses import replace
from functools import lru_cache

import pytest
from test_backend_sector import BACKEND, DISC, FILE, OLD, SOURCE, STREAM
from test_backend_sector import PROFILE as BS_PROFILE
from test_backend_sector import pause as bs_pause
from test_driver_transfer import BUFFER, REQUEST, SP
from test_driver_transfer import pause as base_pause
from test_observer_acquisition import CYCLE, rejects

from tools.inspectors.backend_completion import CompletionProfile, reconcile_backend_completion
from tools.inspectors.driver_transfer import DriverCode
from tools.inspectors.load_lineage import MAX_CYCLES

code = bytearray(64)
code[:32] = BS_PROFILE.caller.data
struct.pack_into("<I", code, 32, 3 << 26 | (0x170000 >> 2))
PROFILE = CompletionProfile(
    replace(BS_PROFILE, caller=DriverCode(BS_PROFILE.caller.address, bytes(code))),
    BS_PROFILE.caller.address + 32,
    0x170000,
)
LABELS = ("driver", "backend", "stream", "file", "disc", "code", "args", "buffer")
SECTOR = bytes(range(256)) * 8
SECTOR_HASH = hashlib.sha256(SECTOR).hexdigest()
WRAPPER = 0x2A0000


@lru_cache(maxsize=96)
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
    if index == 0:
        return bs_pause(
            source=source,
            request=request,
            words=words,
            values=(("code", PROFILE.backend.caller.data),) + values,
            addresses=addresses,
            physical=physical,
            registers=registers,
            **kwargs,
        )
    first = pause(0, source=source, request=request)
    data = {p.label: p.packets[0][237:] for p in first}
    locations = {p.label: p.plan.request.virtual_start for p in first}
    sector = source.offset // 2048
    rows = {
        label: list(struct.unpack("<" + str(len(data[label]) // 4) + "I", data[label]))
        for label in ("driver", "backend", "stream", "disc", "file")
    }
    rows["backend"][0] = 1 | (index + 1) << 8
    rows["backend"][2] = WRAPPER if index == 1 else 0
    rows["backend"][5:11] = [sector + index - 1, sector, 1, index - 1, BUFFER, 2048]
    rows["stream"][0] = 1 | (index + 1) << 8
    rows["stream"][1] = WRAPPER
    rows["stream"][3:6] = [0, sector, 2048]
    rows["stream"][8] = index - 1
    rows["stream"][12:14] = [1, (index - 1) * 2048]
    rows["disc"][3] = sector + index - 1
    if index == 2:
        rows["disc"][0] = 0x10001
        rows["disc"][4:8] = [1, 1, BUFFER, 0]
    for label, at, value in words:
        rows[label][at] = value
    data.update(
        (label, struct.pack("<" + str(len(row)) + "I", *row)) for label, row in rows.items()
    )
    data["buffer"] = bytes(2048) if index == 1 else SECTOR
    data.update(values)
    locations["buffer"] = BUFFER
    locations.update(addresses)
    remap = dict(zip(LABELS, OLD, strict=True))
    pc = PROFILE.backend.call_pc + 8 if index == 1 else PROFILE.status_call_pc + 8
    points = base_pause(
        0,
        request=request,
        pc=kwargs.pop("pc", pc),
        sequence=kwargs.pop("sequence", 1 + index * 8),
        slot=kwargs.pop("slot", index + 1),
        cycle=kwargs.pop("cycle", CYCLE + index + 1),
        values=tuple((remap[k], data[k]) for k in LABELS),
        addresses=tuple((remap[k], locations[k]) for k in LABELS),
        physical=tuple((remap[k], v) for k, v in physical),
        registers=((2, 1 if index == 1 else 3), (31, pc)) + registers,
        **kwargs,
    )
    return tuple(replace(p, label=label) for p, label in zip(points, LABELS, strict=True))


def run(*, source=SOURCE, request=REQUEST, profile=PROFILE, sector_sha256=SECTOR_HASH, stages=None):
    return reconcile_backend_completion(
        source,
        request,
        profile,
        sector_sha256,
        tuple(pause(i, source=source, request=request) for i in range(3))
        if stages is None
        else stages,
    )


def changed(index, **kwargs):
    return tuple(pause(i, **kwargs) if i == index else pause(i) for i in range(3))


def test_receipt_reports_consistency_without_execution_or_new_fill():
    receipt = run()
    assert receipt == run() and len(receipt["points"]) == 24
    assert receipt["completion_and_buffer_consistent"]
    assert receipt["valid_sector_size"] == 2048 and receipt["completed_sectors"] == 1
    assert receipt["read_events_produced"] == 0
    assert receipt["capabilities"] == receipt["resource_links"] == []
    for key in (
        "buffer_preexisting_at_submission",
        "backend_completion_verified",
        "buffer_fill_verified",
        "inner_copy_verified",
        "source_anchor_reverified",
        "profile_semantics_authenticated",
        "pool_membership_verified",
        "generation_verified",
        "opening_observed",
        "continuous_lifetime_verified",
        "inner_route_verified",
        "cache_origin_verified",
        "disk_read_verified",
        "live_acquisition_verified",
    ):
        assert receipt[key] is False
    assert receipt["execution_authentication"] == "not_provided"
    assert repr(PROFILE) == object.__repr__(PROFILE)
    raw = json.dumps(receipt)
    assert all(f'"{k}":' not in raw for k in ("pc", "pid", "address", "path", "words", "lsn"))
    assert run(stages=changed(1, values=(("buffer", SECTOR),)))["buffer_preexisting_at_submission"]


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"profile": None}, "COMPLETION_INPUT"),
        ({"profile": replace(PROFILE, backend=None)}, "BACKEND_INPUT"),
        ({"sector_sha256": "A" * 64}, "COMPLETION_HASH"),
        ({"sector_sha256": None}, "COMPLETION_HASH"),
        ({"source": None}, "BACKEND_INPUT"),
        ({"request": None}, "BACKEND_INPUT"),
    ],
)
def test_input_contract(changes, error):
    with rejects(error):
        run(stages=(), **changes)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status_call_pc", True),
        ("status_call_pc", PROFILE.status_call_pc + 1),
        ("status_call_pc", PROFILE.backend.call_pc),
        ("status_call_pc", PROFILE.backend.call_pc + 4),
        ("status_call_pc", PROFILE.backend.caller.address + 56),
        ("status_target", 0),
        ("status_target", 0x170001),
        ("status_target", PROFILE.backend.read_target),
        ("status_target", 0x180000),
    ],
)
def test_status_call_contract(field, value):
    with rejects("COMPLETION_CALL"):
        run(profile=replace(PROFILE, **{field: value}))


@pytest.mark.parametrize("offset,word", [(32, 0), (36, 1)])
def test_status_opcode_and_delay(offset, word):
    raw = bytearray(PROFILE.backend.caller.data)
    struct.pack_into("<I", raw, offset, word)
    profile = replace(
        PROFILE,
        backend=replace(PROFILE.backend, caller=replace(PROFILE.backend.caller, data=bytes(raw))),
    )
    with rejects("COMPLETION_CALL"):
        run(profile=profile)


@pytest.mark.parametrize("stages", [(), ((),), [(), (), ()]])
def test_stage_contract(stages):
    with rejects("COMPLETION_STAGES"):
        run(stages=stages)


@pytest.mark.parametrize(
    "index,kwargs,error",
    [
        (1, {"slot": 1}, "COMPLETION_SLOTS"),
        (2, {"slot": 2}, "COMPLETION_SLOTS"),
        (1, {"sequence": 10}, "COMPLETION_IDENTITY"),
        (2, {"session": "b" * 32}, "COMPLETION_IDENTITY"),
        (1, {"cycle": CYCLE + 1}, "COMPLETION_CYCLE"),
        (2, {"cycle": CYCLE + MAX_CYCLES + 2}, "COMPLETION_CYCLE"),
        (1, {"pc": PROFILE.backend.call_pc}, "COMPLETION_PC"),
        (2, {"pc": PROFILE.status_call_pc}, "COMPLETION_PC"),
        (1, {"registers": ((29, SP + 16),)}, "COMPLETION_ABI"),
        (2, {"registers": ((31, 0),)}, "COMPLETION_ABI"),
        (1, {"registers": ((2, 0),)}, "COMPLETION_RESULT"),
        (1, {"registers": ((2, 0xFFFFFFFF),)}, "COMPLETION_RESULT"),
        (1, {"registers": ((2, 2),)}, "COMPLETION_RESULT"),
        (2, {"registers": ((2, 4),)}, "COMPLETION_RESULT"),
        (1, {"physical": (("backend", BACKEND + 4096),)}, "COMPLETION_PAGE"),
        (2, {"addresses": (("disc", DISC + 4),)}, "COMPLETION_BACKING"),
        (2, {"physical": (("buffer", BUFFER + 4096),)}, "COMPLETION_PAGE"),
        (1, {"values": (("buffer", bytes(2047)),)}, "COMPLETION_LAYOUT"),
        (0, {"words": (("driver", 11, 4),)}, "BACKEND_CACHE_HIT"),
        (0, {"words": (("backend", 2, WRAPPER),)}, "COMPLETION_ADMISSION"),
    ],
)
def test_pause_and_initial_request_rejections(index, kwargs, error):
    with rejects(error):
        run(stages=changed(index, **kwargs))


@pytest.mark.parametrize(
    "index,label,at,value,error",
    [
        (1, "backend", 0, 0x301, "COMPLETION_STATE"),
        (2, "backend", 0, 0x401, "COMPLETION_STATE"),
        (2, "backend", 0, 0x101, "COMPLETION_STATE"),
        (2, "backend", 0, 0x201, "COMPLETION_STATE"),
        (2, "backend", 0, 0x1000301, "COMPLETION_STATE"),
        (2, "backend", 0, 0x10301, "COMPLETION_STATE"),
        (2, "stream", 0, 0x401, "COMPLETION_STREAM"),
        (1, "stream", 0, 0x10201, "COMPLETION_STREAM"),
        (2, "stream", 17, 1, "COMPLETION_STREAM"),
        (2, "backend", 1, STREAM + 72, "COMPLETION_CHAIN"),
        (2, "backend", 4, 65535, "COMPLETION_CHAIN"),
        (1, "stream", 2, FILE + 8, "COMPLETION_CHAIN"),
        (2, "disc", 8, 101, "COMPLETION_CHAIN"),
        (2, "disc", 0, 0x10000, "COMPLETION_CHAIN"),
        (1, "backend", 5, 5, "COMPLETION_PROGRESS"),
        (2, "backend", 5, 4, "COMPLETION_PROGRESS"),
        (2, "backend", 6, 3, "COMPLETION_PROGRESS"),
        (2, "backend", 7, 2, "COMPLETION_PROGRESS"),
        (2, "backend", 8, 0, "COMPLETION_PROGRESS"),
        (2, "backend", 8, 2048, "COMPLETION_PROGRESS"),
        (2, "backend", 9, BUFFER + 2048, "COMPLETION_PROGRESS"),
        (2, "backend", 10, 1, "COMPLETION_PROGRESS"),
        (1, "stream", 3, 1, "COMPLETION_STREAM_PROGRESS"),
        (2, "stream", 4, 3, "COMPLETION_STREAM_PROGRESS"),
        (2, "stream", 5, 65536, "COMPLETION_STREAM_PROGRESS"),
        (2, "stream", 12, 2, "COMPLETION_STREAM_PROGRESS"),
        (2, "stream", 13, 1, "COMPLETION_STREAM_PROGRESS"),
        (1, "stream", 13, 2048, "COMPLETION_STREAM_PROGRESS"),
        (1, "backend", 2, 0, "COMPLETION_WRAPPER"),
        (1, "backend", 2, WRAPPER + 1, "COMPLETION_WRAPPER"),
        (1, "stream", 1, WRAPPER + 4, "COMPLETION_WRAPPER"),
        (2, "backend", 2, WRAPPER, "COMPLETION_WRAPPER"),
        (2, "stream", 1, WRAPPER + 4, "COMPLETION_WRAPPER"),
        (1, "disc", 0, 0x20001, "COMPLETION_DISC"),
        (1, "disc", 3, 5, "COMPLETION_DISC"),
        (1, "disc", 7, 1, "COMPLETION_DISC"),
        (2, "disc", 0, 1, "COMPLETION_DISC"),
        (2, "disc", 3, 4, "COMPLETION_DISC"),
        (2, "disc", 4, 2, "COMPLETION_DISC"),
        (2, "disc", 5, 0, "COMPLETION_DISC"),
        (2, "disc", 6, BUFFER + 2048, "COMPLETION_DISC"),
        (2, "disc", 7, 1, "COMPLETION_DISC"),
        (2, "stream", 8, 0, "COMPLETION_DISC"),
        (1, "driver", 11, 4, "COMPLETION_CHANGED"),
        (2, "file", 1, DISC + 72, "COMPLETION_CHANGED"),
    ],
)
def test_failure_cancel_short_stale_and_foreign_state(index, label, at, value, error):
    with rejects(error):
        run(stages=changed(index, words=((label, at, value),)))


def test_wrong_region_and_source_packet():
    points = tuple(replace(p, label="other") if p.label == "buffer" else p for p in pause(2))
    with rejects("COMPLETION_REGIONS"):
        run(stages=(pause(0), pause(1), points))
    points = (replace(pause(2)[0], state=pause(2)[0].state + b"x"), *pause(2)[1:])
    with rejects("PAUSE_STATE_HASH"):
        run(stages=(pause(0), pause(1), points))


def test_full_sector_hash_rejects_other_content_even_when_resource_matches():
    foreign = SECTOR[:32] + bytes(2016)
    with rejects("COMPLETION_SECTOR"):
        run(stages=changed(2, values=(("buffer", foreign),)))
    with rejects("COMPLETION_RESOURCE"):
        run(
            sector_sha256=hashlib.sha256(bytes(2048)).hexdigest(),
            stages=changed(2, values=(("buffer", bytes(2048)),)),
        )


@pytest.mark.parametrize(
    "size,offset,file_size", [(2048, 8192, 65536), (32, 8200, 8232), (1, 8192, 8193)]
)
def test_full_sector_subrange_and_partial_file_padding(size, offset, file_size):
    data = SECTOR[offset % 2048 : offset % 2048 + size]
    digest = hashlib.sha256(data).hexdigest()
    source = replace(SOURCE, offset=offset, file_size=file_size, size=size, resource_sha256=digest)
    request = replace(
        REQUEST,
        offset=offset,
        file_size=file_size,
        size=size,
        requested=size,
        resource_sha256=digest,
    )
    valid_size = min(2048, file_size - offset // 2048 * 2048)
    payload = SECTOR[:valid_size] + b"x" * (2048 - valid_size)
    stages = (
        pause(0, source=source, request=request),
        pause(1, source=source, request=request),
        pause(2, source=source, request=request, values=(("buffer", payload),)),
    )
    result = run(
        source=source,
        request=request,
        sector_sha256=hashlib.sha256(SECTOR[:valid_size]).hexdigest(),
        stages=stages,
    )
    assert result["valid_sector_size"] == valid_size and result["resource_size"] == size


def test_foreign_buffer_and_physical_alias_to_control():
    with rejects("COMPLETION_BUFFER"):
        run(
            stages=(
                pause(0),
                pause(1, addresses=(("buffer", BUFFER + 4096),)),
                pause(2, addresses=(("buffer", BUFFER + 4096),)),
            )
        )
    # The buffer aliases code physically, while each captured range still matches RAM.
    payload = PROFILE.backend.caller.data + bytes(2048 - len(PROFILE.backend.caller.data))
    stages = (
        pause(0),
        *(
            pause(
                i,
                physical=(("buffer", PROFILE.backend.caller.address),),
                values=(("buffer", payload),),
            )
            for i in (1, 2)
        ),
    )
    with rejects("COMPLETION_OVERLAP"):
        run(stages=stages)


def test_buffer_cannot_alias_device_table_only_observed_at_initial_pause():
    payload = PROFILE.backend.device.data + bytes(1984)
    stages = (
        pause(0),
        *(
            pause(
                i,
                physical=(("buffer", PROFILE.backend.device.address),),
                values=(("buffer", payload),),
            )
            for i in (1, 2)
        ),
    )
    with rejects("COMPLETION_OVERLAP"):
        run(stages=stages)


def test_region_budget_last_sequence_and_cycle_limit():
    stages = tuple(
        pause(i, sequence=233 + i * 8, cycle=CYCLE + 1 + (MAX_CYCLES if i == 2 else i))
        for i in range(3)
    )
    assert run(stages=stages)["points"][-1]["sequence"] == 256
    with rejects("MAPPING_CONTEXT"):
        run(stages=tuple(pause(i, sequence=234 + i * 8) for i in range(3)))


def test_host_backing_changes_between_pauses():
    points = []
    for point in pause(2):
        packets = []
        for raw in point.packets:
            packet = bytearray(raw)
            # A changed host vmap retains valid per-pause RAM mappings.
            for at in (61, 149):
                value = struct.unpack_from("<Q", packet, at + 28)[0]
                struct.pack_into("<Q", packet, at + 28, value + 4096)
            packets.append(bytes(packet))
        points.append(replace(point, packets=tuple(packets)))
    with rejects("COMPLETION_BACKING"):
        run(stages=(pause(0), pause(1), tuple(points)))
