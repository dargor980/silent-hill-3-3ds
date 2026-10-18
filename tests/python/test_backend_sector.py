"""Own backend/stream/device/disc chain; no original data or code."""

import json
import struct
from dataclasses import replace

import pytest
from test_driver_transfer import BUFFER, OBJECT, REQUEST, SP
from test_driver_transfer import pause as base_pause
from test_observer_acquisition import rejects

from tools.inspectors.backend_sector import BackendProfile, DiscSource, reconcile_backend_sector
from tools.inspectors.driver_transfer import DriverCode

BACKEND, STREAM, FILE, DEVICE, DISC = 0x250000, 0x260000, 0x270000, 0x280000, 0x290000
SOURCE = DiscSource(
    "a" * 64, "b" * 64, REQUEST.resource_sha256, 2 * 1024 * 1024, 100 * 2048, 65536, 8192, 32
)
code = bytearray(32)
struct.pack_into("<I", code, 8, 3 << 26 | (0x160000 >> 2))
device = bytearray(64)
for at, target in ((16, 0x170000), (24, 0x180000), (32, 0x190000)):
    struct.pack_into("<I", device, at, target)
PROFILE = BackendProfile(
    DriverCode(0x150000, bytes(code)), 0x150008, 0x160000, DriverCode(DEVICE, bytes(device))
)
LABELS = ("driver", "backend", "stream", "file", "device", "disc", "code", "args")
OLD = ("root", "pool", "object", "vtable", "dispatch", "reader", "destination", "args")


def pause(
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
    sectors = (source.file_size + 2047) // 2048
    rows = {
        "driver": [
            request.handle,
            0x210000,
            0,
            5,
            4,
            0,
            source.file_size,
            BACKEND,
            source.offset,
            0xFFFFFFFF,
            BUFFER,
            0xFFFFFFFF,
        ],
        "backend": [
            0x101,
            STREAM,
            0,
            sectors,
            source.file_size,
            source.offset // 2048,
            0,
            0,
            0,
            0,
            0,
            512,
            0,
            0,
        ],
        "stream": [0x101, 0, FILE, 0, 0, 2048, 0, 0, 0, 0, 0, 512, 0, 0, 0, 0, 0, 0],
        "file": [DEVICE, DISC],
        "disc": [
            1,
            source.file_size,
            sectors,
            0,
            0,
            0,
            0,
            0,
            source.file_offset // 2048,
            source.file_size,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ],
    }
    for label, index, value in words:
        rows[label][index] = value
    data = {label: struct.pack("<" + str(len(row)) + "I", *row) for label, row in rows.items()}
    args = bytearray(52)
    for at, value in (
        (0, OBJECT),
        (16, 0x230000),
        (32, source.offset),
        (48, source.offset + source.size),
    ):
        struct.pack_into("<I", args, at, value)
    data.update(device=PROFILE.device.data, code=PROFILE.caller.data, args=bytes(args))
    data.update(values)
    location = dict(
        zip(
            LABELS,
            (OBJECT, BACKEND, STREAM, FILE, DEVICE, DISC, PROFILE.caller.address, SP + 48),
            strict=True,
        )
    )
    location.update(addresses)
    old = dict(zip(LABELS, OLD, strict=True))
    points = base_pause(
        0,
        request=request,
        pc=kwargs.pop("pc", PROFILE.call_pc),
        values=tuple((old[k], data[k]) for k in LABELS),
        addresses=tuple((old[k], location[k]) for k in LABELS),
        physical=tuple((old[k], v) for k, v in physical),
        registers=((4, BACKEND), (5, 1), (6, BUFFER)) + registers,
        **kwargs,
    )
    return tuple(replace(p, label=label) for p, label in zip(points, LABELS, strict=True))


def run(*, source=SOURCE, request=REQUEST, profile=PROFILE, points=None):
    return reconcile_backend_sector(source, request, profile, pause() if points is None else points)


def test_chain_receipt_is_deterministic_minimal_and_not_completion():
    result = run()
    assert result == run() and len(result["points"]) == 8
    assert result["backend_chain_consistent"] and result["file_extent_and_sector_consistent"]
    assert result["requested_sectors"] == 1 and result["sector_size"] == 2048
    assert (
        result["read_events_produced"] == 0
        and result["resource_links"] == result["capabilities"] == []
    )
    for key in (
        "source_anchor_reverified",
        "profile_semantics_authenticated",
        "pool_membership_verified",
        "generation_verified",
        "opening_observed",
        "continuous_lifetime_verified",
        "inner_route_verified",
        "backend_completion_verified",
        "cache_origin_verified",
        "disk_read_verified",
        "live_acquisition_verified",
    ):
        assert result[key] is False
    raw = json.dumps(result)
    assert all(
        f'"{k}":' not in raw
        for k in ("pc", "pid", "address", "path", "words", "handle", "lsn", "file_offset")
    )
    for value in (SOURCE, PROFILE, PROFILE.device):
        assert repr(value) == object.__repr__(value)


@pytest.mark.parametrize("key", ("source", "request", "profile"))
def test_exact_input_types(key):
    with rejects("BACKEND_INPUT"):
        run(**{key: None})


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("image_sha256", "A" * 64, "BACKEND_HASH"),
        ("container_sha256", None, "BACKEND_HASH"),
        ("resource_sha256", "bad", "BACKEND_HASH"),
        ("image_size", True, "BACKEND_EXTENT"),
        ("image_size", 2047, "BACKEND_EXTENT"),
        ("image_size", 2**42 + 1, "BACKEND_EXTENT"),
        ("file_offset", -1, "BACKEND_EXTENT"),
        ("file_offset", 100 * 2048 + 1, "BACKEND_EXTENT"),
        ("file_offset", SOURCE.image_size - 2048, "BACKEND_EXTENT"),
        ("file_size", 0, "BACKEND_EXTENT"),
        ("file_size", 2**31, "BACKEND_EXTENT"),
        ("size", 0, "BACKEND_RANGE"),
        ("size", 2049, "BACKEND_RANGE"),
        ("offset", -1, "BACKEND_RANGE"),
        ("offset", 65520, "BACKEND_RANGE"),
        ("offset", 2040, "BACKEND_SECTOR"),
        ("file_size", 65535, "BACKEND_REQUEST"),
    ],
)
def test_source_bounds(field, value, error):
    with rejects(error):
        run(source=replace(SOURCE, **{field: value}))


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("handle", True, "BACKEND_HANDLE"),
        ("handle", -1, "BACKEND_HANDLE"),
        ("offset", True, "BACKEND_REQUEST"),
        ("requested", 31, "BACKEND_REQUEST"),
        ("resource_sha256", "c" * 64, "BACKEND_REQUEST"),
    ],
)
def test_request_correspondence(field, value, error):
    with rejects(error):
        run(request=replace(REQUEST, **{field: value}))


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("caller", None, "BACKEND_CODE"),
        ("caller", DriverCode(1, bytes(32)), "BACKEND_CODE"),
        ("caller", DriverCode(0x150000, bytearray(32)), "BACKEND_CODE"),
        ("caller", DriverCode(0x150000, bytes(33)), "BACKEND_CODE"),
        ("caller", DriverCode(0x150000, bytes(4100)), "BACKEND_CODE"),
        ("caller", DriverCode(0x150000, bytes(32)), "BACKEND_CALL"),
        ("device", DriverCode(DEVICE, bytes(60)), "BACKEND_DEVICE"),
        ("device", DriverCode(DEVICE, bytes(64)), "BACKEND_DEVICE"),
        ("call_pc", 0x150009, "BACKEND_CALL"),
        ("call_pc", 0x15001C, "BACKEND_CALL"),
        ("read_target", 0, "BACKEND_CALL"),
        ("read_target", 0x160004, "BACKEND_CALL"),
    ],
)
def test_profile_bounds(field, value, error):
    with rejects(error):
        run(profile=replace(PROFILE, **{field: value}))


