"""PS01-08: one owner, one channel, terminal peer-bound diagnostic session."""

import os
import secrets
import threading
from dataclasses import dataclass
from typing import Protocol

from tools.inspectors.diagnostic_budget import BudgetStopped, DiagnosticSessionBudget
from tools.inspectors.platform_diagnostic import (
    MAX_U64,
    DiagnosticExpectation,
    DiagnosticFormatError,
    DiagnosticRequest,
    UnverifiedDiagnosticRejection,
    UnverifiedPlatformDiagnostic,
    _expectation,
    decode_platform_diagnostic,
    encode_diagnostic_request,
)


class PeerUnavailable(ValueError):
    """Sanitized native/transport failure; contains no peer payload or pathname."""


@dataclass(frozen=True)
class ExpectedPeer:
    pid: int
    birth_ns: int
    uid: int


@dataclass(frozen=True)
class PeerIdentity:
    pid: int
    euid: int
    ruid: int
    pid_version: int
    birth_ns: int
    token: bytes


class DiagnosticChannel(Protocol):
    def peer(self) -> PeerIdentity: ...
    def exchange(self, packet: bytes) -> bytes: ...
    def close(self) -> None: ...


class BudgetedDiagnosticChannel(Protocol):
    def peer(self) -> PeerIdentity: ...
    def exchange_with_budget(self, packet: bytes, budget: DiagnosticSessionBudget) -> bytes: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class PeerBoundDiagnostic:
    """Historical channel observation, never a capture permission or IP identity."""

    peer: PeerIdentity
    diagnostic: UnverifiedPlatformDiagnostic


def _int(value, maximum, minimum=0):
    return type(value) is int and minimum <= value <= maximum


def _valid_peer(p):
    return (
        type(p) is PeerIdentity
        and _int(p.pid, 0x7FFFFFFF, 1)
        and _int(p.birth_ns, MAX_U64, 1)
        and all(_int(v, 0xFFFFFFFF) for v in (p.euid, p.ruid, p.pid_version))
        and type(p.token) is bytes
        and len(p.token) == 32
        and any(p.token)
    )


def _identity(d):
    return (
        d.expectation,
        d.scope,
        d.platform_assumed,
        d.pid,
        d.birth_ns,
        d.provider_nonce,
        d.file_objects,
        d.classified_images,
        d.loader_revision,
        d.application_images,
        d.platform_images,
        d.epochs,
    )


