"""Decode one explicit PS2 indexed block into a new external private bundle."""

import argparse
import hashlib
import json
import zlib
from functools import partial
from pathlib import Path

from tools.inspectors.candidates import CandidateReader, validate_evidence
from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.private_reader import MAX_RANGE_BYTES, VerifiedPrivateReader
from tools.inspectors.texture_probe import TextureProbeError, probe_texture
from tools.pipeline.decoders.ps2_indexed8 import (
    RECIPE,
    TextureDecodeError,
    decode_indexed8,
    render_palette,
    validate_dimensions,
)
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.preview_png import encode_rgba_png
from tools.pipeline.private_output import resource_filename
from tools.pipeline.private_texture_output import write_texture_bundle
from tools.pipeline.profile import ProfileError


def decode_resource(
    reader: CandidateReader,
    catalog: dict,
    receipt: dict,
    catalog_hash: str,
    receipt_hash: str,
    identity: str,
    ordinal: int,
) -> tuple[dict[str, bytes], dict]:
    validate_image_hash(catalog_hash)
    validate_image_hash(receipt_hash)
    resource_filename(identity)
    resources = validate_evidence(catalog, receipt, catalog_hash)
    resource = next((item for item in resources if item["id"] == identity), None)
    if resource is None:
        raise TextureDecodeError("PX_RESOURCE_MISSING")
    if type(ordinal) is not int or not 0 <= ordinal < 256:
        raise TextureDecodeError("PX_ORDINAL")
    reader.verify_set(resources)
    structure = probe_texture(resource["size"], partial(reader.read_verified, resource))
    if ordinal >= len(structure["blocks"]):
        raise TextureDecodeError("PX_ORDINAL")
    block = structure["blocks"][ordinal]
    if block["bpp"] != 8 or block["clut"]["declared_count"] != 4:
        raise TextureDecodeError("PX_UNSUPPORTED_VARIANT")
    validate_dimensions(block["width"], block["height"])

    def read_range(offset, size):
        data = bytearray()
        while len(data) < size:
            length = min(MAX_RANGE_BYTES, size - len(data))
            part = reader.read_verified(resource, offset + len(data), length)
            if type(part) is not bytes or len(part) != length:
                raise ProfileError("PX_READ_CONTRACT", "Incomplete texture range")
            data.extend(part)
        return bytes(data)

    indices = read_range(**block["indices"])
    clut = read_range(block["clut"]["data_offset"], block["clut"]["size"])
    reader.verify_set(resources)
    decoded = decode_indexed8(block["width"], block["height"], indices, clut)
    files, palettes = {"indices.bin": decoded.indices}, []
    for index, palette in enumerate(decoded.palettes):
        original = render_palette(decoded, index, normalize_alpha=False)
        preview = render_palette(decoded, index, normalize_alpha=True)
        files[f"palette-{index}.bin"] = palette
        files[f"palette-{index}.rgba"] = original
        files[f"palette-{index}.png"] = encode_rgba_png(decoded.width, decoded.height, preview)
        alpha = original[3::4]
        palettes.append(
            {
                "ordinal": index,
                "uniform_zero": palette == bytes(1024),
                "uniform_cc": palette == b"\xcc" * 1024,
                "unique_rgba_colors": len({palette[i : i + 4] for i in range(0, 1024, 4)}),
                "alpha_min": min(alpha),
                "alpha_max": max(alpha),
                "normalized_saturated_pixels": sum(a >= 128 for a in alpha),
                "preview_rgba_sha256": hashlib.sha256(preview).hexdigest(),
            }
        )
    return files, {
        "schema_version": 1,
        "scope": "ps2_indexed_texture_decode",
        "recipe": RECIPE,
        "status": "decoded_candidate",
        "evidence": {"catalog_sha256": catalog_hash, "receipt_sha256": receipt_hash},
        "resource": {key: resource[key] for key in ("id", "container_id", "size", "sha256")},
        "block": block,
        "source_ranges": {
            "indices_sha256": hashlib.sha256(indices).hexdigest(),
            "clut_sha256": hashlib.sha256(clut).hexdigest(),
        },
        "palettes": palettes,
        "alpha": {"rgba": "original_ps2", "png": "min(255,2*a)", "loss": "png_alpha_saturation"},
        "orientation": "row_major_no_flip",
        "zlib_version": zlib.ZLIB_RUNTIME_VERSION,
        "visual_comparison": "pending",
        "material_palette_selection": "pending",
        "capabilities": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog", "receipt", "private-copy", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("catalog-sha256", "receipt-sha256", "resource-id", "run-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--ordinal", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        repository = Path(__file__).resolve().parents[2]
        catalog = load_catalog(args.catalog, args.catalog_sha256)
        receipt = load_catalog(args.receipt, args.receipt_sha256)
        with VerifiedPrivateReader(args.private_copy, repository) as reader:
            files, report = decode_resource(
                reader,
                catalog,
                receipt,
                args.catalog_sha256,
                args.receipt_sha256,
                args.resource_id,
                args.ordinal,
            )
        write_texture_bundle(args.private_root, repository, args.run_id, files, report)
    except (ProfileError, TextureProbeError, TextureDecodeError, OSError) as error:
        code = getattr(error, "code", None)
        if isinstance(error, TextureDecodeError):
            code = str(error)
        print(json.dumps({"status": "rejected", "code": code or "PX_IO_ERROR"}))
        return 1
    print(
        json.dumps({"status": "decoded_candidate", "palettes": 4, "visual_comparison": "pending"})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
