"""BC01–08: accumulated deadlines, ownership, real streams and cancellation."""

import os
import signal
import socket
import threading
import time
from dataclasses import replace

import pytest
from test_diagnostic_channel import REQUEST, Reader
from test_diagnostic_session import EXPECTED, LAUNCH, PEER, VECTOR, Channel

from tools.inspectors import diagnostic_channel as transport
from tools.inspectors import diagnostic_session as sessions
from tools.inspectors.diagnostic_budget import BudgetStopped, DiagnosticSessionBudget
from tools.inspectors.diagnostic_channel import UnixDiagnosticChannel
from tools.inspectors.diagnostic_session import PeerUnavailable, PlatformDiagnosticSession


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class ControlledChannel(Channel):
    def __init__(self):
        super().__init__()
        self.budgets = []
        self.close_threads = []

    def exchange_with_budget(self, packet, budget):
        self.budgets.append(budget)
        budget.checkpoint()
        return super().exchange(packet)

    def exchange(self, packet):
        raise AssertionError("budgeted session silently fell back to legacy IO")

    def close(self):
        self.close_threads.append(threading.get_ident())
        super().close()


def make_session(channel=None, clock=None):
    channel = channel or ControlledChannel()
    clock = clock or Clock()
    session = PlatformDiagnosticSession(
        EXPECTED, LAUNCH, channel, entropy=lambda n: b"c" * n, budget_clock=clock
    )
    return session, channel, clock


def assert_terminal(s, c, reason):
    assert s.reason == reason and s.last is None and s.closed
    old = (c.peer_calls, c.exchanges, c.closes)
    assert s.sample() is None
    s.close()
    s.cancel()
    assert (c.peer_calls, c.exchanges, c.closes) == old and c.closes == 1
    assert s.reason == reason


@pytest.mark.parametrize("initial", [True, False])
@pytest.mark.parametrize("edge", [-0.000001, 0, 0.000001])
def test_budget_exact_deadline(initial, edge):
    clock = Clock()
    budget = DiagnosticSessionBudget(clock)
    budget.begin(initial=initial)
    clock.now += (5 if initial else 2) + edge
    if edge < 0:
        assert budget.remaining() > 0
        assert budget.publish(lambda: 123) == 123
    else:
        with pytest.raises(BudgetStopped, match="^deadline$"):
            budget.publish(lambda: pytest.fail("late publication"))
        clock.now = 100
        with pytest.raises(BudgetStopped, match="^deadline$"):
            budget.begin(initial=True)


@pytest.mark.parametrize("value", [True, None, "1", float("nan"), float("inf"), 10**1000])
def test_invalid_clock_is_terminal(value):
    budget = DiagnosticSessionBudget(lambda: value)
    with pytest.raises(BudgetStopped, match="clock_invalid"):
        budget.begin(initial=True)


def test_clock_regression_between_samples_and_nonadvancing_deadline():
    clock = Clock()
    budget = DiagnosticSessionBudget(clock)
    budget.begin(initial=True)
    budget.publish(lambda: None)
    clock.now -= 1
    with pytest.raises(BudgetStopped, match="clock_invalid"):
        budget.begin(initial=False)
    with pytest.raises(BudgetStopped, match="clock_invalid"):
        DiagnosticSessionBudget(lambda: 1e308).begin(initial=True)


def test_budget_cannot_restart_active_operation_or_publish_without_begin():
    b = DiagnosticSessionBudget(Clock())
    with pytest.raises(BudgetStopped, match="budget_inactive"):
        b.publish(lambda: None)
    b = DiagnosticSessionBudget(Clock())
    b.begin(initial=True)
    with pytest.raises(BudgetStopped, match="reentrant"):
        b.begin(initial=True)


