"""Small deterministic RGBA8 PNG encoder for bounded inspection previews."""

import struct
import zlib


def encode_rgba_png(width: int, height: int, rgba: bytes) -> bytes:
    if (
        type(width) is not int
        or type(height) is not int
        or not 1 <= width <= 1024
        or not 1 <= height <= 1024
        or type(rgba) is not bytes
        or len(rgba) != width * height * 4
    ):
        raise ValueError("PNG_INPUT")

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    stride = width * 4
    rows = b"".join(b"\0" + rgba[y * stride : (y + 1) * stride] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )
