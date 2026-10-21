"""Independent double-precision oracle for the observed single-clip PS2 path.

No decoder, emulator, renderer, or filesystem dependency. Matrices are columns;
the output is a model-space pose, not skinning or a console basis conversion.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass


def _finite(values: Sequence[float], size: int) -> tuple[float, ...]:
    if len(values) != size or not all(math.isfinite(v) for v in values):
        raise ValueError("Expected a finite vector of the specified size")
    return tuple(values)


def _matrix(values: Sequence[float]) -> tuple[float, ...]:
    matrix = _finite(values, 16)
    if tuple(matrix[i] for i in (3, 7, 11, 15)) != (0, 0, 0, 1):
        raise ValueError("Expected an affine matrix in columns")
    return matrix


def nlerp(
    current: Sequence[float], following: Sequence[float], fraction: float
) -> tuple[float, ...]:
    """Shortest-hemisphere normalized linear quaternion interpolation."""
    a, b = _finite(current, 4), _finite(following, 4)
    if not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("Fraction outside [0, 1]")
    if any(abs(sum(v * v for v in q) - 1) > 1e-3 for q in (a, b)):
        raise ValueError("Expected unit quaternion endpoints")
    sign = -1 if sum(x * y for x, y in zip(a, b, strict=True)) < 0 else 1
    mixed = tuple((1 - fraction) * x + fraction * sign * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(v * v for v in mixed))
    return tuple(v / norm for v in mixed)


def rotation_translation(
    quaternion: Sequence[float], translation: Sequence[float]
) -> tuple[float, ...]:
    x, y, z, w = nlerp(quaternion, quaternion, 0)
    tx, ty, tz = _finite(translation, 3)
    return (
        1 - 2 * (y * y + z * z),
        2 * (x * y + z * w),
        2 * (x * z - y * w),
        0,
        2 * (x * y - z * w),
        1 - 2 * (x * x + z * z),
        2 * (y * z + x * w),
        0,
        2 * (x * z + y * w),
        2 * (y * z - x * w),
        1 - 2 * (x * x + y * y),
        0,
        tx,
        ty,
        tz,
        1,
    )


def multiply(left: Sequence[float], right: Sequence[float]) -> tuple[float, ...]:
    a, b = _matrix(left), _matrix(right)
    return tuple(
        sum(a[k * 4 + row] * b[column * 4 + k] for k in range(4))
        for column in range(4)
        for row in range(4)
    )


def rest_child_offset(
    parent_global: Sequence[float], child_global: Sequence[float]
) -> tuple[float, ...]:
    """R_parent^T * (t_child - t_parent), requiring a rigid parent."""
    parent, child = _matrix(parent_global), _matrix(child_global)
    for i in range(3):
        for j in range(3):
            dot = sum(parent[i * 4 + k] * parent[j * 4 + k] for k in range(3))
            if abs(dot - (1 if i == j else 0)) > 1e-5:
                raise ValueError("Rest parent must have orthonormal rotation")
    delta = [child[12 + i] - parent[12 + i] for i in range(3)]
    return tuple(sum(parent[j * 4 + i] * delta[i] for i in range(3)) for j in range(3))


def compose_pose(
    local_matrices: Sequence[Sequence[float]], parents: Sequence[int]
) -> tuple[tuple[float, ...], ...]:
    """Evaluate an acyclic forest, including parents stored after children."""
    count = len(parents)
    if not 1 <= count <= 128 or len(local_matrices) != count:
        raise ValueError("Invalid skeleton size")
    if any(type(p) is not int or not -1 <= p < count for p in parents):
        raise ValueError("Invalid parent")
    local = tuple(_matrix(m) for m in local_matrices)
    result: dict[int, tuple[float, ...]] = {}
    visiting: set[int] = set()

    def evaluate(index: int) -> tuple[float, ...]:
        if index in visiting:
            raise ValueError("Skeleton cycle")
        if index not in result:
            visiting.add(index)
            parent = parents[index]
            result[index] = (
                local[index] if parent == -1 else multiply(evaluate(parent), local[index])
            )
            visiting.remove(index)
        return result[index]

    return tuple(evaluate(i) for i in range(count))


@dataclass(frozen=True)
class ClipStep:
    current: int
    following: int
    fraction: float
    next_counter: int
    stopped: bool


def clip_step(start: int, end: int, loop: bool, counter: int, speed: int, ticks: int) -> ClipStep:
    """Observed forward, steady single-clip path; excludes clip blending."""
    if any(type(v) is not int for v in (start, end, counter, speed, ticks)):
        raise ValueError("Expected integer clock inputs")
    if not (0 <= start <= end < 4096 and 0 <= counter < (end - start + 1) * 4096):
        raise ValueError("Invalid clip or counter")
    if type(loop) is not bool or not 0 < speed <= 32767 or not 0 <= ticks <= 3:
        raise ValueError("Unsupported forward clock")
    increment = speed * ticks
    if increment > 32767:
        raise ValueError("Observed signed speed field would overflow")
    current = start + counter // 4096
    following = current + 1 if current < end else (start if loop else end)
    next_counter = counter + increment
    if loop:
        length = (end - start + 1) * 4096
        if next_counter >= 2 * length:
            raise ValueError("Multiple wraps are outside the observed path")
        return ClipStep(current, following, (counter % 4096) / 4096, next_counter % length, False)
    limit = (end - start) * 4096
    return ClipStep(
        current,
        following,
        (counter % 4096) / 4096,
        min(next_counter, limit),
        next_counter == 0 or next_counter >= limit,
    )
