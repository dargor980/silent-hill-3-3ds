"""Independent checks of HG-T3 literals, not the future C++ implementation.

No pipeline, native evaluator, private resource or acquisition helper is imported.
HG-T4 must feed these same cases to C++/reader/controller and inject failures.
"""

import itertools
import json
import struct
from collections import deque
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parents[1] / "fixtures/synthetic"
DATA = json.loads((FIXTURES / "heather-turns-native-v1.json").read_text())
LEGACY = json.loads((FIXTURES / "heather-locomotion-v1.json").read_text())
CLIPS = {c["id"]: c for c in DATA["clips"]}
IDS = tuple(CLIPS)
NEW_ARCS = {(a["source"], a["target"]): a for a in DATA["arcs"]}
LEGACY_EDGES = {(101, 109), (109, 101), (113, 101), (109, 113), (113, 109)}
EDGES = LEGACY_EDGES | {(101, 107), (107, 101), (101, 108), (108, 101)}


def shortest_path(start, goal):
    queue = deque([(start, [])])
    seen = {start}
    while queue:
        node, path = queue.popleft()
        if node == goal:
            return path
        for next_node in IDS:
            if (node, next_node) in EDGES and next_node not in seen:
                seen.add(next_node)
                queue.append((next_node, [*path, next_node]))
    raise AssertionError("Disconnected contract graph")


def decimal_nlerp(a, b, fraction):
    a, b = ([Decimal(str(v)) for v in q] for q in (a, b))
    sign = -1 if sum(x * y for x, y in zip(a, b, strict=True)) < 0 else 1
    q = [x * (1 - fraction) + sign * y * fraction for x, y in zip(a, b, strict=True)]
    norm = sum(v * v for v in q).sqrt()
    return [v / norm for v in q]


def rational_mix(a, b, fraction):
    return [
        Fraction(x) * (1 - fraction) + Fraction(y) * fraction for x, y in zip(a, b, strict=True)
    ]


def test_fixture_is_contract_only_and_contains_no_original_pose_data():
    assert DATA["schema"] == "heather-turns-native-v1"
    assert DATA["status"] == "specified_not_integrated"
    assert DATA["provenance"] == "authored_synthetic_no_game_assets"
    assert DATA["atomicity"]["runtime_verified"] is False
    assert DATA["profile"] == {
        "id": 2,
        "name": "heather-original-pal-525-turns-v1",
        "model_resource": 522,
        "animation_resource": 525,
        "sample_count": 78,
    }
    assert len(NEW_ARCS) == 4
    assert len({r["id"] for r in DATA["errors"]}) == len(DATA["errors"])
    assert DATA["channels"] == LEGACY["channels"]
    assert DATA["clips"][:3] == LEGACY["clips"]


@pytest.mark.parametrize("clip", DATA["clips"], ids=lambda c: str(c["id"]))
def test_descriptor_bytes_and_existing_indices_remain_fixed(clip):
    fields = [clip[k] for k in ("id", "count", "speed", "start", "end", "loop", "trailing")]
    raw = bytes.fromhex(clip["wire_hex"])
    assert struct.unpack("<HHhHHBBII", raw) == (*fields, clip["packed_first"], 0)
    assert len(raw) == 20
    assert clip["increment"] == clip["speed"] * 2
    assert clip["period"] == clip["count"] * 4096
    assert clip["count"] == clip["end"] - clip["start"] + 1
    if clip["id"] in (107, 108):
        assert clip["speed"] == 1152  # PAL already applied, never rescale again.
        assert clip["increment"] != 1152 * 60 // 50 * 2


def test_packing_appends_twenty_samples_and_each_clip_wraps_locally():
    ranges = [
        list(range(c["packed_first"], c["packed_first"] + c["count"])) for c in CLIPS.values()
    ]
    assert IDS == (101, 109, 113, 107, 108)
    assert list(itertools.chain.from_iterable(ranges)) == list(range(78))
    assert [CLIPS[i]["packed_first"] for i in (107, 108)] == [58, 68]
    assert all((r[-1] + 1) % 78 != r[0] for r in ranges)


