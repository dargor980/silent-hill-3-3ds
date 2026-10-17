"""Read-only, bounded observations over previously extracted private resources."""

import os
import stat
from pathlib import Path

from tools.inspectors.inventory import validate_image_hash
from tools.pipeline.hashing import fingerprint_stream
from tools.pipeline.private_files import (
    _identity,
    _inode,
    _open_directory,
    _owned_stream,
)
from tools.pipeline.private_output import resource_filename
from tools.pipeline.profile import ProfileError

MAX_RANGE_BYTES = 4096


class VerifiedPrivateReader:
    def __init__(self, root: Path, repository: Path):
        resolved, checkout = root.resolve(), repository.resolve()
        if resolved.is_relative_to(checkout) or checkout.is_relative_to(resolved):
            raise ProfileError("PRIVATE_DATA_IN_REPO", "Private copy must be external")
        self.root, self.descriptor = root, None

    def __enter__(self):
        try:
            self.descriptor = _open_directory(self.root)
        except OSError as error:
            raise ProfileError("PRIVATE_READ_ERROR", "Cannot open private copy") from error
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        descriptor, self.descriptor = self.descriptor, None
        try:
            os.close(descriptor)
        except OSError as error:
            if exc_value is not None:
                exc_value.add_note("Private reader cleanup also failed; close attempted once")
            else:
                raise ProfileError("PRIVATE_READ_ERROR", "Cannot close private copy") from error

    def _assert_attached(self):
        current = _open_directory(self.root)
        try:
            if _inode(os.fstat(current)) != _inode(os.fstat(self.descriptor)):
                raise ProfileError("PRIVATE_CHANGED", "Private directory was replaced")
        finally:
            os.close(current)

    def verify_set(self, resources: list[dict]) -> None:
        try:
            self._assert_attached()
            expected = {resource_filename(item["id"]) for item in resources}
            if len(expected) != len(resources) or set(os.listdir(self.descriptor)) != expected:
                raise ProfileError("PRIVATE_SET_MISMATCH", "Private file set differs")
        except OSError as error:
            raise ProfileError("PRIVATE_READ_ERROR", "Cannot inspect private copy") from error

    def read_verified(self, resource: dict, offset: int, length: int) -> bytes:
        filename = resource_filename(resource["id"])
        validate_image_hash(resource["sha256"])
        size = resource["size"]
        if type(size) is not int or not 0 <= size <= (1 << 63) - 1:
            raise ProfileError("INVALID_SIZE", "Invalid resource size")
        if (
            type(offset) is not int
            or type(length) is not int
            or not 0 <= length <= MAX_RANGE_BYTES
            or not 0 <= offset <= size
            or offset + length > size
        ):
            raise ProfileError("INVALID_RANGE", "Observation range exceeds bounds")
        try:
            self._assert_attached()
            fd = os.open(
                filename,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=self.descriptor,
            )
            with _owned_stream(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                    raise ProfileError("INVALID_PRIVATE_FILE", "Expected one regular resource")
                if before.st_size != size:
                    raise ProfileError("SIZE_MISMATCH", "Private size differs from evidence")
                observed = fingerprint_stream(stream, size)
                if observed["sha256"] != resource["sha256"]:
                    raise ProfileError("PRIVATE_HASH_MISMATCH", "Private hash differs")
                # Only expose a bounded range after the full hash has passed.
                stream.seek(offset)
                data = bytearray()
                while len(data) < length:
                    part = stream.read(length - len(data))
                    if not part or len(part) > length - len(data):
                        raise ProfileError("SIZE_MISMATCH", "Incomplete private range")
                    data.extend(part)
                after = os.fstat(stream.fileno())
            named = os.stat(filename, dir_fd=self.descriptor, follow_symlinks=False)
            if (
                _identity(before) != _identity(after)
                or _identity(after) != _identity(named)
                or not stat.S_ISREG(named.st_mode)
                or after.st_nlink != 1
                or named.st_nlink != 1
            ):
                raise ProfileError("PRIVATE_CHANGED", "Private resource changed")
            self._assert_attached()
            return bytes(data)
        except OSError as error:
            raise ProfileError("PRIVATE_READ_ERROR", "Private resource I/O failed") from error
