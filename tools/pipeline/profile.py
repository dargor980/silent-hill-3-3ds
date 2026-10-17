"""Pure profile validation and verification policies (RF01, RNF06)."""

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol


class ProfileError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RequiredFile:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class GameProfile:
    profile_id: str
    platform: str
    region: str
    revision: str
    serial: str
    language: str
    extractor_version: str
    capabilities: tuple[str, ...]
    files: tuple[RequiredFile, ...]


class FileInspector(Protocol):
    def inspect(self, relative_path: str) -> tuple[int, str]:
        """Return size and SHA-256 or raise ProfileError; never modify an input."""


def _text(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ProfileError("INVALID_PROFILE", f"Invalid field: {key}")
    return value


def safe_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ProfileError("INVALID_PATH", "Expected a bounded relative path")
    parts = value.split("/")
    if (
        PurePosixPath(value).is_absolute()
        or any(part in ("", ".", "..") for part in parts)
        or "\\" in value
        or ":" in value
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ProfileError("INVALID_PATH", "Absolute, ambiguous or escaping path")
    return value


def parse_profile(data: object) -> GameProfile:
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        raise ProfileError("INVALID_PROFILE", "Missing integer schema_version")
    if data["schema_version"] != 1:
        raise ProfileError("UNSUPPORTED_SCHEMA", "Only profile schema 1 is supported")
    profile_id = _text(data, "id")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", profile_id):
        raise ProfileError("INVALID_PROFILE", "Invalid profile ID")
    platform = _text(data, "platform")
    if platform not in ("ps2", "synthetic"):
        raise ProfileError("INVALID_PROFILE", "Unsupported source platform")
    metadata = {
        key: _text(data, key)
        for key in ("region", "revision", "serial", "language", "extractor_version")
    }
    capabilities = data.get("capabilities")
    if (
        not isinstance(capabilities, list)
        or len(capabilities) > 128
        or any(
            not isinstance(item, str) or not item.strip() or len(item) > 128
            for item in capabilities
        )
        or len(set(capabilities)) != len(capabilities)
    ):
        raise ProfileError("INVALID_PROFILE", "Invalid capabilities")
    entries = data.get("files")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 10000:
        raise ProfileError("INVALID_PROFILE", "Expected 1..10000 required files")
    files = []
    paths: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise ProfileError("INVALID_PROFILE", "File entry must be an object")
        path = safe_relative_path(item.get("path"))
        if path.casefold() in paths:
            raise ProfileError("INVALID_PROFILE", "Duplicate or case-ambiguous file path")
        paths.add(path.casefold())
        size, digest = item.get("size"), item.get("sha256")
        if type(size) is not int or not 0 <= size <= (1 << 63) - 1:
            raise ProfileError("INVALID_PROFILE", "Invalid file size")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ProfileError("INVALID_PROFILE", "Expected lowercase SHA-256")
        files.append(RequiredFile(path, size, digest))
    return GameProfile(
        profile_id, platform, **metadata, capabilities=tuple(capabilities), files=tuple(files)
    )


def verify_profile(profile: GameProfile, inspector: FileInspector) -> None:
    """Fail closed at the first mismatch; successful identification is not extraction."""
    for entry in profile.files:
        size, digest = inspector.inspect(entry.path)
        if size != entry.size:
            raise ProfileError("SIZE_MISMATCH", f"Size differs: {entry.path}")
        if digest != entry.sha256:
            raise ProfileError("HASH_MISMATCH", f"SHA-256 differs: {entry.path}")
