"""Independent complete-transaction trace, including rejected requests and recovery.

Uses the pre-existing descriptor/beta fixture and test-only Decimal NLERP.
Matrices are derived through quaternion multiplication of basis vectors,
not the native evaluator's matrix coefficient formulas. Samples are invented.
"""

import copy
import json
import math
import struct
import subprocess
import sys
from decimal import Decimal, localcontext
from pathlib import Path

from locomotion_pose_oracle import mix


def transform(clip, frame, bone):
    slot = {101: 0, 109: 1, 113: 2}[clip]
    rotations = ([0, 0, 0, 1], [0.6, 0, 0, 0.8], [0, 0.8, 0, 0.6], [0, 0, -1, 0])
    values = [
        slot + frame / 16 + bone / 8,
        slot / 4 - frame / 32,
        bone / 16 - frame / 64,
        *rotations[(frame + bone + slot) % 4],
    ]
    # The immutable source presents f32 samples, just like the native test double.
    return [Decimal(str(struct.unpack("<f", struct.pack("<f", v))[0])) for v in values]


def multiply(a, b):
    # Quaternion product in WXYZ order, independent of the renderer's column matrix formula.
    w, x, y, z = a
    r, s, t, u = b
    return [
        w * r - x * s - y * t - z * u,
        w * s + x * r + y * u - z * t,
        w * t - x * u + y * r + z * s,
        w * u + x * t - y * s + z * r,
    ]


def matrices(local):
    with localcontext() as context:
        context.prec = 60
        model = []
        for bone, pose in enumerate(local):
            q = [pose[6], *pose[3:6]]
            conjugate = [q[0], *[-v for v in q[1:]]]
            axes = []
            for index in range(3):
                basis = [Decimal(0)] * 4
                basis[index + 1] = Decimal(1)
                axes.append(multiply(multiply(q, basis), conjugate)[1:])
            rows = [[axes[c][r] for c in range(3)] + [pose[r]] for r in range(3)]
            rows.append([Decimal(0), Decimal(0), Decimal(0), Decimal(1)])
            if bone:
                parent = model[bone - 1]
                rows = [
                    [sum(parent[r][k] * rows[k][c] for k in range(4)) for c in range(4)]
                    for r in range(4)
                ]
            model.append(rows)
        return [[m[r][c] for c in range(4) for r in range(4)] for m in model]


