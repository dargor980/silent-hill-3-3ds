"""DA05-09: one save, independent wire queues, real custody composition."""

import json
import struct
from dataclasses import replace

import pytest
from test_load_call import pause
from test_observer_acquisition import Clock, Guard, Store, rejects
from test_observer_capture import packed

from tools.inspectors.observer_multirange import (
    RegionPlan,
    acquire_regions_and_publish,
    acquire_regions_local,
    validate_regions,
)
from tools.pipeline.profile import ProfileError


def source(count=2):
    if count == 2:
        return pause()
    p = pause()[0]
    result = []
    for i in range(count):
        request = replace(p.plan.request, sequence=i + 1)
        plan = replace(p.plan, request=request, context=replace(p.plan.context, sequence=i + 1))
        packet = bytearray(p.packets[0])
        struct.pack_into("<I", packet, 29, i + 1)
        result.append(replace(p, label=chr(97 + i), plan=plan, packets=(bytes(packet),) * 3))
    return tuple(result)


class Channel:
    def __init__(self, points, store, pending=0):
        self.points, self.store = points, store
        self.open = self.closed = False
        self.close_error = False
        self.pid = points[0].plan.pid
        self.calls = []
        first = points[0].plan
        self.queue = []
        crc = struct.pack("<I", 9) + f"{first.crc:08x}".encode() + b"\0"
        ids = [(b"\x0f", struct.pack("<I", 1)), (b"\x0d", crc)]

        def identity():
            self.queue.extend((b, struct.pack("<IB", 5 + len(r), 0) + r) for b, r in ids)

        identity()
        self.queue.extend((p.plan.request.encode()[4:], p.packets[0]) for p in points)
        self.queue.append((bytes([9, first.slot]), struct.pack("<IB", 5, 0)))
        self.queue.extend(
            (first.request.encode()[4:], packed(first.request, status=3)) for _ in range(pending)
        )
        self.queue.extend((p.plan.request.encode()[4:], p.packets[1]) for p in points)
        for p in points:
            r = p.plan.request
            data = p.packets[0][237:]
            for start in range(0, r.size, 512):
                n = min(512, r.size - start)
                body = b"".join(
                    struct.pack("<BI", 0, r.virtual_start + start + i) for i in range(n)
                )
                self.queue.append((body, struct.pack("<IB", 5 + n, 0) + data[start : start + n]))
        identity()
        self.queue.extend((p.plan.request.encode()[4:], p.packets[2]) for p in points)

    def __enter__(self):
        self.open = True
        return self

    def __exit__(self, *_):
        self.open, self.closed = False, True
        if self.close_error:
            raise OSError("private close")

    def peer_pid(self):
        return self.pid

    def exchange(self, packet):
        assert self.open and packet[:4] == struct.pack("<I", len(packet))
        expected, response = self.queue.pop(0)
        assert packet[4:] == expected
        self.calls.append(expected)
        if expected[0] == 9:
            self.store.visible = True
        if isinstance(response, BaseException):
            raise response
        return response


def run(points=None, *, regions=None, store=None, channel=None, guard=None, **kwargs):
    points = source() if points is None else points
    regions = tuple(RegionPlan(p.label, p.plan) for p in points) if regions is None else regions
    store = store or Store(points[0].state)
    channel = channel or Channel(points, store)
    guard = guard or Guard()
    clock = kwargs.pop("clock", Clock())
    published = []

    def publish(path, report):
        assert path == "public.json" and channel.closed and store.closed and guard.calls == 2
        published.append(report)

    result = acquire_regions_and_publish(
        regions,
        channel,
        store,
        guard,
        "public.json",
        publish=publish,
        clock=clock,
        wait=clock.wait,
        **kwargs,
    )
    assert published == [result] and not channel.queue
    assert sum(b[0] == 9 for b in channel.calls) == 1 and len(store.written) == 3 * len(points)
    return result


