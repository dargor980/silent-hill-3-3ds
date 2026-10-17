"""Prepare a pinned observation plan or validate an external private capture."""

import argparse
import json
from pathlib import Path

from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.capture_files import PrivateCaptureReader
from tools.inspectors.observation_capture import validate_capture
from tools.inspectors.observation_plan import prepare_plan
from tools.pipeline.extract_assets import canonical, load_catalog
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile

INPUTS = {
    "profile": "profile",
    "probe": "camera-probe",
    "consumer": "consumer",
    "pointer": "pointer",
    "repeat": "pointer-repeat",
    "boundary": "boundary",
    "boundary_repeat": "boundary-repeat",
    "catalog": "catalog",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "validate"))
    for name in ("iso", "output", *INPUTS.values()):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("image", *INPUTS.values()):
        parser.add_argument("--" + name + "-sha256", required=True)
    for name in ("plan", "private-root"):
        parser.add_argument("--" + name, type=Path)
    for name in ("plan-sha256", "capture-sha256"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Report already exists")
        if args.action == "validate" and any(
            getattr(args, n) is None
            for n in ("plan", "private_root", "plan_sha256", "capture_sha256")
        ):
            raise ProfileError("CAPTURE_ARGUMENTS", "Capture validation needs explicit inputs")
        hashes = {
            name: getattr(args, flag.replace("-", "_") + "_sha256") for name, flag in INPUTS.items()
        }
        hashes["image"] = args.image_sha256
        documents = {
            name: load_catalog(getattr(args, flag.replace("-", "_")), hashes[name])
            for name, flag in INPUTS.items()
        }
        profile = parse_profile(documents["profile"])
        with IsoImage(args.iso) as image:
            size, digest = image.image_identity()
            if digest != hashes["image"]:
                raise ProfileError("IMAGE_MISMATCH", "Image differs from pinned identity")
            report = prepare_plan(image, profile, documents, size, hashes)
            if args.action == "validate":
                saved = load_catalog(args.plan, args.plan_sha256)
                if canonical(saved) != canonical(report):
                    raise ProfileError("OBSERVATION_PLAN", "Plan differs from regenerated evidence")
                with PrivateCaptureReader(
                    args.private_root, Path(__file__).resolve().parents[2]
                ) as private:
                    report = validate_capture(
                        saved, args.plan_sha256, private.document(args.capture_sha256), private.blob
                    )
                    report["capture_sha256"] = args.capture_sha256
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError) as error:
        code = error.code if isinstance(error, ProfileError) else "OBSERVATION_IO_ERROR"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": report["status"], "f02_07_status": "pending"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