@pytest.mark.parametrize("phase", ["first_peer", "exchange", "decode", "last_peer", "publish"])
@pytest.mark.parametrize("revalidation", [False, True])
def test_each_phase_uses_original_deadline(monkeypatch, phase, revalidation):
    s, c, clock = make_session()
    if revalidation:
        assert s.sample() is not None
    started = clock.now
    duration = 2 if revalidation else 5

    def expire():
        clock.now = started + duration

    if phase.endswith("peer"):
        target = c.peer_calls + (1 if phase == "first_peer" else 2)
        c.on_peer = lambda n: expire() if n == target else None
    elif phase == "exchange":
        c.on_exchange = expire
    elif phase == "decode":
        original = sessions.decode_platform_diagnostic

        def decode(*args, **kwargs):
            value = original(*args, **kwargs)
            expire()
            return value

        monkeypatch.setattr(sessions, "decode_platform_diagnostic", decode)
    else:
        original = sessions._identity

        def identity(value):
            result = original(value)
            expire()
            return result

        monkeypatch.setattr(sessions, "_identity", identity)
    assert s.sample() is None and s.accepted == int(revalidation)
    assert_terminal(s, c, "deadline")


def test_accumulation_success_then_revalidation_is_two_seconds():
    s, c, clock = make_session()
    c.on_peer = lambda _: setattr(clock, "now", clock.now + 1)
    c.on_exchange = lambda: setattr(clock, "now", clock.now + 1)
    assert s.sample() is not None  # 3 s total fits first 5 s.
    assert s.sample() is None  # Same work cannot fit revalidation's 2 s.
    assert s.accepted == 1 and c.budgets[0] is c.budgets[1]
    assert_terminal(s, c, "deadline")


@pytest.mark.parametrize("phase", ["first_peer", "exchange", "last_peer"])
@pytest.mark.parametrize("action", ["cancel", "close", "sample"])
def test_reentrant_stop_does_not_close_active_adapter(phase, action):
    s, c, _ = make_session()

    def stop():
        getattr(s, action)()
        assert not s.closed and c.closes == 0

    if phase == "exchange":
        c.on_exchange = stop
    else:
        c.on_peer = lambda n: stop() if n == (1 if phase == "first_peer" else 2) else None
    assert s.sample() is None and s.accepted == 0
    assert_terminal(s, c, {"cancel": "cancelled", "close": "closed", "sample": "reentrant"}[action])


@pytest.mark.parametrize("action", ["cancel", "close", "sample"])
def test_other_thread_only_signals_while_owner_is_in_native_reader(action):
    entered, release = threading.Event(), threading.Event()
    shared, errors = {}, []

    def owner():
        try:
            s, c, _ = make_session()
            shared.update(session=s, channel=c, owner=threading.get_ident())

            def reader(_):
                entered.set()
                assert release.wait(3)

            c.on_peer = reader
            assert s.sample() is None
        except BaseException as e:
            errors.append(e)

    thread = threading.Thread(target=owner)
    thread.start()
    try:
        assert entered.wait(3)
        s, c = shared["session"], shared["channel"]
        getattr(s, action)()
        assert not s.closed and c.closes == 0 and s.last is None
    finally:
        release.set()
        thread.join(3)
    assert not thread.is_alive() and not errors
    assert s.closed and c.close_threads == [shared["owner"]] and s.accepted == 0
    assert s.reason == {"cancel": "cancelled", "close": "closed", "sample": "owner_changed"}[action]


def test_idle_external_cancel_waits_for_owner_and_preserves_historical_copy():
    s, c, _ = make_session()
    historical = s.sample()
    t = threading.Thread(target=s.cancel)
    t.start()
    t.join(2)
    assert s.reason == "cancelled" and s.last is None and not s.closed
    assert historical.diagnostic.request.sequence == 1
    assert s.sample() is None
    assert_terminal(s, c, "cancelled")


def test_closed_is_false_until_close_callback_returns():
    s, c, _ = make_session()
    old_close = c.close

    def close():
        assert not s.closed
        old_close()

    c.close = close
    s.close()
    assert s.closed


