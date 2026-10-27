"""Reconstruct independently written SRI2 and compare every C++ output field."""

import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.locomotion_rig_fixtures import invalid_sri2, own_sri2  # noqa: E402
from tools.qa.locomotion_rig_oracle import reconstruct_sri2, reconstruct_sri2_bundle  # noqa: E402


def check_dump(text, expected):
    rows = iter(text.splitlines())

    def row(label, values, floats=False, mixed=False):
        actual = next(rows).split()
        assert actual.pop(0) == label
        assert len(actual) == len(values)
        for i, (a, b) in enumerate(zip(actual, values, strict=True)):
            if floats or (mixed and i):
                assert struct.pack("<f", float(a)) == struct.pack("<f", b), (label, i, a, b)
            else:
                assert int(a) == b, (label, i, a, b)

    row(
        "P",
        [
            expected[k]
            for k in ("profile", "model_resource", "animation_resource", "ticks", "inspection_hz")
        ],
    )
    row("F", expected["framing"], floats=True)
    for b in expected["bones"]:
        row("B", [b["source"], b["parent"], b["channel"]])
    for c in expected["clips"]:
        row("C", c)
    for frame in expected["samples"]:
        for tr in frame:
            row("S", tr, floats=True)
    for h in expected["helpers"]:
        row("H", h, mixed=True)
    for v in expected["vertices"]:
        row("V", v)
    row("I", expected["indices"])
    for m in expected["materials"]:
        row("M", m)
    assert next(rows, None) is None


def main(binary):
    files = own_sri2()
    good = files["heather.sri"]
    expected = reconstruct_sri2_bundle(files)
    cases = list(invalid_sri2(good))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / "heather.sri"
        for name, raw in files.items():
            (root / name).write_bytes(raw)
        for args in ([str(path)], [str(root), "bundle"]):
            run = subprocess.run([binary, *args], capture_output=True, text=True, check=True)
            check_dump(run.stdout, expected)
        for name, raw in cases:
            try:
                reconstruct_sri2(raw)
            except ValueError:
                pass
            else:
                raise AssertionError((name, "oracle accepted"))
            path.write_bytes(raw)
            run = subprocess.run([binary, str(path)], capture_output=True, text=True)
            assert run.returncode == 2, (name, run.returncode, run.stderr)
        path.write_bytes(good)
        # Real filesystem, last texture missing: no completed model may escape.
        (root / "texture-01.rgba").unlink()
        run = subprocess.run([binary, str(root), "bundle"], capture_output=True, text=True)
        assert run.returncode == 2 and "texture.open 1" in run.stderr, run.stderr
    print(f"SRI2 independent reconstruction/native: all fields, {len(cases)} rejections PASS")


if __name__ == "__main__":
    main(sys.argv[1])
