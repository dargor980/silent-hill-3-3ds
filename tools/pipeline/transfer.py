"""Exact bounded stream transfer; no paths or container knowledge."""

import hashlib
from typing import BinaryIO

from tools.pipeline.hashing import CHUNK_BYTES
from tools.pipeline.profile import ProfileError


def write_all(destination: BinaryIO, data: bytes) -> None:
    remaining = memoryview(data)
    while remaining:
        written = destination.write(remaining)
        if type(written) is not int or not 0 < written <= len(remaining):
            raise ProfileError("WRITE_ERROR", "Output did not make bounded progress")
        remaining = remaining[written:]


def copy_exact(source: BinaryIO, destination: BinaryIO, length: int) -> tuple[int, str]:
    if type(length) is not int or not 0 <= length <= (1 << 63) - 1:
        raise ProfileError("INVALID_SIZE", "Expected bounded stream length")
    total, digest = 0, hashlib.sha256()
    while total < length:
        limit = min(CHUNK_BYTES, length - total)
        data = source.read(limit)
        if not isinstance(data, bytes) or not 0 < len(data) <= limit:
            raise ProfileError("SHORT_READ", "Source did not return bounded range bytes")
        write_all(destination, data)
        digest.update(data)
        total += len(data)
    return total, digest.hexdigest()
