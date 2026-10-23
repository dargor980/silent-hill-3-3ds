"""Independent SCL1 framing, corruption and stdio failure checks."""

import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pipeline.animation_inspection import encode_clip  # noqa: E402
from tools.qa.character_lighting_oracle import (  # noqa: E402
    DirectionalLight,
    Spotlight16,
    light_vertex,
    quantize_gs_color,
)


def numerical(executable, root, identity):
    """Independent wire writer and double precision oracle; no game assets."""
    model, clip, lights = (root / n for n in ("mesh.scm", "clip.san", "numeric.scl"))
    body = bytearray(struct.pack("<4f3I48f", 0, 0, 0, 0.03, 0, 1, 2, *(identity * 3)))
    for i in range(45):
        body += struct.pack(
            "<8h3H4BH",
            i * 8 - 128,
            32,
            64,
            (i % 5 - 2) * 2048,
            1024,
            4096,
            0,
            0,
            2048,
            2047,
            0,
            0,
            2,
            0,
            255,
            0,
        )
    body += struct.pack("<45H", *range(45))
    scm = zlib.crc32(body)
    model.write_bytes(struct.pack("<8s6I", b"S3CMv1\0\0", 45, 45, 3, 28, len(body), scm) + body)
    san_bytes = encode_clip(
        [-1, -1, 1], [[0, 0, 0], [0, 0, 0], [0, 1, 0]], [[[0, 0, 0, 1]] * 3] * 24
    )
    clip.write_bytes(san_bytes)
    transform = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 2, -3, 4, 1]
    ambient = [0.125, 0.25, 0.375, 120]
    directionals = [
        DirectionalLight((1, 2, -1), (1, 2, 3, 4)),
        DirectionalLight((-2, 0.5, 1), (3, 1, 2, 0.5)),
        DirectionalLight((0, 0, 0), (0, 0, 0, 0)),
    ]
    spot = Spotlight16((-1, -2, -3), (0.25, 0.5, 1), (10, 12, 14, 2), (10, -0.25, 0.5, 0.25))
    values = transform + ambient
    for d in directionals:
        values += list(d.direction) + list(d.color)
    values += list(spot.position + spot.direction + spot.color + spot.attenuation)
    materials = [([2 + i, 3 + i, 4 + i], [5 + i, 6 + i, 7 + i]) for i in range(15)]
    body = struct.pack("<I55f", 0, *values) + b"".join(
        struct.pack("<4I6f", i * 3, 3, i * 3, 3, *diffuse, *amb)
        for i, (diffuse, amb) in enumerate(materials)
    )
    lights.write_bytes(
        struct.pack(
            "<8s10I",
            b"S3CLv1\0\0",
            1,
            15,
            3,
            scm,
            zlib.crc32(san_bytes[32:]),
            3,
            45,
            45,
            len(body),
            zlib.crc32(body),
        )
        + body
    )

    def expected(i, p, n):
        position = [sum(transform[c * 4 + r] * p[c] for c in range(4)) for r in range(3)]
        normal = [sum(transform[c * 4 + r] * n[c] for c in range(3)) for r in range(3)]
        return light_vertex(position, normal, *materials[i], ambient, directionals, spot)

    prefix = [executable, "--asset", str(model), str(clip), str(lights), "3"]
    result = subprocess.run([*prefix, "2048"], capture_output=True, text=True, check=True)
    rows = [[float(x) for x in line.split()] for line in result.stdout.splitlines()]
    assert len(rows) == 45
    for i, row in enumerate(rows):
        reference = expected(i // 3, row[:4], row[4:7])
        assert max(abs(a - b) for a, b in zip(row[7:11], reference, strict=True)) < 0.002
        assert row[11:] == [x / 128 for x in quantize_gs_color(reference, (128, 128, 128, 255))[:3]]
    # Asymmetric normals, fractional W, positive/negative Lambert, clipping and zero normal.
    vectors = [
        (
            i % 15,
            [i / 8 - 16, (i % 7) - 3, 2, 0.5 if i % 2 else 1],
            [(i % 5) - 2, (i % 3) - 1, (i % 7) / 2 - 1.5],
        )
        for i in range(120)
    ]
    raw = "".join(" ".join(str(x) for x in [i, *p, *n]) + "\n" for i, p, n in vectors)
    result = subprocess.run(
        [*prefix, "stdin"], input=raw, capture_output=True, text=True, check=True
    )
    rows = [[float(x) for x in line.split()] for line in result.stdout.splitlines()]
    assert len(rows) == len(vectors)
    for row, (i, p, n) in zip(rows, vectors, strict=True):
        assert max(abs(a - b) for a, b in zip(row, expected(i, p, n), strict=True)) < 0.002


def main():
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    values = (
        identity
        + [0.1, 0.2, 0.3, 120]
        + [0] * 21
        + [0, 0, 0, 0, 0, 1, 10, 12, 14, 2, 1, 0, 0.25, 0.25]
    )
    body = struct.pack("<I55f", 0, *values) + b"".join(
        struct.pack("<4I6f", i * 3, 3, i * 3, 3, 2, 3, 4, 5, 6, 7) for i in range(15)
    )

    def wrap(b):
        return (
            struct.pack("<8s10I", b"S3CLv1\0\0", 1, 15, 3, 1, 2, 3, 45, 45, len(b), zlib.crc32(b))
            + b
        )

    good = wrap(body)
    bad = [b"", good[:-1], good + b"X", b"BADMAGIC" + good[8:]]
    for offset in range(8, 48, 4):
        b = bytearray(good)
        struct.pack_into("<I", b, offset, 0xFFFFFFFF)
        bad.append(b)
    for offset, fmt, value in [
        (0, "I", 98304),
        (4, "f", 2),
        (16, "f", 1),
        (4, "f", -1),
        (68, "f", float("nan")),
        (68, "f", 17),
        (104, "f", -1),
        (168, "f", float("inf")),
        (220, "f", 1000001),
        (224, "I", 3),
        (228, "I", 0xFFFFFFFF),
        (236, "I", 4),
        (240, "f", 129),
        (264, "I", 0),
        (824 - 4, "f", -1),
    ]:
        b = bytearray(body)
        struct.pack_into("<" + fmt, b, offset, value)
        bad.append(wrap(b))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "lighting.scl"

        def run(extra=()):
            return subprocess.run([sys.argv[1], str(path), *extra], capture_output=True)

        path.write_bytes(good)
        assert run().returncode == 0
        for mode in ("read", "short", "close"):
            assert run([mode]).returncode == 2, mode
        for i, raw in enumerate(bad):
            path.write_bytes(raw)
            r = run()
            assert r.returncode == 2, (i, r.stderr)
        numerical(sys.argv[1], Path(tmp), identity)
    print(f"SCL1: valid, {len(bad)} corruptions, 3 I/O failures, 165 oracle vertices PASS")


if __name__ == "__main__":
    main()
