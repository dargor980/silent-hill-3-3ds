"""Run the frozen HG-T3 vectors through C++ clocks, poses and transactions.

No production Python imports or private assets. Expected poses are literals;
hierarchy composition reuses the independent HL quaternion-basis oracle.
Input routing, contacts, SRI2 and lifecycle belong to later HG-T4 units.
"""

import json
import math
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from locomotion_update_oracle import matrices


def verify(executable):
    fixture_dir = Path(__file__).parent / "fixtures/synthetic"
    data = json.loads((fixture_dir / "heather-turns-native-v1.json").read_text())
    legacy = json.loads((fixture_dir / "heather-locomotion-v1.json").read_text())
    clips = {c["id"]: c for c in data["clips"]}
    arcs = {(a["source"], a["target"]): a for a in data["arcs"]}
    rates = {k: a["first"] for k, a in arcs.items()}
    rates.update({(a["source"], a["target"]): a["blends"][0] for a in legacy["mode3_sequences"]})
    errors = dict(
        zip(
            (
                "ok",
                "invalid_profile",
                "invalid_state",
                "invalid_ticks",
                "unknown_clip",
                "transition_busy",
                "unsupported_transition",
                "sample_unavailable",
                "invalid_pose",
            ),
            range(9),
            strict=True,
        )
    )
    commands, expected, labels = [], [], []

    def window(clip_id, phase):
        c = clips[clip_id]
        j = phase // 4096
        k = (j + 1) % c["count"]
        return [
            clip_id,
            j,
            k,
            c["start"] + j,
            c["start"] + k,
            c["packed_first"] + j,
            c["packed_first"] + k,
        ]

    def emit(command, result, label):
        commands.append(command)
        expected.append(result)
        labels.append(label)

    def request_line(kind, before, request, profile=2, ticks=2):
        # before: profile, source, target, mode, counter, beta, cache_valid.
        return " ".join(
            map(
                str,
                [kind, profile, *map(int, before), request or 0, int(request is not None), ticks],
            )
        )

    def case(label, before, request, after, phase, cache=0):
        pid, source, target, mode, _, beta, _ = after
        result = [
            0,
            *after,
            {1: 0, 3: 2, 5: 1}[mode],
            cache,
            phase,
            phase % 4096,
            beta,
            *(window(source, phase) if mode == 5 else [0] * 7),
            *window(target, phase),
        ]
        emit(request_line("C", before, request, pid), result, label)

    for row in data["clock"]:
        c, phase = row["clip"], row["counter"]
        if window(c, phase)[3:] != [*row["frames"], *row["packed_frames"]]:
            raise AssertionError("Phase fixture index mismatch")
        case(
            row["id"],
            [2, c, c, 1, phase, 0, 0],
            None,
            [2, c, c, 1, row["counter_out"], 0, 0],
            row["pose_phase"],
        )
    for cycle in data["cycles"]:
        c = cycle["clip"]
        for i, (phase, counter) in enumerate(cycle["rows"]):
            case(
                f"cycle-{c}-{i}",
                [2, c, c, 1, phase, 0, 0],
                None,
                [2, c, c, 1, counter, 0, 0],
                phase,
            )
    for (source, target), arc in arcs.items():
        before = [2, source, source, 1, arc["initial_counter"], 0, 0]
        for i, beta in enumerate(arc["blends"]):
            after = [2, source, target, 3, 0, beta, 1]
            case(
                f"arc-{source}-{target}-{beta}",
                before,
                target if i == 0 else None,
                after,
                0,
                int(i == 0),
            )
            before = after
        case(
            f"exit-{source}-{target}",
            before,
            None,
            [2, target, target, 1, arc["exit_counter"], 0, 0],
            0,
            2,
        )
    for row in data["direct"]:
        a, b, result = row["source"], row["target"], row["result"]
        before = [2, a, a, 1, 0, 0, 0]
        label = f"direct-{a}-{b}"
        if result == "unsupported_transition":
            emit(request_line("C", before, b), [errors[result]], label)
        elif result == "same":
            case(label, before, b, [2, b, b, 1, clips[b]["increment"], 0, 0], 0)
        elif result == "cached":
            case(label, before, b, [2, a, b, 3, 0, rates[a, b], 1], 0, 1)
        else:
            case(label, before, b, [2, a, b, 5, clips[b]["increment"], 384, 0], 0)

    def clock_fields(s):
        return [
            s[k]
            for k in (
                "profile_id",
                "source_id",
                "target_id",
                "mode",
                "counter",
                "blend",
                "saved_local_valid",
            )
        ]

    for row in data["selection_ok"]:
        after = [row["profile"], *map(int, row["output"])]
        case(
            row["id"],
            clock_fields(row["state"]),
            row["request"],
            after,
            row["pose_phase"],
            2 if row["cache_action"] == "discard" else 0,
        )
        emit(
            request_line("U", clock_fields(row["state"]), row["request"])
            + " 4294967295 4294967295",
            [0, *after],
            f"transaction-{row['id']}",
        )
    for row in data["errors"]:
        before, error = clock_fields(row["state"]), errors[row["expected"]]
        if not row["read_fault"]:
            emit(
                request_line("C", before, row["request"], row["profile"], row["ticks"]),
                [error],
                f"plan-error-{row['id']}",
            )
        faults = row["read_fault"] or []
        invalid = 0 if "invalid_pose" in faults else 4294967295
        missing = (1 if invalid == 0 else 0) if "sample_unavailable" in faults else 4294967295
        emit(
            request_line("U", before, row["request"], row["profile"], row["ticks"])
            + f" {invalid} {missing}",
            [error],
            f"update-error-{row['id']}",
        )
    # Execute the requested animation steps as persistent native state, not independent resets.
    for replay in data["replays"]:
        commands.append(
            "R " + str(len(replay["rows"])) + " " + " ".join(str(r[2]) for r in replay["rows"])
        )
        for i, row in enumerate(replay["rows"]):
            expected.append([0, 2, *row[3:8], int(row[5] == 3)])
            labels.append(f"replay-{replay['id']}-{i}")

    def pose_case(v, arc, label):
        source, target = arc["source"], arc["target"]
        values = ["P", source, target, arc["source_pose_phase"]]
        for t, q in zip(v["source_translations"], v["source_quaternions"], strict=True):
            values.extend([*t, *q])
        values.extend([*v["target_translation"], *v["target_quaternion"]])
        commands.append(" ".join(map(str, values)))
        f = Fraction(v["source_fraction"], 4096)
        saved = [
            float(Fraction(a) * (1 - f) + Fraction(b) * f)
            for a, b in zip(*v["source_translations"], strict=True)
        ] + v["saved_quaternion"]
        rows = [
            ([float(Fraction(n, d)) for n, d in r["translation"]] + r["quaternion"], r["beta"])
            for r in v["rows"]
        ]
        rows.append(([*v["target_translation"], *v["target_quaternion"]], 0))
        for local, beta in rows:
            clock = [
                0,
                2,
                source if beta else target,
                target,
                3 if beta else 1,
                0 if beta else arc["exit_counter"],
                beta,
                int(bool(beta)),
            ]
            poses = [[Decimal(str(x)) for x in local], list(map(Decimal, [5, -3, 2, 0, 0, 0, 1]))]
            expected.append([*clock, *local, *saved, *matrices(poses)[0], *matrices(poses)[1]])
            labels.append(f"pose-{label}-{beta}")

    for v in data["poses"]:
        source, target = map(int, v["id"].split("-"))
        pose_case(v, arcs[source, target], v["id"])
    # Antipodal literals exercise the actual NLERP at 768, 1024 and 3894 among other weights.
    for edge in ((101, 107), (107, 101)):
        arc = arcs[edge] | {"source_pose_phase": 0}
        v = {
            "source_quaternions": [data["hemisphere"]["a"]] * 2,
            "source_translations": [[0, 0, 0]] * 2,
            "source_fraction": 0,
            "saved_quaternion": data["hemisphere"]["a"],
            "target_translation": [0, 0, 0],
            "target_quaternion": data["hemisphere"]["b"],
            "rows": [
                {
                    "beta": b,
                    "quaternion": data["hemisphere"]["expected"],
                    "translation": [[0, 1]] * 3,
                }
                for b in arc["blends"]
            ],
        }
        pose_case(v, arc, f"hemisphere-{edge}")

    completed = subprocess.run(
        [executable, "vectors"],
        input="\n".join(commands) + "\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=25,
    )
    actual = [list(map(float, line.split())) for line in completed.stdout.splitlines()]
    if len(actual) != len(expected):
        raise AssertionError(f"Missing/extra native results: {len(actual)} != {len(expected)}")
    max_local = max_model = 0
    for label, native, reference in zip(labels, actual, expected, strict=True):
        if len(native) != len(reference):
            raise AssertionError(f"{label}: field count mismatch")
        for i, (a, b) in enumerate(zip(native, reference, strict=True)):
            pose_field = label.startswith("pose-") and i >= 8
            tolerance = (1e-6 if i < 22 else 4e-6) if pose_field else 0
            delta = abs(a - float(b))
            if not math.isfinite(delta) or delta > tolerance:
                raise AssertionError(f"{label}, field {i}: {a} != {b}, difference {delta}")
            if pose_field:
                if i < 22:
                    max_local = max(max_local, delta)
                else:
                    max_model = max(max_model, delta)
    print(f"HG native: {len(expected)} results match frozen clock/pose/error/replay vectors")
    print(f"Maximum local difference {max_local:.9g}; model difference {max_model:.9g}")


if __name__ == "__main__":
    verify(sys.argv[1])
