"""Bounded static MAP transforms; world units are distinct from inspection scale."""

import math
from dataclasses import dataclass

INSPECTION_BASIS = (1, -1, -1)


def _finite_vector(values, size):
    if type(values) not in (list, tuple) or len(values) != size:
        raise ValueError("Expected finite numeric vector")
    try:
        valid = all(type(x) in (int, float) and math.isfinite(x) for x in values)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Expected finite numeric vector")
    return tuple(values)


@dataclass(frozen=True)
class MapAffine:
    """Column-major, orientation-preserving model for the verified MAP subset."""

    columns: tuple[float, ...]

    def __post_init__(self):
        model = _finite_vector(self.columns, 16)
        if any(abs(x) > 1_000_000 for x in model) or tuple(model[i] for i in (3, 7, 11, 15)) != (
            0,
            0,
            0,
            1,
        ):
            raise ValueError("Invalid affine model")
        a, b, c = (model[i : i + 3] for i in (0, 4, 8))
        determinant = (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - b[0] * (a[1] * c[2] - a[2] * c[1])
            + c[0] * (a[1] * b[2] - a[2] * b[1])
        )
        if not math.isfinite(determinant) or determinant <= 1e-8:
            raise ValueError("Unsupported model determinant")
        # Copy mutable input so later edits cannot bypass validation.
        object.__setattr__(self, "columns", model)

    def transform_point(self, position: tuple[float, float, float]) -> tuple[float, ...]:
        local = (*_finite_vector(position, 3), 1)
        world = tuple(
            sum(self.columns[col * 4 + row] * local[col] for col in range(4)) for row in range(3)
        )
        return _finite_vector(world, 3)


def inspection_basis(position: tuple[float, float, float]) -> tuple[float, ...]:
    """Rotate world coordinates by 180 degrees about X; no centering or scaling."""
    point = _finite_vector(position, 3)
    return tuple(value * sign for value, sign in zip(point, INSPECTION_BASIS, strict=True))


def material_uv(words: tuple[int, int]) -> tuple[float, float]:
    """Keep signed i16 words and the U control bit; the observed VU path has no V flip."""
    if (
        type(words) not in (list, tuple)
        or len(words) != 2
        or any(type(word) is not int or not -32768 <= word <= 32767 for word in words)
    ):
        raise ValueError("Expected original i16 UV words")
    return words[0] / 32768, words[1] / 32768