@pytest.mark.parametrize("count,pending", [(1, 0), (2, 2), (8, 1)])
def test_one_state_multiple_ranges_closes_before_publish(count, pending):
    points = source(count)
    store = Store(points[0].state)
    channel = Channel(points, store, pending)
    result = run(points, store=store, channel=channel)
    assert result["saved_states"] == 1 and result["region_count"] == count
    assert len({p["state_sha256"] for p in result["points"]}) == 1
    assert result["state_binding_verified"] and not result["live_acquisition_verified"]
    assert not result["file_identity_verified"] and result["read_events_produced"] == 0
    assert all(k not in json.dumps(result) for k in ['"pid"', '"pc"', '"data"', '"path"'])
    assert "plan=" not in repr(RegionPlan("code", points[0].plan))


def test_four_kib_data_uses_bounded_read8_batches():
    assert run(pause(size=4096))["points"][1]["size"] == 4096


@pytest.mark.parametrize("value", [None, [], (), (None,), tuple([None] * 9)])
def test_plan_container_rejected_without_io(value):
    with rejects("MULTI_PLAN"):
        validate_regions(value)


@pytest.mark.parametrize(
    "field", ["label", "duplicate", "pid", "crc", "serial", "slot", "pc", "sequence", "environment"]
)
def test_invalid_plan_before_any_guard_or_channel(field):
    points = source()
    regions = [RegionPlan(p.label, p.plan) for p in points]
    r = regions[1]
    plan = r.plan
    error = "MULTI_IDENTITY"
    if field in ("label", "duplicate"):
        r = replace(r, label=None if field == "label" else "code")
        error = "MULTI_LABELS"
    elif field in ("pid", "crc", "slot"):
        plan = replace(plan, **{field: getattr(plan, field) + 1})
    elif field == "serial":
        plan = replace(plan, serial="SLES-99999")
    elif field == "pc":
        plan = replace(plan, request=replace(plan.request, expected_pc=0x100000))
    elif field == "sequence":
        plan = replace(
            plan,
            request=replace(plan.request, sequence=10),
            context=replace(plan.context, sequence=10),
        )
    else:
        plan = replace(plan, context=replace(plan.context, environment_sha256="e" * 64))
    regions[1] = replace(r, plan=plan)
    store = Store(points[0].state)
    channel = Channel(points, store)
    guard = Guard()
    with rejects(error):
        run(regions=tuple(regions), store=store, channel=channel, guard=guard)
    assert guard.calls == 0 and not channel.calls and not store.open


@pytest.mark.parametrize("index", range(13))
def test_failed_reply_at_each_exchange_never_publishes(index):
    points = source()
    store = Store(points[0].state)
    channel = Channel(points, store)
    body, _ = channel.queue[index]
    channel.queue[index] = (body, struct.pack("<IB", 5, 255))
    with pytest.raises(ProfileError):
        run(store=store, channel=channel)
    assert store.closed and channel.closed


@pytest.mark.parametrize("index", [3, 6, 12])
def test_later_region_change_is_not_accepted(index):
    points = source()
    store = Store(points[0].state)
    channel = Channel(points, store)
    body, data = channel.queue[index]
    channel.queue[index] = (body, data[:-1] + bytes([data[-1] ^ 1]))
    with rejects("MULTI_CHANGED"):
        run(store=store, channel=channel)
    assert not store.written


def test_individually_stable_regions_with_different_cpu_cycles_rejected():
    points = list(source())
    p = points[1]
    packet = bytearray(p.packets[0])
    for start in (61, 149):
        cycle = struct.unpack_from("<Q", packet, start + 12)[0]
        struct.pack_into("<Q", packet, start + 12, cycle + 1)
    points[1] = replace(p, packets=(bytes(packet),) * 3)
    with rejects("PAUSE_CPU"):
        run(tuple(points))


@pytest.mark.parametrize("failure", ["absent", "read", "write", "close", "changed", "hash"])
def test_custody_failures(failure):
    points = source()
    store = Store(points[0].state)
    store.fail = failure
    channel = Channel(points, store)
    with pytest.raises(ProfileError):
        run(store=store, channel=channel)
    assert store.closed and (channel.closed or failure == "absent")