@pytest.mark.parametrize("row", DATA["clock"], ids=lambda r: r["id"])
def test_phase_and_wrap_by_exact_rational_arithmetic(row):
    c = CLIPS[row["clip"]]
    frame, fraction = divmod(Fraction(row["counter"], 4096), 1)
    indices = [int(frame), (int(frame) + 1) % c["count"]]
    assert row["pose_phase"] == row["counter"]
    assert row["counter_out"] == (row["counter"] + c["increment"]) % c["period"]
    assert row["fraction"] == fraction * 4096
    assert row["frames"] == [c["start"] + i for i in indices]
    assert row["packed_frames"] == [c["packed_first"] + i for i in indices]
    assert row["counter_out"] != row["pose_phase"]


@pytest.mark.parametrize("row", DATA["cycles"], ids=lambda r: str(r["clip"]))
def test_cycle_covers_full_period_and_both_wraps(row):
    assert len(row["rows"]) == 19
    assert row["interval_advance"] == (len(row["rows"]) - 1) * 2304 == 41472
    assert row["interval_advance"] - 2304 < row["period"] <= row["interval_advance"]
    assert row["rows"] == [[i * 2304 % 40960, (i + 1) * 2304 % 40960] for i in range(19)]
    assert row["rows"][-2:] == [[39168, 512], [512, 2816]]
    assert {phase // 4096 for phase, _ in row["rows"]} == set(range(10))


@pytest.mark.parametrize("arc", DATA["arcs"], ids=lambda a: f"{a['source']}-{a['target']}")
def test_frozen_transition_schedule_and_completion(arc):
    entry = arc["source"] == 101
    beta = [768 * i for i in range(1, 6)] if entry else [1024 + 410 * i for i in range(8)]
    assert arc["blends"] == beta
    assert (arc["first"], arc["delta"]) == ((768, 768) if entry else (1024, 410))
    assert arc["exit_sum"] == beta[-1] + arc["delta"] >= 4096
    assert arc["exit_counter"] == CLIPS[arc["target"]]["increment"]
    assert arc["exit_counter"] != 2 * CLIPS[arc["target"]]["increment"]
    assert arc["frozen_counter"] == 0 and arc["exit_cache_valid"] is False
    phase = (arc["initial_counter"] - CLIPS[arc["source"]]["increment"]) % 40960
    assert arc["source_pose_phase"] == phase
    assert arc["source_fraction"] == phase % 4096 != 0
    assert arc["source_cache"] == "last_local"
    if not entry:
        assert arc["delta"] == (512 - 307) * 2
        assert beta != LEGACY["mode3_sequences"][1]["blends"]


@pytest.mark.parametrize("row", DATA["direct"], ids=lambda r: f"{r['source']}-{r['target']}")
def test_complete_direct_arc_matrix_including_rejections(row):
    a, b = row["source"], row["target"]
    if a == b:
        expected = "same"
    elif (a, b) not in EDGES:
        expected = "unsupported_transition"
    else:
        expected = "phase_blend" if {a, b} == {109, 113} else "cached"
    assert row["result"] == expected


def test_matrix_exhaustiveness_and_observed_edge_count():
    assert {(r["source"], r["target"]) for r in DATA["direct"]} == set(
        itertools.product(IDS, repeat=2)
    )
    assert len(EDGES) == 9
    assert sum(r["result"] == "unsupported_transition" for r in DATA["direct"]) == 11


@pytest.mark.parametrize(
    "row", DATA["inputs"], ids=lambda r: "".join(str(int(x)) for x in r["bits"])
)
def test_input_priority_and_independent_world_turn(row):
    forward, backward, left, right, run = row["bits"]
    yaw = int(right) - int(left)
    moving = forward and not backward
    assert row["yaw_sign"] == yaw
    desired = (113 if run else 109) if moving else {0: 101, 1: 107, -1: 108}[yaw]
    assert row["desired"] == desired
    assert row["motion"] == ("run" if desired == 113 else "walk" if desired == 109 else "idle")


def test_controls_and_route_vectors_are_exhaustive():
    assert len(DATA["inputs"]) == 32
    assert {tuple(row["bits"]) for row in DATA["inputs"]} == set(
        itertools.product((False, True), repeat=5)
    )
    assert len(DATA["routes"]) == 25
    assert {(row["current"], row["desired"]) for row in DATA["routes"]} == set(
        itertools.product(IDS, repeat=2)
    )


@pytest.mark.parametrize("row", DATA["routes"], ids=lambda r: f"{r['current']}-{r['desired']}")
def test_native_bridge_is_shortest_supported_path(row):
    assert row["hops"] == shortest_path(row["current"], row["desired"])
    assert len(row["hops"]) <= 3
    nodes = [row["current"], *row["hops"]]
    assert all((a, b) in EDGES for a, b in zip(nodes[:-1], nodes[1:], strict=True))
    assert nodes[-1] == row["desired"]


@pytest.mark.parametrize("replay", DATA["replays"], ids=lambda r: r["id"])
def test_latest_goal_replay_never_interrupts_or_queues_obsolete_goals(replay):
    source, target, mode, counter, beta, cached = replay["initial"]
    assert not cached
    for row in replay["rows"]:
        (
            desired,
            world_turn,
            requested,
            out_source,
            out_target,
            out_mode,
            out_counter,
            out_beta,
            pending,
        ) = row
        path = shortest_path(target, desired)
        assert requested == (target if mode != 1 or not path else path[0])
        assert pending == (None if desired == out_target else desired)
        if requested != target:
            assert mode == 1 and (target, requested) in NEW_ARCS
            arc = NEW_ARCS[target, requested]
            assert (out_source, out_target, out_mode, out_counter, out_beta) == (
                target,
                requested,
                3,
                0,
                arc["first"],
            )
        elif mode == 3:
            arc = NEW_ARCS[source, target]
            if beta == arc["blends"][-1]:
                assert (out_source, out_target, out_mode, out_counter, out_beta) == (
                    target,
                    target,
                    1,
                    arc["exit_counter"],
                    0,
                )
            else:
                assert (out_source, out_target, out_mode, out_counter, out_beta) == (
                    source,
                    target,
                    3,
                    0,
                    beta + arc["delta"],
                )
        else:
            assert out_counter == (counter + CLIPS[target]["increment"]) % CLIPS[target]["period"]
        assert world_turn in (-1, 0, 1)  # Applied immediately, not derived from latched clip.
        source, target, mode, counter, beta = (
            out_source,
            out_target,
            out_mode,
            out_counter,
            out_beta,
        )
    if replay["id"] == "reverse-during-entry":
        assert replay["rows"][1][1] == -1 and replay["rows"][1][4] == 107
        assert target == 108
    else:
        assert [r[-1] for r in replay["rows"][:6]] == [None, 113, 108, None, 101, 101]
        assert 113 not in [r[4] for r in replay["rows"]]  # Canceled request is never replayed.
        assert target == 101


@pytest.mark.parametrize("v", DATA["poses"], ids=lambda r: r["id"])
def test_cached_local_pose_with_decimal_and_rational_oracles(v):
    with localcontext() as context:
        context.prec = 60
        cached = decimal_nlerp(*v["source_quaternions"], Decimal(v["source_fraction"]) / 4096)
        cached_translation = rational_mix(
            *v["source_translations"], Fraction(v["source_fraction"], 4096)
        )
        assert [float(x) for x in cached] == pytest.approx(v["saved_quaternion"], abs=1e-12, rel=0)
        mutated_cache = cached
        for row in v["rows"]:
            beta = Decimal(row["beta"]) / 4096
            actual = decimal_nlerp(cached, v["target_quaternion"], beta)
            assert [float(x) for x in actual] == pytest.approx(row["quaternion"], abs=1e-12, rel=0)
            assert abs(sum(x * x for x in actual) - 1) < Decimal("1e-50")
            expected_translation = [Fraction(n, d) for n, d in row["translation"]]
            assert (
                rational_mix(
                    cached_translation, v["target_translation"], Fraction(row["beta"], 4096)
                )
                == expected_translation
            )
            wrong_frame = decimal_nlerp(v["source_quaternions"][0], v["target_quaternion"], beta)
            assert max(abs(a - b) for a, b in zip(actual, wrong_frame, strict=True)) > Decimal(
                "0.001"
            )
            mutated_cache = decimal_nlerp(mutated_cache, v["target_quaternion"], beta)
        assert max(abs(a - b) for a, b in zip(actual, mutated_cache, strict=True)) > Decimal(
            "0.001"
        )


def test_antipodal_hemisphere_and_root_applied_once_after_two_channels():
    h = DATA["hemisphere"]
    for beta in h["betas"]:
        assert decimal_nlerp(h["a"], h["b"], Decimal(beta) / 4096) == h["expected"]
    v = DATA["hierarchy"]
    z, w = (Fraction(str(v["parent_rotation"][i])) for i in (2, 3))
    cosine, sine = 1 - 2 * z * z, 2 * z * w
    x, y, height = v["child_translation"]
    px, py, pz = v["parent_translation"]
    model = [px + cosine * x - sine * y, py + sine * x + cosine * y, pz + height]
    assert model == [Fraction(str(x)) for x in v["model_child_translation"]]
    wx, wy, wz = v["world_translation"]
    assert [wx + model[2], wy + model[1], wz - model[0]] == [
        Fraction(str(x)) for x in v["world_child_translation"]
    ]
    assert v["channel_owners"] == [2, 1]  # Parent may be published after child reads.


def scalar_error(row):
    """Declarative membership/precedence oracle; does not implement pose staging."""
    profile, s = row["profile"], row["state"]
    if profile not in (1, 2):
        return "invalid_profile"
    known = (101, 109, 113) if profile == 1 else IDS
    a, b = s["source_id"], s["target_id"]
    valid = s["profile_id"] == profile and a in known and b in known
    valid = valid and 0 <= s["counter"] < CLIPS[b]["period"]
    if s["mode"] == 1:
        valid = valid and a == b and s["blend"] == 0 and not s["saved_local_valid"]
    elif s["mode"] == 3:
        schedules = {(x["source"], x["target"]): x["blends"] for x in LEGACY["mode3_sequences"]}
        if profile == 2:
            schedules.update({key: a["blends"] for key, a in NEW_ARCS.items()})
        valid = (
            valid
            and s["counter"] == 0
            and s["saved_local_valid"]
            and s["blend"] in schedules.get((a, b), [])
        )
    elif s["mode"] == 5:
        valid = (
            valid
            and {a, b} == {109, 113}
            and not s["saved_local_valid"]
            and s["blend"] in range(384, 4096, 384)
        )
    else:
        valid = False
    if not valid:
        return "invalid_state"
    if row["ticks"] != 2:
        return "invalid_ticks"
    request = row["request"]
    if request is not None and request not in known:
        return "unknown_clip"
    if request not in (None, b):
        if s["mode"] != 1:
            return "transition_busy"
        if (b, request) not in EDGES:
            return "unsupported_transition"
    faults = row["read_fault"] or []
    return next((e for e in ("sample_unavailable", "invalid_pose") if e in faults), "ok")


@pytest.mark.parametrize("row", DATA["errors"], ids=lambda r: r["id"])
def test_error_literals_and_precedence(row):
    assert scalar_error(row) == row["expected"]
    assert row["publish"] is False


def test_transport_lengths_and_memory_without_loading_a_runtime():
    w = DATA["wire"]
    b, f, h, v, i, m = w["counts_b_f_h_v_i_m"]
    size = 16 + 8 * b + 20 * 5 + 28 * b * f + 68 * h + 28 * v + 2 * i + 28 * m
    assert size == w["payload_bytes"] == 310260
    assert w["file_bytes"] == size + 96 == w["legacy_bytes"] + 20200
    assert w["delta_bytes"] == 2 * 20 + 20 * 36 * 28
    assert w["storage_sample_bytes"] == w["max_bones"] * w["decoded_capacity"] * 28
    assert w["storage_delta_bytes"] == (80 - 64) * 73 * 28 == 32704
    assert w["selected_sample_bytes"] == 78 * 36 * 28 == 78624
    assert w["clock_workspace_budget"] == 32 * 1024
    assert w["legacy_sri1_limit"] == 64 < f <= w["decoded_capacity"] == 80
    header = struct.pack(
        "<8s22I",
        bytes.fromhex(w["magic_hex"]),
        b,
        f,
        h,
        v,
        i,
        m,
        5,
        2,
        25,
        2,
        522,
        525,
        size,
        0,
        *([0] * 8),
    )
    assert len(header) == 96 and header[:8] == b"S3RIv2\0\0"
    assert struct.unpack_from("<4I", header, 32) == (5, 2, 25, 2)
    assert header[64:] == bytes(32)
    assert struct.unpack_from(">I", header, 44)[0] != 2


@pytest.mark.parametrize("row", DATA["wire"]["acceptance"])
def test_profile_transport_cross_products_are_not_silently_accepted(row):
    assert row["accept"] is (
        (row["profile"], row["clips"], row["frames"]) in ((1, 3, 58), (2, 5, 78))
    )


def test_atomicity_vectors_are_explicit_future_native_obligations():
    v = DATA["atomicity"]
    assert len(bytes.fromhex(v["sentinel_hex"])) == 8
    assert len(set(v["failure_sites"])) == len(v["failure_sites"]) == 19
    assert v["rollback"] == "state_and_output_byte_identical"
    assert v["retry"] == "same_result_as_fresh_success"
    assert v["publication"] == "whole_snapshot_only"
    assert v["runtime_verified"] is False


@pytest.mark.parametrize("row", DATA["selection_ok"], ids=lambda r: r["id"])
def test_same_target_or_empty_request_preserves_continuation(row):
    assert scalar_error(row) == "ok" and row["publish"] is True
    s, expected = row["state"], row["output"]
    source, target, mode = s["source_id"], s["target_id"], s["mode"]
    increment, period = CLIPS[target]["increment"], CLIPS[target]["period"]
    if mode == 1:
        assert expected == [target, target, 1, (s["counter"] + increment) % period, 0, False]
        assert row["pose_phase"] == s["counter"] and row["cache_action"] == "none"
    elif mode == 3:
        arc = NEW_ARCS[source, target]
        exiting = s["blend"] + arc["delta"] >= 4096
        assert expected == [
            target if exiting else source,
            target,
            1 if exiting else 3,
            increment if exiting else 0,
            0 if exiting else s["blend"] + arc["delta"],
            not exiting,
        ]
        assert row["pose_phase"] == 0
        assert row["cache_action"] == ("discard" if exiting else "none")
    else:
        exiting = s["blend"] == 3840
        advances = 2 if exiting else 1
        assert expected == [
            target if exiting else source,
            target,
            1 if exiting else 5,
            (s["counter"] + advances * increment) % period,
            0 if exiting else s["blend"] + 384,
            False,
        ]
        assert row["pose_phase"] == (s["counter"] + (increment if exiting else 0)) % period
        assert row["cache_action"] == "none"


@pytest.mark.parametrize("row", DATA["lifecycle"], ids=lambda r: r["id"])
def test_lifecycle_literals_keep_cached_pose_out_of_wall_clock(row):
    # These are harness requirements for HG-T4, not calls into MovementController.
    manual = row["session"] == "paused" and row["event"] == "advance"
    assert row["steps"] == int(manual)
    assert row["remainder"] == 0
    if row["event"] == "restart":
        assert row["actor"] == "idle_zero_no_ticks"
    else:
        assert row["actor"] == ("one_update" if manual else "unchanged")
    assert row["pending"] == ("latest_goal_after_update" if manual else "cleared")
    assert row["release"] is (row["event"] in {"pause", "resume", "restart", "error", "quit"})
