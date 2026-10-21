"""Independent SCM1 wire encoder, rejection tests and C++ numerical comparison."""

import math
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pipeline.animation_inspection import encode_clip  # noqa: E402
from tools.qa.character_skinning_oracle import deform_vertex, matrix_product  # noqa: E402


def main():
    executable = sys.argv[1]
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    helpers = [identity[:], identity[:], identity[:]]
    helpers[0][12:15] = [2, -1, 3]
    helpers[1] = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, -2, 1, 0, 1]
    targets = [1, 2, 2]
    positions = [[16, 32, -48], [-32, 16, 64], [48, -32, 16]]
    weights = [[4096], [2048, 2047], [2048, 1023, 1023]]
    normals = [[4096, 2048, -1024], [2048, -2048, 4096], [-4096, 0, 2048]]
    ids = [[], [0], [0, 1]]
    payload = bytearray(
        struct.pack("<4f3I48f", 0, 0, 0, 0.03, *targets, *(v for m in helpers for v in m))
    )
    for p, n, w, h in zip(positions, normals, weights, ids, strict=True):
        payload += struct.pack(
            "<8h3H4BH",
            *p,
            *n,
            0,
            0,
            *(w + [0] * (3 - len(w))),
            0,
            len(w),
            *(h + [255] * (2 - len(h))),
            0,
        )
    payload += struct.pack("<3H", 0, 1, 2)

    def wrap(p):
        return struct.pack("<8s6I", b"S3CMv1\0\0", 3, 3, 3, 28, len(p), zlib.crc32(p)) + p

    good = wrap(payload)
    bad = [b"", good[:-1], good + b"X", b"XXXXXXXX" + good[8:]]
    for offset, value in [(8, 2049), (12, 4609), (16, 4), (20, 27), (24, 0), (28, 0)]:
        raw = bytearray(good)
        struct.pack_into("<I", raw, offset, value)
        bad.append(bytes(raw))
    for offset, fmt, value in [
        (12, "f", 0),
        (0, "f", float("nan")),
        (16, "I", 3),
        (28 + 12, "f", 1),
        (220 + 22, "B", 3),
        (220 + 23, "B", 4),
        (220 + 16, "H", 4097),
        (220 + 18, "H", 1),
        (220 + 24, "B", 0),
        (220 + 26, "H", 1),
        (len(payload) - 2, "H", 3),
    ]:
        p = bytearray(payload)
        struct.pack_into("<" + fmt, p, offset, value)
        bad.append(wrap(p))
    with tempfile.TemporaryDirectory() as temp:
        model, clip = Path(temp) / "mesh.scm", Path(temp) / "clip.san"
        model.write_bytes(good)

        def run(extra=()):
            return subprocess.run([executable, str(model), *extra], capture_output=True, text=True)

        assert run().returncode == 0
        for mode in ("read-failure", "short-read", "close-failure"):
            assert run([mode]).returncode == 2, mode
        for i, raw in enumerate(bad):
            model.write_bytes(raw)
            r = run()
            assert r.returncode == 2, (i, r.stderr)
        model.write_bytes(good)
        translations = [[1, 2, 0], [0, -1, 2], [0, 2, 1]]
        q = [0, 0, math.sqrt(0.5), math.sqrt(0.5)]
        clip.write_bytes(
            encode_clip([-1, -1, 1], translations, [[[0, 0, 0, 1], q, [0, 0, 0, 1]]] * 24)
        )
        p0 = identity[:]
        p0[12:15] = translations[0]
        p1 = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, *translations[1], 1]
        child = identity[:]
        child[12:15] = translations[2]
        bones = [p0, p1, matrix_product(p1, child)]
        auxiliary = [matrix_product(bones[t], h) for t, h in zip(targets, helpers, strict=True)]
        for counter in (0, 2048, 98303, 98304):
            r = run([str(clip), str(counter)])
            assert r.returncode == 0, r.stderr
            actual = [[float(v) for v in line.split()] for line in r.stdout.splitlines()]
            assert len(actual) == 3
            for i in range(3):
                expected = deform_vertex(
                    positions[i],
                    normals[i],
                    weights[i],
                    [bones[0]] + [auxiliary[h] for h in ids[i]],
                )
                assert (
                    max(
                        abs(a - b)
                        for a, b in zip(actual[i], expected.position + expected.normal, strict=True)
                    )
                    < 1e-5
                )
    print(f"SCM1 wire: valid, {len(bad)} corruptions, 3 I/O failures, 12 oracle vertices PASS")


if __name__ == "__main__":
    main()
