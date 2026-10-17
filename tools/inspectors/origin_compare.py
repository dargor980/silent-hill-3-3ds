"""OR05: bounded byte comparisons expressed only as hashes and relative intervals."""

import hashlib

from tools.inspectors.observation_capture import require
from tools.inspectors.origin_memory import MAX_RANGE


def compare_ranges(reference: bytes, observed: bytes) -> dict:
    require(
        isinstance(reference, bytes)
        and isinstance(observed, bytes)
        and 1 <= len(reference) == len(observed) <= MAX_RANGE,
        "ORIGIN_COMPARE",
    )
    intervals = []
    for offset, (left, right) in enumerate(zip(reference, observed, strict=True)):
        if left != right:
            if intervals and intervals[-1]["end"] == offset:
                intervals[-1]["end"] += 1
            else:
                intervals.append({"start": offset, "end": offset + 1})
    return {
        "reference_sha256": hashlib.sha256(reference).hexdigest(),
        "observed_sha256": hashlib.sha256(observed).hexdigest(),
        "size": len(reference),
        "equal": not intervals,
        "different_bytes": sum(r["end"] - r["start"] for r in intervals),
        "difference_ranges": intervals,
    }
