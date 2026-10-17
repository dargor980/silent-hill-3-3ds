"""Catalog an identified ISO into private metadata, without exporting resource bytes."""

import argparse
import json
from importlib.metadata import version
from pathlib import Path

from tools.inspectors.inventory import collect_inventory, validate_image_hash
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError
from tools.pipeline.verify import load_profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--image-sha256", required=True, help="Full hash from prior identification")
    parser.add_argument("--output", required=True, type=Path, help="New private metadata JSON")
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
            report = collect_inventory(image, profile, size, digest)
            report["tool"] = {
                "name": "sh3-source-inventory",
                "version": 1,
                "pycdlib": version("pycdlib"),
            }
        # The context manager has confirmed source stability before serialization.
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
        except OSError as error:
            raise ProfileError("REPORT_WRITE_ERROR", "Cannot create catalog report") from error
    except ProfileError as error:
        print(json.dumps({"status": "rejected", "code": error.code, "message": str(error)}))
        return 1
    print(
        json.dumps(
            {
                "status": "catalogued",
                **report["summary"],
                "extraction": "not_performed",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
