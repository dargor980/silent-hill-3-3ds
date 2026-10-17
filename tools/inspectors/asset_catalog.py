"""Catalog verified MFA resources into private metadata; never export payloads."""

import argparse
import hashlib
import json
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Protocol

from tools.inspectors.asset_selection import AssetSelection, load_selection, validate_selection
from tools.inspectors.inventory import collect_inventory, validate_image_hash
from tools.inspectors.mfa import MfaError, parse_layout
from tools.inspectors.mfa_probe import MemberRange, ProbeReader
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import GameProfile, ProfileError
from tools.pipeline.verify import load_profile

MAX_ASSETS = 100000


class AssetReader(ProbeReader, Protocol):
    def hash_range(self, path: str, offset: int, length: int) -> tuple[int, str]:
        """Return exact size and lowercase SHA-256, or raise a transport error."""


def asset_id(container_id: str, block_offset: int, entry_index: int) -> str:
    key = "\0".join(("sh3-asset-v1", container_id, str(block_offset), str(entry_index)))
    return "asset:" + hashlib.sha256(key.encode("utf-8")).hexdigest()


def collect_assets(
    reader: AssetReader,
    profile: GameProfile,
    image_size: int,
    image_sha256: str,
    selection: AssetSelection,
) -> dict:
    validate_selection(selection, profile, image_sha256)
    inventory = collect_inventory(reader, profile, image_size, image_sha256)
    choices = {c.path: c for c in selection.containers}
    containers, entries, outside_scope = [], [], []
    block_count = 0
    for parent in inventory["entries"]:
        path = parent["path"]
        if path not in choices:
            outside_scope.append(parent)
            continue
        layout = choices[path].layout
        container = {k: parent[k] for k in ("id", "path", "offset", "size", "sha256")}
        container["layout"] = layout
        try:
            index = parse_layout(MemberRange(reader, path), parent["size"], layout)
        except MfaError as error:
            container["result"] = {
                "status": "unknown",
                "code": error.code,
                "details": error.details,
            }
            containers.append(container)
            continue
        if len(entries) + len(index.entries) > MAX_ASSETS:
            raise ProfileError("CATALOG_LIMIT", "Resource catalog budget exceeded")
        # No resource hashing until this container's complete structure has passed.
        for item in index.entries:
            size, digest = reader.hash_range(path, item.offset, item.size)
            if type(size) is not int or size != item.size:
                raise ProfileError("SIZE_MISMATCH", "Resource hash length differs from descriptor")
            validate_image_hash(digest)
            location = {
                k: v
                for k, v in asdict(item).items()
                if k in ("block_index", "block_offset", "entry_index", "entry_ordinal")
            }
            entries.append(
                {
                    "id": asset_id(parent["id"], item.block_offset, item.entry_index),
                    "origin": parent["origin"],
                    "container_id": parent["id"],
                    **location,
                    "container_offset": item.offset,
                    "iso_offset": parent["offset"] + item.offset,
                    "size": size,
                    "sha256": digest,
                    "source_name": item.name,
                    "source_name_encoding": "ascii",
                    "source_name_offset": item.name_offset,
                    "unknown_word": item.unknown_word,
                    "classification": {"type": "unknown", "reason": "not_decoded"},
                    "dependencies": {"status": "not_inspected", "known": []},
                    "support": "metadata_and_hash_only",
                }
            )
        container["result"] = index.summary
        block_count += index.summary["block_count"]
        containers.append(container)
    known = sum(c["result"]["status"] == "structural_candidate" for c in containers)
    return {
        "schema_version": 1,
        "scope": "selected_mfa_entries",
        "tool": {"name": "sh3-asset-catalog", "version": 1},
        "source": inventory["source"],
        "selection": {"schema_version": 1, "canonical_sha256": selection.digest()},
        "containers": containers,
        "entries": entries,
        "outside_scope": outside_scope,
        "summary": {
            "candidate_container_count": len(containers),
            "catalogued_container_count": known,
            "unknown_container_count": len(containers) - known,
            "block_count": block_count,
            "entry_count": len(entries),
            "payload_bytes": sum(e["size"] for e in entries),
            "outside_scope_file_count": len(outside_scope),
        },
        "extraction": "not_performed",
        "payload_decoding": "not_performed",
        "capabilities": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--image-sha256", required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New private metadata JSON")
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Report destination already exists")
        validate_image_hash(args.image_sha256)
        profile = load_profile(args.profile)
        selection = load_selection(args.selection)
        validate_selection(selection, profile, args.image_sha256)
        with IsoImage(args.iso) as image:
            size, digest = image.image_identity()
            if digest != args.image_sha256:
                raise ProfileError("IMAGE_MISMATCH", "Image differs from prior identification")
            report = collect_assets(image, profile, size, digest, selection)
            report["tool"]["pycdlib"] = version("pycdlib")
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
        except OSError as error:
            raise ProfileError("REPORT_WRITE_ERROR", "Cannot create resource catalog") from error
    except ProfileError as error:
        print(json.dumps({"status": "rejected", "code": error.code, "message": str(error)}))
        return 1
    print(json.dumps({"status": "catalogued", **report["summary"], "extraction": "not_performed"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
