"""Revalidate pointer evidence and inspect a bounded level of caller/callee state."""

import argparse
import json
from pathlib import Path

from tools.inspectors.call_boundary import inspect_boundaries
from tools.inspectors.camera_consumer import ExecutableReader
from tools.inspectors.camera_pointer import survey_pointers
from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.elf32 import parse_elf
from tools.inspectors.inventory import entry_id, validate_image_hash
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import GameProfile, ProfileError, parse_profile


def survey_boundaries(
    reader: ExecutableReader,
    profile: GameProfile,
    probe: dict,
    consumer: dict,
    pointer: dict,
    repeat: dict,
    image_size: int,
    hashes: dict,
) -> dict:
    for name in ("image", "profile", "probe", "consumer", "pointer", "repeat"):
        validate_image_hash(hashes[name])
    if hashes["pointer"] != hashes["repeat"] or json.dumps(pointer, sort_keys=True) != json.dumps(
        repeat, sort_keys=True
    ):
        raise ProfileError("BOUNDARY_EVIDENCE", "Pointer repetitions differ")
    current = survey_pointers(
        reader,
        profile,
        probe,
        consumer,
        image_size,
        hashes["image"],
        hashes["profile"],
        hashes["probe"],
        hashes["consumer"],
    )
    if json.dumps(current, sort_keys=True) != json.dumps(pointer, sort_keys=True):
        raise ProfileError("BOUNDARY_EVIDENCE", "Pointer evidence differs from source")
    item = next(
        f
        for f in profile.files
        if entry_id(hashes["image"], profile.profile_id, f.path) == current["executable"]["id"]
    )

    def read(offset, length):
        return reader.read_range(item.path, offset, length)

    analysis = inspect_boundaries(read, parse_elf(read, item.size), current["analysis"]["sites"])
    return {
        "schema_version": 1,
        "tool": {"name": "sh3-camera-boundary", "version": 1},
        "source": current["source"],
        "executable": current["executable"],
        "evidence": {
            **current["evidence"],
            "pointer_sha256": hashes["pointer"],
            "repeat_sha256": hashes["repeat"],
        },
        "scope": "partial_static_call_boundaries",
        "analysis": analysis,
        "summary": {
            "boundaries": len(analysis["boundaries"]),
            "preserved_in_model": sum(
                b.get("callee", {}).get("effect") == "preserved_in_model"
                for b in analysis["boundaries"]
            ),
            "confirmed_resource_links": 0,
        },
        "capabilities": [],
        "binary_execution": "not_performed",
        "payload_export": "not_performed",
        "f02_07_status": "pending",
        "next_task": "F02.07/camera-runtime-observation-plan-eu",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "iso",
        "profile",
        "camera-probe",
        "consumer",
        "pointer",
        "pointer-repeat",
        "output",
    ):
        parser.add_argument("--" + name, required=True, type=Path)
    names = {
        "image": "image",
        "profile": "profile",
        "probe": "camera-probe",
        "consumer": "consumer",
        "pointer": "pointer",
        "repeat": "pointer-repeat",
    }
    for flag in names.values():
        parser.add_argument("--" + flag + "-sha256", required=True)
    args = parser.parse_args(argv)
    hashes = {
        name: getattr(args, flag.replace("-", "_") + "_sha256") for name, flag in names.items()
    }
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Report already exists")
        validate_image_hash(hashes["image"])
        profile = parse_profile(load_catalog(args.profile, hashes["profile"]))
        probe = load_catalog(args.camera_probe, hashes["probe"])
        consumer = load_catalog(args.consumer, hashes["consumer"])
        pointer = load_catalog(args.pointer, hashes["pointer"])
        repeat = load_catalog(args.pointer_repeat, hashes["repeat"])
        with IsoImage(args.iso) as image:
            size, digest = image.image_identity()
            if digest != hashes["image"]:
                raise ProfileError("IMAGE_MISMATCH", "Image differs from pinned identity")
            report = survey_boundaries(
                image, profile, probe, consumer, pointer, repeat, size, hashes
            )
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError) as error:
        code = error.code if isinstance(error, ProfileError) else "BOUNDARY_IO_ERROR"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "surveyed", **report["summary"], "f02_07_status": "pending"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
