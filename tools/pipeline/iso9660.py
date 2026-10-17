"""Read-only ISO9660 adapter. No game-specific layout and no resource export."""

import os
from contextlib import AbstractContextManager
from pathlib import Path

import pycdlib
from pycdlib.pycdlibexception import PyCdlibException

from tools.pipeline.hashing import fingerprint_range, fingerprint_stream
from tools.pipeline.profile import ProfileError, safe_relative_path
from tools.pipeline.transfer import copy_exact

MAX_FILES = 10000


def _identity(stat: os.stat_result) -> tuple[int, ...]:
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


class IsoImage(AbstractContextManager):
    def __init__(self, path: Path):
        self.path = path
        self.iso = pycdlib.PyCdlib()
        self._opened = False
        self.stream = None
        self._entries: dict[str, tuple[str, int]] = {}
        self._offsets: dict[str, int] = {}
        self._digests: dict[str, tuple[int, str]] = {}

    def __enter__(self):
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise ProfileError(
                    "ISO_READ_ERROR", "ISO input must be a regular, non-symlink file"
                )
            self.stream = self.path.open("rb")
            self.before = os.fstat(self.stream.fileno())
            self.iso.open_fp(self.stream)
            self._opened = True
            self._index()
            return self
        except (OSError, PyCdlibException, UnicodeError, ValueError) as error:
            self._close()
            if isinstance(error, ProfileError):
                raise
            code = "ISO_READ_ERROR" if isinstance(error, OSError) else "INVALID_ISO"
            raise ProfileError(code, "Cannot inspect ISO9660 input") from error

    def _index(self) -> None:
        seen = set()
        directories = 0
        for directory, _, files in self.iso.walk(iso_path="/"):
            directories += 1
            if directories > MAX_FILES:
                raise ProfileError("ISO_LIMIT", "Too many ISO directories")
            for name in files:
                iso_path = f"{directory.rstrip('/')}/{name}"
                if not iso_path.endswith(";1"):
                    raise ProfileError("UNSUPPORTED_ISO", "Only ISO file version 1 is supported")
                path = safe_relative_path(iso_path[1:-2])
                if ";" in path or path.casefold() in seen:
                    raise ProfileError("INVALID_PATH", "Ambiguous ISO file path")
                seen.add(path.casefold())
                record = self.iso.get_record(iso_path=iso_path)
                size = record.data_length
                start = record.extent_location() * self.iso.pvd.logical_block_size()
                if record.file_flags & 0x80:
                    raise ProfileError(
                        "UNSUPPORTED_ISO", "Multi-extent ISO files are not supported"
                    )
                if record.xattr_len or record.file_unit_size or record.interleave_gap_size:
                    raise ProfileError(
                        "UNSUPPORTED_ISO", "Extended attributes/interleaved files are unsupported"
                    )
                if size < 0 or start < 0 or start + size > self.before.st_size:
                    raise ProfileError("INVALID_ISO", "ISO file extent exceeds image")
                self._entries[path] = iso_path, size
                self._offsets[path] = start
                if len(self._entries) > MAX_FILES:
                    raise ProfileError("ISO_LIMIT", "Too many ISO files")

    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))

    def _entry(self, path: str) -> tuple[str, int]:
        path = safe_relative_path(path)
        if path not in self._entries:
            raise ProfileError("MISSING_FILE", f"Missing ISO member: {path}")
        return self._entries[path]

    def read_prefix(self, path: str, limit: int) -> bytes:
        if not 0 <= limit <= 4096:
            raise ProfileError("READ_LIMIT", "ISO prefix limit must be 0..4096 bytes")
        iso_path, _ = self._entry(path)
        try:
            with self.iso.open_file_from_iso(iso_path=iso_path) as stream:
                return stream.read(limit)
        except (OSError, PyCdlibException) as error:
            raise ProfileError("ISO_READ_ERROR", "Cannot read ISO member prefix") from error

    def file_offset(self, path: str) -> int:
        """Byte offset of a contiguous ISO member, relative to the image start."""
        self._entry(path)
        return self._offsets[path]

    def read_range(self, path: str, offset: int, length: int) -> bytes:
        """Exact bounded read, relative to one contiguous member, never the whole ISO."""
        if type(length) is not int or not 0 <= length <= 4096:
            raise ProfileError("READ_LIMIT", "ISO range length must be 0..4096 bytes")
        iso_path, size = self._entry(path)
        if type(offset) is not int or offset < 0 or offset + length > size:
            raise ProfileError("READ_RANGE", "Requested range exceeds ISO member")
        try:
            with self.iso.open_file_from_iso(iso_path=iso_path) as stream:
                stream.seek(offset)
                data = stream.read(length)
        except (OSError, PyCdlibException) as error:
            raise ProfileError("ISO_READ_ERROR", "Cannot read ISO member range") from error
        if len(data) != length:
            raise ProfileError("SHORT_READ", "Incomplete ISO member range")
        return data

    def inspect(self, path: str) -> tuple[int, str]:
        iso_path, expected = self._entry(path)
        if path not in self._digests:
            try:
                with self.iso.open_file_from_iso(iso_path=iso_path) as stream:
                    result = self._hash(stream, expected)
            except (OSError, PyCdlibException) as error:
                raise ProfileError("ISO_READ_ERROR", "Cannot hash ISO member") from error
            self._digests[path] = result
        return self._digests[path]

    def hash_range(self, path: str, offset: int, length: int) -> tuple[int, str]:
        """Hash an exact member-relative range with one open and bounded reads."""
        iso_path, size = self._entry(path)
        if (
            type(offset) is not int
            or type(length) is not int
            or offset < 0
            or length < 0
            or offset + length > size
        ):
            raise ProfileError("READ_RANGE", "Requested hash range exceeds ISO member")
        try:
            with self.iso.open_file_from_iso(iso_path=iso_path) as stream:
                stream.seek(offset)
                result = fingerprint_range(stream, length)
        except (OSError, PyCdlibException) as error:
            raise ProfileError("ISO_READ_ERROR", "Cannot hash ISO member range") from error
        return result["size"], result["sha256"]

    @staticmethod
    def _hash(stream, expected: int) -> tuple[int, str]:
        identity = fingerprint_stream(stream, expected)
        return identity["size"], identity["sha256"]

    def copy_range(self, path: str, offset: int, length: int, destination) -> tuple[int, str]:
        """Stream exactly one validated member range to an already-open destination."""
        iso_path, size = self._entry(path)
        if (
            type(offset) is not int
            or type(length) is not int
            or offset < 0
            or length < 0
            or offset + length > size
        ):
            raise ProfileError("READ_RANGE", "Requested copy range exceeds ISO member")
        try:
            with self.iso.open_file_from_iso(iso_path=iso_path) as stream:
                stream.seek(offset)
                return copy_exact(stream, destination, length)
        except (OSError, PyCdlibException) as error:
            raise ProfileError("COPY_IO_ERROR", "Cannot transfer ISO member range") from error

    def image_fingerprints(self) -> dict:
        try:
            self.stream.seek(0)
            return fingerprint_stream(self.stream, self.before.st_size, include_catalog=True)
        except OSError as error:
            raise ProfileError("ISO_READ_ERROR", "Cannot hash ISO image") from error

    def image_identity(self) -> tuple[int, str]:
        try:
            self.stream.seek(0)
            return self._hash(self.stream, self.before.st_size)
        except OSError as error:
            raise ProfileError("ISO_READ_ERROR", "Cannot hash ISO image") from error

    def _close(self) -> None:
        try:
            if self._opened:
                self.iso.close()
                self._opened = False
        finally:
            if self.stream is not None:
                self.stream.close()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                try:
                    changed = _identity(self.before) != _identity(
                        os.fstat(self.stream.fileno())
                    ) or _identity(self.before) != _identity(self.path.stat())
                except OSError as error:
                    raise ProfileError(
                        "INPUT_CHANGED", "ISO input changed while reading"
                    ) from error
                if changed:
                    raise ProfileError("INPUT_CHANGED", "ISO input changed while reading")
        finally:
            self._close()
        return False
