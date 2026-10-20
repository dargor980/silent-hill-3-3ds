"""IT02-IT04: counters, exact insertions and partial trace validation."""

import runpy
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/fixtures/runtime-service"
parser = runpy.run_path(str(FIX / "inventory_timing_parser.py"))
parse = parser["parse"]


def trace():
    rows = []

    def phase(q, name, start, end, complete=1):
        n = end - start
        rows.append(
            f"IT_PHASE role=DW query={q} phase={name} calls=1 complete={complete} "
            f"total_ns={n} min_ns={n} max_ns={n} bytes=0 first_ns={start} last_ns={end}"
        )

    phase(0, "prepare", 105, 120)
    for q in range(1, 4):
        start = q * 1000
        phase(q, "sample", start, start + 100)
        for i, name in enumerate(parser["PARTITION"]):
            phase(q, name, start + 1 + i * 10, start + 9 + i * 10)
    rows += ["IT_END role=DW fine=0 errors=0 calibration_calls=0 calibration_ns=0"]

    def event(name, q, at, deadline=0):
        rows.append(f"IT_EVENT role=IO event={name} query={q} at_ns={at} deadline_ns={deadline}")

    event("open", 0, 100, 5000000100)
    event("binding", 0, 101)
    for q in range(1, 4):
        event("submit", q, q * 1000 - 1, q * 1000 + 1000)
        event("delivered", q, q * 1000 + 101)
    event("cleanup_begin", 0, 3200)
    event("cleanup_end", 0, 3400)
    rows += ["IT_END role=IO fine=0 errors=0 calibration_calls=10000 calibration_ns=500000"]
    return rows


def test_complete_and_nonoverlapping_partition():
    result = parse(trace(), "coarse", 3)
    assert len(result["queries"]) == 3 and result["cleanup_ns"] == 200
    assert all(q["completed"] and q["delivery_margin_ns"] == 899 for q in result["queries"])


def test_partial_is_preserved():
    rows = [
        r for r in trace() if not ("query=3" in r and ("phase=" in r or "event=delivered" in r))
    ]
    rows.insert(
        0,
        "IT_PHASE role=DW query=3 phase=sample calls=1 complete=0 "
        "total_ns=5 min_ns=5 max_ns=5 bytes=0 first_ns=3000 last_ns=3005",
    )
    result = parse(rows, "coarse", 2)
    assert not result["queries"][2]["completed"] and not result["queries"][2]["accepted"]
    assert result["queries"][2]["delivery_margin_ns"] is None
    with pytest.raises(ValueError):
        parse(rows, "coarse", 3)


@pytest.mark.parametrize(
    "old,new",
    [
        ("phase=prepare", "phase=unknown"),
        ("errors=0", "errors=1"),
        ("calls=1 complete=1", "calls=1 complete=2"),
        ("total_ns=15", "total_ns=99"),
        ("query=3", "query=4"),
        ("total_ns=15", "total_ns=-1"),
        ("total_ns=15", "total_ns=18446744073709551616"),
        ("deadline_ns=5000000100", "deadline_ns=5000000101"),
        ("fine=0", "fine=1"),
        ("role=DW", "role=CPU"),
        ("calibration_calls=10000", "calibration_calls=0"),
        ("at_ns=3200", "at_ns=1"),
    ],
)
def test_invalid_metadata_rejected(old, new):
    rows = [r.replace(old, new) for r in trace()]
    with pytest.raises(ValueError):
        parse(rows, "coarse", 3)


def test_duplicate_missing_and_injected_markers():
    rows = trace()
    for invalid in [
        rows + [rows[-1]],
        [rows[0]] + rows,
        rows[:-1],
        rows + ["IT_UNKNOWN role=IO"],
        [r for r in rows if "event=submit query=2" not in r],
    ]:
        with pytest.raises(ValueError):
            parse(invalid, "coarse", 3)


def test_clean_has_no_probe():
    assert parse(["PCSX2 unrelated log"], "clean", 3) == {"instrumented": False, "queries": []}
    with pytest.raises(ValueError):
        parse(trace(), "clean", 3)


@pytest.mark.parametrize("start,end", [(1001, 1009), (1100, 1108)])
def test_partition_overlap_or_outside_sample_rejected(start, end):
    rows = [
        r.replace("first_ns=1011 last_ns=1019", f"first_ns={start} last_ns={end}") for r in trace()
    ]
    with pytest.raises(ValueError):
        parse(rows, "coarse", 3)


def test_exact_integrations_reject_reapplication_and_ambiguity():
    integration = runpy.run_path(str(FIX / "inventory_timing_integration.py"))
    for unit in integration["UNITS"]:
        source = (ROOT / "tools/observer" / unit).read_text()
        result = integration["apply"](Path(unit).name, source)
        assert result.startswith('#include "inventory_timing_probe.hpp"')
        # Duplicate source must never silently select an anchor.
        with pytest.raises(ValueError):
            integration["apply"](Path(unit).name, source + source)


def test_native_accumulator_and_raii(tmp_path):
    binary = tmp_path / "timing-test"
    subprocess.run(
        [
            "/usr/bin/clang++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-O2",
            str(FIX / "inventory_timing_test.cpp"),
            "-o",
            str(binary),
        ],
        check=True,
        timeout=60,
    )
    subprocess.run([str(binary)], check=True, timeout=10)
