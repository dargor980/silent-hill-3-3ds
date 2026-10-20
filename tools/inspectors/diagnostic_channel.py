"""PS02/07: macOS peer bridge and a bounded, exclusively owned Unix stream."""

import ctypes
import math
import os
import select
import socket
import struct
import sys
import threading
import time
from pathlib import Path

from tools.inspectors.diagnostic_session import PeerIdentity, PeerUnavailable
from tools.inspectors.platform_diagnostic import REQUEST_MAGIC, REQUEST_SIZE, RESPONSE_SIZE


class NativePeerReader:
    def __init__(self, library):
        # This is launcher configuration, not a path supplied by the peer.
        if sys.platform != "darwin" or not Path(library).is_absolute():
            raise PeerUnavailable("native_configuration")
        self._library = ctypes.CDLL(str(library))
        self._read = self._library.sh3_macos_peer_v1
        self._read.argtypes = (ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t)
        self._read.restype = ctypes.c_int
        self._birth = self._library.sh3_macos_birth_v1
        self._birth.argtypes = (ctypes.c_int,)
        self._birth.restype = ctypes.c_uint64

    def birth(self, pid):
        if type(pid) is not int or not 0 < pid <= 0x7FFFFFFF:
            raise PeerUnavailable("birth_unavailable")
        value = self._birth(pid)
        if not value:
            raise PeerUnavailable("birth_unavailable")
        return value

    def read(self, fd):
        if type(fd) is not int or not 0 <= fd <= 0x7FFFFFFF:
            raise PeerUnavailable("peer_unavailable")
        buffer = (ctypes.c_ubyte * 56)()
        if self._read(fd, buffer, 56) != 1:
            raise PeerUnavailable("peer_unavailable")
        data = bytes(buffer)
        return PeerIdentity(*struct.unpack_from("<4IQ", data), data[24:])


class UnixDiagnosticChannel:
    """Adopts one connected socket; caller must relinquish every other alias.

    timeout bounds legacy exchange's IO only. exchange_with_budget instead uses
    the session's existing BC control for both time and cooperative cancellation.
    Neither method alone proves the producer's DW budget or runtime gates.
    """

    def __init__(self, connection, reader, *, timeout=2.0, clock=time.monotonic):
        self._socket, self._reader, self._clock = connection, reader, clock
        self._pid = os.getpid()
        self._thread = threading.get_ident()
        self.close_failed = False
        self._timeout = timeout
        if (
            type(timeout) not in (int, float)
            or not math.isfinite(timeout)
            or not 0 < timeout <= 5
            or connection.family != socket.AF_UNIX
            or connection.type != socket.SOCK_STREAM
        ):
            self.close()
            raise PeerUnavailable("channel_configuration")

    def _open(self):
        if self._socket is None or os.getpid() != self._pid:
            raise PeerUnavailable("channel_closed")

    def peer(self):
        self._open()
        return self._reader.read(self._socket.fileno())

    def exchange(self, packet):
        self._open()
        try:
            if (
                type(packet) is not bytes
                or len(packet) != REQUEST_SIZE
                or packet[:8] != REQUEST_MAGIC
            ):
                raise PeerUnavailable("channel_request")
            deadline = self._clock() + self._timeout

            def remaining():
                budget = deadline - self._clock()
                if not math.isfinite(budget) or budget <= 0:
                    raise PeerUnavailable("channel_deadline")
                self._socket.settimeout(budget)

            remaining()
            self._socket.sendall(packet)
            data = bytearray()
            while len(data) < RESPONSE_SIZE:
                remaining()
                part = self._socket.recv(RESPONSE_SIZE - len(data))
                if not part:
                    raise PeerUnavailable("channel_eof")
                data.extend(part)
            remaining()
            if select.select([self._socket], [], [], 0)[0]:
                # Extra data or EOF both invalidate this synchronous exchange.
                raise PeerUnavailable("channel_extra_or_eof")
            return bytes(data)
        except BaseException:
            try:
                self.close()
            except OSError:
                pass
            raise

    def close(self):
        connection, self._socket = self._socket, None
        if connection is not None:
            try:
                connection.close()
            except OSError:
                self.close_failed = True
                raise

    def exchange_with_budget(self, packet, budget):
        """BC03/06: use the owner's existing budget, never restart its clock.

        Partial bytes already sent cannot be withdrawn. The session admits only
        a complete frame that passes identity and budget checks at publication.
        """
        self._open()
        if threading.get_ident() != self._thread:
            raise PeerUnavailable("owner_changed")
        try:
            budget.checkpoint()
            if (
                type(packet) is not bytes
                or len(packet) != REQUEST_SIZE
                or packet[:8] != REQUEST_MAGIC
            ):
                raise PeerUnavailable("channel_request")
            self._socket.setblocking(False)

            def wait(write):
                while True:
                    timeout = min(0.02, budget.remaining())
                    try:
                        ready = select.select(
                            [] if write else [self._socket],
                            [self._socket] if write else [],
                            [],
                            timeout,
                        )
                    except InterruptedError:
                        budget.checkpoint()
                        continue
                    budget.checkpoint()
                    if ready[1 if write else 0]:
                        return

            sent = 0
            while sent < len(packet):
                wait(True)
                budget.checkpoint()
                try:
                    n = self._socket.send(packet[sent:])
                except (BlockingIOError, InterruptedError):
                    budget.checkpoint()
                    continue
                budget.checkpoint()
                if not 0 < n <= len(packet) - sent:
                    raise PeerUnavailable("channel_write")
                sent += n
            data = bytearray()
            while len(data) < RESPONSE_SIZE:
                wait(False)
                budget.checkpoint()
                try:
                    part = self._socket.recv(RESPONSE_SIZE - len(data))
                except (BlockingIOError, InterruptedError):
                    budget.checkpoint()
                    continue
                budget.checkpoint()
                if not part:
                    raise PeerUnavailable("channel_eof")
                data.extend(part)
            budget.checkpoint()
            if select.select([self._socket], [], [], 0)[0]:
                raise PeerUnavailable("channel_extra_or_eof")
            budget.checkpoint()
            return bytes(data)
        except BaseException:
            try:
                self.close()
            except OSError:
                pass
            raise
