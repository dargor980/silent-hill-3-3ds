"""Synthetic socket/clock ports; no emulator or private files required in CI."""

import socket
import struct

import pytest

from tools.inspectors.observer_transport import TransportError, exchange

REQUEST = struct.pack("<IB", 5, 0xE0)
REPLY = struct.pack("<IB", 5, 255)


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


class Socket:
    def __init__(self, chunks=None, fail=None, clock=None, delay=0):
        self.chunks = list(chunks or [REPLY[:4], REPLY[4:]])
        self.fail = fail or {}
        self.clock = clock or Clock()
        self.delay = delay
        self.closed = False
        self.timeouts = []
        self.sent = []

    def call(self, name):
        if name in self.fail:
            raise self.fail[name]

    def settimeout(self, value):
        self.call("timeout")
        self.timeouts.append(value)

    def connect(self, path):
        self.call("connect")
        assert path == "/synthetic/socket"

    def sendall(self, value):
        self.call("send")
        self.sent.append(value)

    def recv(self, size):
        self.call("recv")
        self.clock.now += self.delay
        return self.chunks.pop(0) if self.chunks else b""

    def close(self):
        self.closed = True
        self.call("close")


def call(client, **kwargs):
    def create(family, kind):
        assert (family, kind) == (socket.AF_UNIX, socket.SOCK_STREAM)
        return client

    return exchange("/synthetic/socket", REQUEST, factory=create, clock=client.clock, **kwargs)


def failure(client, code, **kwargs):
    with pytest.raises(TransportError) as caught:
        call(client, **kwargs)
    assert caught.value.code == code
    assert "private" not in str(caught.value)
    assert client.closed


def test_fragmented_reply_and_full_ownership():
    client = Socket([bytes([b]) for b in REPLY])
    assert call(client) == REPLY
    assert client.sent == [REQUEST] and client.closed
    assert all(t == 3 for t in client.timeouts)


@pytest.mark.parametrize("length", [5, 237, 4333])
def test_reply_sizes(length):
    raw = struct.pack("<I", length) + bytes(length - 4)
    client = Socket([raw[:4], raw[4:]])
    assert call(client) == raw


@pytest.mark.parametrize("length", [0, 4, 4334, 2**32 - 1])
def test_untrusted_length(length):
    failure(Socket([struct.pack("<I", length)]), "TRANSPORT_LENGTH")


@pytest.mark.parametrize("chunks", [[b""], [b"a", b""], [REPLY[:4], b""]])
def test_eof(chunks):
    failure(Socket(chunks), "TRANSPORT_EOF")


def test_port_violating_recv_bound():
    failure(Socket([bytes(5)]), "TRANSPORT_LENGTH")


@pytest.mark.parametrize("operation", ["timeout", "connect", "send", "recv"])
@pytest.mark.parametrize(
    "exception,code",
    [(OSError("private"), "TRANSPORT_IO"), (TimeoutError("private"), "TRANSPORT_DEADLINE")],
)
def test_io_failures_close_socket(operation, exception, code):
    failure(Socket(fail={operation: exception}), code)


def test_creation_failure_has_no_socket_to_close():
    def unavailable(*_):
        raise OSError("private path")

    with pytest.raises(TransportError) as caught:
        exchange("/synthetic/socket", REQUEST, factory=unavailable)
    assert caught.value.code == "TRANSPORT_IO"


def test_close_failure_rejects_otherwise_complete_reply():
    failure(Socket(fail={"close": OSError("private")}), "TRANSPORT_CLOSE")


def test_primary_error_is_retained_with_close_failure():
    failure(
        Socket(fail={"recv": OSError("private"), "close": OSError("private")}), "TRANSPORT_IO+CLOSE"
    )


def test_deadline_not_restarted_on_each_fragment():
    client = Socket([bytes([b]) for b in REPLY], delay=0.8)
    failure(client, "TRANSPORT_DEADLINE")
    assert client.timeouts[-1] < 0.7


def test_late_final_fragment_is_rejected():
    failure(Socket(delay=1.5), "TRANSPORT_DEADLINE")


def test_elapsed_factory_is_included_in_deadline():
    client = Socket()

    def delayed(*_):
        client.clock.now = 5
        return client

    with pytest.raises(TransportError) as caught:
        exchange("/synthetic/socket", REQUEST, factory=delayed, clock=client.clock)
    assert caught.value.code == "TRANSPORT_DEADLINE" and client.closed
    assert not client.sent


