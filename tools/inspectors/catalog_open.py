"""CA02-07: supplied catalog/open correspondence, not authenticated file I/O."""

import re
import struct
from dataclasses import dataclass, replace

from tools.inspectors.archive_descriptor import inspect_descriptor
from tools.inspectors.effective_mapping import integer
from tools.inspectors.load_lineage import MAX_CYCLES, _hash
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observation_capture import require
from tools.inspectors.observer_series import _backing


@dataclass(frozen=True, repr=False)
class CatalogSource:
    catalog_sha256: str
    container_sha256: str
    resource_sha256: str
    iso_path: bytes
    name: bytes
    file_size: int
    offset: int
    size: int


@dataclass(frozen=True, repr=False)
class CodeWindow:
    address: int
    data: bytes


@dataclass(frozen=True, repr=False)
class OpenProfile:
    resolver: CodeWindow
    wrapper: CodeWindow
    selected_pc: int
    open_pc: int
    completed_pc: int
    target: int
    config_address: int
    flags: int
    mode: int


def _inputs(source, profile):
    require(type(source) is CatalogSource and type(profile) is OpenProfile, "CATALOG_INPUT")
    require(
        all(
            _hash(h)
            for h in (source.catalog_sha256, source.container_sha256, source.resource_sha256)
        ),
        "CATALOG_HASH",
    )
    require(
        type(source.iso_path) is bytes
        and 1 <= len(source.iso_path) <= 255
        and re.fullmatch(rb"[A-Z0-9_.-]+(?:/[A-Z0-9_.-]+)*", source.iso_path) is not None
        and all(p not in (b".", b"..") for p in source.iso_path.split(b"/"))
        and type(source.name) is bytes
        and re.fullmatch(rb"[A-Za-z0-9_.-]{1,255}", source.name) is not None
        and source.name not in (b".", b"..")
        and 9 + len(source.iso_path) + len(source.name) <= 511,
        "CATALOG_PATH",
    )
    integer(source.file_size, 1, 2**31 - 1, "CATALOG_RANGE")
    integer(source.size, 1, min(4096, source.file_size), "CATALOG_RANGE")
    integer(source.offset, 0, source.file_size - source.size, "CATALOG_RANGE")
    for window in (profile.resolver, profile.wrapper):
        require(type(window) is CodeWindow, "OPEN_CODE")
        integer(window.address, 0, 2**32 - 4096, "OPEN_CODE")
        require(
            window.address % 4 == 0
            and type(window.data) is bytes
            and 12 <= len(window.data) <= 4096
            and len(window.data) % 4 == 0,
            "OPEN_CODE",
        )
    for pc, window in (
        (profile.selected_pc, profile.resolver),
        (profile.open_pc, profile.wrapper),
        (profile.completed_pc, profile.wrapper),
    ):
        integer(pc, window.address, window.address + len(window.data) - 4, "OPEN_PC")
        require(pc % 4 == 0, "OPEN_PC")
    require(profile.open_pc + 8 < profile.completed_pc, "OPEN_PC")
    integer(profile.target, 0, 2**32 - 1, "OPEN_TARGET")
    integer(profile.config_address, 0, 2**32 - 12, "OPEN_CONFIG")
    require(profile.target % 4 == profile.config_address % 4 == 0, "OPEN_ALIGNMENT")
    integer(profile.flags, 0, 2**31 - 1, "OPEN_FLAGS")
    integer(profile.mode, 0, 2**31 - 1, "OPEN_MODE")
    call, delay = struct.unpack_from(
        "<II", profile.wrapper.data, profile.open_pc - profile.wrapper.address
    )
    require(
        call >> 26 == 3
        and ((profile.open_pc + 4) & 0xF0000000) | ((call & 0x3FFFFFF) << 2) == profile.target
        and delay == (18 << 21 | 5 << 11 | 0x2D),
        "OPEN_CALL_SHAPE",
    )


def _regions(pause):
    return {name: (request, observation) for name, request, observation in pause.regions}


def _same(a, b, *, data=True):
    ar, ao = a
    br, bo = b
    require(
        (ar.virtual_start, ar.size, ar.expected_offset)
        == (br.virtual_start, br.size, br.expected_offset)
        and _backing(ao) == _backing(bo),
        "OPEN_BACKING",
    )
    require(not data or ao.data == bo.data, "OPEN_CHANGED")


