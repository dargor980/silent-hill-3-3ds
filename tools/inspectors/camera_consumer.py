"""Read-only PS2 executable survey linked to pinned camera hypothesis evidence."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.elf32 import parse_elf
from tools.inspectors.inventory import entry_id, validate_image_hash
from tools.inspectors.mips_camera import scan_loops
from tools.pipeline.disc import DiscReader, parse_boot_config
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import GameProfile, ProfileError, parse_profile


class ExecutableReader(DiscReader, Protocol):
    def read_range(self, path: str, offset: int, length: int) -> bytes:
        """Read at most 4096 bytes from a verified member."""


def survey_consumer(
    reader: ExecutableReader,
    profile: GameProfile,
    probe: dict,
    image_size: int,
    image_sha256: str,
    profile_sha256: str,
    probe_sha256: str,
) -> dict:
    for digest in (image_sha256, profile_sha256, probe_sha256):
        validate_image_hash(digest)
    expected_profile = {
        "id": profile.profile_id,
        "platform": profile.platform,
        "region": profile.region,
        "revision": profile.revision,
        "serial": profile.serial,
        "language": profile.language,
    }
    expected_source = {
        "id": "iso:" + image_sha256,
        "size": image_size,
        "sha256": image_sha256,
        "profile": expected_profile,
    }
    if (
        type(image_size) is not int
        or image_size <= 0
        or profile.platform != "ps2"
        or not isinstance(probe, dict)
        or type(probe.get("schema_version")) is not int
        or probe.get("schema_version") != 1
        or probe.get("scope") != "camera_hypothesis_survey"
        or probe.get("method") != "sh2-road128-reference-v1"
        or probe.get("capabilities") != []
        or probe.get("f02_07_status") != "pending"
        or json.dumps(probe.get("source"), sort_keys=True)
        != json.dumps(expected_source, sort_keys=True)
    ):
        raise ProfileError("CONSUMER_EVIDENCE", "Inconsistent camera/executable evidence")
    files = {item.path: item for item in profile.files}
    paths = tuple(reader.paths())
    if len(paths) != len(files) or set(paths) != set(files) or "SYSTEM.CNF" not in files:
        raise ProfileError("PROFILE_MISMATCH", "Disc paths differ from pinned profile")

    def verified(path: str) -> None:
        item = files[path]
        if reader.inspect(path) != (item.size, item.sha256):
            raise ProfileError("HASH_MISMATCH", "Required member differs from profile")

    verified("SYSTEM.CNF")
    config_size = files["SYSTEM.CNF"].size
    if not 0 < config_size <= 4096:
        raise ProfileError("INVALID_BOOT_CONFIG", "Boot configuration exceeds budget")
    raw = reader.read_range("SYSTEM.CNF", 0, config_size)
    if not isinstance(raw, bytes) or len(raw) != config_size:
        raise ProfileError("ELF_SHORT_READ", "Incomplete boot configuration")
    boot = parse_boot_config(raw)
    path = boot["executable"]
    if boot["serial"] != profile.serial or path not in files:
        raise ProfileError("PROFILE_MISMATCH", "Boot target differs from profile")
    verified(path)
    item = files[path]

    def read(offset: int, length: int) -> bytes:
        return reader.read_range(path, offset, length)

    mapping = parse_elf(read, item.size)
    scan = scan_loops(read, mapping)
    return {
        "schema_version": 1,
        "tool": {"name": "sh3-camera-consumer", "version": 1},
        "scope": "boot_executable_static_pattern_only",
        "source": expected_source,
        "evidence": {"profile_sha256": profile_sha256, "camera_probe_sha256": probe_sha256},
        "executable": {
            "id": entry_id(image_sha256, profile.profile_id, path),
            "size": item.size,
            "sha256": item.sha256,
        },
        "elf": {
            "entry_address": mapping.entry,
            "flags": mapping.flags,
            "program_header_count": mapping.program_header_count,
            "load_segments": [asdict(segment) for segment in mapping.segments],
            "memory_only_segment_count": sum(not s.file_size for s in mapping.segments),
            "memory_only_overlaps": "not_resolved",
            "section_and_symbol_tables": "not_inspected",
            "complete_abi_validation": "not_performed",
        },
        "scan": scan,
        "verified_members": 2,
        "other_members_individually_verified": False,
        "capabilities": [],
        "payload_export": "not_performed",
        "binary_execution": "not_performed",
        "confirmed_camera_consumers": 0,
        "f02_07_status": "pending",
        "unresolved": ["resource_pointer_origin", "reachability", "tail", "fields_92_108"],
        "next_task": "F02.07/camera-pointer-origin-eu",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("iso", "profile", "camera-probe", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("image-sha256", "profile-sha256", "camera-probe-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Report already exists")
        validate_image_hash(args.image_sha256)
        profile = parse_profile(load_catalog(args.profile, args.profile_sha256))
        probe = load_catalog(args.camera_probe, args.camera_probe_sha256)
        with IsoImage(args.iso) as image:
            size, digest = image.image_identity()
            if digest != args.image_sha256:
                raise ProfileError("IMAGE_MISMATCH", "Image differs from pinned identity")
            report = survey_consumer(
                image, profile, probe, size, digest, args.profile_sha256, args.camera_probe_sha256
            )
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError) as error:
        code = error.code if isinstance(error, ProfileError) else "CONSUMER_IO_ERROR"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(
        json.dumps(
            {
                "status": "surveyed",
                "candidates": report["scan"]["candidate_count"],
                "confirmed_camera_consumers": 0,
                "f02_07_status": "pending",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
