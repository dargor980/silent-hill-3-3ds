"""Own small APNGs and explicit RGBA oracles; no Qt/libpng dependency."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
R, G, B = [255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255]
T, W = [0, 0, 0, 0], [255, 255, 255, 128]


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def header(width, height):
    return SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))


def pixels(width, height, colors):
    assert len(colors) == width * height
    return zlib.compress(b"".join(b"\0" + bytes(c for rgba in colors[y*width:(y+1)*width] for c in rgba)
                                   for y in range(height)), 9)


def animation(width, height, frames, plays, hidden=None):
    data = header(width, height) + chunk(b"acTL", struct.pack(">II", len(frames), plays))
    if hidden is not None:
        data += chunk(b"IDAT", pixels(width, height, hidden))
    sequence = 0
    for index, frame in enumerate(frames):
        w, h, x, y, num, den, disposal, blend, colors = frame
        data += chunk(b"fcTL", struct.pack(">IIIIIHHBB", sequence, w, h, x, y, num, den, disposal, blend))
        sequence += 1
        compressed = pixels(w, h, colors)
        if index == 0 and hidden is None:
            data += chunk(b"IDAT", compressed)
        else:
            data += chunk(b"fdAT", struct.pack(">I", sequence) + compressed)
            sequence += 1
    return data + chunk(b"IEND", b"")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    output = parser.parse_args().output
    output.mkdir(exist_ok=False)
    cases = {}

    def add(name, data, width, height, images, delays, plays, animated=True):
        (output / name).write_bytes(data)
        cases[name] = dict(width=width, height=height, images=images, delays=delays,
                           loops=(-1 if plays == 0 else plays - 1) if animated else 0,
                           plays=plays, animated=animated, sha256=hashlib.sha256(data).hexdigest())

    # Explicit expected canvases: PREVIOUS restores red; BACKGROUND clears one pixel.
    frames = [
        (3, 2, 0, 0, 1, 100, 0, 0, [R]*6),
        (1, 1, 0, 0, 2, 100, 2, 1, [[0, 0, 255, 128]]),
        (1, 1, 1, 0, 3, 100, 1, 0, [G]),
        (1, 1, 2, 1, 4, 100, 0, 0, [W]),
        (2, 1, 0, 0, 5, 100, 0, 1, [[0, 0, 255, 0], [0, 255, 255, 64]]),
    ]
    images = [[R]*6, [[127, 0, 128, 255], R, R, R, R, R], [R, G, R, R, R, R],
              [R, T, R, R, R, W], [R, [0, 255, 255, 64], R, R, R, W]]
    timeline = animation(3, 2, frames, 0)
    add("composition.apng", timeline, 3, 2, images, [10, 20, 30, 40, 50], 0)
    simple = [(1, 1, 0, 0, 1, 100, 0, 0, [R]), (1, 1, 0, 0, 2, 100, 0, 0, [G])]
    for plays in [1, 2]:
        add(f"plays-{plays}.apng", animation(1, 1, simple, plays), 1, 1, [[R], [G]], [10, 20], plays)
    zero_den = [(1, 1, 0, 0, 3, 0, 0, 0, [R]), (1, 1, 0, 0, 5, 100, 0, 0, [G])]
    add("zero-den.apng", animation(1, 1, zero_den, 0), 1, 1, [[R], [G]], [30, 50], 0)
    hidden = [(2, 1, 0, 0, 1, 100, 0, 0, [R, R]), (1, 1, 1, 0, 2, 100, 0, 0, [G])]
    add("hidden.apng", animation(2, 1, hidden, 0, hidden=[B, B]), 2, 1, [[R, R], [R, G]], [10, 20], 0)
    static = header(2, 1) + chunk(b"IDAT", pixels(2, 1, [G, W])) + chunk(b"IEND", b"")
    add("static.png", static, 2, 1, [[G, W]], [0], 1, False)
    # Truncate inside the first IDAT, before a complete compressed frame can exist.
    offset = timeline.index(b"IDAT")
    (output / "truncated.apng").write_bytes(timeline[:offset + 6])
    (output / "invalid.apng").write_bytes(b"Own deliberately invalid APNG content")
    (output / "empty.apng").write_bytes(b"")
    (output / "short.apng").write_bytes(SIGNATURE[:7])
    (output / "oracle.json").write_text(json.dumps(cases, indent=2) + "\n")
    print(json.dumps({"valid_cases": len(cases), "frames": sum(len(c["images"]) for c in cases.values()),
                      "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}}))


if __name__ == "__main__":
    main()
