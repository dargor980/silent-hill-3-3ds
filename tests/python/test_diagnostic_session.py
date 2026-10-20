"""PS03-08: session-owner doubles, not an attestation of a native peer."""

import os
import struct
import threading
from dataclasses import fields, replace
from pathlib import Path

import pytest

from tools.inspectors.diagnostic_session import (
    ExpectedPeer,
    PeerBoundDiagnostic,
    PeerIdentity,
    PeerUnavailable,
    PlatformDiagnosticSession,
)
from tools.inspectors.platform_diagnostic import MAX_U64, DiagnosticExpectation, IdentityProfile

VECTOR = bytes.fromhex(
    (
        Path(__file__).resolve().parents[2] / "tests/fixtures/platform-diagnostic-v2/observed.hex"
    ).read_text()
)
EXPECTED = DiagnosticExpectation(
    IdentityProfile.MACOS_PLATFORM_SLICES_V2, bytes([3]) * 32, bytes([4]) * 32, bytes([5]) * 32
)
PEER = PeerIdentity(0x12345678, 501, 501, 7, 0x1020304050607080, b"t" * 32)
LAUNCH = ExpectedPeer(PEER.pid, PEER.birth_ns, PEER.euid)


class Channel:
    def __init__(self):
        self.peer_value = PEER
        self.response = VECTOR
        self.peer_calls = self.exchanges = self.closes = 0
        self.on_peer = self.on_exchange = None
        self.replay = self.close_error = False
        self.saved = None

    def peer(self):
        self.peer_calls += 1
        if self.on_peer:
            self.on_peer(self.peer_calls)
        if isinstance(self.peer_value, BaseException):
            raise self.peer_value
        return self.peer_value

    def exchange(self, packet):
        self.exchanges += 1
        if self.on_exchange:
            self.on_exchange()
        if isinstance(self.response, BaseException):
            raise self.response
        if self.replay:
            return self.saved
        self.saved = self.response[:16] + packet[8:] + self.response[40:]
        return self.saved

    def close(self):
        self.closes += 1
        if self.close_error:
            raise OSError("private close detail")


def started():
    channel = Channel()
    session = PlatformDiagnosticSession(EXPECTED, LAUNCH, channel, entropy=lambda n: b"c" * n)
    assert session.sample() is not None
    return session, channel


def terminal(session, channel, reason=None):
    assert session.reason and session.last is None
    if reason:
        assert session.reason == reason
    original = session.reason
    calls = (channel.peer_calls, channel.exchanges, channel.closes)
    channel.peer_value, channel.response = PEER, VECTOR
    assert session.sample() is None
    session.cancel()
    session.close()
    assert (
        session.reason == original
        and (channel.peer_calls, channel.exchanges, channel.closes) == calls
    )
    assert channel.closes == 1


def test_stable_session_has_consecutive_requests_and_diagnostic_only():
    s, c = started()
    first = s.last
    assert type(first) is PeerBoundDiagnostic
    for n in range(2, 5):
        r = s.sample()
        assert r.diagnostic.request.sequence == n and r.diagnostic.request.challenge == b"c" * 16
    assert s.accepted == 4 and c.exchanges == 4 and c.peer_calls == 8
    assert {f.name for f in fields(first)} == {"peer", "diagnostic"}
    s.close()
    terminal(s, c, "closed")
    assert first.diagnostic.request.sequence == 1  # Historical copy, never a live permit.


@pytest.mark.parametrize("field", [f.name for f in fields(PeerIdentity)])
@pytest.mark.parametrize("when", ["before", "after"])
def test_each_peer_change_is_terminal(field, when):
    s, c = started()
    before = getattr(PEER, field)
    changed = replace(PEER, **{field: before + 1 if type(before) is int else b"x" * 32})
    if when == "before":
        c.peer_value = changed
    else:
        c.on_peer = lambda n: setattr(c, "peer_value", changed if n == 4 else PEER)
    assert s.sample() is None
    terminal(s, c)


@pytest.mark.parametrize(
    "peer",
    [
        None,
        {},
        replace(PEER, pid=0),
        replace(PEER, pid=True),
        replace(PEER, birth_ns=0),
        replace(PEER, token=bytes(32)),
        replace(PEER, token=b"x" * 31),
        replace(PEER, euid=-1),
        replace(PEER, ruid=1 << 32),
        replace(PEER, pid_version=1 << 32),
    ],
)
def test_invalid_native_read_never_becomes_identity(peer):
    s, c = started()
    c.peer_value = peer
    assert s.sample() is None
    terminal(s, c, "peer_unavailable")


@pytest.mark.parametrize(
    ("offset", "raw"),
    [
        (40, struct.pack("<I", 123)),
        (44, struct.pack("<Q", 123)),
        (52, b"x" * 16),
        (68, b"x" * 32),
        (100, b"x" * 32),
        (228, struct.pack("<Q", 2)),
        (236, struct.pack("<I", 27)),
        (240, struct.pack("<I", 620)),
        (262, struct.pack("<Q", 99)),
        (270, struct.pack("<Q", 99)),
        (278, struct.pack("<Q", 99)),
        (286, struct.pack("<Q", 99)),
    ],
)
def test_message_identity_change_and_restoration_cannot_revive(offset, raw):
    s, c = started()
    c.response = VECTOR[:offset] + raw + VECTOR[offset + len(raw) :]
    assert s.sample() is None
    terminal(s, c, "process_mismatch" if offset in (40, 44) else "identity_changed")


