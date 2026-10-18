"""Compare an unchanged provider program with its unchanged FATE reference."""

import subprocess
import sys
from pathlib import Path

result = subprocess.run([sys.argv[1]], capture_output=True, timeout=20, check=False)
sys.stderr.buffer.write(result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
expected = Path(sys.argv[2]).read_bytes()
if result.stdout != expected:
    sys.stderr.write(f"FATE mismatch: actual {len(result.stdout)} / expected {len(expected)} bytes\n")
    sys.stdout.buffer.write(result.stdout)
    raise SystemExit(1)
print(f"PASS unchanged FATE reference: {len(expected)} bytes")
