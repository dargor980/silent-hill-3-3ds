"""PS05: external private state files, anchored reads and stable close."""

import hashlib
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.pcsx2_state import MAX_ARCHIVE, EEState, read_state_archive
from tools.pipeline.private_files import (
    _close_after_error,
    _identity,
    _inode,
    _open_directory,
    _owned_stream,
)
from tools.pipeline.profile import ProfileError

T = TypeVar("T")


def inspect_private_state(
    root: Path,
    name: str,
    digest: str,
    expected_crc: int,
    repository: Path,
    decode: Callable[[bytes, int], T],
) -> T:
    validate_image_hash(digest)
    resolved, checkout = root.resolve(), repository.resolve()
    if resolved.is_relative_to(checkout) or checkout.is_relative_to(resolved):
        raise ProfileError("PRIVATE_DATA_IN_REPO", "State must be external")
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 128
        or Path(name).name != name
        or any(c in name for c in ("\\", "\0"))
        or not name.endswith(".p2s")
    ):
        raise ProfileError("STATE_PATH", "Invalid state filename")
    parent = _open_directory(root)
    try:
        if stat.S_IMODE(os.fstat(parent).st_mode) != 0o700:
            raise ProfileError("STATE_FILE", "State directory must be private")
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with _owned_stream(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != 0o600
                or not 1 <= before.st_size <= MAX_ARCHIVE
            ):
                raise ProfileError("STATE_FILE", "Invalid private state file")
            raw = stream.read(MAX_ARCHIVE + 1)
            if len(raw) != before.st_size or hashlib.sha256(raw).hexdigest() != digest:
                raise ProfileError("STATE_HASH", "State bytes differ")
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise ProfileError("STATE_CHANGED", "State changed during read")
        result = decode(raw, expected_crc)
        current = _open_directory(root)
        try:
            after = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (
                _inode(os.fstat(current)) != _inode(os.fstat(parent))
                or stat.S_IMODE(os.fstat(current).st_mode) != 0o700
                or _identity(after) != _identity(before)
            ):
                raise ProfileError("STATE_CHANGED", "State changed before close")
        finally:
            os.close(current)
    except BaseException as error:
        _close_after_error(parent, error)
        raise
    os.close(parent)
    return result


def read_private_state(
    root: Path, name: str, digest: str, expected_crc: int, repository: Path
) -> EEState:
    return inspect_private_state(root, name, digest, expected_crc, repository, read_state_archive)
