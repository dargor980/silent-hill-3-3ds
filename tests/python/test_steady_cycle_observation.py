"""Synthetic acquisition corruption controls; no original resources required."""
from dataclasses import replace
import struct

import pytest

from tools.qa.steady_clip_observation import SteadyChannel
from tools.qa.steady_cycle_observation import CycleObservation, full_cycle


def series():
    descriptor = struct.pack('<HHhHHBB', 107, 10, 1152, 60, 69, 1, 0)
    result = []
    for i in range(19):
        c = SteadyChannel(descriptor, descriptor, (i+1)*2304 % 40960,
                          2304, 1, 0, 0)
        result.append(CycleObservation(100+i, 1000+3*i, (c, c)))
    return result


def check(rows):
    return full_cycle(rows, ticks=2, sample_capacity=100)


def test_complete_cycle_including_wrap():
    assert check(series()) == 41472


@pytest.mark.parametrize('size', [0, 1, 2, 18])
def test_incomplete_cycle(size):
    with pytest.raises(ValueError, match='CYCLE_INCOMPLETE'):
        check(series()[:size])


@pytest.mark.parametrize('field,value', [('ordinal', True), ('ordinal', -1),
                                      ('cycle', True), ('cycle', -1)])
def test_invalid_metadata(field, value):
    rows = series(); rows[3] = replace(rows[3], **{field: value})
    with pytest.raises(ValueError, match='CYCLE_METADATA'):
        check(rows)


def test_invalid_record():
    rows = series(); rows[0] = None
    with pytest.raises(ValueError, match='CYCLE_METADATA'):
        check(rows)


@pytest.mark.parametrize('field,value', [('ordinal', 104), ('ordinal', 102),
                                      ('cycle', 1006), ('cycle', 1)])
def test_gap_duplicate_or_reversed_time(field, value):
    rows = series(); rows[3] = replace(rows[3], **{field: value})
    with pytest.raises(ValueError, match='CYCLE_GAP'):
        check(rows)


@pytest.mark.parametrize('change', ['clip', 'speed', 'phase', 'layer', 'blend'])
def test_reject_changed_clip_phase_or_incomplete_consumer(change):
    rows = series(); c = rows[3].channels[0]
    expected = {'clip': 'CYCLE_CHANGED', 'speed': 'CYCLE_CHANGED',
                'phase': 'CYCLE_PHASE', 'layer': 'STEADY_CHANNEL_MISMATCH',
                'blend': 'STEADY_STATE'}[change]
    if change == 'clip':
        d = struct.pack('<HHhHHBB',108,10,1152,70,79,1,0)
        c = replace(c, source=d, target=d)
    elif change == 'speed':
        d = struct.pack('<HHhHHBB',107,10,1000,60,69,1,0)
        c = replace(c, source=d, target=d, increment=2000)
    elif change in ('phase', 'layer'):
        c = replace(c, counter=c.counter+1)
    else:
        c = replace(c, mode=3, blend=768)
    rows[3] = replace(rows[3], channels=(c, rows[3].channels[1] if change=='layer' else c))
    with pytest.raises(ValueError, match=expected):
        check(rows)
