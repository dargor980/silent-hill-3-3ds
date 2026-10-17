"""MP01/03-07: own synthetic vmap samples; no emulator or original assets required."""

import json
from dataclasses import replace

import pytest

from tools.inspectors.effective_mapping import (
    EE_RAM_SIZE,
    MASK64,
    PAGE_SIZE,
    SIGN_BIT,
    MappingContext,
    MappingSnapshot,
    PageEntry,
    validate_mapping,
)
from tools.pipeline.profile import ProfileError

CONTEXT = MappingContext("a" * 32, "b" * 64, "c" * 64, 1, "d" * 64)
HOST = 0x100000000
START = 0x1FF8
OFFSET = 0x4FF8
SIZE = 32


def snapshot(start=START, size=SIZE, offset=OFFSET, host=HOST):
    pages = range(start // PAGE_SIZE, (start + size - 1) // PAGE_SIZE + 1)
    return MappingSnapshot(
        CONTEXT,
        True,
        host,
        EE_RAM_SIZE,
        HOST + 0x10000000,
        tuple(PageEntry(page, (host + offset - start) & MASK64) for page in pages),
    )


def check(before=None, after=None, expected=CONTEXT, start=START, size=SIZE, offset=OFFSET):
    before = snapshot() if before is None else before
    return validate_mapping(
        before, before if after is None else after, expected, start, size, offset
    )


def fails(code, **kwargs):
    with pytest.raises(ProfileError) as error:
        check(**kwargs)
    assert error.value.code == code
    assert str(HOST) not in str(error.value)


def test_contiguous_two_pages_and_private_result():
    result = check()
    assert result.physical_offset == OFFSET
    assert result.metadata() == {
        "status": "consistent_supplied_mapping",
        "size": SIZE,
        "page_count": 2,
        "backing": "ee_main_ram",
        "contiguous": True,
        "matches_expected_backing": True,
        "execution_authentication": "not_provided",
        "live_acquisition_verified": False,
    }
    encoded = json.dumps(result.metadata())
    for value in (HOST, START, OFFSET):
        assert str(value) not in encoded
        assert hex(value) not in encoded
    assert "physical_offset" not in repr(result)
    assert "ee_main" not in repr(snapshot())


@pytest.mark.parametrize(
    "start,size,offset",
    [
        (0, 1, 0),
        (0, 4096, 0),
        (4095, 4096, 4095),
        (0xFFFFFFFF, 1, EE_RAM_SIZE - 1),
        (0xFFFFF000, 4096, EE_RAM_SIZE - 4096),
        (0x1000, 1, EE_RAM_SIZE - 1),
    ],
)
def test_range_boundaries(start, size, offset):
    sample = snapshot(start, size, offset)
    result = check(before=sample, start=start, size=size, offset=offset)
    assert result.size == size and result.matches_expected_backing


def test_negative_raw_bias_can_resolve_to_direct_memory():
    start, host, offset = 0xF0000010, 0x10000000, 16
    sample = snapshot(start, 16, offset, host)
    assert sample.pages[0].bias >= SIGN_BIT
    result = check(before=sample, start=start, size=16, offset=offset)
    assert result.physical_offset == 16


def test_alias_is_valid_but_does_not_match_expected_physical_offset():
    sample = snapshot(offset=OFFSET + PAGE_SIZE)
    result = check(before=sample)
    assert result.physical_offset == OFFSET + PAGE_SIZE
    assert result.matches_expected_backing is False
    assert result.metadata()["matches_expected_backing"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("start", -1),
        ("start", 1 << 32),
        ("start", True),
        ("start", "4096"),
        ("size", 0),
        ("size", 4097),
        ("size", True),
        ("size", 1.5),
        ("offset", -1),
        ("offset", EE_RAM_SIZE),
        ("offset", False),
        ("offset", None),
    ],
)
def test_invalid_range_inputs(field, value):
    fails("MAPPING_RANGE", **{field: value})


def test_virtual_end_overflow():
    fails("MAPPING_RANGE", start=0xFFFFFFFF, size=2)


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", "A" * 32),
        ("session_id", "a" * 31),
        ("session_id", 1),
        ("environment_sha256", "b" * 63),
        ("process_sha256", "g" * 64),
        ("state_sha256", "d" * 65),
        ("state_sha256", None),
        ("sequence", True),
        ("sequence", 0),
        ("sequence", 257),
    ],
)
def test_invalid_expected_context(field, value):
    fails("MAPPING_CONTEXT", expected=replace(CONTEXT, **{field: value}))


