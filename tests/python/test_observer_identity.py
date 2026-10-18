"""AC02: independent process-table/load doubles and real bounded identity files."""

import hashlib
import os
import stat
import subprocess
from dataclasses import replace

import pytest
from test_observer_acquisition import PLAN

from tools.inspectors import observer_identity as identity
from tools.inspectors.observation_capture import ProfileError


@pytest.fixture
def setup(tmp_path, monkeypatch):
    exe, ini, endpoint = tmp_path / "executable", tmp_path / "profile.ini", tmp_path / "pcsx2.sock"
    exe.write_bytes(b"own executable")
    root = tmp_path / "states"
    root.mkdir(mode=0o700)
    ini.write_text(f"[EmuCore]\nEnablePINE=true\nPINESlot=28011\n[Folders]\nSavestates={root}\n")
    endpoint.write_bytes(b"")
    endpoint.chmod(0o700)
    real_stat = os.stat

    def endpoint_stat(path, *args, **kwargs):
        value = real_stat(path, *args, **kwargs)
        if str(path) == "pcsx2.sock":
            fields = list(value)
            fields[0] = stat.S_IFSOCK | 0o700
            return os.stat_result(fields)
        return value

    monkeypatch.setattr(os, "stat", endpoint_stat)
    command = str(exe) + " -datapath own"

    def output(args, **kwargs):
        if args[0] == "/bin/ps":
            return "Sun Oct 18 12:00:00 2026 " + command + "\n"
        return "p42\nn" + str(exe) + "\n"

    monkeypatch.setattr(subprocess, "check_output", output)
    guard = identity.ProcessGuard(
        pid=42,
        executable=exe,
        executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
        profile=ini,
        profile_sha256=hashlib.sha256(ini.read_bytes()).hexdigest(),
        socket_path=endpoint,
        state_root=root,
        command=command,
    )
    plan = replace(
        PLAN,
        context=replace(
            PLAN.context,
            process_sha256=guard.executable_sha256,
            environment_sha256=guard.environment_sha256,
        ),
    )
    return guard, plan


def test_identity_matches_and_process_start_change_is_visible(setup, monkeypatch):
    guard, plan = setup
    first = guard.check(plan)
    assert guard.check(plan) == first
    original = subprocess.check_output

    def changed(args, **kwargs):
        return original(args, **kwargs).replace("12:00:00", "12:00:01")

    monkeypatch.setattr(subprocess, "check_output", changed)
    assert guard.check(plan) != first


@pytest.mark.parametrize(
    "variant", ["context", "executable", "profile", "profile_config", "process", "load", "endpoint"]
)
def test_identity_rejections(setup, monkeypatch, variant):
    guard, plan = setup
    if variant == "context":
        plan = replace(plan, pid=43)
    elif variant == "executable":
        guard.executable.write_bytes(b"different")
    elif variant == "profile":
        guard.profile.write_bytes(b"different")
    elif variant == "profile_config":
        guard.profile.write_text(guard.profile.read_text().replace("true", "false"))
        guard.profile_sha256 = hashlib.sha256(guard.profile.read_bytes()).hexdigest()
    elif variant in ("process", "load"):
        original = subprocess.check_output

        def changed(args, **kwargs):
            if (args[0] == "/bin/ps") == (variant == "process"):
                return "wrong"
            return original(args, **kwargs)

        monkeypatch.setattr(subprocess, "check_output", changed)
    elif variant == "endpoint":
        guard.socket_path = guard.socket_path.with_name("different.sock")
    with pytest.raises(ProfileError):
        guard.check(plan)


@pytest.mark.parametrize("variant", ["subprocess", "config", "unicode"])
def test_identity_diagnostics_sanitized(setup, monkeypatch, variant):
    guard, plan = setup
    if variant == "subprocess":

        def fail(*_args, **_kwargs):
            raise subprocess.TimeoutExpired("private command", 3)

        monkeypatch.setattr(subprocess, "check_output", fail)
    else:
        guard.profile.write_bytes(b"bad config" if variant == "config" else b"\xff")
        guard.profile_sha256 = hashlib.sha256(guard.profile.read_bytes()).hexdigest()
    with pytest.raises(ProfileError) as caught:
        guard.check(plan)
    assert caught.value.code == "ACQUIRE_IDENTITY_IO" and "private" not in str(caught.value)


@pytest.mark.parametrize("variant", ["empty", "large", "symlink", "hardlink"])
def test_identity_file_bounds(tmp_path, variant):
    file = tmp_path / "own"
    file.write_bytes(b"1234")
    if variant == "empty":
        file.write_bytes(b"")
    if variant == "symlink":
        file.rename(tmp_path / "target")
        file.symlink_to(tmp_path / "target")
    if variant == "hardlink":
        os.link(file, tmp_path / "link")
    with pytest.raises((ProfileError, OSError)):
        identity.bound_bytes(file, 3 if variant == "large" else 4)