def test_publication_and_cancel_have_one_serial_order():
    # Cancel-before and publish-before are covered separately; this exercises races.
    for _ in range(100):
        budget = DiagnosticSessionBudget(Clock())
        budget.begin(initial=True)
        barrier = threading.Barrier(2)
        committed = []

        def cancel(barrier=barrier, budget=budget):
            barrier.wait(timeout=2)
            budget.stop("cancelled")

        t = threading.Thread(target=cancel)
        t.start()
        barrier.wait(timeout=2)
        try:
            value = budget.publish(lambda committed=committed: committed.append(True) or 7)
            assert value == 7 and committed == [True]
        except BudgetStopped as error:
            assert str(error) == "cancelled" and not committed
        t.join(2)
        assert not t.is_alive() and budget.reason == "cancelled"


@pytest.mark.parametrize("change", ["token", "payload", "close_error", "regression"])
def test_budget_does_not_replace_identity_lifecycle_or_first_error(change, monkeypatch):
    s, c, clock = make_session()
    assert s.sample() is not None
    reason = ""
    if change == "token":
        c.peer_value = replace(PEER, token=b"z" * 32)
        reason = "peer_changed"
    elif change == "payload":
        c.response = VECTOR[:52] + b"x" * 16 + VECTOR[68:]
        reason = "identity_changed"
    elif change == "close_error":
        c.close_error = True
        c.on_exchange = s.cancel
        reason = "cancelled"
    elif change == "regression":
        clock.now -= 1
        reason = "clock_invalid"
    assert s.sample() is None
    assert_terminal(s, c, reason)
    assert s.close_failed == (change == "close_error")


def test_budget_requires_explicit_transport_port_and_valid_clock():
    for channel, clock in [(Channel(), Clock()), (ControlledChannel(), 4)]:
        s = PlatformDiagnosticSession(EXPECTED, LAUNCH, channel, budget_clock=clock)
        assert_terminal(s, channel, "configuration")
        assert not channel.exchanges


@pytest.mark.parametrize("phase", ["request", "response"])
@pytest.mark.parametrize("mode", ["fragmented", "eagain", "interrupted"])
def test_real_stream_partial_operations_and_retryable_errors(phase, mode):
    a, b = socket.socketpair()
    done = threading.Event()
    errors = []

    class FragmentedSocket(socket.socket):
        send_calls = recv_calls = 0

        def send(self, data, *args):
            self.send_calls += 1
            if phase == "request" and self.send_calls == 1:
                if mode == "eagain":
                    raise BlockingIOError()
                if mode == "interrupted":
                    raise InterruptedError()
            return super().send(data[:1], *args)

        def recv(self, size, *args):
            self.recv_calls += 1
            if phase == "response" and self.recv_calls == 1:
                if mode == "eagain":
                    raise BlockingIOError()
                if mode == "interrupted":
                    raise InterruptedError()
            return super().recv(min(size, 3), *args)

    adopted = FragmentedSocket(fileno=a.detach())

    def server():
        try:
            b.settimeout(2)
            request = bytearray()
            while len(request) < 32:
                request.extend(b.recv(32 - len(request)))
            assert bytes(request) == REQUEST
            b.sendall(b"x" * 294)
            assert done.wait(2)
        except BaseException as e:
            errors.append(e)
        finally:
            b.close()

    t = threading.Thread(target=server)
    t.start()
    channel = UnixDiagnosticChannel(adopted, Reader())
    budget = DiagnosticSessionBudget(time.monotonic)
    budget.begin(initial=True)
    try:
        assert channel.exchange_with_budget(REQUEST, budget) == b"x" * 294
        assert adopted.send_calls >= 32 and adopted.recv_calls >= 98
    finally:
        channel.close()
        done.set()
        t.join(3)
    assert not errors and not t.is_alive()


@pytest.mark.parametrize("mode", ["partial_eof", "eof", "extra"])
def test_real_stream_rejects_truncation_and_extra_bytes(mode):
    a, b = socket.socketpair()
    channel = UnixDiagnosticChannel(a, Reader())
    budget = DiagnosticSessionBudget(time.monotonic)
    budget.begin(initial=True)
    if mode == "extra":
        b.sendall(b"x" * 295)
    else:
        b.sendall(b"x" * (17 if mode == "partial_eof" else 0))
        b.shutdown(socket.SHUT_WR)
    try:
        with pytest.raises(PeerUnavailable):
            channel.exchange_with_budget(REQUEST, budget)
        assert a.fileno() == -1
    finally:
        channel.close()
        b.close()


