"""Survey texture headers in an explicit verified private copy; emit metadata only."""

import argparse
import json
from collections import Counter
from functools import partial
from pathlib import Path, PurePosixPath

from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.candidates import CandidateReader, validate_evidence
from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.inspectors.texture_probe import (
    METHOD,
    REFERENCE_REVISION,
    TextureProbeError,
    probe_texture,
)
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.profile import ProfileError


def survey_textures(
    reader: CandidateReader, catalog: dict, receipt: dict, catalog_hash: str, receipt_hash: str
) -> dict:
    validate_image_hash(catalog_hash)
    validate_image_hash(receipt_hash)
    resources = validate_evidence(catalog, receipt, catalog_hash)
    selected = {
        entry["id"]
        for entry in catalog["entries"]
        if PurePosixPath(entry["source_name"]).suffix.lower() == ".tex"
    }
    if not selected:
        raise ProfileError("TEX_EMPTY_SELECTION", "No texture hints in catalog")
    reader.verify_set(resources)
    entries = []
    for resource in sorted(resources, key=lambda item: item["id"]):
        if resource["id"] not in selected:
            continue
        try:
            result = probe_texture(
                resource["size"],
                partial(reader.read_verified, resource),
            )
        except TextureProbeError as error:
            if error.code == "TEX_READ_CONTRACT":
                raise ProfileError(error.code, "Texture reader returned incomplete data") from error
            result = {"status": "unknown", "code": error.code}
        entries.append(
            {
                **{key: resource[key] for key in ("id", "container_id", "size", "sha256")},
                "classification": {"type": "unknown"},
                "dependencies": {"status": "not_inspected", "known": []},
                "result": result,
            }
        )
    reader.verify_set(resources)
    accepted = [entry["result"] for entry in entries if entry["result"]["status"] != "unknown"]
    blocks = [block for result in accepted for block in result["blocks"]]
    return {
        "schema_version": 1,
        "scope": "ps2_texture_structure_survey",
        "tool": {"name": "sh3-texture-survey", "version": 1},
        "method": METHOD,
        "reference": {"repository": "Sparagas/Silent-Hill", "revision": REFERENCE_REVISION},
        "evidence": {"catalog_sha256": catalog_hash, "receipt_sha256": receipt_hash},
        "source": catalog["source"],
        "selection_basis": "unverified_catalog_suffix_tex",
        "entries": entries,
        "summary": {
            "selected_count": len(entries),
            "structural_candidate_count": len(accepted),
            "unknown_count": len(entries) - len(accepted),
            "unknown_codes": dict(
                sorted(
                    Counter(
                        entry["result"]["code"]
                        for entry in entries
                        if entry["result"]["status"] == "unknown"
                    ).items()
                )
            ),
            "block_count": len(blocks),
            "blocks_by_bpp": dict(sorted(Counter(str(b["bpp"]) for b in blocks).items())),
            "padding_disagreement_count": sum(
                b["padding_declared"] != b["padding_computed"] for b in blocks
            ),
        },
        "payload_decoding": "not_performed",
        "capabilities": [],
        "g02_status": "pending",
        "next_task": "F03.02/indexed-texture-pixels",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog", "receipt", "private-copy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("catalog-sha256", "receipt-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Texture report already exists")
        catalog = load_catalog(args.catalog, args.catalog_sha256)
        receipt = load_catalog(args.receipt, args.receipt_sha256)
        with VerifiedPrivateReader(
            args.private_copy, Path(__file__).resolve().parents[2]
        ) as reader:
            report = survey_textures(
                reader, catalog, receipt, args.catalog_sha256, args.receipt_sha256
            )
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError) as error:
        code = error.code if isinstance(error, ProfileError) else "TEX_IO_ERROR"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "surveyed", **report["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
