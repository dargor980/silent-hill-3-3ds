"""Host callback probe launcher; frozen strict consumer for normal exchanges."""

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

mode = os.environ["SH3_HOST_CALLBACK_MODE"]
assert mode in {"late_cancel", "late_deadline", "duplicate_active", "duplicate_retired"}
passive = mode.startswith("late_")
phase = "release"
reader = NativePeerReader(Path(os.environ["SH3_PEER_LIBRARY"]))
expectation = DiagnosticExpectation(
    IdentityProfile.MACOS_PLATFORM_SLICES_V2,
    *[
        bytes.fromhex(os.environ[k])
        for k in ["SH3_RUNTIME_POLICY", "SH3_RUNTIME_MANIFEST_SHA256", "SH3_RUNTIME_PLATFORM"]
    ],
)


class Channel(UnixDiagnosticChannel):
    def __init__(self, *args):
        super().__init__(*args)
        self.frames = []

    def exchange_with_budget(self, packet, budget):
        wire = super().exchange_with_budget(packet, budget)
        self.frames.append(dict(request=packet.hex(), wire=wire.hex()))
        return wire

    def await_producer_close(self):
        self._open()
        self._socket.settimeout(2.0)
        assert self._socket.recv(1) == b"", "extra response after terminal UI cancellation"


with tempfile.TemporaryDirectory(prefix="sh3hc-", dir="/tmp") as temporary:
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
    print("HC_CHILD", process.pid, flush=True)
    logs = []

    def read_logs():
        for line in process.stdout:
            logs.append(line)
            print(line, end="", flush=True)

    logger = threading.Thread(target=read_logs)
    logger.start()
    session = channel = connection = None
    values, elapsed = [], []
    error = None
    peer_identity = None
    eof = False
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
            channel = Channel(connection, reader)
            connection = None
            session = PlatformDiagnosticSession(
                expectation,
                ExpectedPeer(process.pid, birth, os.geteuid()),
                channel,
                budget_clock=time.monotonic,
            )
            identity = channel.peer()
            assert identity.pid == process.pid and identity.birth_ns == birth
            assert identity.euid == os.geteuid() and identity.ruid == os.getuid()
            peer_identity = dict(
                pid=identity.pid, birth_ns=identity.birth_ns, euid=identity.euid, ruid=identity.ruid
            )
            if passive:
                # No request or acceptance-budget extension. Observe the producer's
                # original five-second expiry with an authenticated, open peer.
                channel._socket.settimeout(7.0)
                assert channel._socket.recv(1) == b"", "unexpected bytes without acquisition"
                eof = True
            for _ in range(0 if passive else 3):
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
            if phase == "release" and session.accepted == 3:
                channel._socket.shutdown(socket.SHUT_WR)
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
    events = [dict(p.split("=", 1) for p in s.split()[1:]) for s in logs if s.startswith("SH3_HC ")]
    print(
        "HC_CONSUMER "
        + json.dumps(
            dict(
                phase=phase,
                mode=mode,
                passive_peer=passive,
                peer_identity=peer_identity,
                eof=eof,
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
