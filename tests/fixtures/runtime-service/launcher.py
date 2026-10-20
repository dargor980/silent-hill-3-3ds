"""Private launcher for one linked candidate; configuration is fixed before exec."""

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

reader = NativePeerReader(Path(os.environ["SH3_PEER_LIBRARY"]))
expectation = DiagnosticExpectation(
    IdentityProfile.MACOS_PLATFORM_SLICES_V2,
    *[
        bytes.fromhex(os.environ[key])
        for key in ("SH3_RUNTIME_POLICY", "SH3_RUNTIME_MANIFEST_SHA256", "SH3_RUNTIME_PLATFORM")
    ],
)
logs = []
with tempfile.TemporaryDirectory(prefix="sh3rt-live-", dir="/tmp") as temporary:
    endpoint = str(Path(temporary) / "peer")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(endpoint)
    os.chmod(endpoint, 0o600)
    server.listen(1)
    server.settimeout(0.2)
    # PINE reads TMPDIR on macOS; use this short, private path for the child.
    env = dict(
        os.environ, SH3_RUNTIME_ENDPOINT=endpoint, TMPDIR=temporary, XDG_RUNTIME_DIR=temporary
    )
    for key in ("DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "SH3_PEER_LIBRARY"):
        env.pop(key, None)
    process = subprocess.Popen(
        sys.argv[1:], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    print("RT_CHILD", process.pid, flush=True)

    def read_logs():
        for line in process.stdout:
            logs.append(line)
            print(line, end="", flush=True)

    logger = threading.Thread(target=read_logs)
    logger.start()
    session = connection = None
    completed = False
    try:
        birth = reader.birth(process.pid)
        until = time.monotonic() + 70
        while connection is None:
            assert process.poll() is None, ("child exited before connection", process.returncode)
            assert time.monotonic() < until, "connection deadline"
            try:
                connection, _ = server.accept()
            except TimeoutError:
                pass
        server.close()
        pine_sockets = sorted(p.name for p in Path(temporary).glob("pcsx2.sock*") if p.is_socket())

        class Channel(UnixDiagnosticChannel):
            def __init__(self, *args):
                super().__init__(*args)
                self.frames = []

            def exchange_with_budget(self, packet, budget):
                raw = super().exchange_with_budget(packet, budget)
                self.frames.append({"request": packet.hex(), "wire": raw.hex()})
                return raw

            def release_after_last_frame(self):
                # All three frames have already passed the unchanged session
                # validator. Keep this endpoint alive while the producer proves
                # our identity and observes EOF from SHUT_WR, then await its EOF.
                assert len(self.frames) == 3
                self._open()
                assert threading.get_ident() == self._thread
                self._socket.shutdown(socket.SHUT_WR)
                self._socket.settimeout(2.0)
                assert self._socket.recv(1) == b"", "extra data during terminal release"

        channel = Channel(connection, reader)
        connection = None
        session = PlatformDiagnosticSession(
            expectation,
            ExpectedPeer(process.pid, birth, os.geteuid()),
            channel,
            budget_clock=time.monotonic,
        )
        values, elapsed = [], []
        for _ in range(3):
            started = time.monotonic()
            value = session.sample()
            elapsed.append(time.monotonic() - started)
            if value is None:
                break
            d = value.diagnostic
            assert d.pid == process.pid == value.peer.pid
            assert d.birth_ns == birth == value.peer.birth_ns
            epochs = [d.epochs.host, d.epochs.pine, d.epochs.vu, d.epochs.gs]
            assert all(epochs)
            values.append(
                {
                    "sequence": d.request.sequence,
                    "pid": d.pid,
                    "birth_ns": d.birth_ns,
                    "nonce": d.provider_nonce.hex(),
                    "peer_token_sha256": hashlib.sha256(value.peer.token).hexdigest(),
                    "application": d.application_images,
                    "platform": d.platform_images,
                    "revision": d.loader_revision,
                    "facts": [fact.value for fact in d.facts],
                    "epochs": epochs,
                }
            )
        if session.accepted == 3:
            channel.release_after_last_frame()
        session.close()
        assert session.closed and not session.close_failed and session.last is None
        assert session.sample() is None
        process.wait(timeout=40)
        logger.join(3)
        assert not logger.is_alive() and process.returncode == 0
        raw = "".join(logs)
        end = [line for line in raw.splitlines() if line.startswith("SH3_RT_END ")]
        assert len(end) == 1, raw
        fields = dict(item.split("=", 1) for item in end[0].split()[1:])
        assert fields["clean"] == "1" and fields["admitted"] == "0"

        print(
            "RT_CONSUMER "
            + json.dumps(
                {
                    "accepted": session.accepted,
                    "reason": session.reason,
                    "closed": session.closed,
                    "close_failed": session.close_failed,
                    "elapsed_seconds": elapsed,
                    "values": values,
                    "frames": channel.frames,
                    "child_exit": process.returncode,
                    "pine_sockets": pine_sockets,
                    "producer": fields,
                    "admitted": False,
                },
                sort_keys=True,
            )
        )
        completed = True
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
        if not completed:
            print("RT_CHILD_EXIT", process.returncode)
