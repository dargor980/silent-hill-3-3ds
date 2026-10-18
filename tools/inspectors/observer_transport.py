"""OBT05/AC03: bounded Unix sessions, independent of observation semantics."""

import socket
import struct
import time


class TransportError(ValueError):
    """Sanitized code only: never include paths, requests or captured bytes."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _path(path):
    try:
        size = len(path.encode()) if isinstance(path, str) else 104
    except UnicodeError:
        raise TransportError("TRANSPORT_PATH") from None
    if not isinstance(path, str) or not path.startswith("/") or "\0" in path or size > 103:
        raise TransportError("TRANSPORT_PATH")


def _request(packet):
    if (
        type(packet) is not bytes
        or not 5 <= len(packet) <= 4096
        or struct.unpack_from("<I", packet)[0] != len(packet)
    ):
        raise TransportError("TRANSPORT_REQUEST")


class Session:
    """AC03: one owned connection, one deadline, no reconnect after failure."""

    def __init__(self, path, *, timeout=3.0, factory=socket.socket, clock=time.monotonic):
        _path(path)
        if type(timeout) not in (int, float) or not 0 < timeout <= 30:
            raise TransportError("TRANSPORT_TIMEOUT_VALUE")
        self.path, self.timeout, self.factory, self.clock = path, timeout, factory, clock
        self.client = None
        self.used = self.broken = False

    def remaining(self):
        budget = self.deadline - self.clock()
        if budget <= 0:
            raise TransportError("TRANSPORT_DEADLINE")
        self.client.settimeout(budget)

    def __enter__(self):
        if self.used:
            raise TransportError("TRANSPORT_REUSE")
        self.used = True
        self.deadline = self.clock() + self.timeout
        try:
            self.client = self.factory(socket.AF_UNIX, socket.SOCK_STREAM)
            self.remaining()
            self.client.connect(self.path)
        except BaseException as error:
            self.__exit__(type(error), error, None)
            raise
        return self

    def __exit__(self, kind, error, traceback):
        client, self.client = self.client, None
        code = None
        if isinstance(error, TransportError):
            code = error.code
        elif isinstance(error, TimeoutError):
            code = "TRANSPORT_DEADLINE"
        elif isinstance(error, OSError):
            code = "TRANSPORT_IO"
        try:
            if client is not None:
                client.close()
        except OSError:
            primary = code or getattr(error, "code", None)
            code = primary + "+CLOSE" if primary else "TRANSPORT_CLOSE"
        if code:
            raise TransportError(code) from None
        return False

    def peer_pid(self):
        """Actual kernel peer. macOS constants verified against the pinned SDK."""
        import sys

        if self.client is None or self.broken:
            raise TransportError("TRANSPORT_CLOSED")
        try:
            if sys.platform == "darwin":
                return struct.unpack("=i", self.client.getsockopt(0, 2, 4))[0]
            if sys.platform.startswith("linux"):
                return struct.unpack(
                    "=3i", self.client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
                )[0]
            raise TransportError("TRANSPORT_PLATFORM")
        except BaseException:
            self.broken = True
            raise

    def exchange(self, packet):
        if self.client is None or self.broken:
            raise TransportError("TRANSPORT_CLOSED")

        def read_exact(size):
            data = bytearray()
            while len(data) < size:
                self.remaining()
                chunk = self.client.recv(size - len(data))
                if not chunk:
                    raise TransportError("TRANSPORT_EOF")
                if len(chunk) > size - len(data):
                    raise TransportError("TRANSPORT_LENGTH")
                data.extend(chunk)
            return bytes(data)

        try:
            _request(packet)
            self.remaining()
            self.client.sendall(packet)
            header = read_exact(4)
            length = struct.unpack("<I", header)[0]
            if not 5 <= length <= 4333:
                raise TransportError("TRANSPORT_LENGTH")
            result = header + read_exact(length - 4)
            if self.clock() >= self.deadline:
                raise TransportError("TRANSPORT_DEADLINE")
            return result
        except BaseException:
            self.broken = True
            raise


def exchange(path, packet, *, timeout=3.0, factory=socket.socket, clock=time.monotonic):
    """OBT05 compatibility: validate before opening and close before returning."""
    _path(path)
    _request(packet)
    with Session(path, timeout=timeout, factory=factory, clock=clock) as session:
        result = session.exchange(packet)
    return result