@pytest.mark.parametrize(
    ("offset", "raw"), [(7, b"1"), (9, b"1"), (132, b"x" * 32), (164, b"x" * 32), (196, b"x" * 32)]
)
def test_crossed_profile_version_evidence(offset, raw):
    s, c = started()
    c.response = VECTOR[:offset] + raw + VECTOR[offset + len(raw) :]
    assert s.sample() is None
    terminal(s, c, "message_invalid")


def test_facts_can_change_but_do_not_grant_capabilities():
    s, c = started()
    c.response = VECTOR[:244] + bytes([1]) * 18 + VECTOR[262:]
    assert s.sample() is not None and s.accepted == 2
    s.close()


def test_replay_is_not_retried():
    s, c = started()
    c.replay = True
    assert s.sample() is None
    terminal(s, c, "message_invalid")
    assert c.exchanges == 2


@pytest.mark.parametrize("reason", range(1, 10))
def test_provider_rejection_erases_previous_diagnostic(reason):
    s, c = started()
    c.response = b"SH3PDR02" + bytes([2, 0, 0, 0, reason, 0, 0, 0]) + bytes(278)
    assert s.sample() is None
    terminal(s, c)
    assert s.reason.startswith("provider_")


@pytest.mark.parametrize("where", ["peer_value", "response"])
@pytest.mark.parametrize(
    "error",
    [PeerUnavailable("private details"), OSError("private details"), ValueError("private details")],
)
def test_io_failures_are_sanitized_and_terminal(where, error):
    s, c = started()
    setattr(c, where, error)
    assert s.sample() is None
    terminal(s, c, "channel_unavailable")


def test_close_failure_preserves_first_cause():
    s, c = started()
    c.close_error = True
    c.peer_value = None
    assert s.sample() is None
    terminal(s, c, "peer_unavailable")
    assert s.close_failed


@pytest.mark.parametrize("error", [RuntimeError("bug"), KeyboardInterrupt()])
def test_unexpected_errors_discard_before_propagating(error):
    s, c = started()
    c.response = error
    with pytest.raises(type(error)):
        s.sample()
    terminal(s, c, "internal_error")


@pytest.mark.parametrize("during", ["first_peer", "exchange", "last_peer"])
@pytest.mark.parametrize("action", ["cancel", "close", "sample"])
def test_terminal_callback_cannot_publish_late_result(during, action):
    s, c = started()

    def callback():
        return getattr(s, action)()

    if during == "exchange":
        c.on_exchange = callback
    else:
        c.on_peer = lambda n: callback() if n == (3 if during == "first_peer" else 4) else None
    assert s.sample() is None
    terminal(s, c, {"cancel": "cancelled", "close": "closed", "sample": "reentrant"}[action])
    assert s.accepted == 1


def test_another_thread_discards_without_channel_io():
    s, c = started()
    t = threading.Thread(target=s.sample)
    t.start()
    t.join()
    terminal(s, c, "owner_changed")
    assert c.exchanges == 1


def test_changed_pid_discards_inherited_session(monkeypatch):
    s, c = started()
    pid = os.getpid()
    monkeypatch.setattr(os, "getpid", lambda: pid + 1)
    assert s.sample() is None
    terminal(s, c, "owner_changed")


def test_sequence_exhaustion_is_terminal():
    s, c = started()
    s._sequence = MAX_U64
    assert s.sample() is None
    terminal(s, c, "sequence_exhausted")


@pytest.mark.parametrize(
    "peer", [None, {}, ExpectedPeer(0, 1, 1), ExpectedPeer(1, 0, 1), ExpectedPeer(1, 1, -1)]
)
def test_bad_launch_expectation_closes_before_io(peer):
    c = Channel()
    s = PlatformDiagnosticSession(EXPECTED, peer, c)
    terminal(s, c, "configuration")
    assert c.peer_calls == c.exchanges == 0


@pytest.mark.parametrize("nonce", [None, b"", bytes(16), b"x" * 15, b"x" * 17])
def test_invalid_entropy_is_not_a_session(nonce):
    c = Channel()
    s = PlatformDiagnosticSession(EXPECTED, LAUNCH, c, entropy=lambda n: nonce)
    terminal(s, c, "configuration")


def test_invalid_policy_is_rejected_before_io():
    c = Channel()
    s = PlatformDiagnosticSession(None, LAUNCH, c)
    terminal(s, c, "configuration")
    assert c.peer_calls == 0


@pytest.mark.parametrize("error", [RuntimeError("entropy bug"), KeyboardInterrupt()])
def test_constructor_bug_closes_before_propagating(error):
    c = Channel()

    def entropy(_):
        raise error

    with pytest.raises(type(error)):
        PlatformDiagnosticSession(EXPECTED, LAUNCH, c, entropy=entropy)
    assert c.closes == 1 and c.peer_calls == c.exchanges == 0


def test_first_observation_requires_equal_peer_at_both_boundaries():
    c = Channel()
    s = PlatformDiagnosticSession(EXPECTED, LAUNCH, c)
    c.on_peer = lambda n: (
        setattr(c, "peer_value", replace(PEER, token=b"z" * 32)) if n == 2 else None
    )
    assert s.sample() is None
    terminal(s, c, "peer_changed")
