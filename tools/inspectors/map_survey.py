"""Inspect an explicit MAP/texture candidate pair; never infer a material link."""

import argparse
import json
from functools import partial
from pathlib import Path, PurePosixPath

from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.candidates import CandidateReader, validate_evidence
from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.map_probe import METHOD, MapProbeError, probe_map
from tools.inspectors.map_render_probe import probe_render_metadata
from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.inspectors.texture_probe import TextureProbeError, probe_texture
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.profile import ProfileError


def inspect_pair(
    reader: CandidateReader,
    catalog: dict,
    receipt: dict,
    catalog_hash: str,
    receipt_hash: str,
    map_id: str,
    texture_id: str,
    embedded_offset: int | None = None,
    render_metadata: bool = False,
) -> dict:
    validate_image_hash(catalog_hash)
    validate_image_hash(receipt_hash)
    resources = validate_evidence(catalog, receipt, catalog_hash)
    by_id = {resource["id"]: resource for resource in resources}
    if map_id == texture_id or map_id not in by_id or texture_id not in by_id:
        raise ProfileError("MAP_SELECTION", "Select two distinct catalog resources")
    metadata = {entry["id"]: entry for entry in catalog["entries"]}
    map_resource, texture = by_id[map_id], by_id[texture_id]
    reader.verify_set(resources)
    structure = probe_map(map_resource["size"], partial(reader.read_verified, map_resource))
    texture_structure = probe_texture(texture["size"], partial(reader.read_verified, texture))
    embedded = {"status": "not_requested"}
    if embedded_offset is not None:
        if (
            type(embedded_offset) is not int
            or embedded_offset % 16 != 0
            or not 48 <= embedded_offset < map_resource["size"]
            or any(
                group["offset"] + group["size"] > embedded_offset for group in structure["groups"]
            )
        ):
            raise ProfileError("MAP_EMBEDDED_RANGE", "Select a range after the map groups")
        embedded = {
            "status": "structural_candidate",
            "selection": "explicit_offset_hypothesis",
            "base_offset": embedded_offset,
            "offsets_relative_to": "embedded_area_start",
            "structure": probe_texture(
                map_resource["size"] - embedded_offset,
                lambda offset, length: reader.read_verified(
                    map_resource, embedded_offset + offset, length
                ),
            ),
        }
    render = {}
    if render_metadata:
        render["render_metadata"] = probe_render_metadata(
            map_resource["size"], partial(reader.read_verified, map_resource)
        )
    reader.verify_set(resources)
    map_name = PurePosixPath(metadata[map_id]["source_name"])
    texture_name = PurePosixPath(metadata[texture_id]["source_name"])
    return {
        "schema_version": 1,
        "scope": "ps2_map_texture_candidate",
        "method": METHOD,
        "evidence": {"catalog_sha256": catalog_hash, "receipt_sha256": receipt_hash},
        "resources": {
            label: {k: resource[k] for k in ("id", "container_id", "size", "sha256")}
            for label, resource in (("map", map_resource), ("texture", texture))
        },
        "selection": {
            "basis": "explicit_pair",
            "same_container": map_resource["container_id"] == texture["container_id"],
            "name_hint": (
                "same_stem_tr_suffix"
                if map_name.suffix.lower() == ".map"
                and texture_name.suffix.lower() == ".tex"
                and texture_name.stem.lower() == map_name.stem.lower() + "tr"
                else "none"
            ),
            "status": "unverified",
        },
        "map": structure,
        "texture": texture_structure,
        "embedded_texture": embedded,
        "material_binding": "unverified",
        "visual_comparison": "pending",
        "capabilities": [],
        "g02_status": "pending",
        **render,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog", "receipt", "private-copy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("catalog-sha256", "receipt-sha256", "map-id", "texture-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--embedded-offset", type=int)
    parser.add_argument("--render-metadata", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Map report already exists")
        catalog = load_catalog(args.catalog, args.catalog_sha256)
        receipt = load_catalog(args.receipt, args.receipt_sha256)
        with VerifiedPrivateReader(
            args.private_copy, Path(__file__).resolve().parents[2]
        ) as reader:
            report = inspect_pair(
                reader,
                catalog,
                receipt,
                args.catalog_sha256,
                args.receipt_sha256,
                args.map_id,
                args.texture_id,
                args.embedded_offset,
                args.render_metadata,
            )
        publish_report(args.output.absolute(), report)
    except (ProfileError, MapProbeError, TextureProbeError, OSError) as error:
        code = error.code if not isinstance(error, OSError) else "MAP_IO_ERROR"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(
        json.dumps({"status": "structural_candidate", **report["map"]["summary"]}, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
