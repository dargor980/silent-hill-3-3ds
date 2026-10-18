"""AC02: verify an explicitly launched private PCSX2 process and profile."""

import configparser
import hashlib
import json
import os
import stat
import subprocess

from tools.inspectors.observation_capture import ProfileError, require
from tools.inspectors.observer_files import _private
from tools.pipeline.private_files import _identity, _open_directory, _owned_stream


def bound_bytes(path, maximum):
    parent = _open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with _owned_stream(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            require(
                stat.S_ISREG(before.st_mode)
                and before.st_nlink == 1
                and 0 < before.st_size <= maximum,
                "ACQUIRE_IDENTITY_FILE",
            )
            data = stream.read(maximum + 1)
            require(
                len(data) == before.st_size
                and _identity(before) == _identity(os.fstat(stream.fileno())),
                "ACQUIRE_IDENTITY_CHANGED",
            )
        require(
            _identity(before)
            == _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
            "ACQUIRE_IDENTITY_CHANGED",
        )
    finally:
        os.close(parent)
    return data


class ProcessGuard:
    """Inputs come from the launch receipt; no discovery or process selection."""

    def __init__(
        self,
        *,
        pid,
        executable,
        executable_sha256,
        profile,
        profile_sha256,
        socket_path,
        state_root,
        command,
    ):
        self.pid, self.executable = pid, executable
        self.executable_sha256, self.profile = executable_sha256, profile
        self.profile_sha256, self.socket_path = profile_sha256, socket_path
        self.state_root, self.command = state_root, command
        manifest = dict(
            executable_sha256=executable_sha256,
            profile_sha256=profile_sha256,
            socket=str(socket_path),
            states=str(state_root),
            command=command,
            pid=pid,
        )
        self.environment_sha256 = hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest()

    def check(self, plan):
        try:
            return self._check(plan)
        except (OSError, subprocess.SubprocessError, configparser.Error, ValueError) as error:
            if isinstance(error, ProfileError):
                raise
            raise ProfileError("ACQUIRE_IDENTITY_IO", "Identity verification failed") from None

    def _check(self, plan):
        require(
            plan.pid == self.pid
            and plan.context.process_sha256 == self.executable_sha256
            and plan.context.environment_sha256 == self.environment_sha256,
            "ACQUIRE_LAUNCH_CONTEXT",
        )
        require(
            hashlib.sha256(bound_bytes(self.executable, 256 * 1024 * 1024)).hexdigest()
            == self.executable_sha256,
            "ACQUIRE_EXECUTABLE",
        )
        raw = bound_bytes(self.profile, 1024 * 1024)
        require(hashlib.sha256(raw).hexdigest() == self.profile_sha256, "ACQUIRE_PROFILE")
        config = configparser.ConfigParser(interpolation=None, strict=False)
        config.read_string(raw.decode())
        require(
            config.getboolean("EmuCore", "EnablePINE")
            and config.getint("EmuCore", "PINESlot") == 28011
            and config.get("Folders", "Savestates") == str(self.state_root),
            "ACQUIRE_PROFILE",
        )
        parent = _open_directory(self.socket_path.parent)
        try:
            _private(os.fstat(parent), True)
            endpoint = os.stat(self.socket_path.name, dir_fd=parent, follow_symlinks=False)
            require(
                self.socket_path.name == "pcsx2.sock"
                and stat.S_ISSOCK(endpoint.st_mode)
                and endpoint.st_uid == os.getuid()
                and stat.S_IMODE(endpoint.st_mode) == 0o700,
                "ACQUIRE_ENDPOINT",
            )
        finally:
            os.close(parent)
        process = (
            subprocess.check_output(
                ["/bin/ps", "-p", str(self.pid), "-o", "lstart=,command="],
                text=True,
                timeout=3,
            )
            .strip()
            .split(maxsplit=5)
        )
        require(len(process) == 6 and process[5] == self.command, "ACQUIRE_PROCESS")
        loaded = subprocess.check_output(
            ["/usr/sbin/lsof", "-a", "-p", str(self.pid), "-d", "txt", "-Fn"],
            text=True,
            timeout=3,
        ).splitlines()
        require("n" + str(self.executable) in loaded, "ACQUIRE_PROCESS")
        return tuple(process[:5]), _identity(endpoint)