@pytest.mark.parametrize("phase", ["send", "receive"])
@pytest.mark.parametrize("stop", ["deadline", "cancelled"])
def test_real_backpressure_or_missing_response_stops_without_external_close(
    phase, stop, monkeypatch
):
    a, b = socket.socketpair()
    a.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
    a.setblocking(False)
    if phase == "send":
        while True:
            try:
                a.send(b"p" * 4096)
            except BlockingIOError:
                break
    channel = UnixDiagnosticChannel(a, Reader())
    clock = Clock()
    budget = DiagnosticSessionBudget(clock)
    budget.begin(initial=True)
    entered = threading.Event()
    finished = threading.Event()
    waits = []
    original = transport.select.select

    def select(read, write, exceptional, timeout):
        waits.append(timeout)
        if (phase == "send" and write) or (phase == "receive" and read):
            entered.set()
        return original(read, write, exceptional, timeout)

    monkeypatch.setattr(transport.select, "select", select)
    errors = []

    def stop_work():
        try:
            assert entered.wait(2)
            assert a.fileno() >= 0
            if stop == "deadline":
                clock.now += 5
            else:
                budget.stop("cancelled")
            assert a.fileno() >= 0  # Signal does not close an active descriptor.
        except BaseException as e:
            errors.append(e)
        finally:
            finished.set()

    t = threading.Thread(target=stop_work)
    t.start()
    try:
        with pytest.raises(BudgetStopped, match=stop):
            channel.exchange_with_budget(REQUEST, budget)
        assert a.fileno() == -1
        assert waits and all(0 <= n <= 0.02 for n in waits)
    finally:
        t.join(3)
        channel.close()
        b.close()
    assert finished.is_set() and not t.is_alive() and not errors


def test_ready_response_is_rejected_if_final_poll_exhausts_budget(monkeypatch):
    a, b = socket.socketpair()
    b.sendall(b"x" * 294)
    clock = Clock()
    budget = DiagnosticSessionBudget(clock)
    budget.begin(initial=True)
    channel = UnixDiagnosticChannel(a, Reader())
    original = transport.select.select

    def select(read, write, exceptional, timeout):
        result = original(read, write, exceptional, timeout)
        if timeout == 0:
            clock.now += 5
        return result

    monkeypatch.setattr(transport.select, "select", select)
    try:
        with pytest.raises(BudgetStopped, match="deadline"):
            channel.exchange_with_budget(REQUEST, budget)
        assert a.fileno() == -1
    finally:
        channel.close()
        b.close()


def test_interrupted_poll_is_retried_under_same_deadline(monkeypatch):
    a, b = socket.socketpair()
    b.sendall(b"x" * 294)
    clock = Clock()
    budget = DiagnosticSessionBudget(clock)
    budget.begin(initial=True)
    channel = UnixDiagnosticChannel(a, Reader())
    original = transport.select.select
    calls = []

    def select(*args):
        calls.append(1)
        if len(calls) == 1:
            clock.now += 4
            raise InterruptedError()
        return original(*args)

    monkeypatch.setattr(transport.select, "select", select)
    try:
        assert channel.exchange_with_budget(REQUEST, budget) == b"x" * 294
        assert budget.remaining() == 1
    finally:
        channel.close()
        b.close()


def test_channel_foreign_owner_cannot_close_or_use_socket():
    a, b = socket.socketpair()
    channel = UnixDiagnosticChannel(a, Reader())
    budget = DiagnosticSessionBudget(Clock())
    budget.begin(initial=True)
    errors = []

    def other():
        try:
            channel.exchange_with_budget(REQUEST, budget)
        except PeerUnavailable as error:
            errors.append(str(error))

    t = threading.Thread(target=other)
    t.start()
    t.join(2)
    try:
        assert errors == ["owner_changed"] and a.fileno() >= 0
    finally:
        channel.close()
        b.close()


