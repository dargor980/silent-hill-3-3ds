"""Bounded endpoint reference for the pinned PCSX2 float32 capture profile.

Products/additions truncate; SQRT rounds to nearest. This is not a general
PS2 FPU emulator, a replacement asset decoder, or an exact hardware claim.
"""

import math
import struct
from collections.abc import Sequence


def _nearest(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _toward_zero(value: float) -> float:
    # All callers operate on bounded normal finite values, or exact zero.
    rounded = _nearest(value)
    if abs(rounded) > abs(value):
        bits = struct.unpack("<I", struct.pack("<f", rounded))[0]
        return struct.unpack("<f", struct.pack("<I", bits - 1))[0]
    return rounded


def reconstruct_quaternion_f32(
    words: Sequence[int], *, negative_w: bool
) -> tuple[float, float, float, float]:
    """Reconstruct one bounded signed XYZ/32768 endpoint and its W sign.

    A small quantization overshoot follows the observed zero-radicand clamp;
    larger non-unit data is outside this audit profile and is rejected.
    """
    if (
        not isinstance(words, (tuple, list))
        or len(words) != 3
        or any(type(v) is not int or not -32768 <= v <= 32767 for v in words)
        or type(negative_w) is not bool
    ):
        raise ValueError("Expected three signed i16 words and a boolean W sign")
    x, y, z = (v / 32768 for v in words)
    if x * x + y * y + z * z > 1.0001:
        raise ValueError("Quaternion norm outside the bounded capture profile")
    squares = tuple(_toward_zero(v * v) for v in (x, y, z))
    squared_norm = _toward_zero(_toward_zero(squares[0] + squares[1]) + squares[2])
    radicand = max(0.0, _toward_zero(1.0 - squared_norm))
    w = _nearest(math.sqrt(radicand))
    return x, y, z, -w if negative_w else w
