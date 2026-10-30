"""Invented three-frame loop and adversarial channel observations; no game data."""

import struct
from dataclasses import replace

import pytest

from tools.qa.steady_clip_observation import SteadyChannel, steady_sample


def channel(**changes):
    descriptor = struct.pack("<HHhHHBB", 7, 3, 128, 11, 13, 1, 0)
    return replace(SteadyChannel(descriptor, descriptor, 256, 256, 1, 0, 0), **changes)


def observe(c=None, **kwargs):
    c = channel() if c is None else c
    return steady_sample(
        (c, c), ticks=kwargs.get("ticks", 2), sample_capacity=kwargs.get("sample_capacity", 32)
    )


@pytest.mark.parametrize(
    "returned,phase,current,following,fraction",
    [
        (0, 12032, 13, 11, 0.9375),
        (256, 0, 11, 12, 0),
        (8192, 7936, 12, 13, 0.9375),
    ],
)
def test_phase_precedes_return_and_wrap_stays_inside_clip(
    returned, phase, current, following, fraction
):
    c = channel(counter=returned)
    before = repr(c)
    result = observe(c)
    assert result.clip_id == 7 and result.pose_counter == phase
    assert result.returned_counter == result.step.next_counter == returned
    assert (result.step.current, result.step.following, result.step.fraction) == (
        current,
        following,
        fraction,
    )
    assert not result.step.stopped and repr(c) == before


@pytest.mark.parametrize(
    "channels",
    [None, [], (), (channel(),), (channel(),) * 3, [channel(), channel()], (channel(), None)],
)
def test_two_explicit_immutable_channels_required(channels):
    with pytest.raises(ValueError, match="STEADY_CHANNELS"):
        steady_sample(channels, ticks=2, sample_capacity=32)


@pytest.mark.parametrize("ticks", [True, False, 0, 1, 3, -1, 2.0, None])
def test_only_pinned_tick_profile(ticks):
    with pytest.raises(ValueError, match="STEADY_TICKS"):
        observe(ticks=ticks)


@pytest.mark.parametrize("capacity", [True, 0, -1, 4097, 32.0, None])
def test_capacity_checked(capacity):
    with pytest.raises(ValueError, match="STEADY_CAPACITY"):
        observe(sample_capacity=capacity)


@pytest.mark.parametrize("field", ["source", "target"])
@pytest.mark.parametrize("value", [None, bytearray(12), b"", bytes(11), bytes(13)])
def test_exact_immutable_descriptor(field, value):
    with pytest.raises(ValueError, match="STEADY_DESCRIPTOR_BYTES"):
        observe(channel(**{field: value}))


@pytest.mark.parametrize("field", ["counter", "increment", "mode", "blend", "speed_offset"])
@pytest.mark.parametrize("value", [True, 0.0, None])
def test_integer_fields_reject_coercion(field, value):
    with pytest.raises(ValueError, match="STEADY_INTEGER"):
        observe(channel(**{field: value}))


@pytest.mark.parametrize(
    "changes",
    [dict(mode=3), dict(mode=5), dict(blend=1), dict(speed_offset=-1), dict(source=bytes(12))],
)
def test_transition_or_offset_cannot_be_treated_as_stable(changes):
    with pytest.raises(ValueError, match="STEADY_STATE"):
        observe(channel(**changes))


@pytest.mark.parametrize("changes", [dict(counter=512), dict(increment=512)])
def test_channels_must_agree(changes):
    with pytest.raises(ValueError, match="STEADY_CHANNEL_MISMATCH"):
        steady_sample((channel(), channel(**changes)), ticks=2, sample_capacity=32)


@pytest.mark.parametrize(
    "index,value",
    [
        (0, 0),
        (1, 0),
        (1, 2),
        (2, 0),
        (2, -128),
        (2, 16384),
        (3, 14),
        (4, 32),
        (5, 0),
        (5, 2),
        (6, 1),
    ],
)
def test_descriptor_anomalies_are_rejected_not_repaired(index, value):
    fields = [7, 3, 128, 11, 13, 1, 0]
    fields[index] = value
    raw = struct.pack("<HHhHHBB", *fields)
    with pytest.raises(ValueError, match="STEADY_DESCRIPTOR"):
        observe(channel(source=raw, target=raw))


@pytest.mark.parametrize(
    "changes", [dict(counter=-1), dict(counter=12288), dict(increment=0), dict(increment=257)]
)
def test_clock_out_of_range_or_wrong_increment(changes):
    with pytest.raises(ValueError, match="STEADY_CLOCK"):
        observe(channel(**changes))


def test_oracle_inconsistency_cannot_publish_observation(monkeypatch):
    from tools.qa import steady_clip_observation as subject

    real = subject.clip_step
    monkeypatch.setattr(subject, "clip_step", lambda *args: replace(real(*args), next_counter=999))
    with pytest.raises(ValueError, match="STEADY_RETURN"):
        observe()
