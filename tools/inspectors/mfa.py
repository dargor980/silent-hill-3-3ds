"""Own bounded structural probe, not an extractor. Provenance: schemas/mfa-probe-v1.md."""

import struct
from dataclasses import dataclass
from typing import Protocol

from tools.inspectors.mfa_names import name_diagnostics
from tools.pipeline.profile import ProfileError, safe_relative_path

SECTOR_SIZE = 2048
MAX_BLOCKS = 4096
MAX_ENTRIES = 100000
LAYOUT = "mfa-d8-blocks-v1"
LAYOUTS = {"d8": (0xD8, LAYOUT), "b8": (0xB8, "mfa-b8-blocks-v1")}


@dataclass(frozen=True)
class MfaEntry:
    block_index: int
    block_offset: int
    entry_index: int
    entry_ordinal: int
    name: str | bytes
    name_offset: int
    offset: int
    size: int
    unknown_word: int


@dataclass(frozen=True)
class MfaIndex:
    summary: dict
    entries: tuple[MfaEntry, ...]


class RangeReader(Protocol):
    def read_at(self, offset: int, length: int) -> bytes:
        """Return exactly length bytes, or raise a ProfileError for a read failure."""


class MfaError(ProfileError):
    """Unsupported or malformed structure; distinct from transport failures."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(code, message)
        self.details = {} if details is None else dict(details)


def layout_descriptor(layout: str) -> tuple[int, str]:
    if not isinstance(layout, str) or layout not in LAYOUTS:
        raise ProfileError("MFA_LAYOUT", "Expected one registered layout: b8 or d8")
    return LAYOUTS[layout]


def _plausible_header(sector: bytes, toc: int, size: int) -> bool:
    """Ambiguity guard only; never enough to accept or select a format."""
    count, data_size = struct.unpack_from("<II", sector, toc)
    return (
        0 < count
        and toc + 8 + count * 16 <= SECTOR_SIZE
        and data_size > 0
        and data_size % SECTOR_SIZE == 0
        and SECTOR_SIZE + data_size <= size
    )


def _raw_name(sector: bytes, offset: int, table_end: int) -> bytes:
    if not table_end <= offset < SECTOR_SIZE:
        raise MfaError("MFA_NAME", "Name is outside the string area", {"reason": "name_range"})
    end = sector.find(b"\0", offset, min(SECTOR_SIZE, offset + 1025))
    if end < 0:
        raise MfaError("MFA_NAME", "Name terminator exceeds limit", {"reason": "name_termination"})
    raw = sector[offset:end]
    if not raw:
        raise MfaError("MFA_PATH", "Empty resource name")
    return raw


def _name(sector: bytes, offset: int, table_end: int) -> str:
    raw = _raw_name(sector, offset, table_end)
    if any(c < 32 or c > 126 for c in raw):
        raise MfaError("MFA_NAME", "Unsupported name bytes", name_diagnostics(raw))
    try:
        return safe_relative_path(raw.decode("ascii"))
    except ProfileError as error:
        raise MfaError("MFA_PATH", "Name is not a safe relative path") from error


def _reserve_path(name: str, files: set[str], directories: set[str]) -> None:
    path = name.casefold()
    parts = path.split("/")
    parents = {"/".join(parts[:i]) for i in range(1, len(parts))}
    if path in files or path in directories or parents & files:
        raise MfaError("MFA_DUPLICATE_PATH", "Duplicate or conflicting resource paths")
    files.add(path)
    directories.update(parents)


def inspect_d8(reader: RangeReader, size: int) -> dict:
    """Compatibility entry point; same strict ASCII policy and complete-chain checks."""
    return inspect_layout(reader, size, "d8")


def inspect_layout(reader: RangeReader, size: int, layout: str) -> dict:
    return parse_layout(reader, size, layout).summary


def parse_layout(
    reader: RangeReader, size: int, layout: str, *, name_policy: str = "ascii_paths"
) -> MfaIndex:
    """Check the requested layout only; no retries under a different hypothesis."""
    initial_toc, layout_id = layout_descriptor(layout)
    if name_policy not in ("ascii_paths", "opaque_bytes"):
        raise MfaError("MFA_NAME_POLICY", "Unknown name policy")
    if type(size) is not int or not 0 < size <= (1 << 63) - 1 or size % SECTOR_SIZE:
        raise MfaError("MFA_SIZE", "Unsupported container size")
    blocks = []
    entries = []
    files: set[str] = set()
    directories: set[str] = set()
    base = 0
    total_entries = 0
    total_payload = 0
    while base < size:
        if len(blocks) >= MAX_BLOCKS:
            raise MfaError("MFA_LIMIT", "Block budget exceeded")
        sector = reader.read_at(base, SECTOR_SIZE)
        if len(sector) != SECTOR_SIZE:
            raise ProfileError("SHORT_READ", "Incomplete container metadata sector")
        if base == 0 and all(_plausible_header(sector, toc, size) for toc, _ in LAYOUTS.values()):
            raise MfaError("MFA_AMBIGUOUS_LAYOUT", "Both initial headers are plausible")
        toc = initial_toc if base == 0 else 8
        count, data_size = struct.unpack_from("<II", sector, toc)
        table_end = toc + 8 + count * 16
        if not count or table_end > SECTOR_SIZE:
            raise MfaError("MFA_TABLE", "Unsupported or incomplete entry table")
        total_entries += count
        if total_entries > MAX_ENTRIES:
            raise MfaError("MFA_LIMIT", "Entry budget exceeded")
        end = base + SECTOR_SIZE + data_size
        if not data_size or data_size % SECTOR_SIZE or end > size:
            raise MfaError("MFA_BLOCK_RANGE", "Block data area is outside the container")
        ranges = []
        unknown_words = set()
        payload_bytes = 0
        for index in range(count):
            name_offset, offset, unknown, length = struct.unpack_from(
                "<IIII", sector, toc + 8 + index * 16
            )
            try:
                if name_policy == "opaque_bytes":
                    name = _raw_name(sector, name_offset, table_end)
                else:
                    name = _name(sector, name_offset, table_end)
                    _reserve_path(name, files, directories)
                if offset + length > data_size:
                    raise MfaError("MFA_PAYLOAD_RANGE", "Resource range exceeds its block")
            except MfaError as error:
                error.details.update(
                    block_index=len(blocks),
                    block_offset=base,
                    entry_index=index,
                    entry_ordinal=total_entries - count + index + 1,
                    name_offset=name_offset,
                )
                raise
            if length:
                ranges.append((offset, offset + length))
            unknown_words.add(unknown)
            payload_bytes += length
            entries.append(
                MfaEntry(
                    len(blocks),
                    base,
                    index,
                    total_entries - count + index + 1,
                    name,
                    base + name_offset,
                    base + SECTOR_SIZE + offset,
                    length,
                    unknown,
                )
            )
        ranges.sort()
        if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:], strict=False)):
            raise MfaError("MFA_OVERLAP", "Nonempty resource ranges overlap")
        blocks.append(
            {
                "offset": base,
                "toc_offset": base + toc,
                "data_end": end,
                "entry_count": count,
                "payload_bytes": payload_bytes,
                "unknown_word_values": sorted(unknown_words),
            }
        )
        total_payload += payload_bytes
        base = end
    summary = {
        "status": "structural_candidate",
        "layout": layout_id,
        "blocks": blocks,
        "block_count": len(blocks),
        "entry_count": total_entries,
        "payload_bytes": total_payload,
        "metadata_bytes_read": len(blocks) * SECTOR_SIZE,
    }
    if name_policy == "opaque_bytes":
        summary["name_policy"] = name_policy
    return MfaIndex(summary, tuple(entries))
