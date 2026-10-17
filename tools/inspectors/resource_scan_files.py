"""RL04/RL06: anchored, verified streaming scans and late stability checks."""

import os
import stat

from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.inspectors.resource_match import scan_stream
from tools.pipeline.private_files import _identity, _owned_stream
from tools.pipeline.private_output import resource_filename
from tools.pipeline.profile import ProfileError


class VerifiedResourceScanner(VerifiedPrivateReader):
    def __enter__(self):
        super().__enter__()
        self.observed = {}
        self.expected = None
        try:
            self.assert_stable()
        except BaseException as error:
            super().__exit__(type(error), error, error.__traceback__)
            raise
        return self

    def verify_set(self, resources):
        super().verify_set(resources)
        self.expected = {resource_filename(r["id"]) for r in resources}

    def assert_stable(self):
        self._assert_attached()
        if stat.S_IMODE(os.fstat(self.descriptor).st_mode) != 0o700:
            raise ProfileError("MATCH_PRIVATE", "Resource directory is not private")
        if self.expected is not None and set(os.listdir(self.descriptor)) != self.expected:
            raise ProfileError("MATCH_CHANGED", "Resource set changed before close")
        for name, identity in self.observed.items():
            if _identity(os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)) != identity:
                raise ProfileError("MATCH_CHANGED", "Previously scanned resource changed")

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_value is None:
                self.assert_stable()
        except BaseException as error:
            super().__exit__(type(error), error, error.__traceback__)
            raise
        super().__exit__(exc_type, exc_value, traceback)

    def scan_verified(self, resource: dict, patterns: dict[str, bytes]) -> dict:
        self._assert_attached()
        name = resource_filename(resource["id"])
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.descriptor)
        with _owned_stream(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_size != resource["size"]
            ):
                raise ProfileError("MATCH_PRIVATE", "Invalid private resource")
            digest, hits = scan_stream(stream, resource["size"], patterns)
            if digest != resource["sha256"]:
                raise ProfileError("MATCH_HASH", "Resource differs from catalog")
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise ProfileError("MATCH_CHANGED", "Resource changed during scan")
        if _identity(os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)) != _identity(
            before
        ):
            raise ProfileError("MATCH_CHANGED", "Resource changed before close")
        self.observed[name] = _identity(before)
        self._assert_attached()
        return hits
