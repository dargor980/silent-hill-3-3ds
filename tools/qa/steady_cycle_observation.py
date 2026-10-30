"""Require a complete, consecutive stable cycle; this is an observation gate."""
from dataclasses import dataclass

from tools.qa.steady_clip_observation import SteadyChannel, steady_sample


@dataclass(frozen=True)
class CycleObservation:
    ordinal: int
    cycle: int
    channels: tuple[SteadyChannel, SteadyChannel]


def full_cycle(observations, *, ticks, sample_capacity):
    """Return total Q12 advance after validating at least one whole period.

    No restoration, session identity or payload authentication can be proved
    here. The acquisition adapter must establish those independently.
    """
    if len(observations) < 2:
        raise ValueError("CYCLE_INCOMPLETE")
    samples = []
    for observation in observations:
        if (type(observation) is not CycleObservation
                or type(observation.ordinal) is not int or observation.ordinal < 0
                or type(observation.cycle) is not int or observation.cycle < 0):
            raise ValueError("CYCLE_METADATA")
        samples.append(steady_sample(observation.channels, ticks=ticks,
                                     sample_capacity=sample_capacity))
    first = observations[0].channels[0]
    # A descriptor is already validated by steady_sample; count is little endian.
    period = int.from_bytes(first.target[2:4], "little") * 4096
    advance = 0
    for index in range(1, len(observations)):
        previous, current = observations[index-1:index+1]
        before, after = samples[index-1:index+1]
        channel = current.channels[0]
        if current.ordinal != previous.ordinal + 1 or current.cycle <= previous.cycle:
            raise ValueError("CYCLE_GAP")
        if channel.target != first.target or channel.increment != first.increment:
            raise ValueError("CYCLE_CHANGED")
        if after.pose_counter != (before.pose_counter + channel.increment) % period:
            raise ValueError("CYCLE_PHASE")
        advance += channel.increment
    if advance < period:
        raise ValueError("CYCLE_INCOMPLETE")
    return advance
