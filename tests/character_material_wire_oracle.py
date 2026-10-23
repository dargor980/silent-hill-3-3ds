"""Independent SCT1 wire writer exercising the real C++ reader."""

import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


def main():
    payload = struct.pack("<9I", 0, 3, 0, 3, 3, 1, 6, 3, 2) + bytes([13, 29, 47, 128]) * (
        3 * 512**2
    )

    def wrap(p):
        return struct.pack("<8s6I", b"S3CTv1\0\0", 3, 512, 3, 0x12345678, len(p), zlib.crc32(p)) + p

    good = wrap(payload)
    bad = [b"", good[:20], good[:60], good[:-1], good + b"X", b"XXXXXXXX" + good[8:]]
    for offset, value in ((8, 4), (12, 256), (16, 2), (20, 0), (24, 0), (28, 0)):
        raw = bytearray(good)
        struct.pack_into("<I", raw, offset, value)
        bad.append(raw)
    for offset, value in (
        (0, 1),
        (4, 0),
        (4, 4),
        (4, 0xFFFFFFFF),
        (8, 2),
        (12, 0),
        (28, 6),
        (32, 0),
    ):
        raw = bytearray(payload)
        struct.pack_into("<I", raw, offset, value)
        bad.append(wrap(raw))
    raw = bytearray(payload)
    raw[-1] = 129
    bad.append(wrap(raw))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "character.sct"

        def run(extra=()):
            return subprocess.run([sys.argv[1], str(path), *extra], capture_output=True)

        path.write_bytes(good)
        assert run().returncode == 0
        for mode in ("read", "close"):
            assert run([mode]).returncode == 2
        for i, raw in enumerate(bad):
            path.write_bytes(raw)
            result = run()
            assert result.returncode == 2, (i, result.stderr)
    print(f"SCT1 wire: valid, {len(bad)} corruptions and I/O failures PASS")


if __name__ == "__main__":
    main()
