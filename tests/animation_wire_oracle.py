"""SAN1 Python/native contract and double-precision independent pose comparison."""

import math
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pipeline.animation_inspection import encode_clip  # noqa: E402
from tools.qa.animation_pose_oracle import compose_pose, nlerp, rotation_translation  # noqa: E402


def verify(executable, path):
    data = path.read_bytes()
    values = struct.unpack("<3i4f9f288f", data[32:])
    parents = values[:3]
    translations = [values[7 + 3 * i : 10 + 3 * i] for i in range(3)]
    rotations = [values[16 + 4 * i : 20 + 4 * i] for i in range(72)]
    result = subprocess.run(
        [executable, str(path), "poses"], check=True, capture_output=True, text=True, timeout=15
    )
    errors = [0.0, 0.0]
    rows = result.stdout.splitlines()
    if len(rows) != len(range(0, 24 * 4096, 257)):
        raise AssertionError("Missing native poses")
    for line in rows:
        parts = line.split()
        counter, actual = int(parts[0]), list(map(float, parts[1:]))
        current, fraction = divmod(counter, 4096)
        local = [
            rotation_translation(
                nlerp(
                    rotations[current * 3 + i],
                    rotations[((current + 1) % 24) * 3 + i],
                    fraction / 4096,
                ),
                translations[i],
            )
            for i in range(3)
        ]
        expected = compose_pose(local, parents)
        if len(actual) != 48:
            raise AssertionError("Incomplete native pose")
        for i, value in enumerate(v for m in expected for v in m):
            group = int(i % 16 in (12, 13, 14))
            error = abs(actual[i] - value)
            errors[group] = max(errors[group], error)
            if not math.isfinite(actual[i]) or error > (1e-3 if group else 1e-5):
                raise AssertionError(f"Native pose differs at counter {counter}, element {i}")
    return {"poses": len(rows), "max_rotation_error": errors[0], "max_translation_error": errors[1]}


def main():
    # Optional private SAN1 path stays outside the repository and CI.
    if len(sys.argv) == 3:
        print(verify(sys.argv[1], Path(sys.argv[2])))
        return
    rotations = []
    for f in range(24):
        frame = []
        for bone in range(3):
            angle = (f + bone) * 0.05
            q = [0.0] * 4
            q[bone] = math.sin(angle)
            q[3] = math.cos(angle)
            frame.append([-v for v in q] if f % 2 else q)
        rotations.append(frame)
    data = encode_clip([-1, -1, 1], [(-2, 1, 0), (1, -2, 3), (2, 3, 1)], rotations)
    invalid = [data[:-1], data + b"x", data[:100], bytes(len(data))]
    # Header fields, parents, NaN/scale/translation and invalid quaternion with valid CRC.
    for offset, value in [
        (8, 4),
        (12, 25),
        (16, 0x144A),
        (20, 4914),
        (24, 1215),
        (32, 0),
        (44, 0x7FC00000),
        (56, 0),
        (60, 0x7F800000),
        (96, 0x40000000),
    ]:
        damaged = bytearray(data)
        struct.pack_into("<I", damaged, offset, value)
        struct.pack_into("<I", damaged, 28, zlib.crc32(damaged[32:]))
        invalid.append(damaged)
    damaged = bytearray(data)
    damaged[-1] ^= 1
    invalid.append(damaged)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "animation.san"
        for raw in invalid:
            path.write_bytes(raw)
            result = subprocess.run([sys.argv[1], str(path)], check=False, timeout=5)
            if result.returncode != 2:
                raise AssertionError("Corrupt SAN1 accepted")
        path.write_bytes(data)
        for failure in ("close-failure", "read-failure", "short-read"):
            result = subprocess.run([sys.argv[1], str(path), failure], check=False, timeout=5)
            if result.returncode != 2:
                raise AssertionError("I/O failure accepted")
        print(verify(sys.argv[1], path))


if __name__ == "__main__":
    main()
