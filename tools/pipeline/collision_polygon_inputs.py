"""CPI01/10: bounded, anchored input custody for the private CLD recipe."""

import os
import stat
from pathlib import Path

from tools.pipeline.intermediate_assets import sha
from tools.pipeline.private_files import _identity, _inode, _open_directory, _owned_stream


def require(condition):
    if not condition:
        raise ValueError("CPI_CUSTODY")


def absolute_path(value):
    require(type(value) is str)
    path = Path(value)
    require(path.is_absolute() and ".." not in path.parts)
    return path


def read_at(directory, name, limit):
    """Read one regular entry; compare its open and named identity after the read."""
    require(type(name) is str and name not in ("", ".", "..") and "/" not in name)
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with _owned_stream(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        require(_identity(before) == _identity(after) == _identity(named))
        require(len(raw) == before.st_size)
    return raw, _identity(before)


def read_path(path, limit):
    directory = _open_directory(path.parent)
    try:
        raw, identity = read_at(directory, path.name, limit)
        current = _open_directory(path.parent)
        try:
            require(_inode(os.fstat(current)) == _inode(os.fstat(directory)))
        finally:
            os.close(current)
        return raw, identity, _inode(os.fstat(directory))
    finally:
        os.close(directory)


class PinnedInputs:
    """Keep only identities, not payloads, and recheck every consumed source."""

    def __init__(self):
        self.sources = {}

    def read(self, path, limit, pin=None):
        raw, identity, parent = read_path(path, limit)
        actual = dict(size=len(raw), sha256=sha(raw))
        if pin is not None:
            require(type(pin["size"]) is int and actual == pin)
        record = (limit, actual, identity, parent)
        if path in self.sources:
            require(self.sources[path] == record)
        self.sources[path] = record
        return raw

    def verify(self):
        for path, (limit, pin, identity, parent) in self.sources.items():
            raw, current, directory = read_path(path, limit)
            require(current == identity and directory == parent)
            require(len(raw) == pin["size"] and sha(raw) == pin["sha256"])