def test_context_requires_contract_type():
    fails("MAPPING_CONTEXT", expected={})


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", "e" * 32),
        ("environment_sha256", "e" * 64),
        ("process_sha256", "e" * 64),
        ("state_sha256", "e" * 64),
        ("sequence", 2),
        ("sequence", True),
    ],
)
@pytest.mark.parametrize("side", ["before", "after"])
def test_mixed_or_changed_context(field, value, side):
    sample = replace(snapshot(), context=replace(CONTEXT, **{field: value}))
    fails("MAPPING_CONTEXT", **{side: sample})


@pytest.mark.parametrize("value", [False, 1, None, "true"])
@pytest.mark.parametrize("side", ["before", "after"])
def test_pause_must_be_explicit_on_both_sides(value, side):
    fails("MAPPING_PAUSE", **{side: replace(snapshot(), paused=value)})


def test_snapshot_requires_contract_type():
    fails("MAPPING_SNAPSHOT", before={})


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("ee_main", 0, "MAPPING_BACKING"),
        ("ee_main", True, "MAPPING_BACKING"),
        ("ee_main", HOST + 1, "MAPPING_BACKING"),
        ("ee_main", SIGN_BIT - EE_RAM_SIZE + 1, "MAPPING_BACKING"),
        ("exposed_ram_size", 128 * 1024 * 1024, "MAPPING_BACKING"),
        ("exposed_ram_size", True, "MAPPING_BACKING"),
        ("vmap", 0, "MAPPING_TABLE"),
        ("vmap", True, "MAPPING_TABLE"),
        ("vmap", HOST + 1, "MAPPING_TABLE"),
        ("vmap", SIGN_BIT - 8, "MAPPING_TABLE"),
    ],
)
def test_invalid_anchors(field, value, code):
    fails(code, before=replace(snapshot(), **{field: value}))


@pytest.mark.parametrize(
    "pages",
    [
        (),
        (PageEntry(1, HOST),),
        (PageEntry(1, HOST), PageEntry(2, HOST), PageEntry(3, HOST)),
        [PageEntry(1, HOST), PageEntry(2, HOST)],
        (PageEntry(1, HOST), {}),
        (PageEntry(1, HOST), PageEntry(1, HOST)),
        (PageEntry(2, HOST), PageEntry(1, HOST)),
        (PageEntry(True, HOST), PageEntry(2, HOST)),
        (PageEntry(-1, HOST), PageEntry(2, HOST)),
        (PageEntry(1 << 20, HOST), PageEntry(2, HOST)),
    ],
)
def test_exact_coverage(pages):
    fails("MAPPING_COVERAGE", before=replace(snapshot(), pages=pages))


@pytest.mark.parametrize("bias", [-1, 1 << 64, True, "0", None])
def test_invalid_entry_encoding(bias):
    sample = snapshot()
    fails("MAPPING_ENTRY", before=replace(sample, pages=(PageEntry(1, bias), sample.pages[1])))


@pytest.mark.parametrize("index", [0, 1])
def test_handler_is_detected_after_virtual_addition(index):
    sample = snapshot()
    pages = list(sample.pages)
    start = max(START, pages[index].virtual_page * PAGE_SIZE)
    # The raw value is below the sign bit; its sum identifies a handler.
    pages[index] = replace(pages[index], bias=SIGN_BIT - start)
    fails("MAPPING_HANDLER", before=replace(sample, pages=tuple(pages)))


@pytest.mark.parametrize("offset", [-1, EE_RAM_SIZE - SIZE + 1, EE_RAM_SIZE])
def test_full_segment_must_be_inside_exposed_ee_ram(offset):
    fails("MAPPING_BACKING", before=snapshot(offset=offset))


@pytest.mark.parametrize("delta", [-PAGE_SIZE, PAGE_SIZE, 1])
def test_noncontiguous_backing_is_rejected(delta):
    sample = snapshot()
    pages = (sample.pages[0], replace(sample.pages[1], bias=sample.pages[1].bias + delta))
    fails("MAPPING_NONCONTIGUOUS", before=replace(sample, pages=pages))


@pytest.mark.parametrize("field", ["ee_main", "vmap", "pages"])
def test_map_change_during_observation_is_rejected(field):
    sample = snapshot()
    value = snapshot(offset=OFFSET + PAGE_SIZE).pages if field == "pages" else HOST + PAGE_SIZE
    fails("MAPPING_UNSTABLE", after=replace(sample, **{field: value}))


def test_maximum_valid_host_backing_does_not_overflow():
    sample = snapshot(host=SIGN_BIT - EE_RAM_SIZE)
    assert check(before=sample).physical_offset == OFFSET