@pytest.mark.parametrize(
    "timeout",
    [0, -1, 31, pytest.param(10**1000, id="huge"), True, None, float("nan"), float("inf")],
)
def test_invalid_timeout(timeout):
    with pytest.raises(TransportError) as caught:
        exchange("/synthetic/socket", REQUEST, timeout=timeout)
    assert caught.value.code == "TRANSPORT_TIMEOUT_VALUE"


@pytest.mark.parametrize("path", [None, "relative", "/bad\0path", "/\ud800", "/" + "x" * 103])
def test_invalid_path(path):
    with pytest.raises(TransportError) as caught:
        exchange(path, REQUEST)
    assert caught.value.code == "TRANSPORT_PATH"


@pytest.mark.parametrize(
    "packet",
    [None, bytearray(5), b"", bytes(4), bytes(4097), bytes(5)],
    ids=["none", "mutable", "empty", "short", "long", "wrong_length"],
)
def test_invalid_request(packet):
    with pytest.raises(TransportError) as caught:
        exchange("/synthetic/socket", packet)
    assert caught.value.code == "TRANSPORT_REQUEST"


def test_persistent_session_two_messages_single_connect_and_total_deadline():
    from tools.inspectors.observer_transport import Session

    client = Socket([REPLY[:4], REPLY[4:], REPLY[:4], REPLY[4:]])
    session = Session("/synthetic/socket", factory=lambda *_: client, clock=client.clock)
    with session as channel:
        assert channel.exchange(REQUEST) == REPLY
        client.clock.now = 2
        assert channel.exchange(REQUEST) == REPLY
        assert client.timeouts[-1] == 1
    assert client.closed and client.sent == [REQUEST, REQUEST]
    with pytest.raises(TransportError, match="TRANSPORT_REUSE"):
        session.__enter__()
    with pytest.raises(TransportError, match="TRANSPORT_CLOSED"):
        session.exchange(REQUEST)


def test_caught_failure_poisons_session_and_prevents_retry():
    from tools.inspectors.observer_transport import Session

    client = Socket([b""])
    with Session("/synthetic/socket", factory=lambda *_: client, clock=client.clock) as session:
        with pytest.raises(TransportError, match="TRANSPORT_EOF"):
            session.exchange(REQUEST)
        with pytest.raises(TransportError, match="TRANSPORT_CLOSED"):
            session.exchange(REQUEST)
        with pytest.raises(TransportError, match="TRANSPORT_CLOSED"):
            session.peer_pid()
    assert client.sent == [REQUEST] and client.closed


def test_enter_interrupt_still_closes_owned_socket():
    from tools.inspectors.observer_transport import Session

    client = Socket(fail={"connect": KeyboardInterrupt()})
    with pytest.raises(KeyboardInterrupt):
        with Session("/synthetic/socket", factory=lambda *_: client):
            pytest.fail("entered")
    assert client.closed


@pytest.mark.parametrize(
    "platform,raw,expected",
    [
        ("darwin", struct.pack("=i", 42), (0, 2, 4)),
        ("linux", struct.pack("=3i", 42, 10, 20), (socket.SOL_SOCKET, 17, 12)),
    ],
)
def test_peer_pid_platform_options(monkeypatch, platform, raw, expected):
    import sys

    from tools.inspectors.observer_transport import Session

    client = Socket()
    options = []
    client.getsockopt = lambda *args: options.append(args) or raw
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(socket, "SO_PEERCRED", 17, raising=False)
    with Session("/synthetic/socket", factory=lambda *_: client) as session:
        assert session.peer_pid() == 42 and options == [expected]


def test_unsupported_peer_platform_and_semantic_close_failure(monkeypatch):
    import sys

    from tools.inspectors.observer_transport import Session
    from tools.pipeline.profile import ProfileError

    client = Socket()
    monkeypatch.setattr(sys, "platform", "unsupported")
    with pytest.raises(TransportError, match="TRANSPORT_PLATFORM"):
        with Session("/synthetic/socket", factory=lambda *_: client) as session:
            session.peer_pid()
    assert client.closed
    client = Socket(fail={"close": OSError()})
    with pytest.raises(TransportError, match=r"SEMANTIC\+CLOSE"):
        with Session("/synthetic/socket", factory=lambda *_: client):
            raise ProfileError("SEMANTIC", "private")


def test_peer_failure_poisons_connection_even_if_caught():
    from tools.inspectors.observer_transport import Session

    client = Socket()

    def failed(*_):
        raise OSError("peer unavailable")

    client.getsockopt = failed
    with Session("/synthetic/socket", factory=lambda *_: client) as session:
        with pytest.raises(OSError):
            session.peer_pid()
        with pytest.raises(TransportError, match="TRANSPORT_CLOSED"):
            session.exchange(REQUEST)
    assert client.closed and not client.sent
