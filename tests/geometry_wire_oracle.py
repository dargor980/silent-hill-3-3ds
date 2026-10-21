"""Python SGM encoder consumed by native reader, including semantic corruption."""

import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pipeline.geometry_inspection import encode_sgm  # noqa: E402

encoded = encode_sgm(
    [(-1, -1, -2, 0, 0, 1, 0, 0), (1, -1, -2, 1, 0, 0, 1, 0), (0, 1, -2, 0, 1, 0, 0, 1)]
)
nan = bytearray(encoded)
struct.pack_into("<f", nan, 24, float("nan"))
struct.pack_into("<I", nan, 20, zlib.crc32(nan[24:]))
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "geometry.sgm"
    for data, valid in (
        (encoded, True),
        (encoded[:-1], False),
        (encoded + b"x", False),
        (encoded[:24] + bytes(96), False),
        (nan, False),
    ):
        path.write_bytes(data)
        result = subprocess.run([sys.argv[1], str(path)], check=False, timeout=5)
        if (result.returncode == 0) != valid:
            raise SystemExit("SGM Python/C++ contract mismatch")
