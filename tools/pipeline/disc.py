"""Disc identification policy; no filesystem, ISO library, extraction or offsets."""

import re
from typing import Protocol

from tools.pipeline.profile import FileInspector, ProfileError, parse_profile, safe_relative_path


class DiscReader(FileInspector, Protocol):
    def paths(self) -> tuple[str, ...]:
        """Return unique relative file paths or raise ProfileError."""

    def read_prefix(self, path: str, limit: int) -> bytes:
        """Read at most limit bytes without changing the source."""


def parse_boot_config(raw: bytes) -> dict[str, str]:
    if len(raw) > 4096:
        raise ProfileError("INVALID_BOOT_CONFIG", "SYSTEM.CNF exceeds 4096 bytes")
    try:
        text = raw.decode("ascii")
    except UnicodeError as error:
        raise ProfileError("INVALID_BOOT_CONFIG", "SYSTEM.CNF must be ASCII") from error
    fields = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or key in fields:
            raise ProfileError("INVALID_BOOT_CONFIG", "Malformed or duplicate SYSTEM.CNF field")
        fields[key] = value
    match = re.fullmatch(r"cdrom0:\\([A-Z]{4})_(\d{3})\.(\d{2});1", fields.get("BOOT2", ""))
    version, video_mode = fields.get("VER", ""), fields.get("VMODE", "")
    if not match or not re.fullmatch(r"\d+\.\d+", version) or video_mode not in {"PAL", "NTSC"}:
        raise ProfileError("INVALID_BOOT_CONFIG", "Unsupported PS2 boot configuration")
    prefix, first, last = match.groups()
    return {
        "executable": f"{prefix}_{first}.{last}",
        "serial": f"{prefix}-{first}{last}",
        "system_cnf_ver": version,
        "video_mode": video_mode,
    }


def collect_disc(reader: DiscReader, region: str, image_sha256: str) -> dict:
    """Record observed identity, without granting format or runtime compatibility."""
    paths = tuple(sorted(reader.paths()))
    if "SYSTEM.CNF" not in paths:
        raise ProfileError("MISSING_FILE", "Missing SYSTEM.CNF")
    config_size, _ = reader.inspect("SYSTEM.CNF")
    if config_size > 4096:
        raise ProfileError("INVALID_BOOT_CONFIG", "SYSTEM.CNF exceeds 4096 bytes")
    boot = parse_boot_config(reader.read_prefix("SYSTEM.CNF", 4096))
    for path in (boot["executable"], "B0.MFA"):
        if path not in paths:
            raise ProfileError("MISSING_FILE", f"Missing {path}")
    header = reader.read_prefix(boot["executable"], 52)
    if (
        len(header) < 52
        or header[:7] != b"\x7fELF\x01\x01\x01"
        or header[16:24] != b"\x02\0\x08\0\x01\0\0\0"
    ):
        raise ProfileError("INVALID_EXECUTABLE", "Expected an ELF32 little-endian MIPS executable")
    files = []
    for path in paths:
        size, digest = reader.inspect(safe_relative_path(path))
        files.append({"path": path, "size": size, "sha256": digest})
    profile = {
        "schema_version": 1,
        "id": f"ps2-{boot['serial'].lower()}-{image_sha256[:16]}",
        "platform": "ps2",
        "region": region,
        "revision": "unverified",
        "serial": boot["serial"],
        "language": "unverified",
        "extractor_version": "none-inspection-only-v1",
        "capabilities": [],
        "files": files,
    }
    parse_profile(profile)
    return {
        "schema_version": 1,
        "boot": boot,
        "executable_format": "ELF32-little-endian-MIPS",
        "region_source": "operator_declaration",
        "file_count": len(files),
        "profile": profile,
        "extraction": "not_performed",
        "compatibility": "unverified",
    }
