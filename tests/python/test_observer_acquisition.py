"""AC01-AC10: independent synthetic packets/states and deterministic fault ports."""

import hashlib
import json
import struct
import zipfile
from contextlib import contextmanager
from dataclasses import replace
from functools import lru_cache

import pytest
from test_observer_capture import CONTEXT, REQUEST, packed
from test_pcsx2_state import CPU, own_archive, own_internals

from tools.inspectors.observation_capture import ProfileError
from tools.inspectors.observer_acquisition import AcquisitionPlan, acquire_and_publish
from tools.inspectors.observer_state import read_acquisition_state
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE


@contextmanager
def rejects(code):
    with pytest.raises(ProfileError) as caught:
        yield
    assert caught.value.code == code


PLAN = AcquisitionPlan(REQUEST, CONTEXT, 42, 0x44556677, "SLES-51434", 1)
CYCLE = 0x10000004D


@lru_cache(maxsize=8)
def state_bytes(
    request=REQUEST, alias=0, cycle=CYCLE, crc=PLAN.crc, delay=0, cut=0, ram_size=RAM_SIZE
):
    internals = bytearray(own_internals(request.expected_pc, delay)).ljust(CPU + 1160, b"\0")
    struct.pack_into("<I", internals, 292, crc)
    struct.pack_into("<Q", internals, CPU + 1088, cycle)
    if cut:
        internals = internals[: CPU + cut]
    ram = bytearray(ram_size)
    offset = request.expected_offset + alias
    ram[offset : offset + request.size] = bytes((i ^ 0x5A) & 255 for i in range(request.size))
    return own_archive(
        [(VERSION_MEMBER, VERSION), (INTERNALS_MEMBER, bytes(internals)), (RAM_MEMBER, bytes(ram))],
        zipfile.ZIP_DEFLATED,
    )


class Clock:
    now = 0.0

    def __call__(self):
        return self.now

    def wait(self, seconds):
        self.now += seconds


class Store:
    def __init__(self, raw):
        self.raw = raw
        self.visible = self.open = self.closed = False
        self.reads = 0
        self.written = []
        self.fail = ""

    def __enter__(self):
        self.open = True
        return self

    def __exit__(self, *_):
        self.open, self.closed = False, True
        if self.fail == "close":
            raise OSError("private close")

    def absent(self, name):
        assert name == PLAN.state_name
        if self.visible:
            raise ProfileError("ACQUIRE_STATE_EXISTS", "exists")
        if self.fail == "absent":
            raise OSError("private stat")

    def read(self, name):
        assert name == PLAN.state_name and self.visible
        self.reads += 1
        if self.fail == "read":
            raise OSError("private read")
        raw = self.raw + (b"changed" if self.reads == 2 and self.fail == "changed" else b"")
        return raw, "a" * 64 if self.fail == "hash" else hashlib.sha256(raw).hexdigest()

    def put(self, name, data):
        if self.fail == "write":
            raise OSError("private write")
        self.written.append((name, data))


class Guard:
    def __init__(self):
        self.calls = 0
        self.changed = False

    def check(self, plan):
        self.calls += 1
        return 2 if self.calls > 1 and self.changed else 1


