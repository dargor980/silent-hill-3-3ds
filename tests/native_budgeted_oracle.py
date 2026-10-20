"""BC08: native macOS peers with synthetic PD bodies in real child processes.

Standard library only. This is not the PCSX2 worker or an inventory attestation.
"""

import hashlib
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.inspectors.diagnostic_channel import NativePeerReader, UnixDiagnosticChannel  # noqa: E402
from tools.inspectors.diagnostic_session import ExpectedPeer, PlatformDiagnosticSession  # noqa: E402
from tools.inspectors.platform_diagnostic import DiagnosticExpectation, IdentityProfile  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VECTOR = bytes.fromhex((ROOT / "tests/fixtures/platform-diagnostic-v2/observed.hex").read_text())


def child(library, endpoint, case):
    reader = NativePeerReader(library)
    body = bytearray(VECTOR)
    struct.pack_into("<IQ", body, 40, os.getpid(), reader.birth(os.getpid()))
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(endpoint)
        for sample in range(3):
            request = bytearray()
            while len(request) < 32:
                part = connection.recv(32 - len(request))
                if not part:
                    return
                request.extend(part)
            assert request[:8] == b"SH3PDQ02"
            if case == "cancel" or (case == "deadline" and sample == 1):
                assert connection.recv(1) == b""
                return
            if case == "disconnect":
                return
            body[16:40] = request[8:32]
            if case == "nonce" and sample == 1:
                body[52] ^= 1
            if case == "truncated":
                connection.sendall(body[:17])
                return
            if case == "fragmented":
                for i in range(0, len(body), 3):
                    connection.sendall(body[i : i + 3])
            else:
                connection.sendall(body)
        assert connection.recv(1) == b""


def main(library):
    reader = NativePeerReader(library)
    expected = DiagnosticExpectation(
        IdentityProfile.MACOS_PLATFORM_SLICES_V2,
        bytes([3]) * 32,
        bytes([4]) * 32,
        bytes([5]) * 32,
    )
    results = []
    for case in [
        "positive",
        "fragmented",
        "truncated",
        "cancel",
        "deadline",
        "nonce",
        "wrong_peer",
        "disconnect",
    ]:
        with tempfile.TemporaryDirectory(prefix="sh3bc-", dir="/tmp") as temporary:
            endpoint = str(Path(temporary) / "peer")
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(endpoint)
            server.listen(1)
            server.settimeout(10)
            process = subprocess.Popen(
                [sys.executable, __file__, "--child", str(library), endpoint, case],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            session = None
            canceller = None
            ready, finished = threading.Event(), threading.Event()
            cancellation_errors = []
            try:
                birth = reader.birth(process.pid)
                connection, _ = server.accept()
                server.close()

                class Channel(UnixDiagnosticChannel):
                    def exchange_with_budget(self, packet, budget, ready=ready):
                        ready.set()
                        return super().exchange_with_budget(packet, budget)

                channel = Channel(connection, reader)
                peer = ExpectedPeer(process.pid, birth, os.geteuid())
                if case == "wrong_peer":
                    peer = ExpectedPeer(os.getpid(), reader.birth(os.getpid()), os.geteuid())
                session = PlatformDiagnosticSession(
                    expected, peer, channel, budget_clock=time.monotonic
                )
                if case == "cancel":

                    def cancel(
                        ready=ready, session=session, errors=cancellation_errors, finished=finished
                    ):
                        try:
                            assert ready.wait(3)
                            session.cancel()
                        except BaseException as error:
                            errors.append(type(error).__name__)
                        finally:
                            finished.set()

                    canceller = threading.Thread(target=cancel)
                    canceller.start()
                elapsed, values = [], []
                for _ in range(3):
                    start = time.monotonic()
                    value = session.sample()
                    elapsed.append(time.monotonic() - start)
                    if value is None:
                        break
                    assert value.peer.pid == value.diagnostic.pid == process.pid
                    assert value.peer.birth_ns == value.diagnostic.birth_ns == birth
                    values.append(
                        dict(
                            sequence=value.diagnostic.request.sequence,
                            peer_token_sha256=hashlib.sha256(value.peer.token).hexdigest(),
                        )
                    )
                session.close()
                assert session.closed and not session.close_failed and session.last is None
                assert session.sample() is None
                expected_count = (
                    3
                    if case in ("positive", "fragmented")
                    else 1
                    if case in ("deadline", "nonce")
                    else 0
                )
                expected_reason = {
                    "positive": "closed",
                    "fragmented": "closed",
                    "truncated": "channel_unavailable",
                    "cancel": "cancelled",
                    "deadline": "deadline",
                    "nonce": "identity_changed",
                    "wrong_peer": "peer_mismatch",
                    "disconnect": "channel_unavailable",
                }[case]
                assert session.accepted == len(values) == expected_count, case
                assert session.reason == expected_reason, (case, session.reason)
                if case == "deadline":
                    assert 2 <= elapsed[-1] < 10
                if values:
                    assert len({v["peer_token_sha256"] for v in values}) == 1
                stdout, stderr = process.communicate(timeout=10)
                assert process.returncode == 0 and not stdout and not stderr, (case, stderr)
                if canceller:
                    canceller.join(3)
                    assert (
                        not canceller.is_alive() and finished.is_set() and not cancellation_errors
                    )
                results.append(
                    dict(
                        case=case,
                        accepted=expected_count,
                        reason=session.reason,
                        elapsed_seconds=elapsed,
                        values=values,
                        closed=True,
                        child_exit=0,
                    )
                )
            finally:
                ready.set()
                if canceller:
                    canceller.join(3)
                if session:
                    session.close()
                server.close()
                if process.poll() is None:
                    process.terminate()
                    process.communicate(timeout=5)
    print(
        json.dumps(
            dict(
                native_budgeted_consumer="passed",
                architecture=os.uname().machine,
                synthetic_payload=True,
                pcsx2_executed=False,
                cases=results,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    if sys.argv[1] == "--child":
        child(Path(sys.argv[2]).resolve(), sys.argv[3], sys.argv[4])
    else:
        main(Path(sys.argv[1]).resolve())