def verify(executable):
    data = json.loads(
        (Path(__file__).parent / "fixtures/synthetic/heather-locomotion-v1.json").read_text()
    )
    clips = {c["id"]: c for c in data["clips"]}
    inputs, expected, labels = [], [], []
    clock = [101, 101, 1, 0, 0, 0]
    local = [mix(transform(101, 0, b), transform(101, 0, b), 0) for b in range(2)]
    saved = [[Decimal(0)] * 7 for _ in range(2)]

    def emit(label, request=None, ticks=2, error=0, initial=False):
        if not initial:
            inputs.append(f"{request or 0} {int(request is not None)} {ticks}")
        row = [error, *clock]
        for t, s, m in zip(local, saved, matrices(local), strict=True):
            row.extend([*t, *s, *m])
        expected.append(row)
        labels.append(label)

    def sample_pair(clip, phase, bone):
        frame, fraction = divmod(phase, 4096)
        return (
            transform(clip, frame, bone),
            transform(clip, (frame + 1) % clips[clip]["count"], bone),
            fraction,
        )

    def stable(count):
        nonlocal clock, local
        clip, base = clock[1], clock[3]
        descriptor = clips[clip]
        for ordinal in range(count):
            phase = (base + ordinal * descriptor["increment"]) % descriptor["period"]
            local = [mix(*sample_pair(clip, phase, b)) for b in range(2)]
            clock = [clip, clip, 1, (phase + descriptor["increment"]) % descriptor["period"], 0, 0]
            emit(f"stable-{clip}-{ordinal}")

    def errors_during_blend(source):
        emit("unknown-before-busy", request=0, error=4)
        emit("busy", request=source, error=5)
        emit("ticks-before-unknown", request=0, ticks=1, error=3)

    def cached_transition(target):
        nonlocal clock, local, saved
        source = clock[1]
        trace = next(
            t for t in data["mode3_sequences"] if t["source"] == source and t["target"] == target
        )
        saved = copy.deepcopy(local)
        for ordinal, blend in enumerate(trace["blends"]):
            local = [mix(s, transform(target, 0, b), blend) for b, s in enumerate(saved)]
            clock = [source, target, 3, 0, blend, 1]
            emit(f"cached-{source}-{target}-{blend}", request=target)
            if ordinal == 0:
                errors_during_blend(source)
        local = [mix(transform(target, 0, b), transform(target, 0, b), 0) for b in range(2)]
        clock = [target, target, 1, trace["exit_counter"], 0, 0]
        emit(f"cached-exit-{target}")

    def phase_transition(target):
        nonlocal clock, local
        source, base = clock[1], clock[3]
        descriptor = clips[target]
        for ordinal in range(1, 12):
            # Independent distance formula: ten ordinary advances, then one before the exit pose.
            advance = ordinal - 1 if ordinal <= 10 else 11
            phase = (base + advance * descriptor["increment"]) % descriptor["period"]
            blend = ordinal * 384 if ordinal <= 10 else 0
            local = []
            for bone in range(2):
                target_a, target_b, fraction = sample_pair(target, phase, bone)
                if blend:
                    source_a, source_b, _ = sample_pair(source, phase, bone)
                    local.append(
                        mix(
                            mix(source_a, target_a, blend), mix(source_b, target_b, blend), fraction
                        )
                    )
                else:
                    local.append(mix(target_a, target_b, fraction))
            clock = [
                source if blend else target,
                target,
                5 if blend else 1,
                (phase + descriptor["increment"]) % descriptor["period"],
                blend,
                0,
            ]
            emit(f"phase-{source}-{target}-{ordinal}", request=target)
            if ordinal == 1:
                errors_during_blend(source)

    emit("initialize", initial=True)
    emit("idle-run-unsupported", request=113, error=6)
    emit("unknown-zero", request=0, error=4)
    emit("invalid-ticks", ticks=0, error=3)
    stable(67)
    for target in (109, 113, 109, 101, 109, 113, 101):
        if 101 in (clock[1], target):
            cached_transition(target)
        else:
            phase_transition(target)
        stable(next(t["updates"] for t in data["full_loops"] if t["clip"] == target))

    completed = subprocess.run(
        [executable, "vectors"],
        input="\n".join(inputs) + "\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    actual = [list(map(float, line.split())) for line in completed.stdout.splitlines()]
    if len(actual) != len(expected):
        raise AssertionError("Missing/extra published snapshots")
    max_local = max_model = 0
    for index, (native, reference, label) in enumerate(zip(actual, expected, labels, strict=True)):
        if len(native) != 67 or native[:7] != reference[:7]:
            raise AssertionError(f"{label}: clock/error mismatch {native[:7]} != {reference[:7]}")
        if native[0] and native[1:] != actual[index - 1][1:]:
            raise AssertionError(f"{label}: error published a partial snapshot")
        for bone in range(2):
            offset = 7 + bone * 30
            for field in range(30):
                delta = abs(native[offset + field] - float(reference[offset + field]))
                matrix = field >= 14
                tolerance = 4e-6 if matrix else 1e-6
                if not math.isfinite(delta) or delta > tolerance:
                    raise AssertionError(f"{label}, bone {bone}, field {field}: difference {delta}")
                if matrix:
                    max_model = max(max_model, delta)
                else:
                    max_local = max(max_local, delta)
    print(
        f"Native transaction: {len(expected)} complete snapshots; all five edges and recovery match"
    )
    print(f"Maximum local difference {max_local:.9g}; model difference {max_model:.9g}")


if __name__ == "__main__":
    verify(sys.argv[1])
