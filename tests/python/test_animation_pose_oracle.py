"""Analytic fixtures for the independent runtime comparison, without game data."""

import math

import pytest

from tools.qa.animation_pose_oracle import (
    clip_step,
    compose_pose,
    multiply,
    nlerp,
    rest_child_offset,
    rotation_translation,
)

IDENTITY = (0, 0, 0, 1)
Z90 = (0, 0, math.sqrt(0.5), math.sqrt(0.5))


def test_quaternion_hemisphere_and_known_half_turn():
    q = nlerp(IDENTITY, Z90, 0.5)
    assert q == pytest.approx((0, 0, math.sin(math.pi / 8), math.cos(math.pi / 8)))
    assert nlerp(IDENTITY, tuple(-v for v in Z90), 0.5) == pytest.approx(q)
    assert nlerp(IDENTITY, (0, 0, 0, -1), 0.5) == IDENTITY


def test_nlerp_is_not_spherical_interpolation():
    q = nlerp(IDENTITY, Z90, 0.25)
    spherical = (0, 0, math.sin(math.pi / 16), math.cos(math.pi / 16))
    assert abs(q[2] - spherical[2]) > 0.005
    assert sum(v * v for v in q) == pytest.approx(1)


def test_parent_rotation_moves_child_translation_in_column_order():
    parent = rotation_translation(Z90, (10, 20, 30))
    child = rotation_translation(IDENTITY, (2, 0, 0))
    actual = multiply(parent, child)
    assert actual[12:15] == pytest.approx((10, 22, 30))
    assert multiply(child, parent)[12:15] == pytest.approx((12, 20, 30))
    assert rest_child_offset(parent, actual) == pytest.approx((2, 0, 0))


def test_forest_and_later_parent_preserve_independent_roots():
    child = rotation_translation(IDENTITY, (2, 0, 0))
    other = rotation_translation(IDENTITY, (-20, 0, 0))
    parent = rotation_translation(Z90, (10, 20, 30))
    pose = compose_pose((child, other, parent), (2, -1, -1))
    assert pose[0][12:15] == pytest.approx((10, 22, 30))
    assert pose[1] == other
    assert pose[2] == parent


def test_loop_uses_inclusive_end_and_interpolates_back_to_start():
    result = clip_step(5, 8, True, 3 * 4096 + 2048, 1024, 3)
    assert (result.current, result.following, result.fraction) == (8, 5, 0.5)
    assert (result.next_counter, result.stopped) == (1024, False)


def test_nonloop_evaluates_input_pose_then_clamps_next_counter():
    result = clip_step(5, 8, False, 2 * 4096 + 2048, 1024, 3)
    assert (result.current, result.following, result.fraction) == (7, 8, 0.5)
    assert (result.next_counter, result.stopped) == (3 * 4096, True)
    final = clip_step(5, 8, False, 3 * 4096 + 2048, 1024, 2)
    assert (final.current, final.following) == (8, 8)
    assert final.next_counter == 3 * 4096


def test_clock_units_and_zero_ticks():
    assert clip_step(0, 10, True, 819, 1000, 2).next_counter == 2819
    assert clip_step(0, 10, True, 819, 1000, 0).next_counter == 819


def test_nonloop_stops_at_zero_when_the_clock_does_not_advance():
    result = clip_step(5, 8, False, 0, 1000, 0)
    assert (result.current, result.following, result.fraction) == (5, 6, 0)
    assert (result.next_counter, result.stopped) == (0, True)
    assert not clip_step(5, 8, False, 1, 1000, 0).stopped


@pytest.mark.parametrize("fraction", [-1, 1.1, math.inf, math.nan])
def test_reject_fraction(fraction):
    with pytest.raises(ValueError):
        nlerp(IDENTITY, IDENTITY, fraction)


@pytest.mark.parametrize("q", [(0, 0, 0, 0), (1, 1, 0, 0), (math.nan, 0, 0, 1), (0,)])
def test_reject_quaternion(q):
    with pytest.raises(ValueError):
        nlerp(q, IDENTITY, 0.5)


@pytest.mark.parametrize("parents", [(0,), (1, 0), (-2,), (2,), (True,)])
def test_reject_bad_forest(parents):
    with pytest.raises(ValueError):
        compose_pose([rotation_translation(IDENTITY, (0, 0, 0))] * len(parents), parents)


def test_reject_nonaffine_scaled_rest_and_bad_sizes():
    matrix = list(rotation_translation(IDENTITY, (0, 0, 0)))
    matrix[0] = 2
    with pytest.raises(ValueError):
        rest_child_offset(matrix, matrix)
    matrix[3] = 1
    with pytest.raises(ValueError):
        multiply(matrix, matrix)
    for matrices, parents in [((), ()), ((), (-1,)), ([matrix] * 129, [-1] * 129)]:
        with pytest.raises(ValueError):
            compose_pose(matrices, parents)


@pytest.mark.parametrize(
    "args",
    [
        (0, 2, True, -1, 1000, 2),
        (0, 2, True, 3 * 4096, 1000, 2),
        (2, 1, True, 0, 1000, 2),
        (0, 2, True, 0.0, 1000, 2),
        (0, 2, 1, 0, 1000, 2),
        (0, 2, True, 0, -1, 2),
        (0, 2, True, 0, 1000, 4),
        (0, 2, True, 0, 20000, 2),
        (0, 0, True, 0, 10000, 1),
    ],
)
def test_reject_unobserved_clock_cases(args):
    with pytest.raises(ValueError):
        clip_step(*args)