class PlatformDiagnosticSession:
    """The channel and its trusted reader are supplied locally, never from PD.

    A sample binds identity at two boundaries. It does not monitor continuously
    or prove absence of unobserved changes. Channel operations belong to one
    thread. An explicit budget_clock enables BC's total consumer deadline and
    permits other threads to request cancel/close without touching the channel.
    """

    def __init__(
        self,
        expectation: DiagnosticExpectation,
        peer: ExpectedPeer,
        channel: DiagnosticChannel | BudgetedDiagnosticChannel,
        *,
        entropy=secrets.token_bytes,
        budget_clock=None,
    ):
        self._expectation, self._expected, self._channel = expectation, peer, channel
        self._owner = (os.getpid(), threading.get_ident())
        self._baseline = self._peer = self._last = None
        self._sequence = 1
        self._busy = False
        self._challenge = b""
        self._reason = ""
        self._accepted = 0
        self._close_failed = False
        self._closed = False
        self._budget = DiagnosticSessionBudget(budget_clock) if budget_clock is not None else None
        try:
            if self._budget and (
                not callable(budget_clock)
                or not callable(getattr(channel, "exchange_with_budget", None))
            ):
                raise DiagnosticFormatError("configuration")
            _expectation(expectation)
            if not (
                type(peer) is ExpectedPeer
                and _int(peer.pid, 0x7FFFFFFF, 1)
                and _int(peer.birth_ns, MAX_U64, 1)
                and _int(peer.uid, 0xFFFFFFFF)
            ):
                raise DiagnosticFormatError("configuration")
            self._challenge = entropy(16)
            encode_diagnostic_request(DiagnosticRequest(self._challenge, 1))
        except (ValueError, OSError):
            self._discard("configuration")
        except BaseException:
            self._discard("internal_error")
            raise

    @property
    def reason(self):
        if self._owner[0] != os.getpid():
            return self._reason or "owner_changed"
        return self._reason or (self._budget.reason if self._budget else "")

    @property
    def last(self):
        return None if self.reason else self._last

    @property
    def closed(self):
        """Owner released the channel; close_failed distinguishes cleanup failure."""
        return self._closed

    @property
    def accepted(self):
        return self._accepted

    @property
    def close_failed(self):
        return self._close_failed

    def _discard(self, reason):
        if self._budget:
            reason = self._budget.stop(reason)
        if not self._reason:
            self._reason = reason
            self._baseline = self._peer = self._last = None
            self._challenge = b""
            channel, self._channel = self._channel, None
            try:
                channel.close()
            except Exception:
                self._close_failed = True
            finally:
                if getattr(channel, "close_failed", False):
                    self._close_failed = True
                self._closed = True
        return None

    def close(self):
        self._stop("closed")

    def cancel(self):
        self._stop("cancelled")

    def _stop(self, reason):
        if self._discard_inherited():
            return
        if self._budget:
            self._budget.stop(reason)
            if self._owner != (os.getpid(), threading.get_ident()) or self._busy:
                return
        self._discard(reason)

    def _discard_inherited(self):
        if self._owner[0] != os.getpid():
            # A fork may inherit a locked budget from a vanished thread. Never
            # acquire it. Closing this process's fd copy does not close the parent.
            self._budget = None
            self._discard("owner_changed")
            return True
        return False

    def _checkpoint(self):
        if self._budget:
            self._budget.checkpoint()

    def _check_peer(self, p):
        if not _valid_peer(p):
            raise PeerUnavailable("peer_unavailable")
        if (p.pid, p.birth_ns, p.euid) != (
            self._expected.pid,
            self._expected.birth_ns,
            self._expected.uid,
        ):
            raise PeerUnavailable("peer_mismatch")
        if self._peer is not None and p != self._peer:
            raise PeerUnavailable("peer_changed")

    def sample(self):
        if self._discard_inherited():
            return None
        if self._budget and self._owner != (os.getpid(), threading.get_ident()):
            self._budget.stop("owner_changed")
            return None
        if self._budget and self._budget.reason:
            if self._busy:
                return None
            return self._discard(self._budget.reason)
        if self._reason:
            return None
        if self._busy:
            if self._budget:
                self._budget.stop("reentrant")
                return None
            return self._discard("reentrant")
        if self._owner != (os.getpid(), threading.get_ident()):
            return self._discard("owner_changed")
        if not 0 < self._sequence < MAX_U64:
            return self._discard("sequence_exhausted")
        self._busy = True
        try:
            if self._budget:
                self._budget.begin(initial=self._accepted == 0)
            self._checkpoint()
            first = self._channel.peer()
            self._checkpoint()
            if self._reason:
                return None
            self._check_peer(first)
            request = DiagnosticRequest(self._challenge, self._sequence)
            packet = encode_diagnostic_request(request)
            self._checkpoint()
            wire = (
                self._channel.exchange_with_budget(packet, self._budget)
                if self._budget
                else self._channel.exchange(packet)
            )
            self._checkpoint()
            value = decode_platform_diagnostic(wire, expectation=self._expectation, request=request)
            self._checkpoint()
            if self._reason:
                return None
            last = self._channel.peer()
            self._checkpoint()
            if self._reason:
                return None
            self._check_peer(last)
            if first != last:
                return self._discard("peer_changed")
            if type(value) is UnverifiedDiagnosticRejection:
                return self._discard("provider_" + value.reason.name.lower())
            if (value.pid, value.birth_ns) != (first.pid, first.birth_ns):
                return self._discard("process_mismatch")
            identity = _identity(value)
            if self._baseline is not None and identity != self._baseline:
                return self._discard("identity_changed")

            def commit():
                self._baseline, self._peer = identity, first
                self._last = PeerBoundDiagnostic(first, value)
                self._sequence += 1
                self._accepted += 1
                return self._last

            return self._budget.publish(commit) if self._budget else commit()
        except BudgetStopped as error:
            return self._discard(str(error))
        except DiagnosticFormatError:
            return self._discard("message_invalid")
        except PeerUnavailable as error:
            # Only fixed codes from a trusted adapter, never its free-form text.
            code = str(error)
            return self._discard(
                code
                if code in ("peer_unavailable", "peer_mismatch", "peer_changed")
                else "channel_unavailable"
            )
        except (OSError, ValueError):
            return self._discard("channel_unavailable")
        except BaseException:
            self._discard("internal_error")
            raise
        finally:
            self._busy = False
            if self._budget and self._budget.reason:
                self._discard(self._budget.reason)
