"""Rigid character instance transforms in original units, preserving homogeneous W.

This bounded host contract does not perform skinning, perspective division,
EE/VU rounding, camera placement or inspection centering/scaling.
"""

import math
from dataclasses import dataclass

_BASIS = (1, -1, -1, 1)
_RIGID_TOLERANCE = 0.002


def _vector(values, size):
    if type(values) not in (list, tuple) or len(values) != size:
        raise ValueError("Expected finite numeric vector")
    try:
        valid = all(type(x) in (int, float) and math.isfinite(x) for x in values)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Expected finite numeric vector")
    return tuple(values)


def inspection_position(position):
    """Apply B to world position4, without changing W or dividing by it."""
    return tuple(x * sign for x, sign in zip(_vector(position, 4), _BASIS, strict=True))


def inspection_normal(normal):
    """Apply the same proper rotation to world normal3, without normalizing."""
    return tuple(x * sign for x, sign in zip(_vector(normal, 3), _BASIS[:3], strict=True))


@dataclass(frozen=True)
class CharacterRigid:
    """Column-major proper rigid transform; observed character profile only."""

    columns: tuple[float, ...]

    def __post_init__(self):
        matrix = _vector(self.columns, 16)
        if any(abs(x) > 1_000_000 for x in matrix) or tuple(matrix[i] for i in (3, 7, 11, 15)) != (
            0,
            0,
            0,
            1,
        ):
            raise ValueError("Invalid affine instance")
        axes = tuple(matrix[i : i + 3] for i in (0, 4, 8))
        for i in range(3):
            for j in range(i, 3):
                dot = sum(x * y for x, y in zip(axes[i], axes[j], strict=True))
                if abs(dot - int(i == j)) > _RIGID_TOLERANCE:
                    raise ValueError("Unsupported instance scale or shear")
        a, b, c = axes
        determinant = (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - b[0] * (a[1] * c[2] - a[2] * c[1])
            + c[0] * (a[1] * b[2] - a[2] * b[1])
        )
        if abs(determinant - 1) > _RIGID_TOLERANCE:
            raise ValueError("Unsupported instance orientation")
        object.__setattr__(self, "columns", matrix)

    def position(self, position):
        """Apply instance exactly once to an already skinned position4."""
        source = _vector(position, 4)
        return _vector(
            tuple(
                sum(self.columns[col * 4 + row] * source[col] for col in range(4))
                for row in range(4)
            ),
            4,
        )

    def normal(self, normal):
        """Apply linear columns only; retain the weighted normal's magnitude."""
        source = _vector(normal, 3)
        return _vector(
            tuple(
                sum(self.columns[col * 4 + row] * source[col] for col in range(3))
                for row in range(3)
            ),
            3,
        )

    def in_inspection_basis(self):
        """Return B*M*B^-1 for inputs already expressed in the inspection basis."""
        return CharacterRigid(
            tuple(
                _BASIS[row] * self.columns[col * 4 + row] * _BASIS[col]
                for col in range(4)
                for row in range(4)
            )
        )
