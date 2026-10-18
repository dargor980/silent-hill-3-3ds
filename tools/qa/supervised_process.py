"""BB03-BB05: bounded process-group supervision with injected measurement/journal."""

import os
import signal
import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    start: int
    floor: int
    maximum: int
    seconds: float
    interval: float = 1

    def __post_init__(self):
        if not (self.start >= self.floor > 0 and self.maximum > 0):
            raise ValueError("invalid capacity limits")
        if not (self.seconds > 0 and self.interval > 0):
            raise ValueError("invalid time limits")


def violation(sample, limits):
    for key in ("free_bytes", "logical_bytes", "allocated_bytes"):
        if type(sample[key]) is not int or sample[key] < 0:
            raise ValueError("invalid measurement")
    if sample["free_bytes"] < limits.floor:
        return "free_space_floor"
    if max(sample["logical_bytes"], sample["allocated_bytes"]) > limits.maximum:
        return "build_budget"
    return None


def live_group(pgid):
    """Return live pids; an unavailable process table raises, never means empty."""
    output = subprocess.check_output(["/bin/ps", "-axo", "pid=,pgid=,stat="], text=True, timeout=5)
    members = []
    for line in output.splitlines():
        pid, group, status = line.split()
        if int(group) == pgid and not status.startswith("Z"):
            members.append(int(pid))
    return members


def stop_group(process, *, probe=live_group, send=os.killpg, grace=5):
    """Only signal the owned session group; retain signal and inspection failures."""
    errors = []
    remaining = None
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            send(process.pid, sig)
        except ProcessLookupError:
            pass
        except OSError as exc:
            errors.append(f"{sig.name}: {exc}")
        deadline = time.monotonic() + grace
        while True:
            process.poll()
            try:
                remaining = probe(process.pid)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                errors.append(f"probe: {exc}")
                remaining = None
                break
            if not remaining:
                return {"verified": True, "remaining": [], "errors": errors}
            if time.monotonic() >= deadline:
                break
            time.sleep(min(0.05, grace))
    return {"verified": False, "remaining": remaining, "errors": errors}


def supervise(argv, *, env, log, limits, measurement, journal, probe=live_group, stop=stop_group):
    """Journal every measurement before a stop; return a rejected receipt on errors."""
    started = time.monotonic()
    samples = []
    process = None
    result = {"accepted": False, "exit_code": None, "abort_reason": None, "shutdown": None}

    def sample():
        value = measurement()
        reason = violation(value, limits)
        value = dict(value, elapsed_seconds=round(time.monotonic() - started, 3))
        samples.append(value)
        journal(value)
        return value, reason

    try:
        initial, reason = sample()
        if initial["free_bytes"] < limits.start or reason:
            result["abort_reason"] = "initial_capacity"
        else:
            with log.open("x") as stream:
                process = subprocess.Popen(
                    argv, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True
                )
                result["pid"] = process.pid
                while True:
                    _, reason = sample()
                    if reason or time.monotonic() - started >= limits.seconds:
                        result["abort_reason"] = reason or "deadline"
                        break
                    if process.poll() is not None:
                        if probe(process.pid):
                            result["abort_reason"] = "remaining_children"
                        else:
                            _, result["abort_reason"] = sample()
                            result["shutdown"] = {"verified": True, "remaining": [], "errors": []}
                        break
                    time.sleep(limits.interval)
    except (Exception, KeyboardInterrupt) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["abort_reason"] = result["abort_reason"] or "supervisor_error"
    finally:
        if process is not None:
            if result["shutdown"] is None:
                try:
                    result["shutdown"] = stop(process)
                except Exception as exc:
                    result["shutdown"] = {"verified": False, "error": str(exc)}
            result["exit_code"] = process.poll()
        result["samples"] = samples
        result["duration_seconds"] = round(time.monotonic() - started, 3)
    result["accepted"] = (
        result["exit_code"] == 0
        and result["abort_reason"] is None
        and result["shutdown"] is not None
        and result["shutdown"]["verified"]
    )
    return result