class Channel:
    def __init__(self, store, plan=PLAN, alias=0, pending=0):
        self.store, self.plan = store, plan
        self.open = self.closed = False
        self.close_error = False
        self.pid = 42
        self.calls = []
        request = plan.request
        crc = struct.pack("<I", 9) + f"{plan.crc:08x}".encode() + b"\0"
        identity = [(b"\x0f", struct.pack("<I", 1)), (b"\x0d", crc)]
        self.queue = [
            (body, struct.pack("<IB", 5 + len(reply), 0) + reply) for body, reply in identity
        ]
        self.queue += [
            (request.encode()[4:], packed(request, alias=alias)),
            (bytes([9, plan.slot]), struct.pack("<IB", 5, 0)),
        ]
        self.queue += [(request.encode()[4:], packed(request, status=3))] * pending
        self.queue += [(request.encode()[4:], packed(request, alias=alias))]
        for start in range(0, request.size, 512):
            count = min(512, request.size - start)
            body = b"".join(
                struct.pack("<BI", 0, request.virtual_start + start + i) for i in range(count)
            )
            self.queue.append(
                (
                    body,
                    struct.pack("<IB", 5 + count, 0)
                    + bytes(((start + i) ^ 0x5A) & 255 for i in range(count)),
                )
            )
        self.queue += [
            (body, struct.pack("<IB", 5 + len(reply), 0) + reply) for body, reply in identity
        ]
        self.queue += [(request.encode()[4:], packed(request, alias=alias))]

    def __enter__(self):
        self.open = True
        return self

    def __exit__(self, *_):
        self.open, self.closed = False, True
        if self.close_error:
            raise OSError("private socket")

    def peer_pid(self):
        return self.pid

    def exchange(self, packet):
        assert self.open and packet[:4] == struct.pack("<I", len(packet))
        expected, response = self.queue.pop(0)
        assert packet[4:] == expected
        self.calls.append(packet[4:])
        if packet[4] == 9:
            self.store.visible = True
        if isinstance(response, BaseException):
            raise response
        return response


def run(plan=PLAN, *, store=None, channel=None, guard=None, clock=None, **kwargs):
    store = store or Store(state_bytes(plan.request))
    channel = channel or Channel(store, plan)
    guard, clock = guard or Guard(), clock or Clock()
    published = []

    def publish(path, report):
        assert path == "public.json" and channel.closed and store.closed
        assert not channel.open and not store.open and guard.calls == 2
        published.append(report)

    report = acquire_and_publish(
        plan,
        channel,
        store,
        guard,
        "public.json",
        publish=publish,
        clock=clock,
        wait=clock.wait,
        **kwargs,
    )
    assert published == [report] and not channel.queue and len(store.written) == 3
    assert sum(body[0] == 9 for body in channel.calls) == 1
    return report


@pytest.mark.parametrize("size,alias,pending", [(1, 0, 0), (32, 16, 2), (4096, 0, 1)])
def test_full_sequence_closes_before_publication_preserves_alias(size, alias, pending):
    plan = replace(PLAN, request=replace(REQUEST, size=size))
    store = Store(state_bytes(plan.request, alias))
    channel = Channel(store, plan, alias, pending)
    result = run(plan, store=store, channel=channel)
    assert result["state_binding_verified"] and not result["live_acquisition_verified"]
    assert result["matches_expected_backing"] == (alias == 0)
    encoded = json.dumps(result)
    assert "SLES" not in encoded
    # A numeric PID can occur by chance in object.__repr__'s hex address.
    assert repr(plan) == object.__repr__(plan)
    assert not any(key in result for key in ["pid", "pc", "cycle", "data", "crc", "path"])


@pytest.mark.parametrize("cycle", [0, 2**32 - 1, 2**32, CYCLE, 2**64 - 1])
def test_cycle_full_width(cycle):
    state = read_acquisition_state(state_bytes(cycle=cycle), PLAN.crc, REQUEST.expected_offset, 32)
    assert state.cycle == cycle and state.cpu.pc == REQUEST.expected_pc
    assert "cycle=" not in repr(state)


@pytest.mark.parametrize("cut", [684, 1088, 1095, 1096, 1159])
def test_full_cpu_required(cut):
    with rejects("ACQUIRE_CPU_TRUNCATED"):
        read_acquisition_state(state_bytes(cut=cut), PLAN.crc, 0, 1)


@pytest.mark.parametrize("variant", ["crc", "delay", "ram", "size", "offset", "bool_size"])
def test_state_rejections(variant):
    kwargs = {
        "crc": {"crc": PLAN.crc + 1},
        "delay": {"delay": 1},
        "ram": {"ram_size": RAM_SIZE - 1},
    }.get(variant, {})
    with pytest.raises(ProfileError):
        read_acquisition_state(
            state_bytes(**kwargs),
            PLAN.crc,
            RAM_SIZE if variant == "offset" else 0,
            0 if variant == "size" else True if variant == "bool_size" else 1,
        )


