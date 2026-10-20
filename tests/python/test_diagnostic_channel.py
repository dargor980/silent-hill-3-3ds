"""PS07 real stream IO tests; reader doubles here, native reader in macOS suite."""

import socket
import threading

import pytest

from tools.inspectors.diagnostic_channel import NativePeerReader, UnixDiagnosticChannel
from tools.inspectors.diagnostic_session import PeerUnavailable

REQUEST = b"SH3PDQ02" + b"c" * 16 + (1).to_bytes(8, "little")


class Reader:
    def read(self, fd):
        return fd


@pytest.mark.parametrize("mode", ["whole", "fragmented", "eof", "short", "extra", "timeout"])
def test_real_stream_boundaries(mode):
    client, server = socket.socketpair()
    done = threading.Event()
    errors = []

    def serve():
        try:
            data = b""
            while len(data) < 32:
                data += server.recv(32 - len(data))
            assert data == REQUEST
            if mode == "fragmented":
                for _ in range(294):
                    server.sendall(b"x")
            elif mode == "whole":
                server.sendall(b"x" * 294)
            elif mode == "extra":
                server.sendall(b"x" * 295)
            elif mode == "short":
                server.sendall(b"x" * 17)
                server.shutdown(socket.SHUT_WR)
            elif mode == "eof":
                server.shutdown(socket.SHUT_WR)
            done.wait(1)
        except BaseException as e:
            errors.append(e)
        finally:
            server.close()

    thread = threading.Thread(target=serve)
    thread.start()
    channel = UnixDiagnosticChannel(client, Reader(), timeout=0.15)
    try:
        assert channel.peer() == client.fileno()
        if mode in ("whole", "fragmented"):
            assert channel.exchange(REQUEST) == b"x" * 294
        else:
            with pytest.raises((PeerUnavailable, TimeoutError)):
                channel.exchange(REQUEST)
            with pytest.raises(PeerUnavailable):
                channel.exchange(REQUEST)
    finally:
        channel.close()
        done.set()
        thread.join(2)
    assert not thread.is_alive() and not errors


@pytest.mark.parametrize("timeout", [0, -1, 6, True, float("nan"), float("inf"), "2"])
def test_bad_budget_closes_owned_socket(timeout):
    a, b = socket.socketpair()
    try:
        with pytest.raises(PeerUnavailable):
            UnixDiagnosticChannel(a, Reader(), timeout=timeout)
        assert a.fileno() == -1
    finally:
        a.close()
        b.close()


@pytest.mark.parametrize("packet", [b"", b"x" * 32, bytearray(REQUEST), b"SH3PDQ01" + REQUEST[8:]])
def test_bad_request_closes_socket(packet):
    a, b = socket.socketpair()
    channel = UnixDiagnosticChannel(a, Reader())
    try:
        with pytest.raises(PeerUnavailable):
            channel.exchange(packet)
        assert a.fileno() == -1
    finally:
        channel.close()
        b.close()


def test_inherited_channel_and_expired_clock(monkeypatch):
    a, b = socket.socketpair()
    channel = UnixDiagnosticChannel(a, Reader())
    channel._pid += 1
    try:
        with pytest.raises(PeerUnavailable):
            channel.peer()
    finally:
        channel.close()
        b.close()
    a, b = socket.socketpair()
    ticks = iter([1.0, 9.0])
    channel = UnixDiagnosticChannel(a, Reader(), clock=lambda: next(ticks))
    try:
        with pytest.raises(PeerUnavailable, match="deadline"):
            channel.exchange(REQUEST)
    finally:
        channel.close()
        b.close()


def test_native_configuration_is_local_absolute_path():
    with pytest.raises(PeerUnavailable):
        NativePeerReader("relative.dylib")


def test_close_error_does_not_replace_original_transport_error():
    class RaisingClose(socket.socket):
        def close(self):
            super().close()
            raise OSError("close error")

    a, b = socket.socketpair()
    adopted = RaisingClose(fileno=a.detach())
    channel = UnixDiagnosticChannel(adopted, Reader())
    try:
        with pytest.raises(PeerUnavailable, match="channel_request"):
            channel.exchange(b"invalid")
        assert adopted.fileno() == -1
    finally:
        channel.close()
        b.close()
