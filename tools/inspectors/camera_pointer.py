"""Reconcile prior executable evidence and publish bounded pointer-origin hypotheses."""

import argparse
import json
from pathlib import Path

from tools.inspectors.camera_consumer import ExecutableReader, survey_consumer
from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.elf32 import parse_elf
from tools.inspectors.inventory import entry_id, validate_image_hash
from tools.inspectors.pointer_graph import inspect_pointers
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import GameProfile, ProfileError, parse_profile


def survey_pointers(
    reader: ExecutableReader,
    profile: GameProfile,
    probe: dict,
    prior: dict,
    image_size: int,
    image_sha256: str,
    profile_sha256: str,
    probe_sha256: str,
    consumer_sha256: str,
) -> dict:
    validate_image_hash(consumer_sha256)
    current = survey_consumer(
        reader, profile, probe, image_size, image_sha256, profile_sha256, probe_sha256
    )
    if json.dumps(current, sort_keys=True) != json.dumps(prior, sort_keys=True):
        raise ProfileError("POINTER_EVIDENCE", "Prior consumer evidence differs from source")
    item = next(
        f
        for f in profile.files
        if entry_id(image_sha256, profile.profile_id, f.path) == current["executable"]["id"]
    )

    def read(offset, length):
        return reader.read_range(item.path, offset, length)

    mapping = parse_elf(read, item.size)
    analysis = inspect_pointers(read, mapping, current["scan"]["candidates"])
    counts = {}
    for site in analysis["sites"]:
        for origin in site["trace"]["origins"]:
            counts[origin["kind"]] = counts.get(origin["kind"], 0) + 1
    return {
        "schema_version": 1,
        "tool": {"name": "sh3-camera-pointer", "version": 1},
        "source": current["source"],
        "executable": current["executable"],
        "evidence": {**current["evidence"], "consumer_sha256": consumer_sha256},
        "scope": "partial_static_pointer_origins",
        "analysis": analysis,
        "summary": {
            "sites": analysis["site_count"],
            "origin_counts": dict(sorted(counts.items())),
            "confirmed_resource_links": 0,
        },
        "capabilities": [],
        "binary_execution": "not_performed",
        "payload_export": "not_performed",
        "f02_07_status": "pending",
        "next_task": "F02.07/camera-caller-boundary-eu",
        "unresolved": [
            "caller_state",
            "unknown_effects",
            "resource_identity",
            "tail",
            "fields_92_108",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("iso", "profile", "camera-probe", "consumer", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("image-sha256", "profile-sha256", "camera-probe-sha256", "consumer-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Report already exists")
        validate_image_hash(args.image_sha256)
        profile = parse_profile(load_catalog(args.profile, args.profile_sha256))
        probe = load_catalog(args.camera_probe, args.camera_probe_sha256)
        prior = load_catalog(args.consumer, args.consumer_sha256)
        with IsoImage(args.iso) as image:
            size, digest = image.image_identity()
            if digest != args.image_sha256:
                raise ProfileError("IMAGE_MISMATCH", "Image differs from pinned identity")
            report = survey_pointers(
                image,
                profile,
                probe,
                prior,
                size,
                digest,
                args.profile_sha256,
                args.camera_probe_sha256,
                args.consumer_sha256,
            )
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError) as error:
        code = error.code if isinstance(error, ProfileError) else "POINTER_IO_ERROR"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "surveyed", **report["summary"], "f02_07_status": "pending"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
