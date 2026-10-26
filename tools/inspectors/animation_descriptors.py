"""Bounded, lossless inventory of clip metadata; never authorizes playback."""

import struct
from dataclasses import dataclass

_RECORD = struct.Struct("<HHhHHBB")
MAX_RECORDS = 512
MAX_SAMPLES = 4096


@dataclass(frozen=True)
class AnimationDescriptor:
    clip_id: int
    sample_count: int
    speed: int
    start: int
    end: int
    loop_byte: int
    trailing_byte: int
    raw: bytes
    observations: tuple[str, ...]


def inventory_descriptors(data: bytes, *, sample_capacity: int) -> tuple[AnimationDescriptor, ...]:
    """Read a caller-delimited table ending in exactly one all-zero record.

    Preserve semantic anomalies as observations, not repaired data. The caller
    owns table/resource association, address mapping and source provenance.
    """
    if type(data) is not bytes:
        raise ValueError("Descriptor input must be immutable bytes")
    if type(sample_capacity) is not int or not 1 <= sample_capacity <= MAX_SAMPLES:
        raise ValueError("Sample capacity outside inventory bounds")
    if not 24 <= len(data) <= (MAX_RECORDS + 1) * 12 or len(data) % 12:
        raise ValueError("Descriptor table size outside inventory bounds")
    if data[-12:] != bytes(12):
        raise ValueError("Missing exact zero terminator")
    result = []
    ids: set[int] = set()
    for offset in range(0, len(data) - 12, 12):
        raw = data[offset : offset + 12]
        clip_id, count, speed, start, end, loop, trailing = _RECORD.unpack(raw)
        if clip_id == 0 or clip_id in ids:
            raise ValueError("Premature terminator, zero ID or duplicate ID")
        ids.add(clip_id)
        observations = []
        if count == 0:
            observations.append("empty_count")
        if start > end:
            observations.append("reversed_range")
        elif count != 0 and count != end - start + 1:
            observations.append("count_range_mismatch")
        if max(start, end) >= sample_capacity:
            observations.append("range_outside_resource")
        if speed <= 0:
            observations.append("nonpositive_speed")
        if loop not in (0, 1):
            observations.append("unknown_loop_byte")
        if trailing != 0:
            observations.append("nonzero_trailing_byte")
        result.append(
            AnimationDescriptor(
                clip_id, count, speed, start, end, loop, trailing, raw, tuple(observations)
            )
        )
    return tuple(result)
