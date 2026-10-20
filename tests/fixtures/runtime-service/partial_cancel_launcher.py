"""Observe real partial bytes without changing the strict consumer or its budget."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, os.environ["SH3_REPO"])
from tools.inspectors.diagnostic_channel import NativePeerReader, UnixDiagnosticChannel
from tools.inspectors.diagnostic_session import ExpectedPeer, PlatformDiagnosticSession
from tools.inspectors.platform_diagnostic import DiagnosticExpectation, IdentityProfile

phase = "partial"
prefix_bytes = int(os.environ["SH3_PARTIAL_BYTES"])
assert prefix_bytes in (1, 293)
reader = NativePeerReader(Path(os.environ["SH3_PEER_LIBRARY"]))
expectation = DiagnosticExpectation(
    IdentityProfile.MACOS_PLATFORM_SLICES_V2,
    *[
        bytes.fromhex(os.environ[k])
        for k in ["SH3_RUNTIME_POLICY", "SH3_RUNTIME_MANIFEST_SHA256", "SH3_RUNTIME_PLATFORM"]
    ],
)


class RecordedSocket:
    def __init__(self, connection):
        self.connection = connection
        self.received = bytearray()
        self.eof = False
        self.ready_ns = None

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def recv(self, *args):
        part = self.connection.recv(*args)
        self.received.extend(part)
        self.eof = not part
        if len(self.received) == prefix_bytes and self.ready_ns is None:
            with Path(os.environ["SH3_PARTIAL_READY"]).open("x") as ready:
                ready.write("received prefix\n")
            self.ready_ns = time.monotonic_ns()
        return part


class Channel(UnixDiagnosticChannel):
    def __init__(self, *args):
        super().__init__(*args)
        self.frames = []
        self.requests = []
        self.exchange_error = None
        self.peers = []

    def exchange_with_budget(self, packet, budget):
        self.requests.append(packet.hex())
        try:
            wire = super().exchange_with_budget(packet, budget)
        except Exception as exc:
            self.exchange_error = type(exc).__name__ + ": " + str(exc)
            raise
        self.frames.append(dict(request=packet.hex(), wire=wire.hex()))
        return wire

    def peer(self):
        p = super().peer()
        self.peers.append(
            dict(
                pid=p.pid,
                birth_ns=p.birth_ns,
                euid=p.euid,
                ruid=p.ruid,
                pid_version=p.pid_version,
                token=p.token.hex(),
            )
        )
        return p


with tempfile.TemporaryDirectory(prefix="sh3pc-", dir="/tmp") as temporary:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    endpoint = str(Path(temporary) / "peer")
    server.bind(endpoint)
    os.chmod(endpoint, 0o600)
    server.listen(1)
    server.settimeout(0.2)
    env = dict(
        os.environ, SH3_RUNTIME_ENDPOINT=endpoint, TMPDIR=temporary, XDG_RUNTIME_DIR=temporary
    )
    for key in ["DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "SH3_PEER_LIBRARY"]:
        env.pop(key, None)
    process = subprocess.Popen(
        sys.argv[1:], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    print("PC_CHILD", process.pid, flush=True)
    logs = []

    def read_logs():
        for line in process.stdout:
            logs.append(line)
            print(line, end="", flush=True)

    logger = threading.Thread(target=read_logs)
    logger.start()
    session = channel = connection = recorded = None
    values, elapsed = [], []
    error = None
    try:
        if phase != "waiting":
            birth = reader.birth(process.pid)
            until = time.monotonic() + 70
            while connection is None:
                assert process.poll() is None and time.monotonic() < until
                try:
                    connection, _ = server.accept()
                except TimeoutError:
                    pass
            recorded = RecordedSocket(connection)
            channel = Channel(recorded, reader)
            connection = None
            session = PlatformDiagnosticSession(
                expectation,
                ExpectedPeer(process.pid, birth, os.geteuid()),
                channel,
                budget_clock=time.monotonic,
            )
            for _ in range(3 if phase == "release" else 1):
                start = time.monotonic()
                value = session.sample()
                elapsed.append(time.monotonic() - start)
                if value is None:
                    break
                d = value.diagnostic
                assert d.pid == process.pid == value.peer.pid
                assert d.birth_ns == birth == value.peer.birth_ns
                values.append(
                    dict(
                        sequence=d.request.sequence,
                        pid=d.pid,
                        birth_ns=d.birth_ns,
                        nonce=d.provider_nonce.hex(),
                        application=d.application_images,
                        platform=d.platform_images,
                        revision=d.loader_revision,
                        facts=[f.value for f in d.facts],
                        epochs=[d.epochs.host, d.epochs.pine, d.epochs.vu, d.epochs.gs],
                    )
                )
        process.wait(timeout=70 if phase == "waiting" else 40)
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)
    finally:
        if session:
            session.close()
        if connection:
            connection.close()
        server.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        logger.join(3)
    assert not logger.is_alive()
    ends = [s for s in logs if s.startswith("SH3_RT_END ")]
    events = [dict(p.split("=", 1) for p in s.split()[1:]) for s in logs if s.startswith("SH3_PC ")]
    print(
        "PC_CONSUMER "
        + json.dumps(
            dict(
                phase=phase,
                route=os.environ["SH3_PARTIAL_ROUTE"],
                prefix_bytes=prefix_bytes,
                received=bytes(recorded.received).hex() if recorded else "",
                eof=recorded.eof if recorded else False,
                ready_ns=recorded.ready_ns if recorded else None,
                requests=channel.requests if channel else [],
                exchange_error=channel.exchange_error if channel else None,
                peers=channel.peers if channel else [],
                reason=session.reason if session else "",
                last_is_none=session.last is None if session else True,
                accepted=session.accepted if session else 0,
                frames=channel.frames if channel else [],
                values=values,
                elapsed_seconds=elapsed,
                error=error,
                producer=dict(p.split("=", 1) for p in ends[0].split()[1:])
                if len(ends) == 1
                else None,
                events=events,
                child_exit=process.returncode,
                closed=session.closed if session else True,
                close_failed=session.close_failed if session else False,
                admitted=False,
            ),
            sort_keys=True,
        ),
        flush=True,
    )
