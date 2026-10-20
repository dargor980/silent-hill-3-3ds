"""RX: exercise peer abandonment against a separately pinned PCSX2 candidate."""

import hashlib
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

mode = sys.argv[1]
requested = {"connect": 0, "first": 1, "third": 3, "extra": 3}[mode]
reader = NativePeerReader(Path(os.environ["SH3_PEER_LIBRARY"]))
expectation = DiagnosticExpectation(
    IdentityProfile.MACOS_PLATFORM_SLICES_V2,
    *[
        bytes.fromhex(os.environ[key])
        for key in ("SH3_RUNTIME_POLICY", "SH3_RUNTIME_MANIFEST_SHA256", "SH3_RUNTIME_PLATFORM")
    ],
)


class RecordingChannel(UnixDiagnosticChannel):
    def __init__(self, *args):
        super().__init__(*args)
        self.frames = []

    def exchange_with_budget(self, packet, budget):
        wire = super().exchange_with_budget(packet, budget)
        self.frames.append({"request": packet.hex(), "wire": wire.hex()})
        return wire

    def send_terminal_extra(self):
        self._open()
        assert threading.get_ident() == self._thread
        self._socket.settimeout(2.0)
        self._socket.sendall(b"X")
        # EOF/reset records transport closure only; producer telemetry must
        # independently prove a protocol rejection and orderly process exit.
        try:
            assert self._socket.recv(1) == b"", "unexpected fourth response"
            return "eof"
        except ConnectionResetError:
            return "reset"


with tempfile.TemporaryDirectory(prefix="sh3rx-", dir="/tmp") as temporary:
    endpoint = str(Path(temporary) / "peer")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(endpoint)
    os.chmod(endpoint, 0o600)
    server.listen(1)
    server.settimeout(0.2)
    env = dict(
        os.environ, SH3_RUNTIME_ENDPOINT=endpoint, TMPDIR=temporary, XDG_RUNTIME_DIR=temporary
    )
    for key in ("DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "SH3_PEER_LIBRARY"):
        env.pop(key, None)
    process = subprocess.Popen(
        sys.argv[2:], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    print("RX_CHILD", process.pid, flush=True)
    logs = []

    def read_logs():
        for line in process.stdout:
            logs.append(line)
            print(line, end="", flush=True)

    logger = threading.Thread(target=read_logs)
    logger.start()
    channel = session = connection = None
    try:
        birth = reader.birth(process.pid)
        until = time.monotonic() + 70
        while connection is None:
            assert process.poll() is None, "child exited before connection"
            assert time.monotonic() < until, "connection deadline"
            try:
                connection, _ = server.accept()
            except TimeoutError:
                pass
        server.close()
        channel = RecordingChannel(connection, reader)
        connection = None
        peer = channel.peer()
        assert peer.pid == process.pid and peer.birth_ns == birth
        assert peer.euid == os.geteuid() and peer.ruid == os.getuid()
        session = PlatformDiagnosticSession(
            expectation,
            ExpectedPeer(process.pid, birth, os.geteuid()),
            channel,
            budget_clock=time.monotonic,
        )
        values, elapsed = [], []
        for _ in range(requested):
            started = time.monotonic()
            value = session.sample()
            elapsed.append(time.monotonic() - started)
            if value is None:
                break
            d = value.diagnostic
            assert d.pid == peer.pid == value.peer.pid
            assert d.birth_ns == peer.birth_ns == value.peer.birth_ns
            assert value.peer == peer
            values.append(
                dict(
                    sequence=d.request.sequence,
                    pid=d.pid,
                    birth_ns=d.birth_ns,
                    nonce=d.provider_nonce.hex(),
                    application=d.application_images,
                    platform=d.platform_images,
                    revision=d.loader_revision,
                    facts=[fact.value for fact in d.facts],
                    epochs=[d.epochs.host, d.epochs.pine, d.epochs.vu, d.epochs.gs],
                )
            )
        reached = session.accepted == requested
        reason_before_action = session.reason
        terminal = None
        if reached and mode == "extra":
            terminal = channel.send_terminal_extra()
        # Physical close intentionally differs from FC's successful SHUT_WR.
        session.close()
        assert session.closed and not session.close_failed and session.last is None
        assert session.sample() is None
        process.wait(timeout=40)
        logger.join(3)
        assert not logger.is_alive()
        ends = [line for line in logs if line.startswith("SH3_RT_END ")]
        assert len(ends) == 1
        producer = dict(item.split("=", 1) for item in ends[0].split()[1:])
        print(
            "RX_CONSUMER "
            + json.dumps(
                dict(
                    mode=mode,
                    requested=requested,
                    action_reached=reached,
                    reason_before_action=reason_before_action,
                    terminal_transport=terminal,
                    authenticated_peer=dict(
                        pid=peer.pid,
                        birth_ns=peer.birth_ns,
                        token_sha256=hashlib.sha256(peer.token).hexdigest(),
                    ),
                    accepted=session.accepted,
                    frames=channel.frames,
                    values=values,
                    elapsed_seconds=elapsed,
                    closed=session.closed,
                    close_failed=session.close_failed,
                    producer=producer,
                    child_exit=process.returncode,
                    admitted=False,
                ),
                sort_keys=True,
            ),
            flush=True,
        )
    finally:
        if session:
            session.close()
        elif channel:
            channel.close()
        if connection:
            connection.close()
        server.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        logger.join(3)