@pytest.mark.parametrize(
    "label,index,value,error",
    [
        ("driver", 7, 0, "BACKEND_CHAIN"),
        ("backend", 1, STREAM + 4, "BACKEND_CHAIN"),
        ("stream", 2, FILE + 4, "BACKEND_CHAIN"),
        ("file", 0, DEVICE + 4, "BACKEND_CHAIN"),
        ("file", 1, DISC + 4, "BACKEND_CHAIN"),
        ("driver", 0, 0xFFFFFFFF, "BACKEND_DRIVER"),
        ("driver", 3, 0xFFFFFFFF, "BACKEND_DRIVER"),
        ("driver", 4, 0, "BACKEND_DRIVER"),
        ("driver", 5, 2, "BACKEND_DRIVER"),
        ("backend", 0, 0, "BACKEND_STATE"),
        ("backend", 0, 0x201, "BACKEND_STATE"),
        ("stream", 0, 0, "BACKEND_STATE"),
        ("stream", 0, 0x201, "BACKEND_STATE"),
        ("stream", 0, 0x10101, "BACKEND_STATE"),
        ("disc", 0, 0, "BACKEND_STATE"),
        ("disc", 0, 0x20001, "BACKEND_STATE"),
        ("driver", 6, 65535, "BACKEND_FILE_SIZE"),
        ("backend", 4, 65535, "BACKEND_FILE_SIZE"),
        ("backend", 3, 31, "BACKEND_FILE_SIZE"),
        ("backend", 12, 1, "BACKEND_FILE_SIZE"),
        ("disc", 1, 65535, "BACKEND_FILE_SIZE"),
        ("disc", 9, 65535, "BACKEND_FILE_SIZE"),
        ("disc", 2, 0x7FFFFFFF, "BACKEND_FILE_SIZE"),
        ("disc", 8, 101, "BACKEND_FILE_EXTENT"),
        ("driver", 8, 8191, "BACKEND_POSITION"),
        ("backend", 5, 3, "BACKEND_POSITION"),
        ("backend", 5, 8192, "BACKEND_POSITION"),
        ("driver", 11, 4, "BACKEND_CACHE_HIT"),
        ("driver", 11, 32, "BACKEND_CACHE"),
        ("driver", 10, 0, "BACKEND_BUFFER"),
        ("driver", 10, BUFFER + 4, "BACKEND_BUFFER"),
        ("driver", 10, 0xFFFFFFC0, "BACKEND_BUFFER"),
    ],
)
def test_chain_and_sector_rejections(label, index, value, error):
    with rejects(error):
        run(points=pause(words=((label, index, value),)))


