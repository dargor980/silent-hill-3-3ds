"""Native local poses vs pre-existing literals and independent Decimal arithmetic.

Only invented transforms cross the process boundary. No production Python,
private resources or native evaluator formulas are imported.
"""

import json
import math
import subprocess
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


def mix(a, b, q12):
    with localcontext() as context:
        context.prec = 60
        a, b = [[Decimal(str(v)) for v in t] for t in (a, b)]
        f = Decimal(q12) / 4096
        sign = -1 if sum(x * y for x, y in zip(a[3:], b[3:], strict=True)) < 0 else 1
        rotation = [(1 - f) * x + f * sign * y for x, y in zip(a[3:], b[3:], strict=True)]
        length = sum(v * v for v in rotation).sqrt()
        return [
            *[(1 - f) * x + f * y for x, y in zip(a[:3], b[:3], strict=True)],
            *[v / length for v in rotation],
        ]


def close(actual, expected, *, tolerance=1e-6):
    if len(actual) != len(expected) or any(
        not math.isfinite(x) or abs(x - float(y)) > tolerance
        for x, y in zip(actual, expected, strict=True)
    ):
        raise AssertionError(f"native {actual} != expected {expected}")


def verify(executable):
    data = json.loads(
        (Path(__file__).parent / "fixtures/synthetic/heather-locomotion-v1.json").read_text()
    )
    identity = [0, 0, 0, 0, 0, 0, 1]
    clips = {row["id"]: row for row in data["clips"]}
    cases = []

    def scenario(name, clock, requests, bones=1):
        case = {
            "name": name,
            "clock": clock,
            "requests": requests,
            "bones": bones,
            "parents": [-1] + [0] * (bones - 1),
            "owners": [1, 2][:bones],
            "samples": [[identity[:] for _ in range(bones)] for _ in range(58)],
        }
        cases.append(case)
        return case

    def assign(case, clip, frame, transform, bone=0):
        case["samples"][clips[clip]["packed_first"] + frame][bone] = transform

    v = data["pose"]["mode5_order"]
    ordered = scenario("mode5-order", [109, 113, 5, v["fraction"], v["blend"] - 384], [None])
    for clip, prefix in ((109, "source"), (113, "target")):
        for i in range(2):
            assign(
                ordered, clip, i, [*v[f"{prefix}_translations"][i], *v[f"{prefix}_quaternions"][i]]
            )

    v = data["pose"]["cached_stop"]
    stopped = scenario(
        "cached-stop", [109, 109, 1, v["source_fraction"], 0], [None, 101] + [None] * 8
    )
    for i in range(2):
        assign(stopped, 109, i, [*v["source_translations"][i], *v["source_quaternions"][i]])
    assign(stopped, 101, 0, [*v["target_translation"], *v["target_quaternion"]])

    v = data["pose"]["hemisphere"]
    antipodal = scenario("antipodal", [101, 101, 1, v["blend"], 0], [None])
    assign(antipodal, 101, 0, [0, 0, 0, *v["first"]])
    assign(antipodal, 101, 1, [0, 0, 0, *v["second"]])

    v = data["pose"]["channels"]
    channels = scenario("channels", [101, 101, 1, 0, 0], [], 2)
    channels["parents"], channels["owners"] = v["parents"], v["owners"]
    for bone in range(2):
        assign(channels, 101, 0, [*v["translations"][bone], *v["rotations"][bone]], bone)

    for clip in clips.values():
        case = scenario(
            f"wrap-{clip['id']}", [clip["id"], clip["id"], 1, clip["period"] - 2048, 0], [None]
        )
        assign(case, clip["id"], clip["count"] - 1, [6, 4, 2, 0.6, 0, 0, 0.8])
        assign(case, clip["id"], 0, [2, 0, -2, 0, 0.8, 0, 0.6])

    for source, target in ((109, 113), (113, 109)):
        case = scenario(f"exit-{source}-{target}", [source, target, 5, 97040, 3840], [None])
        assign(case, target, 0, [6, 4, 2, 0.6, 0, 0, 0.8])
        assign(case, target, 1, [2, 0, -2, 0, 0.8, 0, 0.6])

    inputs = [str(len(cases))]
    for case in cases:
        inputs.append(" ".join(map(str, [case["bones"], *case["clock"], len(case["requests"])])))
        inputs.extend(f"{p} {o}" for p, o in zip(case["parents"], case["owners"], strict=True))
        inputs.extend(" ".join(map(str, t)) for frame in case["samples"] for t in frame)
        inputs.extend(f"{r or 0} {int(r is not None)}" for r in case["requests"])
    completed = subprocess.run(
        [executable, "vectors"],
        input="\n".join(inputs) + "\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    rows = [list(map(float, line.split())) for line in completed.stdout.splitlines()]
    if len(rows) != sum(1 + len(case["requests"]) for case in cases):
        raise AssertionError("Missing/extra native poses")
    results, offset = {}, 0
    for case in cases:
        end = offset + 1 + len(case["requests"])
        results[case["name"]] = rows[offset:end]
        if any(len(row) != 6 + case["bones"] * 30 for row in rows[offset:end]):
            raise AssertionError("Invalid native pose length")
        for bone in range(case["bones"]):
            start = 6 + bone * 30
            expected = mix(case["samples"][0][bone], case["samples"][0][bone], 0)
            close(rows[offset][start : start + 7], expected)
        offset = end

    v = data["pose"]["mode5_order"]
    row = results["mode5-order"][1]
    close(row[6:9], [Fraction(n, d) for n, d in v["expected_translation_rational"]])
    close(row[9:13], v["expected_quaternion"])
    source = [ordered["samples"][10 + i][0] for i in range(2)]
    target = [ordered["samples"][34 + i][0] for i in range(2)]
    wrong = mix(mix(*source, v["fraction"]), mix(*target, v["fraction"]), v["blend"])
    if (
        max(abs(x - float(y)) for x, y in zip(row[9:13], wrong[3:], strict=True))
        <= v["wrong_order_max_difference_min"]
    ):
        raise AssertionError("The wrong temporal-first order was not distinguished")

    v = data["pose"]["cached_stop"]
    rows = results["cached-stop"]
    cached = mix(*[stopped["samples"][10 + i][0] for i in range(2)], v["source_fraction"])
    close(rows[1][6:13], cached)
    close(rows[1][9:13], v["expected_cached_quaternion"])
    close(rows[2][9:13], v["expected_quaternion"])
    close(rows[2][6:9], [Fraction(n, d) for n, d in v["expected_translation_rational"]])
    trace = next(t for t in data["mode3_sequences"] if t["source"] == 109 and t["target"] == 101)
    for row, blend in zip(rows[2:-1], trace["blends"], strict=True):
        close(row[6:13], mix(cached, stopped["samples"][0][0], blend))
        close(row[13:20], cached)
        if row[3] != 0 or row[5] != 1:
            raise AssertionError("Mode 3 advanced or lost its cache")
        # No roundoff drift or iterative re-freezing is allowed in the cached source.
        if row[13:20] != rows[2][13:20]:
            raise AssertionError("Frozen source changed")
    close(rows[-1][6:13], mix(stopped["samples"][0][0], stopped["samples"][0][0], 0))
    if rows[-1][5] != 0 or rows[-1][3] != trace["exit_counter"]:
        raise AssertionError("Cache not invalidated at the exit")

    close(results["antipodal"][1][9:13], data["pose"]["hemisphere"]["expected"])
    close(
        results["channels"][0][50:66],
        data["pose"]["channels"]["expected_child_matrix_columns"],
        tolerance=4e-6,
    )
    for case in cases[4:]:
        source, target, mode, phase, _ = case["clock"]
        clip = clips[target]
        if mode == 5:
            phase = (phase + clip["increment"]) % clip["period"]
        first, fraction = divmod(phase, 4096)
        a, b = [
            case["samples"][clip["packed_first"] + i][0]
            for i in (first, (first + 1) % clip["count"])
        ]
        close(results[case["name"]][1][6:13], mix(a, b, fraction))
    # The fixture remains a diagnostic only; no new runtime edge is inferred from it.
    if data["pose"]["interrupted_diagnostic"]["runtime_supported"] is not False:
        raise AssertionError("Unexpected expansion of the runtime profile")
    print(f"Native locomotion poses: {offset} snapshots in {len(cases)} synthetic scenarios match")


if __name__ == "__main__":
    verify(sys.argv[1])
