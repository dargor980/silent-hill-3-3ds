"""Private integration fixture, never a launcher for untrusted configuration."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(os.environ["SH3_REPO"])
sys.path.insert(0, str(ROOT))
from tools.inspectors.diagnostic_channel import NativePeerReader, UnixDiagnosticChannel
from tools.inspectors.diagnostic_session import ExpectedPeer, PlatformDiagnosticSession
from tools.inspectors.platform_diagnostic import DiagnosticExpectation, IdentityProfile
from tools.inspectors.process_diagnostic import Fact

case = os.environ["SH3_WORK_CONTROL"]
reader = NativePeerReader(Path(os.environ["SH3_PEER_LIBRARY"]))
expectation = DiagnosticExpectation(
    IdentityProfile.MACOS_PLATFORM_SLICES_V2,
    *[bytes.fromhex(os.environ[k]) for k in ("SH3_POLICY", "SH3_TRUE_MANIFEST_SHA256", "SH3_PLATFORM")],
)
events = {name: threading.Event() for name in ("work", "backpressure")}
logs, errors = [], []
with tempfile.TemporaryDirectory(prefix="sh3nr-", dir="/tmp") as temporary:
    endpoint = str(Path(temporary) / "peer")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(endpoint)
    os.chmod(endpoint, 0o600)
    server.listen(1)
    server.settimeout(15)
    env = {k: v for k, v in os.environ.items() if k != "SH3_PEER_LIBRARY"}
    env["SH3_ENDPOINT"] = endpoint
    env["DYLD_INSERT_LIBRARIES"] = env.pop("SH3_PROBE_LIBRARY")
    if env.get("SH3_LOADER_TRACE") == "1":
        env["DYLD_PRINT_LIBRARIES"] = "1"  # Local diagnostic control, child only.
    process = subprocess.Popen(sys.argv[1:], env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, bufsize=1)

    def read_logs():
        try:
            for line in process.stdout:
                logs.append(line)
                if line.startswith("NR_EVENT "):
                    row = dict(p.split("=", 1) for p in line.split()[1:])
                    events[row["phase"]].set()
        except BaseException as error:
            errors.append(repr(error))

    logger = threading.Thread(target=read_logs)
    logger.start()
    session = canceller = connection = None
    completed = False
    try:
        birth = reader.birth(process.pid)
        connection, _ = server.accept()
        server.close()

        class Socket:
            def __init__(self, value):
                self.value, self.sent, self.waited = value, 0, False

            def __getattr__(self, key):
                return getattr(self.value, key)

            def send(self, data):
                n = self.value.send(data[:5] if case == "fragmented" else data)
                self.sent += n
                if case == "disconnect_read" and self.sent == 32:
                    assert events["work"].wait(6), "work injection absent"
                    self.value.shutdown(socket.SHUT_RDWR)
                    self.value.close()
                    raise OSError("local disconnect control")
                return n

            def recv(self, size):
                if case == "backpressure_resume" and not self.waited:
                    self.waited = True
                    assert events["backpressure"].wait(5), "backpressure absent"
                    time.sleep(0.2)
                return self.value.recv(size)

        class Channel(UnixDiagnosticChannel):
            def __init__(self, *args):
                super().__init__(*args)
                self.frames = []

            def exchange_with_budget(self, packet, budget):
                raw = super().exchange_with_budget(packet, budget)
                self.frames.append(dict(request=packet.hex(), wire=raw.hex()))
                return raw

        channel = Channel(Socket(connection), reader)
        connection = None
        peer = ExpectedPeer(process.pid, birth, os.geteuid())
        if case == "wrong_consumer_peer":
            peer = ExpectedPeer(os.getpid(), reader.birth(os.getpid()), os.geteuid())
        session = PlatformDiagnosticSession(expectation, peer, channel, budget_clock=time.monotonic)
        if case == "consumer_cancel_read":
            def cancel():
                try:
                    assert events["work"].wait(6), "cancel target absent"
                    session.cancel()
                except BaseException as error:
                    errors.append(repr(error))
            canceller = threading.Thread(target=cancel)
            canceller.start()
        values, elapsed = [], []
        for _ in range(3):
            started = time.monotonic()
            value = session.sample()
            elapsed.append(time.monotonic() - started)
            if value is None:
                break
            diagnostic = value.diagnostic
            assert diagnostic.pid == process.pid == value.peer.pid
            assert diagnostic.birth_ns == birth == value.peer.birth_ns
            facts = [Fact.UNKNOWN] * 18
            for index in (0, 1, 2, 13, 15, 16):
                facts[index] = Fact.SATISFIED
            facts[11] = Fact.VIOLATED
            assert diagnostic.facts == tuple(facts)
            epochs = diagnostic.epochs
            assert (epochs.host, epochs.pine, epochs.vu, epochs.gs) == (11, 12, 13, 14)
            values.append(dict(sequence=diagnostic.request.sequence, pid=diagnostic.pid,
                birth_ns=diagnostic.birth_ns, nonce=diagnostic.provider_nonce.hex(),
                peer_token_sha256=hashlib.sha256(value.peer.token).hexdigest(),
                application=diagnostic.application_images, platform=diagnostic.platform_images,
                revision=diagnostic.loader_revision, facts=[f.value for f in diagnostic.facts],
                epochs=[11, 12, 13, 14]))
        session.close()
        assert session.closed and not session.close_failed and session.last is None and session.sample() is None
        process.wait(timeout=10)
        logger.join(3)
        assert not logger.is_alive() and process.returncode == 0
        if canceller:
            canceller.join(3)
            assert not canceller.is_alive()
        assert not errors, errors
        raw = "".join(logs)
        assert "NR_FAIL" not in raw, raw
        print(raw, end="")
        print("NR_CONSUMER " + json.dumps(dict(case=case, accepted=session.accepted,
            reason=session.reason, closed=session.closed, close_failed=session.close_failed,
            elapsed_seconds=elapsed, values=values, frames=channel.frames,
            child_exit=process.returncode, events={k: e.is_set() for k, e in events.items()},
            admitted=False), sort_keys=True))
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
        if canceller:
            canceller.join(3)
        if not completed:
            print("NR_CHILD_EXIT", process.returncode)
            print("".join(logs), end="")