@pytest.mark.parametrize("failure", ["peer", "socket_close", "guard", "memory", "io"])
def test_identity_transport_and_memory_failures(failure):
    points = source()
    store = Store(points[0].state)
    channel = Channel(points, store)
    guard = Guard()
    if failure == "peer":
        channel.pid += 1
    elif failure == "socket_close":
        channel.close_error = True
    elif failure == "guard":
        guard.changed = True
    else:
        i = 7 if failure == "memory" else 2
        body, data = channel.queue[i]
        channel.queue[i] = (
            body,
            OSError("private I/O") if failure == "io" else data[:-1] + bytes([data[-1] ^ 1]),
        )
    with pytest.raises(ProfileError):
        run(store=store, channel=channel, guard=guard)
    assert store.closed and channel.closed


@pytest.mark.parametrize("timeout", [0, -1, True, 31, float("nan"), float("inf")])
def test_timeout_values(timeout):
    with rejects("MULTI_TIMEOUT"):
        run(timeout=timeout)


@pytest.mark.parametrize(
    "pending,timeout,error", [(256, 30, "MULTI_POLL_BUDGET"), (3, 0.05, "MULTI_DEADLINE")]
)
def test_pending_retry_budget_never_repeats_save(pending, timeout, error):
    points = source()
    store = Store(points[0].state)
    channel = Channel(points, store, pending)
    with rejects(error):
        run(store=store, channel=channel, timeout=timeout)
    assert sum(b[0] == 9 for b in channel.calls) == 1 and not store.written


def test_final_guard_deadline_prevents_acceptance():
    clock = Clock()
    guard = Guard()
    original = guard.check

    def check(plan):
        answer = original(plan)
        if guard.calls == 2:
            clock.now = 31
        return answer

    guard.check = check
    with rejects("MULTI_DEADLINE"):
        run(guard=guard, clock=clock)


def test_local_invalid_plan_rejected_before_adapters_or_paths():
    with rejects("MULTI_PLAN"):
        acquire_regions_local((), object(), object(), "unused")


def test_real_private_store_composition(tmp_path, monkeypatch):
    from tools.inspectors import observer_transport
    from tools.inspectors.observer_files import PrivateAcquisitionStore

    points = source()
    regions = tuple(RegionPlan(p.label, p.plan) for p in points)
    root, repo = tmp_path / "private", tmp_path / "repo"
    root.mkdir(mode=0o700)
    repo.mkdir()
    guard = Guard()
    guard.state_root, guard.socket_path = root, root / "pcsx2.sock"
    store = PrivateAcquisitionStore(root, repo)
    channel = Channel(points, store)
    original = channel.exchange

    def exchange(packet):
        result = original(packet)
        if packet[4] == 9:
            p = root / points[0].plan.state_name
            p.write_bytes(points[0].state)
            p.chmod(0o600)
        return result

    channel.exchange = exchange
    monkeypatch.setattr(observer_transport, "Session", lambda path, timeout: channel)
    output = repo / "receipt.json"
    result = acquire_regions_local(regions, guard, repo, output)
    assert json.loads(output.read_text()) == result and channel.closed
    assert len(list(root.glob("*.p2s"))) == 1 and len(list(root.glob("*.bin"))) == 6


def test_partial_packet_write_is_preserved_without_acceptance():
    points = source()
    store = Store(points[0].state)
    channel = Channel(points, store)
    original = store.put

    def put(name, raw):
        if len(store.written) == 2:
            raise OSError("private write failure")
        original(name, raw)

    store.put = put
    with rejects("MULTI_IO"):
        run(store=store, channel=channel)
    assert len(store.written) == 2 and store.visible and store.closed and channel.closed


def test_publisher_failure_is_not_retried_after_closure():
    points = source()
    regions = tuple(RegionPlan(p.label, p.plan) for p in points)
    store = Store(points[0].state)
    channel = Channel(points, store)
    calls = []

    def publish(path, report):
        assert store.closed and channel.closed
        calls.append(path)
        raise RuntimeError("publication outcome unknown")

    with pytest.raises(RuntimeError, match="publication outcome unknown"):
        acquire_regions_and_publish(regions, channel, store, Guard(), "receipt", publish=publish)
    assert calls == ["receipt"] and len(store.written) == 6
