"""Invented SRI2 and independent contiguous-partition checks for HS-T1."""

import random
import re
from pathlib import Path

import pytest

from tests.locomotion_rig_fixtures import changed, own_sri2
from tools.qa.skinning_workload import RIG_BONE_CAPACITY, analyze_sri2, partition_palettes


def test_native_palette_offset_has_not_drifted():
    header = Path("engine/domain/include/sh3/domain/inspection_rig.hpp").read_text()
    assert int(re.search(r"rig_bones\s*=\s*(\d+)", header)[1]) == RIG_BONE_CAPACITY


@pytest.mark.parametrize("turns", [False, True])
def test_shared_geometry_deficient_w_and_distinct_helper_matrices(turns):
    raw = own_sri2(turns=turns)["heather.sri"]
    report = analyze_sri2(raw, [2, 3, 201])
    assert report["profile"] == (2 if turns else 1)
    assert report["clips"] == ([101, 109, 113, 107, 108] if turns else [101, 109, 113])
    assert report["samples"] == (78 if turns else 58)
    assert report["bones"] == 36 and report["helpers"] == 2
    assert report["current_palette_matrices"] == 38
    assert report["stored_vertices"] == 3 and report["unreferenced_vertices"] == 0
    assert report["current_cpu_influence_evaluations"] == 9
    assert report["all_referenced"] == dict(
        indices=6,
        triangles=2,
        unique_vertices=3,
        influences={"3": 3},
        weight_sums_q12={"4095": 3},
        zero_weight_active_influences=0,
        matrix_slots=[35, 73, 74],
        primary_matrices=1,
        helper_matrices=2,
        unique_vertex_influence_evaluations=9,
        expanded_vertex_influence_evaluations=18,
    )
    assert report["shared_opaque_blended_vertices"] == 3
    assert report["helper_targets"] == [1, 35]  # h1 must NOT collapse to primary 35.
    assert report["opaque"] == report["blended"]
    assert report["materials"][1]["first_index"] == 3
    rejected, *accepted = report["opaque_capacity_curve"]
    assert rejected["feasible"] is False and rejected["rejected_materials"] == [0]
    assert rejected["batches"] == [] and rejected["matrix_uploads"] == 0
    for curve in accepted:
        assert curve["feasible"] and curve["batch_count"] == 1
        assert curve["vertices_if_duplicated_per_batch"] == 3
        assert curve["batches"] == [
            dict(
                material=0,
                first_index=0,
                index_count=3,
                matrix_slots=[35, 73, 74],
                unique_vertices=3,
            )
        ]


def test_one_two_three_influences_and_zero_weight_slot_remains():
    raw = own_sri2(turns=True)["heather.sri"]
    vertex_offset = 96 + 16 + 36 * 8 + 5 * 20 + 78 * 36 * 28 + 2 * 68
    raw = changed(raw, vertex_offset + 16, "3H4B", 4096, 0, 0, 2, 1, 255, 255)
    raw = changed(raw, vertex_offset + 28 + 16, "3H4B", 4095, 0, 0, 3, 2, 0, 255)
    raw = changed(raw, vertex_offset + 56 + 16, "3H4B", 1364, 1365, 1365, 4, 3, 0, 1)
    report = analyze_sri2(raw)
    stats = report["all_referenced"]
    assert stats["influences"] == {"1": 1, "2": 1, "3": 1}
    assert stats["weight_sums_q12"] == {"4094": 1, "4095": 1, "4096": 1}
    assert stats["matrix_slots"] == [2, 3, 4, 73, 74]
    assert stats["zero_weight_active_influences"] == 1
    assert stats["unique_vertex_influence_evaluations"] == 6


def test_unreferenced_vertices_still_count_in_current_cpu_work():
    raw = own_sri2()["heather.sri"]
    index_offset = 96 + 16 + 36 * 8 + 3 * 20 + 58 * 36 * 28 + 2 * 68 + 3 * 28
    raw = changed(raw, index_offset, "6H", 0, 1, 0, 1, 0, 1)
    report = analyze_sri2(raw)
    assert report["stored_vertices"] == 3 and report["unreferenced_vertices"] == 1
    assert report["current_cpu_influence_evaluations"] == 9
    assert report["all_referenced"]["unique_vertex_influence_evaluations"] == 6


