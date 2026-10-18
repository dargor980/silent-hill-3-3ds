"""DA02-04: supplied descriptor consistency, never proof of an opened file."""

import hashlib
import struct
from dataclasses import dataclass

from tools.inspectors.effective_mapping import integer
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.mapped_pause import MappedPause, validate_pause
from tools.inspectors.observation_capture import require
from tools.inspectors.observer_series import _backing


@dataclass(frozen=True, repr=False)
class DescriptorView:
    pause: MappedPause
    table: bytes
    row: bytes


def inspect_descriptor(points, token: int, offset: int, size: int) -> DescriptorView:
    integer(token, 0, 2**31 - 1, "DESCRIPTOR_TOKEN")
    integer(offset, 0, 2**31 - 1, "DESCRIPTOR_RANGE")
    integer(size, 1, 2**31 - 1 - offset, "DESCRIPTOR_RANGE")
    pause = validate_pause(points)
    require(tuple(r[0] for r in pause.regions) == ("table", "descriptor"), "DESCRIPTOR_REGIONS")
    table, row = (r[2].data for r in pause.regions)
    require(len(table) == 12 and len(row) == 16, "DESCRIPTOR_LAYOUT")
    count, _, base = struct.unpack("<3I", table)
    integer(count, 2, 256, "DESCRIPTOR_CAPACITY")
    stride = 1 << (count - 1).bit_length()
    index = token & (stride - 1)
    require(
        index < count and base >= 16 and base % 16 == 0 and base + 16 * count <= 2**32,
        "DESCRIPTOR_TABLE",
    )
    require(pause.regions[1][1].virtual_start == base + 16 * index, "DESCRIPTOR_ROW")
    underlying, generation, actual_offset, actual_size = struct.unpack("<4I", row)
    require(underlying < 2**31, "DESCRIPTOR_CLOSED_OR_RESERVED")
    require(0 < generation and generation * stride + index == token, "DESCRIPTOR_GENERATION")
    require((actual_offset, actual_size) == (offset, size), "DESCRIPTOR_RANGE")
    return DescriptorView(pause, table, row)


def reconcile_descriptors(before, after, token: int, offset: int, size: int) -> dict:
    a, b = (inspect_descriptor(p, token, offset, size) for p in (before, after))
    require(
        a.pause.identity == b.pause.identity and b.pause.sequence == a.pause.sequence + 2,
        "DESCRIPTOR_IDENTITY",
    )
    require(a.pause.slot != b.pause.slot, "DESCRIPTOR_SLOT")
    require(a.pause.cycle < b.pause.cycle <= a.pause.cycle + MAX_CYCLES, "DESCRIPTOR_CYCLE")
    require(a.table == b.table and a.row == b.row, "DESCRIPTOR_CHANGED")
    for (_, ar, ao), (_, br, bo) in zip(a.pause.regions, b.pause.regions, strict=True):
        require(
            (ar.virtual_start, ar.size, ar.expected_offset)
            == (br.virtual_start, br.size, br.expected_offset)
            and _backing(ao) == _backing(bo),
            "DESCRIPTOR_BACKING",
        )
    return {
        "schema_version": 1,
        "status": "consistent_supplied_descriptor_pair",
        "candidate_size": size,
        "table_sha256": hashlib.sha256(a.table).hexdigest(),
        "descriptor_sha256": hashlib.sha256(a.row).hexdigest(),
        "points": [*a.pause.metadata, *b.pause.metadata],
        "file_identity_verified": False,
        "open_observed": False,
        "code_checked": False,
        "disk_read_verified": False,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "read_events_produced": 0,
        "load_provenance": "pending_open_file_binding_and_live_capture",
        "resource_links": [],
        "capabilities": [],
    }
