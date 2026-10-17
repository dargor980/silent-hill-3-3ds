"""Shared POSIX descriptor ownership and anchored directory traversal."""

import os
from contextlib import contextmanager
from pathlib import Path

from tools.pipeline.profile import ProfileError

DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _close_after_error(descriptor: int, primary: BaseException) -> None:
    try:
        os.close(descriptor)
    except OSError:
        # A failed close has platform-dependent release semantics; never retry that fd.
        primary.add_note("Descriptor cleanup also failed; close was attempted once")


@contextmanager
def _owned_stream(descriptor: int, mode: str):
    """Transfer ownership only after fdopen succeeds; otherwise release the raw fd."""
    try:
        stream = os.fdopen(descriptor, mode)
    except BaseException as error:
        _close_after_error(descriptor, error)
        raise
    with stream:
        yield stream


def _open_directory(path: Path) -> int:
    if not path.is_absolute() or ".." in path.parts:
        raise ProfileError("INVALID_DESTINATION", "Expected absolute path without traversal")
    descriptor = os.open("/", DIRECTORY_FLAGS)
    try:
        for component in path.parts[1:]:
            next_fd = os.open(component, DIRECTORY_FLAGS, dir_fd=descriptor)
            previous = descriptor
            descriptor = next_fd
            os.close(previous)
        return descriptor
    except BaseException as error:
        _close_after_error(descriptor, error)
        raise


def _identity(value: os.stat_result) -> tuple:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _inode(value: os.stat_result) -> tuple:
    return value.st_dev, value.st_ino
