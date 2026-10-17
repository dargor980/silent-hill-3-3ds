"""RL04-RL05: streaming exact matches, never a semantic resource link."""

import hashlib
from typing import BinaryIO

from tools.inspectors.inventory import validate_image_hash
from tools.pipeline.profile import ProfileError

CHUNK = 1024 * 1024
MAX_BYTES = 4 * 1024 * 1024 * 1024
MAX_HITS = 128


def scan_stream(stream: BinaryIO, size: int, patterns: dict[str, bytes]) -> tuple[str, dict]:
    if type(size) is not int or not 0 <= size <= MAX_BYTES or not isinstance(patterns, dict):
        raise ProfileError("MATCH_BUDGET", "Invalid scan budget")
    if len(patterns) > 10:
        raise ProfileError("MATCH_BUDGET", "Too many patterns")
    for key, value in patterns.items():
        validate_image_hash(key)
        if not isinstance(value, bytes) or len(value) not in (64, 256) or len(set(value)) == 1:
            raise ProfileError("MATCH_PATTERN", "Invalid or non-discriminating pattern")
    digest, hits, tail, done = hashlib.sha256(), {key: [] for key in patterns}, b"", 0
    overlap = max((len(p) - 1 for p in patterns.values()), default=0)
    while done < size:
        wanted = min(CHUNK, size - done)
        block = stream.read(wanted)
        if not isinstance(block, bytes) or not 0 < len(block) <= wanted:
            raise ProfileError("MATCH_READ", "Incomplete or oversized resource read")
        digest.update(block)
        window, base = tail + block, done - len(tail)
        for key, pattern in patterns.items():
            at = window.find(pattern)
            while at >= 0:
                if base + at + len(pattern) > done:
                    if len(hits[key]) == MAX_HITS:
                        raise ProfileError("MATCH_HITS", "Match budget exceeded")
                    hits[key].append(base + at)
                at = window.find(pattern, at + 1)
        done += len(block)
        tail = window[-overlap:] if overlap else b""
    if stream.read(1) != b"":
        raise ProfileError("MATCH_READ", "Resource exceeds declared size")
    return digest.hexdigest(), hits
