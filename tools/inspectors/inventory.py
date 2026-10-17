"""Inventory policy over a verified reader; no filesystem or ISO dependency."""

import hashlib
import re
from collections import Counter
from pathlib import PurePosixPath
from typing import Protocol

from tools.inspectors.signatures import PREFIX_LIMIT, classify
from tools.pipeline.disc import DiscReader
from tools.pipeline.profile import GameProfile, ProfileError, safe_relative_path, verify_profile


class InventoryReader(DiscReader, Protocol):
    def file_offset(self, path: str) -> int:
        """Return a contiguous member's byte offset from the ISO start."""


def validate_image_hash(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ProfileError("INVALID_IMAGE_HASH", "Expected a complete lowercase SHA-256")


def entry_id(image_sha256: str, profile_id: str, path: str) -> str:
    identity = "\x00".join(("sh3-inventory-v1", image_sha256, profile_id, path))
    return "entry:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def collect_inventory(
    reader: InventoryReader, profile: GameProfile, image_size: int, image_sha256: str
) -> dict:
    validate_image_hash(image_sha256)
    if type(image_size) is not int or not 0 < image_size <= (1 << 63) - 1:
        raise ProfileError("INVALID_SIZE", "Expected a bounded positive image size")
    if profile.platform != "ps2":
        raise ProfileError("PROFILE_MISMATCH", "Expected a PS2 disc profile")
    paths = tuple(reader.paths())
    expected_paths = {item.path for item in profile.files}
    if len(paths) != len(expected_paths) or set(paths) != expected_paths:
        raise ProfileError("PROFILE_MISMATCH", "Profile must describe the complete disc")
    if "SYSTEM.CNF" not in paths:
        raise ProfileError("MISSING_FILE", "Missing SYSTEM.CNF")
    # Verify every entry before any prefix is interpreted, including unknown formats.
    verify_profile(profile, reader)
    files = {item.path: item for item in profile.files}
    source_id = "iso:" + image_sha256
    entries = []
    for path in sorted(paths):
        safe_relative_path(path)
        item = files[path]
        offset = reader.file_offset(path)
        if type(offset) is not int or offset < 0 or offset + item.size > image_size:
            raise ProfileError("INVALID_OFFSET", "Member range exceeds image")
        prefix = reader.read_prefix(path, min(item.size, PREFIX_LIMIT))
        classification = classify(path, prefix, item.size)
        dependencies = {"status": "not_inspected", "known": []}
        if classification["type"] == "ps2_boot_config":
            boot = classification["boot"]
            if boot["serial"] != profile.serial or boot["executable"] not in paths:
                raise ProfileError("PROFILE_MISMATCH", "Boot configuration differs from profile")
            dependencies = {
                "status": "partial",
                "known": [
                    {
                        "target_id": entry_id(image_sha256, profile.profile_id, boot["executable"]),
                        "relation": "boot_executable",
                        "evidence": "SYSTEM.CNF:BOOT2",
                    }
                ],
            }
        entries.append(
            {
                "id": entry_id(image_sha256, profile.profile_id, path),
                "path": path,
                "origin": {"profile_id": profile.profile_id, "image_id": source_id},
                "container_id": source_id,
                "offset": offset,
                "size": item.size,
                "sha256": item.sha256,
                "extension_hint": PurePosixPath(path).suffix.lower(),
                "classification": classification,
                "dependencies": dependencies,
                "support": "inventory_only",
            }
        )
    by_path = {entry["path"]: entry for entry in entries}
    executable = by_path["SYSTEM.CNF"]["classification"]["boot"]["executable"]
    if by_path[executable]["classification"]["type"] != "elf32_le_mips":
        raise ProfileError("INVALID_EXECUTABLE", "Boot executable header is not supported")
    return {
        "schema_version": 1,
        "source": {
            "id": source_id,
            "size": image_size,
            "sha256": image_sha256,
            "profile": {
                "id": profile.profile_id,
                "platform": profile.platform,
                "region": profile.region,
                "revision": profile.revision,
                "serial": profile.serial,
                "language": profile.language,
            },
        },
        "scope": "iso_files_only",
        "entries": entries,
        "summary": {
            "file_count": len(entries),
            "type_counts": dict(
                sorted(Counter(e["classification"]["type"] for e in entries).items())
            ),
            "recognition_counts": dict(
                sorted(Counter(e["classification"]["recognition"] for e in entries).items())
            ),
        },
        "extraction": "not_performed",
        "nested_inventory": "not_performed",
        "capabilities": [],
    }
