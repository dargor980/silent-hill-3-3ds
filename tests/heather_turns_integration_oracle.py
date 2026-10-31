"""Feed frozen HG-T3 control/routes/replays to the actual native controller."""

import json
import math
import subprocess
import sys
from pathlib import Path


def main(binary):
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "tests/fixtures/synthetic/heather-turns-native-v1.json").read_text())
    commands = []
    for row in data["inputs"]:
        commands.append("I " + str(sum(int(b) << i for i, b in enumerate(row["bits"]))))
    for route in data["routes"]:
        commands.append(f"H {route['current']} {route['desired']}")
    for replay in data["replays"]:
        commands.append(f"R {len(replay['rows'])}")
        commands.extend(f"{row[0]} {row[1]}" for row in replay["rows"])
    run = subprocess.run(
        [binary, "protocol"],
        input="\n".join(commands) + "\n",
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    lines = iter(run.stdout.splitlines())
    for row in data["inputs"]:
        got = list(map(float, next(lines).split()))
        assert len(got) == 12
        assert got[0] == row["desired"]
        expected_clip = 109 if row["desired"] == 113 else row["desired"]
        assert got[1] == got[3] == expected_clip
        assert abs(got[8] - row["yaw_sign"] * 0.088) < 1e-7
        distance = 28 if expected_clip == 109 else 0
        assert abs(math.hypot(got[9], got[10]) - distance) < 3e-6
    for route in data["routes"]:
        assert list(map(int, next(lines).split())) == route["hops"] + [0], route
    total = 0
    for replay in data["replays"]:
        yaw = 0.0
        for ordinal, row in enumerate(replay["rows"], 1):
            got = list(map(float, next(lines).split()))
            assert got[:7] == [*row[2:8], row[8] or 0], (replay["id"], ordinal, got[:7], row)
            assert abs(got[7] - row[1] * 0.088) < 2e-7
            yaw += row[1] * 0.088
            assert got[8:10] == [0.0, 0.0] and got[10] == ordinal
            total += 1
    assert next(lines, None) is None
    print(f"HG controller literals: 32 inputs, 25 routes, {total} replay rows PASS")


if __name__ == "__main__":
    main(sys.argv[1])