@pytest.mark.parametrize("packet", [b"", b"z" * 32, bytearray(REQUEST)])
def test_bad_budgeted_request_closes_once(packet):
    a, b = socket.socketpair()
    channel = UnixDiagnosticChannel(a, Reader())
    budget = DiagnosticSessionBudget(Clock())
    budget.begin(initial=True)
    try:
        with pytest.raises(PeerUnavailable, match="channel_request"):
            channel.exchange_with_budget(packet, budget)
        assert a.fileno() == -1
    finally:
        channel.close()
        b.close()


def test_zero_write_and_close_error_are_reported_to_session():
    class FailingSocket(socket.socket):
        def send(self, data, *args):
            return 0

        def close(self):
            super().close()
            raise OSError("synthetic close failure")

    class NativeReaderDouble:
        def read(self, _):
            return PEER

    a, b = socket.socketpair()
    adopted = FailingSocket(fileno=a.detach())
    channel = UnixDiagnosticChannel(adopted, NativeReaderDouble())
    s, _, _ = make_session(channel)
    try:
        assert s.sample() is None and s.reason == "channel_unavailable"
        assert s.closed and s.close_failed and channel.close_failed and adopted.fileno() == -1
    finally:
        s.close()
        b.close()


def test_repeated_stop_during_active_callback_does_not_close_early():
    s, c, _ = make_session()

    def cancelled_callback(_):
        s.cancel()
        assert s.sample() is None
        s.close()
        assert not s.closed

    c.on_peer = cancelled_callback
    assert s.sample() is None
    assert_terminal(s, c, "cancelled")


def test_readiness_can_be_spurious_without_resetting_clock(monkeypatch):
    a, b = socket.socketpair()
    b.sendall(b"x" * 294)
    clock = Clock()
    budget = DiagnosticSessionBudget(clock)
    budget.begin(initial=True)
    channel = UnixDiagnosticChannel(a, Reader())
    original = transport.select.select
    calls = []

    def select(*args):
        calls.append(1)
        if len(calls) == 1:
            clock.now += 4
            return [], [], []
        return original(*args)

    monkeypatch.setattr(transport.select, "select", select)
    try:
        assert channel.exchange_with_budget(REQUEST, budget) == b"x" * 294
        assert budget.remaining() == 1
    finally:
        channel.close()
        b.close()


@pytest.mark.parametrize("error", [ValueError("clock"), RuntimeError("clock bug")])
def test_clock_errors_close_and_do_not_publish(error):
    def clock():
        raise error

    s, c, _ = make_session(clock=clock)
    if type(error) is RuntimeError:
        with pytest.raises(RuntimeError):
            s.sample()
        assert_terminal(s, c, "internal_error")
    else:
        assert s.sample() is None
        assert_terminal(s, c, "clock_invalid")


@pytest.mark.parametrize("action", ["sample", "cancel", "close"])
def test_real_fork_never_acquires_inherited_budget_lock(action):
    class NativeReaderDouble:
        def read(self, _):
            return PEER

    a, b = socket.socketpair()
    channel = UnixDiagnosticChannel(a, NativeReaderDouble())
    s, _, _ = make_session(channel)
    try:
        with s._budget._lock:
            pid = os.fork()
            if pid == 0:
                signal.alarm(2)  # A lock regression cannot hang the test runner.
                try:
                    assert s.reason == "owner_changed" and s.last is None
                    getattr(s, action)()
                    assert s.closed and s.reason == "owner_changed" and a.fileno() == -1
                    os._exit(0)
                except BaseException:
                    os._exit(1)
            _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status) == 0
        assert not s.closed and s.reason == "" and a.fileno() >= 0
        b.sendall(b"parent still owns the connection")
        assert a.recv(128) == b"parent still owns the connection"
    finally:
        s.close()
        b.close()
