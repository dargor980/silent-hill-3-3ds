"""PS09: standalone Python/macOS bridge oracle; standard library only."""

import json
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.inspectors.diagnostic_channel import NativePeerReader  # noqa: E402
from tools.inspectors.diagnostic_session import PeerUnavailable  # noqa: E402


def rejected(action):
    try:
        action()
    except PeerUnavailable:
        return
    raise AssertionError("native peer accepted invalid input")


def main(library):
    reader = NativePeerReader(Path(library).resolve())
    birth = reader.birth(os.getpid())
    a, b = socket.socketpair()
    try:
        peer = reader.read(a.fileno())
        assert (peer.pid, peer.euid, peer.ruid, peer.birth_ns) == (
            os.getpid(),
            os.geteuid(),
            os.getuid(),
            birth,
        )
        assert peer == reader.read(a.fileno()) and len(peer.token) == 32
        for fd in (-1, True, "0", 1 << 32):
            rejected(lambda fd=fd: reader.read(fd))
        for pid in (0, -1, True, "1", 1 << 32, 0x7FFFFFFF):
            rejected(lambda pid=pid: reader.birth(pid))
        b.close()
        rejected(lambda: reader.read(a.fileno()))
        a.close()
        rejected(lambda: reader.read(a.fileno()))
    finally:
        a.close()
        b.close()
    print(
        json.dumps(
            {
                "native_python_bridge": "passed",
                "negative_inputs": 12,
                "architecture": os.uname().machine,
            }
        )
    )


if __name__ == "__main__":
    main(sys.argv[1])
