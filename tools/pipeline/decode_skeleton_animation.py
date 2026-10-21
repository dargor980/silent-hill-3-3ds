"""Decode one hash-pinned MDL/ANM pair from a complete opaque-name MFA traversal."""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.mfa import parse_layout
from tools.inspectors.mfa_probe import MemberRange
from tools.pipeline.decoders.ps2_animation import (
    MAX_ANIMATION_BYTES,
    AnimationDecodeError,
    decode_animation,
)
from tools.pipeline.decoders.ps2_skeleton import (
    MAX_MODEL_BYTES,
    SkeletonDecodeError,
    decode_skeleton,
)
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.private_texture_output import write_skeleton_animation_bundle
from tools.pipeline.profile import ProfileError, safe_relative_path


class PairReader(Protocol):
    def image_identity(self) -> tuple[int, str]: ...
    def inspect(self, path: str) -> tuple[int, str]: ...
    def read_range(self, path: str, offset: int, length: int) -> bytes: ...


def validate_selection(selection):
    def fields(value, expected):
        if type(value) is not dict or set(value) != set(expected.split()):
            raise ProfileError("SA_SELECTION", "Unexpected selection fields")

    def positive(value, maximum):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ProfileError("SA_SELECTION", "Invalid selection limit")

    fields(selection, "schema_version image_size image_sha256 container model animation")
    if type(selection["schema_version"]) is not int or selection["schema_version"] != 1:
        raise ProfileError("SA_SELECTION", "Unsupported selection schema")
    positive(selection["image_size"], (1 << 63) - 1)
    validate_image_hash(selection["image_sha256"])
    container = selection["container"]
    fields(container, "path size sha256 layout")
    if container["layout"] != "d8":
        raise ProfileError("SA_SELECTION", "This pair contract requires explicit D8")
    safe_relative_path(container["path"])
    positive(container["size"], selection["image_size"])
    validate_image_hash(container["sha256"])
    for name, limit in (("model", MAX_MODEL_BYTES), ("animation", MAX_ANIMATION_BYTES)):
        resource = selection[name]
        fields(resource, "ordinal size sha256")
        positive(resource["ordinal"], 100000)
        positive(resource["size"], min(limit, container["size"]))
        validate_image_hash(resource["sha256"])
    if selection["model"]["ordinal"] == selection["animation"]["ordinal"]:
        raise ProfileError("SA_SELECTION", "Resources must be distinct")


def read_pair_payloads(reader: PairReader, selection: dict) -> tuple[dict, dict, dict]:
    """Acquire the pinned pair once; reusable by independent pure decoders."""
    validate_selection(selection)
    if reader.image_identity() != (selection["image_size"], selection["image_sha256"]):
        raise ProfileError("IMAGE_MISMATCH", "Image differs from selected identity")
    container = selection["container"]
    path = container["path"]
    if reader.inspect(path) != (container["size"], container["sha256"]):
        raise ProfileError("SA_CONTAINER_IDENTITY", "Container differs from selected identity")
    index = parse_layout(
        MemberRange(reader, path), container["size"], "d8", name_policy="opaque_bytes"
    )
    resources, payloads = {}, {}
    for name in ("model", "animation"):
        choice = selection[name]
        if choice["ordinal"] > len(index.entries):
            raise ProfileError("SA_RESOURCE_MISSING", "Selected ordinal is absent")
        entry = index.entries[choice["ordinal"] - 1]
        if entry.size != choice["size"]:
            raise ProfileError("SA_RESOURCE_SIZE", "Selected size differs")
        payload = bytearray()
        for start in range(0, entry.size, 4096):
            length = min(4096, entry.size - start)
            part = reader.read_range(path, entry.offset + start, length)
            if type(part) is not bytes or len(part) != length:
                raise ProfileError("SA_READ_CONTRACT", "Incomplete selected resource")
            payload.extend(part)
        raw = bytes(payload)
        if hashlib.sha256(raw).hexdigest() != choice["sha256"]:
            raise ProfileError("SA_RESOURCE_HASH", "Selected bytes differ")
        payloads[name] = raw
        resources[name] = {
            **choice,
            "block_offset": entry.block_offset,
            "entry_index": entry.entry_index,
            "container_offset": entry.offset,
            "name_bytes_hex": entry.name.hex(),
            "name_encoding": "unresolved",
        }
    return payloads, resources, index.summary


def decode_pair(reader: PairReader, selection: dict) -> tuple[dict[str, bytes], dict]:
    payloads, resources, structure = read_pair_payloads(reader, selection)
    skeleton = decode_skeleton(payloads["model"])
    animation = decode_animation(payloads["animation"], skeleton.model_id, skeleton.parents)
    report = {
        "schema_version": 1,
        "scope": "ps2_skeleton_animation_candidate",
        "status": "decoded_candidate",
        "selection": selection,
        "container_structure": structure,
        "resources": resources,
        "recipe": animation.recipe,
        "model_id": skeleton.model_id,
        "summary": {
            "bones": len(skeleton.parents),
            "roots": skeleton.parents.count(-1),
            "samples": len(animation.frames),
            "tracks": sum(len(frame.tracks) for frame in animation.frames),
        },
        "skeleton_matrices": "stored_columns_pose_space_unverified",
        "animation_time": "sample_index_only_no_rate_or_clip_boundaries",
        "interpolation": "unverified",
        "flag_bit_3": "preserved_uninterpreted",
        "runtime_binding": "unverified",
        "skinning": "not_decoded",
        "capabilities": [],
    }
    documents = {"skeleton": asdict(skeleton), "animation": asdict(animation)}
    return {
        f"{name}.json": (
            json.dumps({"schema_version": 1, **document}, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode()
        for name, document in documents.items()
    }, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("iso", "selection", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("selection-sha256", "run-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        selection = load_catalog(args.selection, args.selection_sha256)
        validate_selection(selection)
        with IsoImage(args.iso) as reader:
            files, report = decode_pair(reader, selection)
        manifest = write_skeleton_animation_bundle(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
        )
    except (ProfileError, SkeletonDecodeError, AnimationDecodeError, OSError) as error:
        code = "SA_IO_ERROR" if isinstance(error, OSError) else getattr(error, "code", str(error))
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "decoded_candidate", **manifest["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
