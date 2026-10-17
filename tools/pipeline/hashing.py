"""Bounded stream hashing shared by image and member readers."""

import hashlib
import zlib
from typing import BinaryIO

from tools.pipeline.profile import ProfileError

CHUNK_BYTES = 1024 * 1024


class _RangeStream:
    """Expose a logical EOF without consuming bytes beyond a requested range."""

    def __init__(self, stream: BinaryIO, length: int):
        self.stream = stream
        self.remaining = length

    def read(self, limit: int) -> bytes:
        requested = min(limit, self.remaining)
        if requested == 0:
            return b""
        data = self.stream.read(requested)
        if len(data) > requested:
            raise ProfileError("SIZE_MISMATCH", "Range reader exceeded requested bytes")
        self.remaining -= len(data)
        return data


def fingerprint_range(stream: BinaryIO, length: int) -> dict:
    """Hash exactly length bytes from the current stream position, without exporting."""
    # fingerprint_stream validates length before the wrapper receives a read.
    return fingerprint_stream(_RangeStream(stream, length), length)


def fingerprint_stream(stream: BinaryIO, expected: int, *, include_catalog: bool = False) -> dict:
    if type(expected) is not int or not 0 <= expected <= (1 << 63) - 1:
        raise ProfileError("INVALID_SIZE", "Expected a bounded non-negative stream size")
    algorithms = ("sha256", "sha1", "md5") if include_catalog else ("sha256",)
    # Legacy digests identify records in preservation catalogs; SHA-256 is retained.
    digests = {name: hashlib.new(name, usedforsecurity=False) for name in algorithms}
    crc, total = 0, 0
    while chunk := stream.read(min(CHUNK_BYTES, expected - total + 1)):
        total += len(chunk)
        if total > expected:
            raise ProfileError("SIZE_MISMATCH", "Read exceeds declared size")
        for digest in digests.values():
            digest.update(chunk)
        if include_catalog:
            crc = zlib.crc32(chunk, crc)
    if total != expected:
        raise ProfileError("SIZE_MISMATCH", "Truncated input while hashing")
    result = {"size": total, **{name: digest.hexdigest() for name, digest in digests.items()}}
    if include_catalog:
        result["crc32"] = f"{crc:08x}"
    return result
