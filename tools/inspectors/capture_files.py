"""Bounded private capture reader, with anchored descriptors and stable close."""

import hashlib
import json
import os
import re
import stat
from pathlib import Path

from tools.inspectors.inventory import validate_image_hash
from tools.pipeline.extract_assets import _invalid_constant, _unique_object
from tools.pipeline.private_files import (
    _close_after_error,
    _identity,
    _inode,
    _open_directory,
    _owned_stream,
)
from tools.pipeline.profile import ProfileError

MAX_JSON = 1024 * 1024


class PrivateCaptureReader:
    def __init__(self, root: Path, repository: Path):
        resolved, checkout = root.resolve(), repository.resolve()
        if resolved.is_relative_to(checkout) or checkout.is_relative_to(resolved):
            raise ProfileError("PRIVATE_DATA_IN_REPO", "Capture must be external")
        self.root, self.fd, self.observed = root, None, {}

    def __enter__(self):
        self.fd = _open_directory(self.root)
        return self

    def assert_stable(self):
        current = _open_directory(self.root)
        try:
            if _inode(os.fstat(current)) != _inode(os.fstat(self.fd)):
                raise ProfileError("CAPTURE_CHANGED", "Capture directory changed")
            for name, before in self.observed.items():
                after = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
                if _identity(after) != before:
                    raise ProfileError("CAPTURE_CHANGED", "Capture file changed")
        finally:
            os.close(current)

    def __exit__(self, exc_type, exc_value, traceback):
        descriptor = self.fd
        try:
            if exc_value is None:
                self.assert_stable()
        except BaseException as error:
            self.fd = None
            _close_after_error(descriptor, error)
            raise
        self.fd = None
        if exc_value is not None:
            _close_after_error(descriptor, exc_value)
        else:
            os.close(descriptor)

    def read(self, name: str, digest: str, size: int | None, limit: int) -> bytes:
        validate_image_hash(digest)
        if (
            not isinstance(name, str)
            or (name != "capture.json" and not re.fullmatch(r"[0-9a-f]{64}\.bin", name))
            or type(limit) is not int
            or not 1 <= limit <= MAX_JSON
            or (size is not None and (type(size) is not int or not 1 <= size <= limit))
        ):
            raise ProfileError("CAPTURE_RANGE", "Invalid capture read")
        self.assert_stable()
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        with _owned_stream(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) & 0o077
                or not 1 <= before.st_size <= limit
                or (size is not None and before.st_size != size)
            ):
                raise ProfileError("CAPTURE_FILE", "Invalid private capture file")
            data = stream.read(limit + 1)
            if len(data) != before.st_size or hashlib.sha256(data).hexdigest() != digest:
                raise ProfileError("CAPTURE_HASH", "Capture bytes differ")
            if _identity(before) != _identity(os.fstat(stream.fileno())):
                raise ProfileError("CAPTURE_CHANGED", "Capture changed during read")
        self.observed[name] = _identity(before)
        self.assert_stable()
        return data

    def document(self, digest: str) -> dict:
        raw = self.read("capture.json", digest, None, MAX_JSON)
        try:
            result = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_constant,
            )
            if not isinstance(result, dict):
                raise ValueError("object required")
            return result
        except (ValueError, RecursionError) as error:
            raise ProfileError("CAPTURE_JSON", "Invalid capture JSON") from error

    def blob(self, digest: str, size: int) -> bytes:
        return self.read(digest + ".bin", digest, size, 4096)
