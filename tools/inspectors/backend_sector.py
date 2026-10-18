"""BS01-06: supplied backend chain and sector request, without read completion."""

import struct
from dataclasses import dataclass

from tools.inspectors.driver_transfer import DriverCode, DriverRequest
from tools.inspectors.effective_mapping import integer
from tools.inspectors.load_lineage import _hash
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observation_capture import require


@dataclass(frozen=True, repr=False)
class DiscSource:
    image_sha256: str
    container_sha256: str
    resource_sha256: str
    image_size: int
    file_offset: int
    file_size: int
    offset: int
    size: int


@dataclass(frozen=True, repr=False)
class BackendProfile:
    caller: DriverCode
    call_pc: int
    read_target: int
    device: DriverCode


def _inputs(source, request, profile):
    require(
        type(source) is DiscSource
        and type(request) is DriverRequest
        and type(profile) is BackendProfile,
        "BACKEND_INPUT",
    )
    require(
        all(
            _hash(h) for h in (source.image_sha256, source.container_sha256, source.resource_sha256)
        ),
        "BACKEND_HASH",
    )
    integer(source.image_size, 2048, 2**42, "BACKEND_EXTENT")
    integer(source.file_offset, 0, source.image_size - 2048, "BACKEND_EXTENT")
    integer(source.file_size, 1, 2**31 - 2048, "BACKEND_EXTENT")
    sectors = (source.file_size + 2047) // 2048
    require(
        source.file_offset % 2048 == 0
        and source.file_offset + sectors * 2048 <= source.image_size
        and source.file_offset // 2048 + sectors < 2**31,
        "BACKEND_EXTENT",
    )
    integer(source.size, 1, min(2048, source.file_size), "BACKEND_RANGE")
    integer(source.offset, 0, source.file_size - source.size, "BACKEND_RANGE")
    require(source.offset // 2048 == (source.offset + source.size - 1) // 2048, "BACKEND_SECTOR")
    integer(request.handle, 0, 2**31 - 1, "BACKEND_HANDLE")
    for value in (request.file_size, request.offset, request.requested, request.size):
        integer(value, 0, 2**31 - 1, "BACKEND_REQUEST")
    require(
        (
            request.file_size,
            request.offset,
            request.requested,
            request.size,
            request.resource_sha256,
        )
        == (source.file_size, source.offset, source.size, source.size, source.resource_sha256),
        "BACKEND_REQUEST",
    )
    for code in (profile.caller, profile.device):
        require(type(code) is DriverCode, "BACKEND_CODE")
        integer(code.address, 4, 2**32 - 4096, "BACKEND_CODE")
        require(
            code.address % 4 == 0
            and type(code.data) is bytes
            and 12 <= len(code.data) <= 4096
            and len(code.data) % 4 == 0,
            "BACKEND_CODE",
        )
    require(len(profile.device.data) == 64, "BACKEND_DEVICE")
    for at in (16, 24, 32):
        target = struct.unpack_from("<I", profile.device.data, at)[0]
        require(target >= 4 and target % 4 == 0, "BACKEND_DEVICE")
    integer(profile.read_target, 4, 2**32 - 4, "BACKEND_CALL")
    integer(
        profile.call_pc,
        profile.caller.address,
        profile.caller.address + len(profile.caller.data) - 8,
        "BACKEND_CALL",
    )
    require(profile.call_pc % 4 == profile.read_target % 4 == 0, "BACKEND_CALL")
    call, delay = struct.unpack_from(
        "<II", profile.caller.data, profile.call_pc - profile.caller.address
    )
    require(
        call >> 26 == 3
        and ((profile.call_pc + 4) & 0xF0000000) | ((call & 0x3FFFFFF) << 2) == profile.read_target
        and delay == 0,
        "BACKEND_CALL",
    )


def reconcile_backend_sector(source, request, profile, points):
    _inputs(source, request, profile)
    pause = validate_pause(points)
    labels = ("driver", "backend", "stream", "file", "device", "disc", "code", "args")
    require(tuple(r[0] for r in pause.regions) == labels, "BACKEND_REGIONS")
    regions = {label: (r, o) for label, r, o in pause.regions}
    require(
        tuple(len(o.data) for _, _, o in pause.regions)
        == (48, 56, 72, 8, 64, 72, len(profile.caller.data), 52),
        "BACKEND_LAYOUT",
    )
    for label in labels[:6]:
        address = regions[label][0].virtual_start
        require(address >= 4 and address % 4 == 0, "BACKEND_POINTER")
    driver = struct.unpack("<12I", regions["driver"][1].data)
    backend = struct.unpack("<14I", regions["backend"][1].data)
    stream = struct.unpack("<18I", regions["stream"][1].data)
    file = struct.unpack("<2I", regions["file"][1].data)
    disc = struct.unpack("<18I", regions["disc"][1].data)
    require(
        driver[7] == regions["backend"][0].virtual_start
        and backend[1] == regions["stream"][0].virtual_start
        and stream[2] == regions["file"][0].virtual_start
        and file == (regions["device"][0].virtual_start, regions["disc"][0].virtual_start),
        "BACKEND_CHAIN",
    )
    require(
        driver[0] == request.handle and driver[3] < 2**31 and driver[4] > 0 and driver[5] in (0, 1),
        "BACKEND_DRIVER",
    )
    flags = tuple(regions[label][1].data[:4] for label in ("backend", "stream", "disc"))
    b, s, d = flags
    require(
        b[0] == s[0] == d[0] == 1
        and b[1] in (1, 3)
        and b[2] in (0, 1)
        and b[3] in (0, 1)
        and s[1] in (1, 3)
        and s[2] == 0
        and d[1] in (0, 1)
        and d[2] in (0, 1),
        "BACKEND_STATE",
    )
    sectors = (source.file_size + 2047) // 2048
    require(
        driver[6] == backend[4] == disc[1] == disc[9] == source.file_size
        and backend[3] == disc[2] == sectors
        and backend[12] == 0,
        "BACKEND_FILE_SIZE",
    )
    require(disc[8] == source.file_offset // 2048, "BACKEND_FILE_EXTENT")
    sector = source.offset // 2048
    require(driver[8] == source.offset and backend[5] == sector, "BACKEND_POSITION")
    require(driver[11] == 0xFFFFFFFF or driver[11] < sectors, "BACKEND_CACHE")
    require(driver[11] != sector, "BACKEND_CACHE_HIT")
    require(0 < driver[10] <= 2**32 - 2048 and driver[10] % 64 == 0, "BACKEND_BUFFER")
    for label, code in (("code", profile.caller), ("device", profile.device)):
        require(
            regions[label][0].virtual_start == code.address and regions[label][1].data == code.data,
            "BACKEND_CODE",
        )
    require(pause.cpu.pc == profile.call_pc, "BACKEND_PC")
    g = pause.cpu.gpr_low32
    require(
        g[29] % 16 == 0
        and regions["args"][0].virtual_start == g[29] + 48
        and g[4] == driver[7]
        and g[5] == 1
        and g[6] == driver[10],
        "BACKEND_ABI",
    )
    args = regions["args"][1].data
    object_at, destination, start, end = (
        struct.unpack_from("<I", args, i)[0] for i in (0, 16, 32, 48)
    )
    require(
        object_at == regions["driver"][0].virtual_start
        and 0 < destination <= 2**32 - source.size
        and (start, end) == (source.offset, source.offset + source.size),
        "BACKEND_ARGS",
    )
    return {
        "schema_version": 1,
        "status": "consistent_supplied_backend_sector_request",
        "image_sha256": source.image_sha256,
        "container_sha256": source.container_sha256,
        "resource_sha256": source.resource_sha256,
        "resource_size": source.size,
        "sector_size": 2048,
        "requested_sectors": 1,
        "points": list(pause.metadata),
        "backend_chain_consistent": True,
        "file_extent_and_sector_consistent": True,
        "source_anchor_reverified": False,
        "profile_semantics_authenticated": False,
        "pool_membership_verified": False,
        "generation_verified": False,
        "opening_observed": False,
        "continuous_lifetime_verified": False,
        "inner_route_verified": False,
        "backend_completion_verified": False,
        "cache_origin_verified": False,
        "disk_read_verified": False,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "read_events_produced": 0,
        "load_provenance": "pending_completion_copy_joint_profile_and_live_capture",
        "resource_links": [],
        "capabilities": [],
    }