@pytest.mark.parametrize("variant", ["pid", "slot", "crc", "serial", "session", "request"])
def test_bad_plan(variant):
    changes = {
        "pid": {"pid": True},
        "slot": {"slot": 0},
        "crc": {"crc": 0},
        "serial": {"serial": "../bad"},
        "session": {"context": replace(CONTEXT, sequence=2)},
        "request": {"request": None},
    }[variant]
    with pytest.raises(ProfileError):
        replace(PLAN, **changes).validate()


@pytest.mark.parametrize("operation", ["absent", "read", "write", "close", "changed", "hash"])
def test_store_failure_never_publishes(operation):
    store = Store(state_bytes())
    store.fail = operation
    channel = Channel(store)
    with pytest.raises(ProfileError):
        run(store=store, channel=channel)
    assert store.closed
    assert channel.closed or operation == "absent"


def test_existing_state_never_connects_or_saves():
    store = Store(state_bytes())
    store.visible = True
    channel = Channel(store)
    with rejects("ACQUIRE_STATE_EXISTS"):
        run(store=store, channel=channel)
    assert not channel.calls and store.closed


@pytest.mark.parametrize("variant", ["peer", "socket_close", "identity"])
def test_identity_and_close_failures(variant):
    store = Store(state_bytes())
    channel = Channel(store)
    guard = Guard()
    if variant == "peer":
        channel.pid = 43
    if variant == "socket_close":
        channel.close_error = True
    if variant == "identity":
        guard.changed = True
    with pytest.raises(ProfileError):
        run(store=store, channel=channel, guard=guard)
    assert channel.closed and store.closed


@pytest.mark.parametrize("index", range(9))
def test_protocol_failure_each_stage(index):
    store = Store(state_bytes())
    channel = Channel(store)
    body, _ = channel.queue[index]
    channel.queue[index] = body, struct.pack("<IB", 5, 255)
    with pytest.raises(ProfileError):
        run(store=store, channel=channel)
    assert channel.closed and store.closed


@pytest.mark.parametrize("index", [4, 8])
def test_changed_observer_content(index):
    store = Store(state_bytes())
    channel = Channel(store)
    body, response = channel.queue[index]
    channel.queue[index] = body, response[:-1] + bytes([response[-1] ^ 1])
    with rejects("ACQUIRE_CHANGED"):
        run(store=store, channel=channel)


def test_pine_memory_mismatch():
    store = Store(state_bytes())
    channel = Channel(store)
    body, response = channel.queue[5]
    channel.queue[5] = body, response[:-1] + bytes([response[-1] ^ 1])
    with rejects("ACQUIRE_MEMORY"):
        run(store=store, channel=channel)


@pytest.mark.parametrize("cycle", [CYCLE + 1, CYCLE & 0xFFFFFFFF])
def test_state_cycle_disagreement(cycle):
    with rejects("ACQUIRE_STATE"):
        run(store=Store(state_bytes(cycle=cycle)))


def test_only_pending_can_retry_and_poll_count_is_bounded():
    store = Store(state_bytes())
    channel = Channel(store, pending=256)
    with rejects("ACQUIRE_POLL_BUDGET"):
        run(store=store, channel=channel)
    assert sum(c[0] == 9 for c in channel.calls) == 1


def test_pending_timeout_and_no_retry_save():
    store = Store(state_bytes())
    channel = Channel(store, pending=3)
    with rejects("ACQUIRE_DEADLINE"):
        run(store=store, channel=channel, timeout=0.05)
    assert sum(c[0] == 9 for c in channel.calls) == 1


@pytest.mark.parametrize("timeout", [0, -1, True, 31, float("nan"), float("inf")])
def test_timeout_value(timeout):
    with rejects("ACQUIRE_TIMEOUT_VALUE"):
        run(timeout=timeout)