@pytest.mark.parametrize(
    "reg,value", [(4, BACKEND + 4), (5, 2), (6, BUFFER + 64), (29, SP + 16), (29, SP + 1)]
)
def test_abi(reg, value):
    with rejects("BACKEND_ABI"):
        run(points=pause(registers=((reg, value),)))


@pytest.mark.parametrize(
    "offset,value", [(0, OBJECT + 4), (16, 0), (16, 0xFFFFFFFF), (32, 8191), (48, 8223)]
)
def test_saved_args(offset, value):
    args = bytearray(52)
    for at, word in ((0, OBJECT), (16, 0x230000), (32, 8192), (48, 8224), (offset, value)):
        struct.pack_into("<I", args, at, word)
    with rejects("BACKEND_ARGS"):
        run(points=pause(values=(("args", bytes(args)),)))


def test_layout_mapping_and_code():
    for label in LABELS:
        with rejects("BACKEND_LAYOUT"):
            run(points=pause(values=((label, bytes(4)),)))
    with rejects("BACKEND_POINTER"):
        run(points=pause(addresses=(("backend", BACKEND + 1),)))
    with rejects("BACKEND_PC"):
        run(points=pause(pc=PROFILE.call_pc + 8))
    for label in ("device", "code"):
        length = 64 if label == "device" else 32
        with rejects("BACKEND_CODE"):
            run(points=pause(values=((label, bytes([7]) * length),)))
    with rejects("BACKEND_REGIONS"):
        run(points=tuple(replace(p, label="other") if p.label == "driver" else p for p in pause()))
    points = list(pause())
    points[0] = replace(points[0], state=points[0].state + b"x")
    with rejects("PAUSE_STATE_HASH"):
        run(points=tuple(points))


def test_stream_read_length_and_old_disc_position_are_not_file_identity():
    result = run(
        points=pause(
            words=(
                ("stream", 5, 16),
                ("stream", 0, 0x301),
                ("backend", 0, 0x301),
                ("disc", 3, 7),
                ("driver", 11, 3),
            )
        )
    )
    assert result["file_extent_and_sector_consistent"] and not result["backend_completion_verified"]


def test_last_partial_sector_and_full_sector():
    for size, file_size in ((2048, 65536), (1, 8193)):
        source = replace(SOURCE, size=size, file_size=file_size)
        request = replace(REQUEST, size=size, requested=size, file_size=file_size)
        assert (
            run(source=source, request=request, points=pause(source=source, request=request))[
                "resource_size"
            ]
            == size
        )


def test_extent_signed_sector_overflow():
    with rejects("BACKEND_EXTENT"):
        run(source=replace(SOURCE, image_size=2**42, file_offset=(2**31 - 1) * 2048))


def test_first_extent_and_region_budget_boundary():
    source = replace(SOURCE, file_offset=0)
    assert (
        run(source=source, points=pause(source=source, sequence=249))["points"][-1]["sequence"]
        == 256
    )
    with rejects("MAPPING_CONTEXT"):
        run(points=pause(sequence=250))


def test_shared_page_mapping_rejected():
    points = pause(
        addresses=(("stream", BACKEND + 64),),
        physical=(("stream", STREAM),),
        words=(("backend", 1, BACKEND + 64),),
    )
    with rejects("PAUSE_PAGE"):
        run(points=points)


def test_signed_sector_rounding_boundary():
    source = replace(SOURCE, image_size=3 * 1024**3, file_size=2**31 - 2048)
    request = replace(REQUEST, file_size=source.file_size)
    assert run(source=source, request=request, points=pause(source=source, request=request))[
        "backend_chain_consistent"
    ]
    with rejects("BACKEND_EXTENT"):
        run(source=replace(source, file_size=source.file_size + 1))
