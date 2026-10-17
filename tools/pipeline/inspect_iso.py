"""Record a PS2 ISO identity without extracting or converting original resources."""

import argparse
import json
from importlib.metadata import version
from pathlib import Path

from tools.pipeline.catalog import CatalogReference, match_catalog, parse_catalog
from tools.pipeline.disc import collect_disc
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, verify_profile
from tools.pipeline.verify import load_profile


def load_catalog(path: Path) -> CatalogReference:
    try:
        with path.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ProfileError("INVALID_CATALOG", "Catalog reference exceeds 64 KiB")
        return parse_catalog(json.loads(raw))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProfileError("CATALOG_READ_ERROR", "Cannot read catalog JSON") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, required=True, help="New JSON report; never overwritten"
    )
    parser.add_argument(
        "--region",
        choices=("Europe", "NorthAmerica", "Japan", "unknown"),
        default="unknown",
        help="Operator declaration, not inferred from filename",
    )
    parser.add_argument(
        "--profile", type=Path, help="Optional previously recorded profile to verify"
    )
    parser.add_argument(
        "--catalog", type=Path, help="Optional frozen catalog JSON; never fetched from the network"
    )
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Report destination already exists")
        expected = load_profile(args.profile) if args.profile else None
        catalog = load_catalog(args.catalog) if args.catalog else None
        region = (
            expected.region if expected is not None and args.region == "unknown" else args.region
        )
        if expected is not None and expected.region != region:
            raise ProfileError("PROFILE_MISMATCH", "Declared region differs from profile")
        with IsoImage(args.iso) as image:
            if catalog is not None:
                identity = image.image_fingerprints()
            else:
                size, digest = image.image_identity()
                identity = {"size": size, "sha256": digest}
            if expected is not None:
                verify_profile(expected, image)
            report = collect_disc(image, region, identity["sha256"])
            if expected is not None and (
                expected.platform != "ps2"
                or expected.serial != report["boot"]["serial"]
                or {entry.path for entry in expected.files} != set(image.paths())
            ):
                raise ProfileError(
                    "PROFILE_MISMATCH", "Profile does not describe this complete disc"
                )
            report["image"] = identity
            report["tool"] = {
                "name": "sh3-iso-inspector",
                "version": 2,
                "pycdlib": version("pycdlib"),
            }
            report["status"] = "matched_local_profile" if expected is not None else "observed"
            if catalog is not None:
                match_catalog(catalog, identity, report["boot"], region)
                languages = ",".join(catalog.languages)
                if expected is not None and (
                    expected.revision not in ("unverified", catalog.revision)
                    or expected.language not in ("unverified", languages)
                ):
                    raise ProfileError("PROFILE_MISMATCH", "Profile metadata differs from catalog")
                report["profile"].update(
                    region=catalog.region, revision=catalog.revision, language=languages
                )
                report["catalog"] = {
                    "id": catalog.reference_id,
                    "source_url": catalog.source_url,
                    "retrieved_on": catalog.retrieved_on,
                    "evidence": "complete_image_checksum_match",
                    "languages": list(catalog.languages),
                    "language_runtime_verified": False,
                }
                report["region_source"] = "matched_catalog"
                report["status"] = "matched_catalog"
        # Only serialize after the adapter checks the input remained unchanged.
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
        except OSError as error:
            raise ProfileError("REPORT_WRITE_ERROR", "Cannot create report") from error
    except ProfileError as error:
        print(json.dumps({"status": "rejected", "code": error.code, "message": str(error)}))
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "serial": report["boot"]["serial"],
                "files": report["file_count"],
                "extraction": "not_performed",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
