"""Analytical, synthetic checks; no game assets or emulator dependency."""

import math

import pytest

from tools.qa.character_skinning_oracle import deform_vertex, matrix_product

IDENTITY = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
TRANSLATION = IDENTITY[:12] + (10, -20, 30, 1)
ROTATION = (0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


def test_rigid_position_and_normal_have_distinct_translation_rules():
    sample = deform_vertex((16, -32, 48), (4096, 0, 0), (4096,), (TRANSLATION,))
    assert sample.position == (11, -22, 33, 1)
    assert sample.normal == (1, 0, 0)


def test_matrix_order_rotates_translation_only_on_the_left():
    assert matrix_product(ROTATION, TRANSLATION)[12:] == (20, 10, 30, 1)
    assert matrix_product(TRANSLATION, ROTATION)[12:] == (10, -20, 30, 1)
    assert matrix_product(IDENTITY, ROTATION) == ROTATION


def test_three_influences_use_helpers_in_the_supplied_order():
    helper = matrix_product(TRANSLATION, ROTATION)
    sample = deform_vertex(
        (16, 32, 48), (4096, 0, 0), (2048, 1024, 1024), (IDENTITY, ROTATION, helper)
    )
    assert sample.position == (2, -3.5, 10.5, 1)
    assert sample.normal == (0.5, 0.5, 0)


@pytest.mark.parametrize("weights", [(4096,), (2048, 2047), (1365, 1365, 1364), (1024,) * 4])
def test_weight_deficit_is_preserved_including_homogeneous_w(weights):
    factor = sum(weights) / 4096
    result = deform_vertex((16, 32, -48), (0, 4096, 0), weights, (IDENTITY,) * len(weights))
    assert result.position == (factor, 2 * factor, -3 * factor, factor)
    assert result.normal == (0, factor, 0)


def test_projective_palette_retains_w_equal_to_z():
    projective = list(IDENTITY)
    projective[11], projective[15] = 1, 0
    result = deform_vertex((16, 32, 48), (0, 0, 4096), (4096,), (projective,))
    assert result.position == (1, 2, 3, 3)
    assert result.normal == (0, 0, 1)
    assert matrix_product(projective, TRANSLATION)[15] == 30


def test_normal_is_neither_normalized_nor_inverse_transposed():
    scale = list(IDENTITY)
    scale[0], scale[5] = 2, 3
    result = deform_vertex((0, 0, 0), (2048, 2048, 0), (4096,), (scale,))
    assert result.normal == (1, 1.5, 0)


@pytest.mark.parametrize(
    "weights",
    [(), (4096,) * 5, (4095,), (2048, 2046), (4097,), (-1, 4096), (2048.0, 2048), (True, 4095)],
)
def test_invalid_weights_rejected(weights):
    with pytest.raises(ValueError):
        deform_vertex((0, 0, 0), (0, 0, 0), weights, (IDENTITY,) * len(weights))


def test_mismatched_palette_rejected():
    with pytest.raises(ValueError):
        deform_vertex((0, 0, 0), (0, 0, 0), (2048, 2048), (IDENTITY,))


@pytest.mark.parametrize(
    "vector", [(1, 2), (1, 2, 32768), (-32769, 0, 0), (True, 0, 0), (1.5, 0, 0)]
)
@pytest.mark.parametrize("field", ["position", "normal"])
def test_invalid_fixed_components(vector, field):
    with pytest.raises(ValueError):
        deform_vertex(
            vector if field == "position" else (0, 0, 0),
            vector if field == "normal" else (0, 0, 0),
            (4096,),
            (IDENTITY,),
        )


@pytest.mark.parametrize(
    "matrix", [IDENTITY[:-1], (math.nan,) * 16, (math.inf,) * 16, (True,) * 16, ("1",) * 16]
)
def test_invalid_matrix_rejected_by_both_operations(matrix):
    with pytest.raises(ValueError):
        matrix_product(matrix, IDENTITY)
    with pytest.raises(ValueError):
        deform_vertex((0, 0, 0), (0, 0, 0), (4096,), (matrix,))


def test_nonfinite_results_rejected():
    with pytest.raises(ValueError):
        matrix_product((1e308,) * 16, (2,) * 16)
    with pytest.raises(ValueError):
        deform_vertex((32767,) * 3, (0, 0, 0), (4096,), ((1e308,) * 16,))
