"""Synthetic clock traces; no game, private save, or emulator dependency."""

from dataclasses import replace

import pytest

from tools.qa.animation_continuity import ClockReturn, reconcile_loop


def trace():
    # Three samples, starting halfway through the last sample. Six half-sample
    # increments make a full turn, including one wrap.
    counters = [10240, 0, 2048, 4096, 6144, 8192, 10240]
    frames = [2, 2, 0, 0, 1, 1, 2]
    following = [0, 0, 1, 1, 2, 2, 0]
    return [
        ClockReturn(i, 100 + i * 10, "session-actor-resources-clip", c, 2, -512, 2048, 1, f, n)
        for i, (c, f, n) in enumerate(zip(counters, frames, following, strict=True))
    ]


def test_full_loop_and_fraction_from_previous_return():
    result = reconcile_loop(trace(), start=0, end=2, speed=1536)
    assert result.full_loop and result.advanced_units == 12288
    assert result.wraps == 1
    assert result.steps[0].current == 2 and result.steps[0].following == 0
    assert result.steps[0].fraction == 0.5
    assert result.steps[-1].fraction == 0


def test_wrap_is_not_a_complete_loop():
    result = reconcile_loop(trace()[:2], start=0, end=2, speed=1536)
    assert result.wraps == 1 and not result.full_loop


def test_ticks_can_vary_and_wall_pause_is_not_a_clock_reset():
    a = ClockReturn(40, 10, "same", 0, 1, 0, 0, 1, 5, 6)
    b = ClockReturn(41, 1000, "same", 3072, 3, 0, 3072, 1, 5, 6)
    c = ClockReturn(42, 1001, "same", 3072, 0, 0, 0, 1, 5, 6)
    result = reconcile_loop([a, b, c], start=5, end=6, speed=1024)
    assert result.advanced_units == 3072 and not result.full_loop
    assert result.steps[-1].fraction == 0.75


@pytest.mark.parametrize(
    "changes",
    [
        {"identity": "reused-actor"},
        {"ordinal": 0},
        {"ordinal": 2},
        {"cycle": 100},
        {"cycle": 99},
        {"counter": 1},
        {"increment": 2049},
        {"increment": -1},
        {"increment": 32768},
        {"frame": 0},
        {"following": 1},
        {"mode": 255},
        {"speed_offset": -32769},
        {"speed_offset": -1536},
        {"speed_offset": 32768},
        {"ticks": 4},
        {"ticks": True},
        {"frame": 3},
        {"following": -1},
        {"cycle": -1},
    ],
)
def test_reject_discontinuity_or_invalid_metadata(changes):
    samples = trace()
    samples[1] = replace(samples[1], **changes)
    with pytest.raises(ValueError):
        reconcile_loop(samples, start=0, end=2, speed=1536)


def test_reject_missing_return_even_when_cycle_still_increases():
    samples = trace()
    del samples[2]
    with pytest.raises(ValueError):
        reconcile_loop(samples, start=0, end=2, speed=1536)


@pytest.mark.parametrize("samples", [[], trace()[:1]])
def test_reject_no_comparison(samples):
    with pytest.raises(ValueError):
        reconcile_loop(samples, start=0, end=2, speed=1536)


@pytest.mark.parametrize("identity", ["", None])
def test_reject_missing_identity(identity):
    samples = [replace(s, identity=identity) for s in trace()]
    with pytest.raises(ValueError):
        reconcile_loop(samples, start=0, end=2, speed=1536)


def test_reject_invalid_anchor():
    for changes in [{"ordinal": -1}, {"counter": 12288}, {"mode": 0}, {"frame": -1}]:
        samples = trace()
        samples[0] = replace(samples[0], **changes)
        with pytest.raises(ValueError):
            reconcile_loop(samples, start=0, end=2, speed=1536)


@pytest.mark.parametrize(
    "clip",
    [
        {"start": True, "end": 2, "speed": 1536},
        {"start": 0, "end": 2.0, "speed": 1536},
        {"start": 0, "end": 2, "speed": "1536"},
    ],
)
def test_reject_noninteger_descriptor(clip):
    with pytest.raises(ValueError):
        reconcile_loop(trace(), **clip)