def reconcile_catalog_open(source, profile, stages):
    _inputs(source, profile)
    require(type(stages) is tuple and len(stages) == 4, "OPEN_STAGES")
    pauses = tuple(validate_pause(points) for points in stages)
    expected = ("code", "config", "directory", "record", "prefix", "name", "request")
    common = ("code", "config", "descriptor", "path", "range")
    for i, pause in enumerate(pauses):
        require(
            tuple(r[0] for r in pause.regions) == (expected if i == 0 else common), "OPEN_REGIONS"
        )
    a, b, c, d = pauses
    require(len({p.slot for p in pauses}) == 4, "OPEN_SLOTS")
    for before, after in zip(pauses[:-1], pauses[1:], strict=True):
        require(
            before.identity == after.identity
            and after.sequence == before.sequence + len(before.regions),
            "OPEN_IDENTITY",
        )
        require(before.cycle < after.cycle <= a.cycle + MAX_CYCLES, "OPEN_CYCLE")
    require(
        tuple(p.cpu.pc for p in pauses)
        == (profile.selected_pc, profile.open_pc, profile.open_pc + 8, profile.completed_pc),
        "OPEN_PC",
    )
    maps = tuple(_regions(p) for p in pauses)
    x, y, z, w = maps
    pages = {}
    for i, regions in enumerate(maps):
        window = profile.resolver if i == 0 else profile.wrapper
        require(
            regions["code"][0].virtual_start == window.address
            and regions["code"][1].data == window.data,
            "OPEN_CODE",
        )
        require(regions["config"][0].virtual_start == profile.config_address, "OPEN_CONFIG")
        _same(x["config"], regions["config"])
        for _, obs in regions.values():
            for page in obs.before.pages:
                require(pages.get(page.virtual_page, page.bias) == page.bias, "OPEN_PAGE")
                pages[page.virtual_page] = page.bias
    require(len(x["config"][1].data) == 12 and len(x["directory"][1].data) == 16, "CATALOG_LAYOUT")
    _, root, _ = struct.unpack("<3I", x["config"][1].data)
    capacity, heap, count, sorted_count = struct.unpack("<4I", x["directory"][1].data)
    require(
        16 <= root == x["directory"][0].virtual_start
        and root % 16 == 0
        and 1 <= count <= 4096
        and sorted_count <= count
        and 16 + 16 * count <= capacity <= 4 * 1024 * 1024
        and root + 16 + 16 * count <= heap < root + capacity <= 2**32,
        "CATALOG_DIRECTORY",
    )
    record = x["record"][0].virtual_start
    require(
        root + 16 <= record < root + 16 + 16 * count
        and (record - root) % 16 == 0
        and a.cpu.gpr_low32[9] == record
        and len(x["record"][1].data) == 16,
        "CATALOG_SELECTION",
    )
    prefix_at, name_at, offset, size = struct.unpack("<4I", x["record"][1].data)
    require((offset, size) == (source.offset, source.size), "CATALOG_RANGE")
    prefix = x["prefix"][1].data
    require(
        prefix.startswith(b"cdrom0:/")
        and prefix.endswith(b"%\0")
        and prefix[8:-2].upper() == source.iso_path
        and x["name"][1].data == source.name + b"\0",
        "CATALOG_NAMES",
    )
    for label, address in (("prefix", prefix_at), ("name", name_at)):
        region, obs = x[label]
        require(
            heap <= address == region.virtual_start and address + len(obs.data) <= root + capacity,
            "CATALOG_STRING_POINTER",
        )
    request = prefix[:-1] + source.name + b"\0"
    require(x["request"][1].data == request, "CATALOG_REQUEST")
    g = a.cpu.gpr_low32
    sp = b.cpu.gpr_low32[29]
    require(
        g[21] == x["request"][0].virtual_start
        and g[20] == g[21] + len(prefix) - 1
        and g[19] == 512
        and g[29] + 176 == sp
        and g[16] == y["path"][0].virtual_start == sp + 80
        and g[22] == y["range"][0].virtual_start == sp + 600
        and g[23] == sp + 604,
        "OPEN_RESOLVER_FRAME",
    )
    for p, regions in zip(pauses[1:], maps[1:], strict=True):
        g = p.cpu.gpr_low32
        require(
            g[29] == sp
            and g[17] == regions["descriptor"][0].virtual_start
            and g[18] == profile.flags
            and g[19] == x["request"][0].virtual_start,
            "OPEN_FRAME",
        )
        for label in common:
            _same(y[label], regions[label], data=label != "descriptor")
    require(y["path"][1].data == prefix[:-2] + b"\0", "OPEN_PATH")
    require(y["range"][1].data == struct.pack("<II", source.offset, source.size), "OPEN_RANGE")
    require(
        b.cpu.gpr_low32[4] == y["path"][0].virtual_start
        and b.cpu.gpr_low32[6] == b.cpu.gpr_low32[16] == c.cpu.gpr_low32[16] == profile.mode
        and c.cpu.gpr_low32[31] == profile.open_pc + 8
        and d.cpu.gpr_low32[31] == profile.completed_pc,
        "OPEN_ARGUMENTS",
    )
    _same(y["descriptor"], z["descriptor"])
    require(len(y["descriptor"][1].data) == 16, "OPEN_DESCRIPTOR")
    reserved, generation, _, _ = struct.unpack("<4I", y["descriptor"][1].data)
    require(reserved == 0xFFFFFFFE, "OPEN_RESERVATION")
    fd, token = c.cpu.gpr_low32[2], d.cpu.gpr_low32[2]
    require(fd < 2**31 and d.cpu.gpr_low32[16] == fd, "OPEN_RESULT")
    final = inspect_descriptor(
        (replace(stages[3][1], label="table"), stages[3][2]), token, source.offset, source.size
    )
    final_fd, final_generation, _, _ = struct.unpack("<4I", final.row)
    require(final_fd == fd and final_generation == generation + 1, "OPEN_GENERATION")
    return {
        "schema_version": 1,
        "status": "consistent_supplied_catalog_open",
        "catalog_sha256": source.catalog_sha256,
        "container_sha256": source.container_sha256,
        "resource_sha256": source.resource_sha256,
        "resource_size": source.size,
        "points": [m for p in pauses for m in p.metadata],
        "catalog_entry_and_open_consistent": True,
        "pinned_code_matches": True,
        "source_anchor_reverified": False,
        "profile_semantics_authenticated": False,
        "callee_execution_verified": False,
        "file_identity_verified": False,
        "driver_object_identified": False,
        "position_verified": False,
        "disk_read_verified": False,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "read_events_produced": 0,
        "load_provenance": "pending_driver_position_route_and_live_capture",
        "resource_links": [],
        "capabilities": [],
    }
