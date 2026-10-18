"""Own synthetic payloads; equal final bytes alone must never establish origin."""

import json
from dataclasses import replace

import pytest
from test_observer_acquisition import rejects

from tools.inspectors.load_lineage import (
    MAX_CYCLES,
    Copy,
    Deliver,
    Identity,
    Read,
    Source,
    Stamp,
    Write,
    reconcile_load,
)

IDENTITY = Identity("1" * 32, "2" * 64, "3" * 64)
SOURCE = Source("4" * 64, 1024, 100, b"synthetic-origin")
DATA = SOURCE.payload
A, B = 10000, 20000


def stamp(sequence, cycle=None):
    return Stamp(IDENTITY, sequence, sequence * 10 if cycle is None else cycle)


def read(sequence=1, destination=A, offset=100, data=DATA):
    return Read(stamp(sequence), SOURCE.file_sha256, offset, len(data), destination, data)


def copy(sequence=2, source=A, destination=B, data=DATA):
    return Copy(stamp(sequence), source, destination, data, data)


def deliver(sequence=3, destination=B, data=DATA):
    return Deliver(stamp(sequence), destination, data)


def test_complete_chain_is_deterministic_and_not_live_provenance():
    events = [read(), copy(), deliver()]
    result = reconcile_load(SOURCE, iter(events))
    assert result == reconcile_load(SOURCE, iter(events))
    assert (result["reads"], result["copies"], result["peak_tracked_bytes"]) == (1, 1, 32)
    assert result["active_cycle_span"] == 20
    assert result["disk_read_verified"] is result["mapping_verified"] is False
    assert not result["live_acquisition_verified"] and result["resource_links"] == []
    assert result["capabilities"] == [] and result["load_provenance"].startswith("pending")
    output = json.dumps(result)
    assert (
        DATA.decode() not in output and "destination" not in output and "source_data" not in output
    )
    assert "payload" not in repr(SOURCE) and DATA.decode() not in repr(events)


def test_split_reads_reordered_within_file_assemble_exact_lineage():
    events = [read(1, A + 8, 108, DATA[8:]), read(2, A, 100, DATA[:8]), copy(3), deliver(4)]
    assert reconcile_load(SOURCE, events)["reads"] == 2


def test_read_with_sector_padding_tracks_only_candidate_intersection():
    events = [read(data=b"left" + DATA + b"right", offset=96, destination=A - 4), deliver(2, A)]
    result = reconcile_load(SOURCE, events)
    assert result["peak_tracked_bytes"] == 16 and not result["non_candidate_read_bytes_verified"]


def test_copy_via_multiple_fragments_and_intermediate_buffer():
    events = [read(), copy(2, data=DATA[:7]), copy(3, A + 7, B + 7, DATA[7:]), deliver(4)]
    assert reconcile_load(SOURCE, events)["copies"] == 2


@pytest.mark.parametrize("delta", [-3, 0, 3])
def test_overlap_uses_pre_copy_lineage(delta):
    events = [read(), copy(destination=A + delta), deliver(destination=A + delta)]
    assert reconcile_load(SOURCE, events)["copies"] == 1


def test_external_write_to_other_range_does_not_invalidate_candidate():
    events = [read(), Write(stamp(2), B, b"other"), deliver(3, A)]
    assert reconcile_load(SOURCE, events)["invalidating_writes"] == 1


def test_new_verified_read_can_reestablish_invalidated_lineage():
    events = [read(), Write(stamp(2), A, DATA), read(3), deliver(4, A)]
    assert reconcile_load(SOURCE, events)["reads"] == 2


@pytest.mark.parametrize(
    "events,error",
    [
        ([], "LINEAGE_INCOMPLETE"),
        (None, "LINEAGE_EVENTS"),
        ([object()], "LINEAGE_EVENT"),
        ([read()], "LINEAGE_INCOMPLETE"),
        ([deliver(1, A)], "LINEAGE_GAP"),
        ([copy(1), deliver(2)], "LINEAGE_GAP"),
        ([Write(stamp(1), B, DATA), deliver(2)], "LINEAGE_GAP"),
        ([read(), Write(stamp(2), A, DATA), deliver(3, A)], "LINEAGE_GAP"),
        ([read(), copy(2, B, A), deliver(3, A)], "LINEAGE_GAP"),
        ([read(), read(2, A, 0), deliver(3, A)], "LINEAGE_GAP"),
        ([read(data=DATA[:-1]), deliver(2, A)], "LINEAGE_GAP"),
        ([read(), copy(data=DATA[:-1]), deliver()], "LINEAGE_GAP"),
        ([read(), deliver(2, A), copy(3)], "LINEAGE_ORDER"),
        ([read(), deliver(2, A), deliver(3, A)], "LINEAGE_ORDER"),
        ([replace(read(), stamp=None)], "LINEAGE_STAMP"),
        ([replace(read(), stamp=Stamp(None, 1, 10))], "LINEAGE_STAMP"),
        ([replace(read(), file_sha256="5" * 64)], "LINEAGE_FILE"),
        ([replace(read(), requested=15)], "LINEAGE_READ"),
        ([replace(read(), requested=True)], "LINEAGE_READ"),
        ([read(offset=-1)], "LINEAGE_READ"),
        ([read(offset=1020)], "LINEAGE_READ"),
        ([read(offset=True)], "LINEAGE_READ"),
        ([read(data=b"X" + DATA[1:])], "LINEAGE_READ_DATA"),
        ([read(destination=-1)], "LINEAGE_RAM"),
        ([read(destination=True)], "LINEAGE_RAM"),
        ([read(destination=32 * 1024 * 1024 - 8)], "LINEAGE_RAM"),
        ([read(destination=0x80001000)], "LINEAGE_RAM"),
        ([read(data=b"")], "LINEAGE_DATA"),
        ([read(data=bytes(4097))], "LINEAGE_DATA"),
        ([read(data=bytearray(DATA))], "LINEAGE_DATA"),
        ([read(), copy(source=-1)], "LINEAGE_RAM"),
        ([read(), replace(copy(), source_data=b"X" + DATA[1:])], "LINEAGE_COPY"),
        ([read(), replace(copy(), source_data=bytearray(DATA))], "LINEAGE_COPY"),
        ([read(), copy(data=b"X" + DATA[1:])], "LINEAGE_COPY_DATA"),
        ([read(), deliver(2, A, DATA[:-1])], "LINEAGE_DELIVERY_DATA"),
    ],
)
def test_reject_incomplete_fabricated_or_malformed_events(events, error):
    with rejects(error):
        reconcile_load(SOURCE, events)


