"""GC07–GC11: asymmetric hand-derived contract, independent of game assets."""

import math
from dataclasses import FrozenInstanceError

import pytest

from tools.pipeline.character_space import CharacterRigid, inspection_normal, inspection_position

# world = (11*w-y, -7*w+z, 13*w-x, w); proper rotation with three different axes.
MODEL = (0, 0, -1, 0, -1, 0, 0, 0, 0, 1, 0, 0, 11, -7, 13, 1)
IDENTITY = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


@pytest.mark.parametrize("w", [0, 1, 4093 / 4096, 4095 / 4096])
def test_homogeneous_world_and_basis(w):
    rigid = CharacterRigid(MODEL)
    p = (2, -3, 5, w)
    expected = (11 * w + 3, -7 * w + 5, 13 * w - 2, w)
    assert rigid.position(p) == expected
    assert inspection_position(expected) == (expected[0], -expected[1], -expected[2], w)
    assert rigid.in_inspection_basis().position(inspection_position(p)) == inspection_position(
        expected
    )
    assert rigid.in_inspection_basis().in_inspection_basis() == rigid


def test_normal_magnitude_translation_and_basis():
    rigid = CharacterRigid(MODEL)
    n = (2, -3, 5)
    assert rigid.normal(n) == (3, 5, -2)
    assert sum(x * x for x in rigid.normal(n)) == 38
    assert rigid.in_inspection_basis().normal(inspection_normal(n)) == (3, -5, 2)
    no_translation = CharacterRigid(MODEL[:12] + (0, 0, 0, 1))
    assert no_translation.normal(n) == rigid.normal(n)
    assert rigid.normal((0, 0, 0)) == (0, 0, 0)


def test_hand_derived_negative_controls():
    rigid = CharacterRigid(MODEL)
    w = 4095 / 4096
    p = (2, -3, 5, w)
    world = (11 * w + 3, -7 * w + 5, 13 * w - 2, w)
    target = (world[0], -world[1], -world[2], w)
    # Transposing the full matrix destroys its affine row; reject it.
    with pytest.raises(ValueError):
        CharacterRigid(tuple(MODEL[r * 4 + c] for c in range(4) for r in range(4)))
    wrong_rotation = (0, -1, 0, 0, 0, 0, 1, 0, -1, 0, 0, 0, 11, -7, 13, 1)
    variants = (
        inspection_position(CharacterRigid(wrong_rotation).position(p)),
        inspection_position(rigid.position(world)),
        rigid.position(inspection_position(p)),
        inspection_position(rigid.position((*p[:3], 1))),
        inspection_position(tuple(x / w for x in world)),
    )
    assert all(max(abs(a - b) for a, b in zip(v, target, strict=True)) > 0.001 for v in variants)
    n = rigid.normal((2, -3, 5))
    assert tuple(x / math.sqrt(38) for x in n) != n


def _signed_volume(points):
    origin = points[0]
    a, b, c = [tuple(p[i] - origin[i] for i in range(3)) for p in points[1:]]
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def test_orientation_preserved_without_reversing_indices():
    points = ((2, 3, 5, 1), (4, 3, 5, 1), (2, 6, 5, 1), (2, 3, 12, 1))
    placed = tuple(inspection_position(CharacterRigid(MODEL).position(p)) for p in points)
    assert _signed_volume(points) == _signed_volume(placed) == 42


@pytest.mark.parametrize(
    "bad",
    [None, {}, "123", [1], [False] * 16, [float("nan")] * 16, [float("inf")] * 16, [10**1000] * 16],
)
def test_bad_matrix_shape_and_numbers(bad):
    with pytest.raises(ValueError):
        CharacterRigid(bad)


@pytest.mark.parametrize(
    "index,value",
    [
        (3, 0.01),
        (7, 1),
        (11, 1),
        (15, 0),
        (12, 1_000_001),
        (0, 2),
        (4, 0.1),
        (0, -1),
        (0, 0),
        (0, 1.0008),
    ],
)
def test_invalid_affine_scale_shear_reflection_and_determinant(index, value):
    matrix = list(IDENTITY)
    matrix[index] = value
    # All axes individually within tolerance, but determinant outside it.
    if value == 1.0008:
        matrix[5] = matrix[10] = value
    with pytest.raises(ValueError):
        CharacterRigid(matrix)


@pytest.mark.parametrize("size", [3, 4])
@pytest.mark.parametrize(
    "bad", [None, {}, "bad", [], [1], True, float("nan"), float("inf"), 10**1000]
)
def test_bad_vectors(size, bad):
    value = [bad] * size if type(bad) not in (list, dict, str) and bad is not None else bad
    rigid = CharacterRigid(MODEL)
    methods = (
        (rigid.position, inspection_position) if size == 4 else (rigid.normal, inspection_normal)
    )
    for method in methods:
        with pytest.raises(ValueError):
            method(value)


def test_overflow_is_rejected_before_result():
    with pytest.raises(ValueError):
        CharacterRigid(MODEL).position((0, 0, 0, 1e308))
    h = math.sqrt(0.5)
    rotated = CharacterRigid((h, h, 0, 0, -h, h, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))
    with pytest.raises(ValueError):
        rotated.normal((1.7e308, 1.7e308, 0))


def test_validation_is_immutable_and_bounds_include_endpoint():
    source = list(MODEL)
    rigid = CharacterRigid(source)
    source[12] = float("nan")
    assert rigid.columns == MODEL
    with pytest.raises(FrozenInstanceError):
        rigid.columns = IDENTITY
    endpoint = CharacterRigid(MODEL[:12] + (1_000_000, -1_000_000, 0, 1))
    assert endpoint.position([0, 0, 0, 1]) == (1_000_000, -1_000_000, 0, 1)