def test_real_custody_and_atomic_publication_composition(tmp_path, monkeypatch):
    from tools.inspectors import observer_transport
    from tools.inspectors.observer_acquisition import acquire_local
    from tools.inspectors.observer_files import PrivateAcquisitionStore

    root, repo = tmp_path / "private", tmp_path / "repo"
    root.mkdir(mode=0o700)
    repo.mkdir()
    guard = Guard()
    guard.state_root, guard.socket_path = root, root / "pcsx2.sock"
    store = PrivateAcquisitionStore(root, repo)
    channel = Channel(store)
    original = channel.exchange

    def exchange(packet):
        reply = original(packet)
        if packet[4] == 9:
            file = root / PLAN.state_name
            file.write_bytes(state_bytes())
            file.chmod(0o600)
        return reply

    channel.exchange = exchange
    monkeypatch.setattr(observer_transport, "Session", lambda path, timeout: channel)
    # acquire_local owns its actual store; the channel writes only the simulated producer output.
    output = repo / "receipt.json"
    report = acquire_local(PLAN, guard, repo, output)
    assert json.loads(output.read_text()) == report
    assert report["state_binding_verified"] and not report["live_acquisition_verified"]
    assert len(list(root.glob("*.bin"))) == 3 and channel.closed


def test_save_acknowledged_but_no_file_is_not_success(tmp_path):
    from tools.inspectors.observer_files import PrivateAcquisitionStore

    root, repo = tmp_path / "private", tmp_path / "repo"
    root.mkdir(mode=0o700)
    repo.mkdir()
    store = PrivateAcquisitionStore(root, repo)
    channel = Channel(store)
    with rejects("ACQUIRE_IO"):
        run(store=store, channel=channel)
    assert channel.closed and store.parent is None
    assert not list(root.glob("*.p2s")) and not list(root.glob("*.bin"))


def large_tail_state(length, compression=zipfile.ZIP_DEFLATED, bad_tag=False):
    internals = bytearray(own_internals(REQUEST.expected_pc)).ljust(length, b"\0")
    struct.pack_into("<I", internals, 292, PLAN.crc)
    struct.pack_into("<Q", internals, CPU + 1088, CYCLE)
    if bad_tag:
        internals[CPU - 32] ^= 1
    return own_archive(
        [
            (VERSION_MEMBER, VERSION),
            (INTERNALS_MEMBER, bytes(internals)),
            (RAM_MEMBER, bytes(RAM_SIZE)),
        ],
        compression,
    )


@pytest.mark.parametrize("length", [1024 * 1024 + 1, 2597162, 4 * 1024 * 1024])
def test_ac11_variable_tail_within_explicit_budget_and_legacy_unchanged(length):
    from tools.inspectors.pcsx2_state import read_state_archive

    raw = large_tail_state(length)
    value = read_acquisition_state(raw, PLAN.crc, 0, 1)
    assert value.cycle == CYCLE and value.data == b"\0"
    with rejects("STATE_BUDGET"):
        read_state_archive(raw, PLAN.crc)


def test_ac11_oversize_rejected_before_member_open(monkeypatch):
    raw = large_tail_state(4 * 1024 * 1024 + 1)
    original = zipfile.ZipFile.open

    def checked_open(archive, name, *args, **kwargs):
        assert getattr(name, "filename", name) != INTERNALS_MEMBER
        return original(archive, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", checked_open)
    with rejects("STATE_BUDGET"):
        read_acquisition_state(raw, PLAN.crc, 0, 1)


def test_ac11_corrupt_opaque_tail_crc_is_not_skipped():
    from io import BytesIO

    raw = bytearray(large_tail_state(2 * 1024 * 1024, zipfile.ZIP_STORED))
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        info = archive.getinfo(INTERNALS_MEMBER)
        start = info.header_offset + 30 + len(info.filename.encode())
    raw[start + 1500000] ^= 1
    with rejects("STATE_ZIP"):
        read_acquisition_state(bytes(raw), PLAN.crc, 0, 1)


def test_ac11_large_tail_still_requires_cpu_tag():
    with rejects("STATE_FORMAT"):
        read_acquisition_state(large_tail_state(2 * 1024 * 1024, bad_tag=True), PLAN.crc, 0, 1)
