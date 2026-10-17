"""Probe one explicitly selected MFA layout on a verified ISO; metadata only."""

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Protocol

from tools.inspectors.inventory import InventoryReader, collect_inventory, validate_image_hash
from tools.inspectors.mfa import LAYOUTS, MfaError, inspect_layout, layout_descriptor
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import GameProfile, ProfileError
from tools.pipeline.verify import load_profile


class ProbeReader(InventoryReader, Protocol):
    def read_range(self, path: str, offset: int, length: int) -> bytes:
        """Return an exact bounded range relative to a member."""


@dataclass(frozen=True)
class MemberRange:
    reader: ProbeReader
    path: str

    def read_at(self, offset: int, length: int) -> bytes:
        return self.reader.read_range(self.path, offset, length)


def collect_probe(
    reader: ProbeReader,
    profile: GameProfile,
    image_size: int,
    image_sha256: str,
    layout: str = "d8",
) -> dict:
    _, layout_id = layout_descriptor(layout)
    inventory = collect_inventory(reader, profile, image_size, image_sha256)
    entries = []
    for entry in inventory["entries"]:
        if entry["extension_hint"] != ".mfa":
            continue
        try:
            result = inspect_layout(MemberRange(reader, entry["path"]), entry["size"], layout)
        except MfaError as error:
            result = {"status": "unknown", "code": error.code, "details": error.details}
        entries.append(
            {**{k: entry[k] for k in ("id", "path", "size", "sha256")}, "result": result}
        )
    return {
        "schema_version": 2,
        "source": inventory["source"],
        "scope": "mfa_structure_only",
        "selection": {"mode": "fixed_layout", "layout": layout},
        "tool": {"name": "sh3-mfa-probe", "version": 2, "layout": layout_id},
        "entries": entries,
        "summary": {
            "candidate_count": len(entries),
            "status_counts": dict(sorted(Counter(e["result"]["status"] for e in entries).items())),
            "structural_entry_count": sum(e["result"].get("entry_count", 0) for e in entries),
            "structural_block_count": sum(e["result"].get("block_count", 0) for e in entries),
        },
        "extraction": "not_performed",
        "payload_validation": "not_performed",
        "capabilities": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--image-sha256", required=True)
    parser.add_argument("--layout", choices=tuple(LAYOUTS), default="d8")
    parser.add_argument("--output", type=Path, required=True, help="New private metadata JSON")
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Report destination already exists")
        validate_image_hash(args.image_sha256)
        profile = load_profile(args.profile)
        with IsoImage(args.iso) as image:
            size, digest = image.image_identity()
            if digest != args.image_sha256:
                raise ProfileError("IMAGE_MISMATCH", "Image differs from prior identification")
            report = collect_probe(image, profile, size, digest, args.layout)
            report["tool"]["pycdlib"] = version("pycdlib")
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
        except OSError as error:
            raise ProfileError("REPORT_WRITE_ERROR", "Cannot create probe report") from error
    except ProfileError as error:
        print(json.dumps({"status": "rejected", "code": error.code, "message": str(error)}))
        return 1
    print(json.dumps({"status": "probed", **report["summary"], "extraction": "not_performed"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
