"""MP01/03-07: pure validation of supplied vmap samples, not live acquisition."""

import re
from dataclasses import dataclass

from tools.inspectors.observation_capture import require

PAGE_SIZE = 4096
EE_RAM_SIZE = 32 * 1024 * 1024
SIGN_BIT = 1 << 63
MASK64 = (1 << 64) - 1


@dataclass(frozen=True, repr=False)
class MappingContext:
    session_id: str
    environment_sha256: str
    process_sha256: str
    sequence: int
    state_sha256: str


@dataclass(frozen=True, repr=False)
class PageEntry:
    virtual_page: int
    bias: int


@dataclass(frozen=True, repr=False)
class MappingSnapshot:
    context: MappingContext
    paused: bool
    ee_main: int
    exposed_ram_size: int
    vmap: int
    pages: tuple[PageEntry, ...]


@dataclass(frozen=True, repr=False)
class MappingResult:
    """The physical offset is private; only metadata() is suitable for a report."""

    physical_offset: int
    size: int
    page_count: int
    matches_expected_backing: bool

    def metadata(self) -> dict:
        return {
            "status": "consistent_supplied_mapping",
            "size": self.size,
            "page_count": self.page_count,
            "backing": "ee_main_ram",
            "contiguous": True,
            "matches_expected_backing": self.matches_expected_backing,
            "execution_authentication": "not_provided",
            "live_acquisition_verified": False,
        }


def integer(value, low, high, code):
    require(type(value) is int and low <= value <= high, code)


def validate_context(context):
    require(type(context) is MappingContext, "MAPPING_CONTEXT")
    for value, length in (
        (context.session_id, 32),
        (context.environment_sha256, 64),
        (context.process_sha256, 64),
        (context.state_sha256, 64),
    ):
        require(
            isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is not None,
            "MAPPING_CONTEXT",
        )
    integer(context.sequence, 1, 256, "MAPPING_CONTEXT")


def validate_snapshot(snapshot, expected, pages):
    require(type(snapshot) is MappingSnapshot, "MAPPING_SNAPSHOT")
    validate_context(snapshot.context)
    require(snapshot.context == expected, "MAPPING_CONTEXT")
    require(snapshot.paused is True, "MAPPING_PAUSE")
    integer(snapshot.ee_main, PAGE_SIZE, SIGN_BIT - EE_RAM_SIZE, "MAPPING_BACKING")
    integer(snapshot.exposed_ram_size, EE_RAM_SIZE, EE_RAM_SIZE, "MAPPING_BACKING")
    require(snapshot.ee_main % PAGE_SIZE == 0, "MAPPING_BACKING")
    integer(snapshot.vmap, 8, SIGN_BIT - (1 << 20) * 8, "MAPPING_TABLE")
    require(snapshot.vmap % 8 == 0, "MAPPING_TABLE")
    require(
        type(snapshot.pages) is tuple
        and len(snapshot.pages) == len(pages)
        and all(type(entry) is PageEntry for entry in snapshot.pages),
        "MAPPING_COVERAGE",
    )
    for entry, page in zip(snapshot.pages, pages, strict=True):
        integer(entry.virtual_page, 0, (1 << 20) - 1, "MAPPING_COVERAGE")
        require(entry.virtual_page == page, "MAPPING_COVERAGE")
        integer(entry.bias, 0, MASK64, "MAPPING_ENTRY")


def validate_mapping(
    before: MappingSnapshot,
    after: MappingSnapshot,
    expected: MappingContext,
    virtual_start: int,
    size: int,
    expected_offset: int,
) -> MappingResult:
    """Resolve every requested segment; do not normalize aliases or trust byte equality."""
    validate_context(expected)
    integer(virtual_start, 0, (1 << 32) - 1, "MAPPING_RANGE")
    integer(size, 1, PAGE_SIZE, "MAPPING_RANGE")
    end = virtual_start + size
    require(end <= 1 << 32, "MAPPING_RANGE")
    integer(expected_offset, 0, EE_RAM_SIZE - size, "MAPPING_RANGE")
    pages = range(virtual_start // PAGE_SIZE, (end - 1) // PAGE_SIZE + 1)
    for snapshot in (before, after):
        validate_snapshot(snapshot, expected, pages)
    require(before == after, "MAPPING_UNSTABLE")
    first = None
    for entry in before.pages:
        start = max(virtual_start, entry.virtual_page * PAGE_SIZE)
        stop = min(end, (entry.virtual_page + 1) * PAGE_SIZE)
        pointer = (entry.bias + start) & MASK64
        require(pointer < SIGN_BIT, "MAPPING_HANDLER")
        offset = pointer - before.ee_main
        require(0 <= offset <= EE_RAM_SIZE - (stop - start), "MAPPING_BACKING")
        if first is None:
            first = offset
        require(offset == first + start - virtual_start, "MAPPING_NONCONTIGUOUS")
    return MappingResult(first, size, len(pages), first == expected_offset)
