"""Own metadata examples; no game table or resource is used by this suite."""

import struct
from dataclasses import FrozenInstanceError

import pytest

from tools.inspectors.animation_descriptors import inventory_descriptors


def record(clip=7, count=3, speed=512, start=2, end=4, loop=1, trailing=0):
    return struct.pack("<HHhHHBB", clip, count, speed, start, end, loop, trailing)


def test_literal_little_endian_vector_and_lossless_fields():
    raw = bytes.fromhex("3412030000fe020004000122")
    (item,) = inventory_descriptors(raw + bytes(12), sample_capacity=5)
    assert (item.clip_id, item.sample_count, item.speed) == (0x1234, 3, -512)
    assert (item.start, item.end, item.loop_byte, item.trailing_byte) == (2, 4, 1, 34)
    assert item.raw == raw
    assert item.observations == ("nonpositive_speed", "nonzero_trailing_byte")
    with pytest.raises(FrozenInstanceError):
        item.speed = 1


def test_order_and_overlapping_ranges_are_preserved_without_action_names():
    raw = record(9) + record(2, start=3, end=5) + bytes(12)
    items = inventory_descriptors(raw, sample_capacity=6)
    assert [item.clip_id for item in items] == [9, 2]
    assert all(item.observations == () for item in items)
    assert b"".join(item.raw for item in items) + bytes(12) == raw


@pytest.mark.parametrize(
    "changes,observations",
    [
        ({"count": 0}, ("empty_count",)),
        ({"count": 2}, ("count_range_mismatch",)),
        ({"start": 5, "end": 2}, ("reversed_range",)),
        ({"end": 9, "count": 8}, ("range_outside_resource",)),
        ({"start": 9, "end": 2}, ("reversed_range", "range_outside_resource")),
        ({"speed": 0}, ("nonpositive_speed",)),
        ({"loop": 255}, ("unknown_loop_byte",)),
        ({"trailing": 255}, ("nonzero_trailing_byte",)),
        ({"count": 0, "start": 8, "end": 9}, ("empty_count", "range_outside_resource")),
    ],
)
def test_semantic_anomalies_are_preserved_not_repaired(changes, observations):
    raw = record(**changes)
    (item,) = inventory_descriptors(raw + bytes(12), sample_capacity=8)
    assert item.raw == raw and item.observations == observations


@pytest.mark.parametrize("capacity", [0, -1, 4097, True, 5.0, None])
def test_capacity_is_explicit_and_bounded(capacity):
    with pytest.raises(ValueError, match="capacity"):
        inventory_descriptors(record() + bytes(12), sample_capacity=capacity)


@pytest.mark.parametrize("raw", [bytearray(24), memoryview(bytes(24)), None, ""])
def test_mutable_or_nonbyte_input_rejected(raw):
    with pytest.raises(ValueError, match="immutable"):
        inventory_descriptors(raw, sample_capacity=8)


@pytest.mark.parametrize("size", [0, 12, 23, 25, 6157, 6168])
def test_truncated_empty_and_excessive_tables_rejected(size):
    with pytest.raises(ValueError, match="size"):
        inventory_descriptors(bytes(size), sample_capacity=8)


@pytest.mark.parametrize(
    "raw",
    [
        record() + bytes(11) + b"\x01",
        record() + record(8),
        bytes(12) + record() + bytes(12),
        record(0) + bytes(12),
        record() + record() + bytes(12),
        record() + bytes(24),
    ],
)
def test_bad_terminator_and_duplicate_ids_rejected_atomically(raw):
    with pytest.raises(ValueError):
        inventory_descriptors(raw, sample_capacity=8)


def test_maximum_table_and_sample_boundaries():
    raw = b"".join(record(i + 1, 1, 32767, 4095, 4095, 0) for i in range(512)) + bytes(12)
    items = inventory_descriptors(raw, sample_capacity=4096)
    assert len(items) == 512 and all(item.observations == () for item in items)
    single = record(65535, 1, -32768, 0, 0, 0) + bytes(12)
    (item,) = inventory_descriptors(single, sample_capacity=1)
    assert item.speed == -32768 and item.raw == single[:12]
