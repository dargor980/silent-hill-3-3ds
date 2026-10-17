"""POSIX private output adapter: anchored directories, exclusive files and receipts."""

import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path

from tools.pipeline.hashing import fingerprint_stream
from tools.pipeline.private_files import (
    DIRECTORY_FLAGS,
    _close_after_error,
    _identity,
    _inode,
    _open_directory,
    _owned_stream,
)
from tools.pipeline.profile import ProfileError
from tools.pipeline.transfer import write_all

COPIES = ("copy-a", "copy-b")
RECEIPTS = {"started.json", "copy-a.json", "copy-b.json", "verified.json", "failed.json"}


def required_space(payload_bytes: int, count: int) -> int:
    if type(payload_bytes) is not int or payload_bytes < 0 or type(count) is not int or count < 1:
        raise ProfileError("INVALID_SIZE", "Invalid output budget")
    payload = 2 * payload_bytes
    return payload + 2 * count * 8192 + max(64 * 1024 * 1024, (payload + 9) // 10)


def resource_filename(identity: str) -> str:
    if not isinstance(identity, str) or not re.fullmatch(r"asset:[0-9a-f]{64}", identity):
        raise ProfileError("INVALID_RESOURCE_ID", "Invalid output identity")
    return identity[6:] + ".bin"


class PrivateOutput:
    def __init__(self, root: Path, repository: Path, run_id: str):
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", run_id):
            raise ProfileError("INVALID_DESTINATION", "Invalid session name")
        resolved, checkout = root.resolve(), repository.resolve()
        if resolved.is_relative_to(checkout) or checkout.is_relative_to(resolved):
            raise ProfileError("PRIVATE_DATA_IN_REPO", "Extraction root must be external")
        self.root, self.run_id = root, run_id
        self.root_fd = self.session_fd = None
        self.copy_fds: dict[str, int] = {}

    def __enter__(self):
        self.root_fd = _open_directory(self.root)
        # Fail early for an occupied name, without following links or changing its contents.
        try:
            os.stat(self.run_id, dir_fd=self.root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return self
        except BaseException as error:
            _close_after_error(self.root_fd, error)
            self.root_fd = None
            raise
        else:
            error = ProfileError("OUTPUT_EXISTS", "Extraction session already exists")
            _close_after_error(self.root_fd, error)
            self.root_fd = None
            raise error

    @property
    def reserved(self) -> bool:
        return self.session_fd is not None

    def __exit__(self, exc_type, exc_value, traceback):
        descriptors = [*self.copy_fds.values(), self.session_fd, self.root_fd]
        self.copy_fds.clear()
        self.session_fd = self.root_fd = None
        close_error = None
        for descriptor in descriptors:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError as error:
                    close_error = close_error or error
        if close_error is not None:
            if exc_value is None:
                raise close_error
            exc_value.add_note("Output directory cleanup also failed; all closes were attempted")

    def reserve(self, payload_bytes: int, count: int) -> int:
        space = os.fstatvfs(self.root_fd)
        needed = required_space(payload_bytes, count)
        if space.f_bavail * space.f_frsize < needed:
            raise ProfileError("INSUFFICIENT_SPACE", "Private output budget exceeds free space")
        os.mkdir(self.run_id, mode=0o700, dir_fd=self.root_fd)
        self.session_fd = os.open(self.run_id, DIRECTORY_FLAGS, dir_fd=self.root_fd)
        for name in COPIES:
            os.mkdir(name, mode=0o700, dir_fd=self.session_fd)
            self.copy_fds[name] = os.open(name, DIRECTORY_FLAGS, dir_fd=self.session_fd)
        return needed

    def assert_attached(self) -> None:
        current = _open_directory(self.root)
        try:
            if _inode(os.fstat(current)) != _inode(os.fstat(self.root_fd)):
                raise ProfileError("OUTPUT_CHANGED", "Private root was replaced")
        finally:
            os.close(current)
        paths = [(self.root_fd, self.run_id, self.session_fd)]
        paths.extend((self.session_fd, name, fd) for name, fd in self.copy_fds.items())
        for parent, name, descriptor in paths:
            observed = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(observed.st_mode) or _inode(observed) != _inode(
                os.fstat(descriptor)
            ):
                raise ProfileError("OUTPUT_CHANGED", "Extraction directory was replaced")

    @contextmanager
    def open_resource(self, copy: str, identity: str):
        filename = resource_filename(identity)
        descriptor = os.open(
            filename,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            mode=0o600,
            dir_fd=self.copy_fds[copy],
        )
        with _owned_stream(descriptor, "wb") as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())

    def verify(self, copy: str, resources: list[dict]) -> list[dict]:
        descriptor = self.copy_fds[copy]
        expected = {resource_filename(item["id"]) for item in resources}
        if set(os.listdir(descriptor)) != expected:
            raise ProfileError("OUTPUT_SET_MISMATCH", "Unexpected or missing output files")
        inventory = []
        for item in resources:
            filename = resource_filename(item["id"])
            fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
            with _owned_stream(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                    raise ProfileError("INVALID_OUTPUT", "Expected a regular unlinked resource")
                observed = fingerprint_stream(stream, item["size"])
                after = os.fstat(stream.fileno())
            named = os.stat(filename, dir_fd=descriptor, follow_symlinks=False)
            if _identity(before) != _identity(after) or _identity(after) != _identity(named):
                raise ProfileError("OUTPUT_CHANGED", "Resource changed during verification")
            if observed["sha256"] != item["sha256"]:
                raise ProfileError("OUTPUT_HASH_MISMATCH", "Resource hash differs from catalog")
            inventory.append({"id": item["id"], "file": filename, **observed})
        return inventory

    def receipt(self, name: str, document: dict) -> None:
        if name not in RECEIPTS:
            raise ProfileError("INVALID_RECEIPT", "Unknown extraction receipt")
        raw = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode("utf-8")
        temporary = "." + name + ".pending"
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            mode=0o600,
            dir_fd=self.session_fd,
        )
        with _owned_stream(fd, "wb") as stream:
            write_all(stream, raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic no-clobber publication; keep staging metadata for diagnosis.
        os.link(
            temporary,
            name,
            src_dir_fd=self.session_fd,
            dst_dir_fd=self.session_fd,
            follow_symlinks=False,
        )
