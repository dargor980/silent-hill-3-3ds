"""Synthetic process contracts; never load private game/emulator assets."""

import os
import signal
import subprocess
import sys
from unittest.mock import Mock

import pytest

from tools.qa.supervised_process import Limits, live_group, stop_group, supervise, violation


def reading(free=100, logical=0, allocated=0):
    return dict(free_bytes=free, logical_bytes=logical, allocated_bytes=allocated)


def run(tmp_path, code="pass", measurement=lambda: reading(), **kwargs):
    journal = []
    result = supervise(
        [sys.executable, "-c", code],
        env=os.environ.copy(),
        log=tmp_path / "process.log",
        limits=Limits(80, 50, 20, 3, 0.01),
        measurement=measurement,
        journal=journal.append,
        **kwargs,
    )
    return result, journal


@pytest.mark.parametrize(
    "free,logical,allocated,expected",
    [
        (50, 20, 20, None),
        (49, 0, 0, "free_space_floor"),
        (100, 21, 0, "build_budget"),
        (100, 0, 21, "build_budget"),
    ],
)
def test_capacity_boundaries(free, logical, allocated, expected):
    assert violation(reading(free, logical, allocated), Limits(80, 50, 20, 1)) == expected


@pytest.mark.parametrize("value", [-1, True, 1.5])
def test_reject_invalid_measurements(value):
    with pytest.raises(ValueError):
        violation(reading(value), Limits(80, 50, 20, 1))


@pytest.mark.parametrize(
    "args", [(40, 50, 20, 1), (80, 0, 20, 1), (80, 50, 0, 1), (80, 50, 20, 0), (80, 50, 20, 1, 0)]
)
def test_invalid_limits(args):
    with pytest.raises(ValueError):
        Limits(*args)


def test_success_and_child_failure(tmp_path):
    result, journal = run(tmp_path, 'print("synthetic")')
    assert result["accepted"] and result["samples"] == journal
    assert (tmp_path / "process.log").read_text().strip() == "synthetic"
    sub = tmp_path / "failed"
    sub.mkdir()
    result, _ = run(sub, "raise SystemExit(7)")
    assert not result["accepted"] and result["exit_code"] == 7


def test_no_spawn_below_initial_capacity(tmp_path):
    result, _ = run(tmp_path, measurement=lambda: reading(79))
    assert result["abort_reason"] == "initial_capacity"
    assert not (tmp_path / "process.log").exists()


def test_capacity_abort_retains_trigger_before_shutdown(tmp_path):
    values = iter([reading(), reading(49)])
    result, journal = run(tmp_path, "import time; time.sleep(30)", lambda: next(values))
    assert result["abort_reason"] == "free_space_floor"
    assert result["shutdown"]["verified"] and journal[-1]["free_bytes"] == 49


def test_measurement_error_does_not_lose_receipt(tmp_path):
    values = iter([reading()])
    result, journal = run(tmp_path, "import time; time.sleep(30)", lambda: next(values))
    assert result["abort_reason"] == "supervisor_error"
    assert result["shutdown"]["verified"] and len(journal) == 1


def test_shutdown_failure_is_rejected(tmp_path):
    result, _ = run(
        tmp_path,
        probe=Mock(side_effect=PermissionError("denied")),
        stop=Mock(side_effect=PermissionError("denied")),
    )
    assert not result["accepted"] and not result["shutdown"]["verified"]


def test_eperm_after_exit_is_recorded_not_raised():
    process = Mock(pid=123)
    report = stop_group(process, probe=lambda _: [], send=Mock(side_effect=PermissionError()))
    assert report["verified"] and "SIGTERM" in report["errors"][0]


def test_unknown_group_is_never_reported_closed():
    report = stop_group(
        Mock(pid=123),
        probe=Mock(side_effect=PermissionError()),
        send=Mock(side_effect=ProcessLookupError()),
        grace=0,
    )
    assert not report["verified"] and report["remaining"] is None


def test_live_group_escalates_boundedly():
    send = Mock()
    report = stop_group(Mock(pid=123), probe=lambda _: [124], send=send, grace=0)
    assert not report["verified"] and report["remaining"] == [124]
    assert [call.args[1] for call in send.call_args_list] == [signal.SIGTERM, signal.SIGKILL]


def test_terminate_real_child_after_leader_exit(tmp_path):
    marker = tmp_path / "ready"
    child = (
        "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        f"open({str(marker)!r},'w').write('ready'); time.sleep(30)"
    )
    code = (
        "import subprocess,sys,time,pathlib\n"
        f"subprocess.Popen([sys.executable,'-c',{child!r}])\n"
        "deadline=time.monotonic()+3\n"
        f"while not pathlib.Path({str(marker)!r}).exists():\n"
        " assert time.monotonic()<deadline\n"
        " time.sleep(.01)\n"
    )
    process = subprocess.Popen([sys.executable, "-c", code], start_new_session=True)
    try:
        process.wait(timeout=5)
        assert marker.exists() and live_group(process.pid)
        report = stop_group(process, grace=0.2)
        assert report["verified"] and not live_group(process.pid)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_deadline_stops_process(tmp_path):
    result = supervise(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        env=os.environ.copy(),
        log=tmp_path / "timeout.log",
        limits=Limits(80, 50, 20, 0.05, 0.01),
        measurement=reading,
        journal=lambda _: None,
    )
    assert result["abort_reason"] == "deadline" and result["shutdown"]["verified"]


def test_supervisor_rejects_orphaned_child(tmp_path):
    child = "import time; time.sleep(30)"
    code = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child!r}])"
    result, _ = run(tmp_path, code)
    assert result["abort_reason"] == "remaining_children"
    assert not result["accepted"] and result["shutdown"]["verified"]
