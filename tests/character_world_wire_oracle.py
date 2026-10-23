"""Independent SCW1 wire contract: no production encoder imports."""

import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


def main():
    payload = struct.pack("<4f", 0, 0, 0, 0.001)
    for ident in (1, 2, 3):
        payload += struct.pack(
            "<I16f", ident, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, ident * 11, 0, 0, 1
        )
    payload += bytes(4)
    raw = struct.pack("<8s8I", b"S3CWv1\0\0", 1, 3, 1, 2, 3, 0, 224, zlib.crc32(payload)) + payload
    variants = [raw[:i] for i in (0, 7, 39, 55, 123, 263)] + [raw + b"x"]
    for offset, value in (
        (0, 0),
        (8, 2),
        (12, 4),
        (16, 9),
        (20, 9),
        (24, 9),
        (28, 98304),
        (32, 220),
        (36, 0),
        (52, 0),
        (56, 0),
        (124, 1),
        (260, 1),
    ):
        b = bytearray(raw)
        struct.pack_into("<I", b, offset, value)
        if offset >= 40:
            struct.pack_into("<I", b, 36, zlib.crc32(b[40:]))
        variants.append(bytes(b))
    for offset, value in (
        (40, float("nan")),
        (44, 1000001),
        (52, 1),
        (60, -1),
        (60, 2),
        (72, 1),
        (108, float("inf")),
    ):
        b = bytearray(raw)
        struct.pack_into("<f", b, offset, value)
        struct.pack_into("<I", b, 36, zlib.crc32(b[40:]))
        variants.append(bytes(b))
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "world.scw"
        p.write_bytes(raw)
        assert subprocess.run([sys.argv[1], str(p)], check=False).returncode == 0
        for failure in ("short", "read", "close"):
            assert subprocess.run([sys.argv[1], str(p), failure], check=False).returncode == 2
        for b in variants:
            p.write_bytes(b)
            assert subprocess.run([sys.argv[1], str(p)], check=False).returncode == 2
    print(f"SCW1: valid, {len(variants)} corruptions, 3 I/O failures passed")


if __name__ == "__main__":
    main()