@pytest.mark.parametrize(
    "source",
    [
        None,
        replace(SOURCE, file_sha256="not-a-hash"),
        replace(SOURCE, file_sha256=None),
        replace(SOURCE, file_size=True),
        replace(SOURCE, file_size=0),
        replace(SOURCE, file_size=1 << 63),
        replace(SOURCE, offset=-1),
        replace(SOURCE, offset=True),
        replace(SOURCE, offset=1020),
        replace(SOURCE, payload=b""),
        replace(SOURCE, payload=bytearray(DATA)),
        replace(SOURCE, payload=bytes(4097)),
    ],
)
def test_reject_malformed_source(source):
    with rejects("LINEAGE_SOURCE"):
        reconcile_load(source, [])


@pytest.mark.parametrize(
    "identity",
    [
        replace(IDENTITY, session="wrong"),
        replace(IDENTITY, session=1),
        replace(IDENTITY, environment_sha256=None),
        replace(IDENTITY, process_sha256="A" * 64),
    ],
)
def test_reject_bad_identity(identity):
    with rejects("LINEAGE_IDENTITY"):
        reconcile_load(SOURCE, [replace(read(), stamp=Stamp(identity, 1, 10))])


@pytest.mark.parametrize(
    "field,value",
    [("session", "9" * 32), ("environment_sha256", "9" * 64), ("process_sha256", "9" * 64)],
)
def test_reject_mixed_identity(field, value):
    bad = replace(deliver(2, A), stamp=Stamp(replace(IDENTITY, **{field: value}), 2, 20))
    with rejects("LINEAGE_IDENTITY"):
        reconcile_load(SOURCE, [read(), bad])


@pytest.mark.parametrize("sequence", [True, 0, 2, "1"])
def test_reject_sequence(sequence):
    with rejects("LINEAGE_SEQUENCE"):
        reconcile_load(SOURCE, [replace(read(), stamp=Stamp(IDENTITY, sequence, 0))])


@pytest.mark.parametrize("cycle", [True, -1, 1 << 64, "1"])
def test_reject_cycle_type_range(cycle):
    with rejects("LINEAGE_CYCLE"):
        reconcile_load(SOURCE, [replace(read(), stamp=stamp(1, cycle))])


@pytest.mark.parametrize("cycle", [9, 10, 10 + MAX_CYCLES + 1])
def test_reject_nonincreasing_or_exhausted_cycles(cycle):
    with rejects("LINEAGE_CYCLE"):
        reconcile_load(SOURCE, [read(), replace(deliver(2, A), stamp=stamp(2, cycle))])


def test_active_budget_inclusive_boundary():
    result = reconcile_load(
        SOURCE, [read(), replace(deliver(2, A), stamp=stamp(2, 10 + MAX_CYCLES))]
    )
    assert result["active_cycle_span"] == MAX_CYCLES


def test_equal_repeated_bytes_still_require_correct_source_offsets():
    source = replace(SOURCE, payload=b"a" * 16)
    events = [
        read(data=b"a" * 16),
        copy(source=A + 8, data=b"a" * 8),
        copy(3, A, B + 8, b"a" * 8),
        deliver(4, B, b"a" * 16),
    ]
    with rejects("LINEAGE_GAP"):
        reconcile_load(source, events)


def test_event_budget_is_bounded_and_inclusive():
    good = [read()] + [Write(stamp(i), B, b"x") for i in range(2, 256)] + [deliver(256, A)]
    assert len(reconcile_load(SOURCE, good)["events"]) == 256

    def excessive():
        yield read()
        for i in range(2, 258):
            assert i <= 257  # The iterator must not be drained after its first excess.
            yield Write(stamp(i), B, b"x")
        pytest.fail("unbounded event consumption")

    with rejects("LINEAGE_BUDGET"):
        reconcile_load(SOURCE, excessive())


def test_tracked_byte_budget_and_overwrite_releases_capacity():
    source = replace(SOURCE, file_size=4096, offset=0, payload=bytes(4096))
    events = [Read(stamp(1), source.file_sha256, 0, 4096, 0, source.payload)]
    events += [
        Copy(stamp(i), 0, (i - 1) * 4096, source.payload, source.payload) for i in range(2, 5)
    ]
    result = reconcile_load(source, events + [Deliver(stamp(5), 12288, source.payload)])
    assert result["peak_tracked_bytes"] == 16384
    extra = Copy(stamp(5), 0, 16384, source.payload, source.payload)
    with rejects("LINEAGE_TRACKED_BUDGET"):
        reconcile_load(source, events + [extra])
    events += [
        Write(stamp(5), 12288, source.payload),
        replace(extra, stamp=stamp(6)),
        Deliver(stamp(7), 16384, source.payload),
    ]
    assert reconcile_load(source, events)["peak_tracked_bytes"] == 16384
