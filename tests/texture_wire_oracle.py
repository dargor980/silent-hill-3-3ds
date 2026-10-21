"""Cross-language STX1 contract: Python encoding consumed by the actual C++ reader."""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pipeline.texture_inspection import encode_stx  # noqa: E402

rgba = bytes(c for y in range(256) for x in range(256) for c in (x, y, x ^ y, 255))
encoded = encode_stx(rgba)
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "texture.stx"
    for data, valid in (
        (encoded, True),
        (encoded[:-1], False),
        (encoded[:24] + bytes(262144), False),
        (encoded + b"x", False),
    ):
        path.write_bytes(data)
        result = subprocess.run([sys.argv[1], str(path)], check=False, timeout=5)
        if (result.returncode == 0) != valid:
            raise SystemExit("STX Python/C++ contract mismatch")
