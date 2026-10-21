"""STX1 encoder and deterministic SD archive; no proprietary inputs or paths."""

import struct
import zlib

from tools.pipeline.inspection_archive import inspection_archive

WIDTH = 256
PIXEL_BYTES = WIDTH * WIDTH * 4
MAGIC = b"S3TXv1\0\0"


def encode_stx(rgba: bytes) -> bytes:
    """Input is already normalized RGBA8, top-down. Do not normalize twice."""
    if type(rgba) is not bytes or len(rgba) != PIXEL_BYTES:
        raise ValueError("STX1 requires exactly 256x256 RGBA8")
    return struct.pack("<8sHHIII", MAGIC, WIDTH, WIDTH, 1, len(rgba), zlib.crc32(rgba)) + rgba


def normalize_ps2_alpha(rgba: bytes) -> bytes:
    if type(rgba) is not bytes or len(rgba) != PIXEL_BYTES:
        raise ValueError("Expected 256x256 PS2 RGBA")
    output = bytearray(rgba)
    output[3::4] = bytes(min(255, 2 * value) for value in rgba[3::4])
    return bytes(output)


def sd_archive(files: dict[str, bytes]) -> bytes:
    """Fixed names from the caller, stable metadata, STORE independent of zlib."""
    expected = {"texture.stx", "sh3_texture_probe.3dsx", "sh3_texture_probe.smdh", "LEEME.txt"}
    if set(files) != expected:
        raise ValueError("Unexpected SD archive files")
    return inspection_archive(files, "sh3_texture_probe")
