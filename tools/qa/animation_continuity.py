"""Reconcile metadata from consecutive, forward, single-clip consumer returns.

The recorder owns provenance: an ordinal represents one observed resume/stop,
not an emulator hit counter or proof that the VM was never modified. Pose
comparison remains the responsibility of the independent pose oracle.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from tools.qa.animation_pose_oracle import ClipStep, clip_step


@dataclass(frozen=True)
class ClockReturn:
    ordinal: int
    cycle: int
    identity: str
    counter: int
    ticks: int
    speed_offset: int
    increment: int
    mode: int
    frame: int
    following: int


@dataclass(frozen=True)
class ClockContinuity:
    steps: tuple[ClipStep, ...]
    wraps: int
    advanced_units: int
    full_loop: bool


def reconcile_loop(
    samples: Sequence[ClockReturn], *, start: int, end: int, speed: int
) -> ClockContinuity:
    """Validate one stable looping clip; derive each pose's input from the prior return.

    Identity must bind session, actor, resource addresses/hashes and descriptor.
    The first return anchors the counter; its already-computed pose is not inferred.
    A wrap alone does not certify a whole loop: accumulated advance must span the
    inclusive clip length. Emulated cycles only establish ordering, never wall FPS.
    """
    if len(samples) < 2:
        raise ValueError("At least two consumer returns are required")
    if any(type(value) is not int for value in (start, end, speed)):
        raise ValueError("Clip metadata must contain integers")
    first = samples[0]
    if not isinstance(first.identity, str) or not first.identity:
        raise ValueError("Missing observation identity")
    steps: list[ClipStep] = []
    advanced, wraps = 0, 0
    for index, sample in enumerate(samples):
        numbers = (
            sample.ordinal,
            sample.cycle,
            sample.counter,
            sample.ticks,
            sample.speed_offset,
            sample.increment,
            sample.mode,
            sample.frame,
            sample.following,
        )
        if any(type(value) is not int for value in numbers):
            raise ValueError("Clock metadata must contain integers")
        if sample.ordinal < 0 or sample.cycle < 0 or sample.identity != first.identity:
            raise ValueError("Observation identity or position changed")
        if sample.mode != 1 or not -32768 <= sample.speed_offset <= 32767:
            raise ValueError("Expected steady forward mode and signed speed offset")
        if not 0 <= sample.increment <= 32767:
            raise ValueError("Increment outside the observed signed forward range")
        if not start <= sample.frame <= end or not start <= sample.following <= end:
            raise ValueError("Sample indices outside the clip")
        # Check even the anchor's counter and clock bounds without claiming its input.
        clip_step(start, end, True, sample.counter, speed + sample.speed_offset, sample.ticks)
        if not index:
            continue
        previous = samples[index - 1]
        if sample.ordinal != previous.ordinal + 1 or sample.cycle <= previous.cycle:
            raise ValueError("Missing, repeated, or reordered consumer return")
        step = clip_step(
            start, end, True, previous.counter, speed + sample.speed_offset, sample.ticks
        )
        increment = (speed + sample.speed_offset) * sample.ticks
        if (sample.counter, sample.increment, sample.frame, sample.following) != (
            step.next_counter,
            increment,
            step.current,
            step.following,
        ):
            raise ValueError("Clock or sample discontinuity")
        advanced += increment
        wraps += int(previous.counter + increment >= (end - start + 1) * 4096)
        steps.append(step)
    return ClockContinuity(tuple(steps), wraps, advanced, advanced >= (end - start + 1) * 4096)
