"""LP02-LP08: supplied byte lineage, never authentication of disk I/O or mapping."""

import hashlib
import re
from dataclasses import dataclass

from tools.inspectors.observation_capture import require

MAX_BYTES = 4096
MAX_TRACKED = 16384
MAX_EVENTS = 256
MAX_CYCLES = 60 * 294912000
RAM_SIZE = 32 * 1024 * 1024


@dataclass(frozen=True, repr=False)
class Identity:
    session: str
    environment_sha256: str
    process_sha256: str


@dataclass(frozen=True, repr=False)
class Stamp:
    identity: Identity
    sequence: int
    cycle: int


@dataclass(frozen=True, repr=False)
class Source:
    file_sha256: str
    file_size: int
    offset: int
    payload: bytes


@dataclass(frozen=True, repr=False)
class Read:
    stamp: Stamp
    file_sha256: str
    offset: int
    requested: int
    destination: int
    data: bytes


@dataclass(frozen=True, repr=False)
class Copy:
    stamp: Stamp
    source: int
    destination: int
    source_data: bytes
    data: bytes


@dataclass(frozen=True, repr=False)
class Write:
    stamp: Stamp
    destination: int
    data: bytes


@dataclass(frozen=True, repr=False)
class Deliver:
    stamp: Stamp
    destination: int
    data: bytes


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _range(start, size, limit):
    return type(start) is int and type(size) is int and 0 <= start < start + size <= limit


def reconcile_load(source: Source, events) -> dict:
    require(type(source) is Source, "LINEAGE_SOURCE")
    require(
        _hash(source.file_sha256)
        and type(source.file_size) is int
        and 0 < source.file_size < 1 << 63
        and type(source.payload) is bytes
        and 0 < len(source.payload) <= MAX_BYTES
        and _range(source.offset, len(source.payload), source.file_size),
        "LINEAGE_SOURCE",
    )
    try:
        iterator = iter(events)
    except TypeError:
        require(False, "LINEAGE_EVENTS")
    tags, records = {}, []
    identity = previous = None
    delivered = False
    peak = reads = copies = writes = 0
    for index, event in enumerate(iterator, 1):
        require(index <= MAX_EVENTS, "LINEAGE_BUDGET")
        require(not delivered, "LINEAGE_ORDER")
        require(type(event) in (Read, Copy, Write, Deliver), "LINEAGE_EVENT")
        stamp = event.stamp
        require(type(stamp) is Stamp and type(stamp.identity) is Identity, "LINEAGE_STAMP")
        current = stamp.identity
        require(
            type(current.session) is str
            and re.fullmatch(r"[0-9a-f]{32}", current.session) is not None
            and _hash(current.environment_sha256)
            and _hash(current.process_sha256),
            "LINEAGE_IDENTITY",
        )
        require(type(stamp.sequence) is int and stamp.sequence == index, "LINEAGE_SEQUENCE")
        require(type(stamp.cycle) is int and 0 <= stamp.cycle < 1 << 64, "LINEAGE_CYCLE")
        if identity is None:
            identity, first_cycle = current, stamp.cycle
        else:
            require(current == identity, "LINEAGE_IDENTITY")
            require(previous < stamp.cycle <= first_cycle + MAX_CYCLES, "LINEAGE_CYCLE")
        previous = stamp.cycle
        data, destination = event.data, event.destination
        require(type(data) is bytes and 0 < len(data) <= MAX_BYTES, "LINEAGE_DATA")
        require(_range(destination, len(data), RAM_SIZE), "LINEAGE_RAM")
        assigned = {}
        if type(event) is Read:
            require(event.file_sha256 == source.file_sha256, "LINEAGE_FILE")
            require(
                type(event.requested) is int
                and event.requested == len(data)
                and _range(event.offset, len(data), source.file_size),
                "LINEAGE_READ",
            )
            for i, value in enumerate(data):
                relative = event.offset + i - source.offset
                if 0 <= relative < len(source.payload):
                    require(value == source.payload[relative], "LINEAGE_READ_DATA")
                    assigned[destination + i] = relative
            reads += 1
        elif type(event) is Copy:
            require(_range(event.source, len(data), RAM_SIZE), "LINEAGE_RAM")
            require(type(event.source_data) is bytes and event.source_data == data, "LINEAGE_COPY")
            for i, value in enumerate(event.source_data):
                relative = tags.get(event.source + i)
                if relative is not None:
                    require(value == source.payload[relative], "LINEAGE_COPY_DATA")
                    assigned[destination + i] = relative
            copies += 1
        elif type(event) is Deliver:
            require(data == source.payload, "LINEAGE_DELIVERY_DATA")
            require(
                all(tags.get(destination + i) == i for i in range(len(data))),
                "LINEAGE_GAP",
            )
            delivered = True
        else:
            writes += 1
        if not delivered:
            for address in range(destination, destination + len(data)):
                tags.pop(address, None)
            tags.update(assigned)
            require(len(tags) <= MAX_TRACKED, "LINEAGE_TRACKED_BUDGET")
            peak = max(peak, len(tags))
        records.append(
            {
                "kind": type(event).__name__,
                "sequence": index,
                "size": len(data),
                "content_sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    require(delivered, "LINEAGE_INCOMPLETE")
    return {
        "schema_version": 1,
        "status": "consistent_supplied_byte_lineage",
        "file_sha256": source.file_sha256,
        "resource_sha256": hashlib.sha256(source.payload).hexdigest(),
        "resource_size": len(source.payload),
        "events": records,
        "reads": reads,
        "copies": copies,
        "invalidating_writes": writes,
        "peak_tracked_bytes": peak,
        "active_cycle_span": previous - first_cycle,
        "mapping_verified": False,
        "live_acquisition_verified": False,
        "disk_read_verified": False,
        "execution_authentication": "not_provided",
        "unobserved_writes_excluded": False,
        "non_candidate_read_bytes_verified": False,
        "load_provenance": "pending_evidence_adapter_and_live_capture",
        "resource_links": [],
        "capabilities": [],
    }