def test_rejected_later_material_does_not_publish_partial_plan():
    raw = own_sri2()["heather.sri"]
    vertex_offset = 96 + 16 + 36 * 8 + 3 * 20 + 58 * 36 * 28 + 2 * 68
    raw = changed(raw, vertex_offset + 16, "3H4B", 4096, 0, 0, 2, 1, 255, 255)
    raw = changed(raw, vertex_offset + 3 * 28, "6H", 0, 0, 0, 0, 1, 2)
    raw = changed(raw, len(raw) - 8, "I", 0)
    curve = analyze_sri2(raw, [1])["opaque_capacity_curve"][0]
    assert curve["rejected_materials"] == [1]
    assert curve["feasible"] is False and curve["batches"] == []
    assert curve["batch_count"] == curve["matrix_uploads"] == 0
    assert curve["vertices_if_duplicated_per_batch"] == 0


def test_opaque_material_boundaries_and_no_transparent_batch_plan():
    raw = own_sri2()["heather.sri"]
    both_opaque = changed(raw, len(raw) - 8, "I", 0)
    report = analyze_sri2(both_opaque, [3])
    batches = report["opaque_capacity_curve"][0]["batches"]
    assert [(b["material"], b["first_index"]) for b in batches] == [(0, 0), (1, 3)]
    both_blended = changed(raw, len(raw) - 36, "I", 1)
    report = analyze_sri2(both_blended, [1])
    assert report["opaque"]["unique_vertices"] == 0
    assert report["blended"]["unique_vertices"] == 3
    assert report["opaque_capacity_curve"][0]["feasible"]
    assert report["opaque_capacity_curve"][0]["batches"] == []


@pytest.mark.parametrize("capacities", [[], [3, 3], [0], [-1], [202], [True], [3.0]])
def test_invalid_capacities(capacities):
    with pytest.raises(ValueError, match="HS_CAPACIT"):
        analyze_sri2(own_sri2()["heather.sri"], capacities)


def test_malformed_sri_rejected_before_analysis():
    raw = own_sri2()["heather.sri"]
    with pytest.raises(ValueError, match="SRI2"):
        analyze_sri2(raw[:-1])


def test_indivisible_triangle_and_empty_input():
    assert partition_palettes([], 1) == []
    for triangles in ([[]], [[1], [1, 2, 3]]):
        with pytest.raises(ValueError, match="HS_TRIANGLE_CAPACITY"):
            partition_palettes(triangles, 2)


def test_ordered_partition_has_minimum_contiguous_batch_count():
    # Independent exhaustive cut search, not the greedy implementation.
    rng = random.Random(603)
    for length in range(1, 9):
        for capacity in range(3, 7):
            triangles = [set(rng.sample(range(9), rng.randint(1, 3))) for _ in range(length)]
            possible_counts = []
            for cuts in range(1 << (length - 1)):
                boundaries = [0] + [i for i in range(1, length) if cuts & (1 << (i - 1))]
                boundaries += [length]
                if all(
                    len(set.union(*triangles[a:b])) <= capacity
                    for a, b in zip(boundaries[:-1], boundaries[1:], strict=True)
                ):
                    possible_counts.append(len(boundaries) - 1)
            batches = partition_palettes(triangles, capacity)
            assert len(batches) == min(possible_counts)
            cursor = 0
            for first, count, palette in batches:
                assert first == cursor and count > 0
                assert palette == sorted(set.union(*triangles[first : first + count]))
                assert len(palette) <= capacity
                cursor += count
            assert cursor == length


def test_repeated_palettes_keep_order_and_exact_capacity():
    assert partition_palettes([[2, 1, 1], [1, 2], [3], [2]], 2) == [(0, 2, [1, 2]), (2, 2, [2, 3])]
