"""Validate a completed two-channel steady observation, never a transition.

The caller authenticates sources, masks and the consumer-return boundary.
This checker separates the returned counter from the phase just evaluated.
It neither grants runtime clip support nor proves an uninterrupted cycle.
"""

import struct
from dataclasses import dataclass

from tools.qa.animation_pose_oracle import ClipStep, clip_step


@dataclass(frozen=True)
class SteadyChannel:
    source: bytes
    target: bytes
    counter: int
    increment: int
    mode: int
    blend: int
    speed_offset: int


@dataclass(frozen=True)
class ObservedSample:
    clip_id: int
    pose_counter: int
    returned_counter: int
    step: ClipStep


def steady_sample(
    channels: tuple[SteadyChannel, SteadyChannel], *, ticks: int, sample_capacity: int
) -> ObservedSample:
    """Reject unsupported/ambiguous state before returning any interpretation."""
    if (
        type(channels) is not tuple
        or len(channels) != 2
        or any(type(c) is not SteadyChannel for c in channels)
    ):
        raise ValueError("STEADY_CHANNELS")
    if type(ticks) is not int or ticks != 2:
        raise ValueError("STEADY_TICKS")
    if type(sample_capacity) is not int or not 1 <= sample_capacity <= 4096:
        raise ValueError("STEADY_CAPACITY")
    for c in channels:
        if (
            type(c.source) is not bytes
            or type(c.target) is not bytes
            or len(c.source) != 12
            or len(c.target) != 12
        ):
            raise ValueError("STEADY_DESCRIPTOR_BYTES")
        if any(
            type(v) is not int for v in (c.counter, c.increment, c.mode, c.blend, c.speed_offset)
        ):
            raise ValueError("STEADY_INTEGER")
        if c.mode != 1 or c.blend != 0 or c.speed_offset != 0 or c.source != c.target:
            raise ValueError("STEADY_STATE")
    if channels[0] != channels[1]:
        raise ValueError("STEADY_CHANNEL_MISMATCH")
    c = channels[0]
    clip, count, speed, start, end, loop, trailing = struct.unpack("<HHhHHBB", c.target)
    if (
        clip == 0
        or not 0 <= start <= end < sample_capacity
        or count != end - start + 1
        or loop != 1
        or trailing != 0
        or not 0 < speed * ticks <= 32767
    ):
        raise ValueError("STEADY_DESCRIPTOR")
    period = count * 4096
    if not 0 <= c.counter < period or c.increment != speed * ticks:
        raise ValueError("STEADY_CLOCK")
    phase = (c.counter - c.increment) % period
    step = clip_step(start, end, True, phase, speed, ticks)
    if step.next_counter != c.counter:
        raise ValueError("STEADY_RETURN")
    return ObservedSample(clip, phase, c.counter, step)
