"""Cross-language OB wire oracle; all bytes are synthetic."""

import struct
import subprocess
import sys

packet = bytes.fromhex(subprocess.check_output([sys.argv[1], "--emit"], text=True))
session = bytes([1]) + bytes(15)
header = struct.pack(
    "<4sBBH16s8I", b"SH3O", 1, 0, 0, session, 1, 0x100000, 0x1FF0, 32, 0xFF0, 32, 0xFF0, 1
)
snapshot = struct.pack(
    "<QIQQQIIII",
    42,
    0x100000,
    0x10000004D,
    0x10000000,
    0x20000000,
    32 * 1024 * 1024,
    1,
    0x44556677,
    2,
)
snapshot += struct.pack("<IIQIIQI", 1, 0, 0x0FFFF000, 2, 0, 0x0FFFF000, 0)
expected = header + snapshot * 2 + bytes(((0xFF0 + i) ^ 0x5A) & 255 for i in range(32))
if packet != expected:
    raise SystemExit("OBSERVER_WIRE_ORACLE_MISMATCH")
print("observer: exact Python struct oracle passed")
