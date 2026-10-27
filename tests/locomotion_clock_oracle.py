"""Compare the native scalar planner with the literals fixed before implementation.

Test-only process adapter: no imports from production modules or private evidence.
The fixture's mathematical consistency is checked separately by pytest.
"""

import json
import subprocess
import sys
from pathlib import Path


def verify(executable):
    data = json.loads(
        (Path(__file__).parent / "fixtures/synthetic/heather-locomotion-v1.json").read_text()
    )
    clips = {c["id"]: c for c in data["clips"]}
    inputs, expected, labels = [], [], []

    def window(clip_id, phase):
        clip = clips[clip_id]
        frame, _ = divmod(phase, 4096)
        following = (frame + 1) % clip["count"]
        return [
            clip_id,
            frame,
            following,
            clip["start"] + frame,
            clip["start"] + following,
            clip["packed_first"] + frame,
            clip["packed_first"] + following,
        ]

    def case(label, before, request, *, source, target, mode, phase, counter, blend, cache=0):
        # before: source, target, mode, next phase, blend, cache validity.
        inputs.append([*before, 0 if request is None else request, int(request is not None), 2])
        expected.append(
            [
                0,
                source,
                target,
                mode,
                counter,
                blend,
                int(mode == 3),
                {1: 0, 3: 2, 5: 1}[mode],
                cache,
                phase,
                phase % 4096,
                blend,
                *(window(source, phase) if mode == 5 else [0] * 7),
                *window(target, phase),
            ]
        )
        labels.append(label)

    for row in data["clock"]:
        kind, source, target = row["kind"], row["source"], row["target"]
        request, cache = None, 0
        if kind == "stable":
            before = [source, target, 1, row["counter"], 0, 0]
            mode, blend = 1, 0
        elif kind == "mode5":
            mode, blend = 5, row["blend"]
            if blend == 384:
                before = [source, source, 1, row["counter"], 0, 0]
                request = target
            else:
                before = [source, target, 5, row["counter"], blend - 384, 0]
        elif kind == "mode3":
            # A nonzero source phase must be reset, not carried into the destination.
            before = [source, source, 1, 12345, 0, 0]
            request, cache, mode, blend = target, 1, 3, row["blend"]
        else:
            old_mode = {"mode3_exit": 3, "mode5_exit": 5}[kind]
            before = [source, target, old_mode, row["counter"], row["blend"], int(old_mode == 3)]
            mode, blend, cache = 1, 0, 2 if old_mode == 3 else 0
            source = target
        case(
            row["id"],
            before,
            request,
            source=source,
            target=target,
            mode=mode,
            phase=row["pose_phase"],
            counter=row["counter_out"],
            blend=blend,
            cache=cache,
        )
        # Check fixture index literals as well, not only the phase-derived mapping.
        if expected[-1][22:26] != [*row["frames"], *row["packed_frames"]]:
            raise AssertionError(f"Inconsistent frame literal: {row['id']}")
        if "source_frames" in row and expected[-1][15:17] != row["source_frames"]:
            raise AssertionError(f"Inconsistent source frame literal: {row['id']}")

    for trace in data["mode5_sequences"]:
        source, target = trace["source"], trace["target"]
        before = [source, source, 1, trace["initial_counter"], 0, 0]
        for ordinal, (blend, phase, counter) in enumerate(trace["rows_blend_pose_counter"]):
            mode = 5 if blend else 1
            case(
                f"mode5-{source}-{target}-{ordinal}",
                before,
                target if ordinal == 0 else None,
                source=source if blend else target,
                target=target,
                mode=mode,
                phase=phase,
                counter=counter,
                blend=blend,
            )
            before = [source if blend else target, target, mode, counter, blend, 0]

    for trace in data["mode3_sequences"]:
        source, target = trace["source"], trace["target"]
        before = [source, source, 1, 12345, 0, 0]
        for ordinal, blend in enumerate(trace["blends"]):
            case(
                f"mode3-{source}-{target}-{ordinal}",
                before,
                target if ordinal == 0 else None,
                source=source,
                target=target,
                mode=3,
                phase=0,
                counter=0,
                blend=blend,
                cache=int(ordinal == 0),
            )
            before = [source, target, 3, 0, blend, 1]
        case(
            f"mode3-{source}-{target}-exit",
            before,
            None,
            source=target,
            target=target,
            mode=1,
            phase=0,
            counter=trace["exit_counter"],
            blend=0,
            cache=2,
        )

    for loop in data["full_loops"]:
        clip_id = loop["clip"]
        clip = clips[clip_id]
        for ordinal in range(loop["updates"]):
            phase = ordinal * clip["increment"] % clip["period"]
            counter = (ordinal + 1) * clip["increment"] % clip["period"]
            case(
                f"loop-{clip_id}-{ordinal}",
                [clip_id, clip_id, 1, phase, 0, 0],
                None,
                source=clip_id,
                target=clip_id,
                mode=1,
                phase=phase,
                counter=counter,
                blend=0,
            )
        if expected[-1][4] != loop["counter_out"]:
            raise AssertionError("Loop endpoint disagrees with literal")

    completed = subprocess.run(
        [executable, "vectors"],
        input="\n".join(" ".join(map(str, row)) for row in inputs) + "\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    actual = [list(map(int, line.split())) for line in completed.stdout.splitlines()]
    if len(actual) != len(expected):
        raise AssertionError(f"Missing/extra native results: {len(actual)} != {len(expected)}")
    for label, native, literal in zip(labels, actual, expected, strict=True):
        if native != literal:
            raise AssertionError(f"{label}: native {native} != expected {literal}")
    print(f"Native locomotion planner: {len(expected)} updates match the contract")


if __name__ == "__main__":
    verify(sys.argv[1])
