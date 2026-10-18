"""DT01/04-07: supplied single-sector dispatch, position and payload consistency."""

import hashlib
import struct
from dataclasses import dataclass

from tools.inspectors.driver_object import inspect_driver
from tools.inspectors.effective_mapping import integer
from tools.inspectors.load_lineage import MAX_CYCLES, _hash
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observation_capture import require
from tools.inspectors.observer_series import _backing


@dataclass(frozen=True, repr=False)
class DriverRequest:
    handle: int
    file_size: int
    offset: int
    requested: int
    size: int
    resource_sha256: str


@dataclass(frozen=True, repr=False)
class DriverCode:
    address: int
    data: bytes


@dataclass(frozen=True, repr=False)
class DriverProfile:
    root_address: int
    dispatch: DriverCode
    reader: DriverCode
    call_pc: int


def _inputs(request, profile):
    require(type(request) is DriverRequest and type(profile) is DriverProfile, "TRANSFER_INPUT")
    integer(request.handle, 0, 2**31 - 1, "DRIVER_HANDLE")
    integer(request.file_size, 1, 2**31 - 1, "TRANSFER_RANGE")
    integer(request.offset, 0, request.file_size - 1, "TRANSFER_RANGE")
    integer(request.requested, 1, 4096, "TRANSFER_RANGE")
    integer(request.size, 1, 4096, "TRANSFER_RANGE")
    require(
        request.offset + request.requested < 2**31
        and request.size == min(request.requested, request.file_size - request.offset),
        "TRANSFER_LENGTH",
    )
    require(
        request.offset // 2048 == (request.offset + request.size - 1) // 2048, "TRANSFER_SECTOR"
    )
    require(_hash(request.resource_sha256), "TRANSFER_HASH")
    integer(profile.root_address, 4, 2**32 - 4, "TRANSFER_ROOT")
    require(profile.root_address % 4 == 0, "TRANSFER_ROOT")
    for code in (profile.dispatch, profile.reader):
        require(type(code) is DriverCode, "TRANSFER_CODE")
        integer(code.address, 4, 2**32 - 4096, "TRANSFER_CODE")
        require(
            code.address % 4 == 0
            and type(code.data) is bytes
            and 20 <= len(code.data) <= 4096
            and len(code.data) % 4 == 0,
            "TRANSFER_CODE",
        )
    code = profile.dispatch
    integer(profile.call_pc, code.address + 8, code.address + len(code.data) - 12, "TRANSFER_PC")
    require(profile.call_pc % 4 == 0, "TRANSFER_PC")
    shape = struct.unpack_from("<4I", code.data, profile.call_pc - code.address - 8)
    require(
        shape
        == (
            35 << 26 | 16 << 21 | 2 << 16 | 4,
            35 << 26 | 2 << 21 | 2 << 16,
            2 << 21 | 31 << 11 | 9,
            0,
        ),
        "TRANSFER_CALL_SHAPE",
    )


def reconcile_driver_transfer(request, profile, stages):
    _inputs(request, profile)
    require(type(stages) is tuple and len(stages) == 2, "TRANSFER_STAGES")
    a, b = (validate_pause(points) for points in stages)
    labels = ("root", "pool", "object", "vtable", "dispatch", "reader", "destination", "args")
    require(all(tuple(r[0] for r in p.regions) == labels for p in (a, b)), "TRANSFER_REGIONS")
    require(a.identity == b.identity and b.sequence == a.sequence + 8, "TRANSFER_IDENTITY")
    require(a.slot != b.slot, "TRANSFER_SLOT")
    require(a.cycle < b.cycle <= a.cycle + MAX_CYCLES, "TRANSFER_CYCLE")
    require((a.cpu.pc, b.cpu.pc) == (profile.call_pc, profile.call_pc + 8), "TRANSFER_PC")
    for (_, ar, ao), (_, br, bo) in zip(a.regions, b.regions, strict=True):
        require(
            (ar.virtual_start, ar.size, ar.expected_offset)
            == (br.virtual_start, br.size, br.expected_offset)
            and _backing(ao) == _backing(bo),
            "TRANSFER_BACKING",
        )
    maps = tuple({label: (r, o) for label, r, o in p.regions} for p in (a, b))
    x, y = maps
    for label in labels:
        require(
            label in ("object", "destination") or x[label][1].data == y[label][1].data,
            "TRANSFER_CHANGED",
        )
    require(x["root"][0].virtual_start == profile.root_address, "TRANSFER_ROOT")
    for label, code in (("dispatch", profile.dispatch), ("reader", profile.reader)):
        require(
            x[label][0].virtual_start == code.address and x[label][1].data == code.data,
            "TRANSFER_CODE",
        )
    before, after = (
        inspect_driver(
            points[:4], request.handle, request.file_size, position, profile.reader.address
        )
        for points, position in zip(
            stages, (request.offset, request.offset + request.size), strict=True
        )
    )
    require(
        all(before.words[i] == after.words[i] for i in range(12) if i not in (8, 11)),
        "TRANSFER_OBJECT_CHANGED",
    )
    buffer, cached = before.words[10:]
    sector = request.offset // 2048
    require(0 < buffer <= 2**32 - 2048, "TRANSFER_BUFFER")
    require(cached == 0xFFFFFFFF or cached < (request.file_size + 2047) // 2048, "TRANSFER_CACHE")
    require(after.words[11] == sector, "TRANSFER_CACHE")
    dest, args = x["destination"], x["args"]
    require(dest[0].size == request.size and len(args[1].data) == 36, "TRANSFER_LAYOUT")
    g, h = a.cpu.gpr_low32, b.cpu.gpr_low32
    require(
        g[29] == h[29]
        and g[29] % 16 == 0
        and args[0].virtual_start == g[29] + 48
        and g[16] == h[16] == x["object"][0].virtual_start
        and g[4] == g[16]
        and g[2] == profile.reader.address
        and g[5] == dest[0].virtual_start
        and g[6] == request.requested
        and h[31] == profile.call_pc + 8
        and h[2] == request.size,
        "TRANSFER_ARGUMENTS",
    )
    require(
        tuple(struct.unpack_from("<I", args[1].data, i)[0] for i in (0, 16, 32))
        == (request.handle, dest[0].virtual_start, request.requested),
        "TRANSFER_SAVED_ARGS",
    )
    require(
        hashlib.sha256(y["destination"][1].data).hexdigest() == request.resource_sha256,
        "TRANSFER_PAYLOAD",
    )
    return {
        "schema_version": 1,
        "status": "consistent_supplied_driver_transfer",
        "resource_sha256": request.resource_sha256,
        "resource_size": request.size,
        "requested_size": request.requested,
        "points": [*a.metadata, *b.metadata],
        "object_and_position_consistent": True,
        "pinned_code_matches": True,
        "destination_preexisting": x["destination"][1].data == y["destination"][1].data,
        "initial_cache_index_matches": cached == sector,
        "source_anchor_reverified": False,
        "profile_semantics_authenticated": False,
        "open_generation_observed": False,
        "continuous_lifetime_verified": False,
        "file_identity_verified": False,
        "inner_route_verified": False,
        "cache_origin_verified": False,
        "disk_read_verified": False,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "read_events_produced": 0,
        "load_provenance": "pending_open_bridge_backend_cache_and_live_capture",
        "resource_links": [],
        "capabilities": [],
    }
