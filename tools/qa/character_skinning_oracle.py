"""Double-precision reference for the observed pre-lighting VU1 skinning path.

Matrices are columns, already prepared by the caller (including helpers).
This is an independent QA oracle, not a PS2 floating-point emulator or renderer.
It preserves deficient Q12 weight sums and the homogeneous position component.
Normals use the same linear columns, without translation or normalization.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass


def _finite(values: Sequence[float], size: int) -> tuple[float, ...]:
    if len(values) != size or any(
        type(v) not in (int, float) or not math.isfinite(v) for v in values
    ):
        raise ValueError("Expected finite numeric components")
    return tuple(values)


def matrix_product(left: Sequence[float], right: Sequence[float]) -> tuple[float, ...]:
    """General 4x4 product; the observed palette may have W=Z, not affine W."""
    a, b = _finite(left, 16), _finite(right, 16)
    return _finite(
        tuple(
            sum(a[k * 4 + row] * b[column * 4 + k] for k in range(4))
            for column in range(4)
            for row in range(4)
        ),
        16,
    )


def _qvector(values: Sequence[int], size: int, low: int, high: int) -> tuple[int, ...]:
    if len(values) != size or any(type(v) is not int or not low <= v <= high for v in values):
        raise ValueError("Invalid fixed-point vector")
    return tuple(values)


@dataclass(frozen=True)
class DeformedVertex:
    position: tuple[float, ...]
    normal: tuple[float, ...]


def deform_vertex(
    position_q4: Sequence[int],
    normal_q12: Sequence[int],
    weights_q12: Sequence[int],
    matrices: Sequence[Sequence[float]],
) -> DeformedVertex:
    """Blend primary and helper-transformed influences in their stored order."""
    count = len(weights_q12)
    if not 1 <= count <= 4 or len(matrices) != count:
        raise ValueError("Expected one to four paired influences")
    weights = _qvector(weights_q12, count, 0, 4096)
    if not 4096 - (count - 1) <= sum(weights) <= 4096:
        raise ValueError("Unsupported Q12 weight sum")
    position = tuple(x / 16 for x in _qvector(position_q4, 3, -32768, 32767)) + (1,)
    normal = tuple(x / 4096 for x in _qvector(normal_q12, 3, -32768, 32767))
    palette = tuple(_finite(matrix, 16) for matrix in matrices)

    def blend(vector: tuple[float, ...], rows: int) -> tuple[float, ...]:
        return _finite(
            tuple(
                sum(
                    weight
                    / 4096
                    * sum(matrix[k * 4 + row] * value for k, value in enumerate(vector))
                    for weight, matrix in zip(weights, palette, strict=True)
                )
                for row in range(rows)
            ),
            rows,
        )

    return DeformedVertex(blend(position, 4), blend(normal, 3))
