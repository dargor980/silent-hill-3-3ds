"""Decode one explicitly selected MAP group to an exclusive private inspection bundle."""

import argparse
import hashlib
import json
from dataclasses import asdict
from functools import partial
from pathlib import Path

from tools.inspectors.candidates import CandidateReader, validate_evidence
from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.map_probe import MapProbeError, probe_map
from tools.inspectors.private_reader import MAX_RANGE_BYTES, VerifiedPrivateReader
from tools.pipeline.decoders.ps2_map_geometry import (
    MAX_VERTICES,
    RECIPE,
    GeometryDecodeError,
    decode_shape,
)
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.geometry_obj import encode_obj
from tools.pipeline.private_output import resource_filename
from tools.pipeline.private_texture_output import write_geometry_bundle
from tools.pipeline.profile import ProfileError


def decode_group(
    reader: CandidateReader,
    catalog: dict,
    receipt: dict,
    catalog_hash: str,
    receipt_hash: str,
    identity: str,
    group_offset: int,
) -> tuple[dict[str, bytes], dict]:
    validate_image_hash(catalog_hash)
    validate_image_hash(receipt_hash)
    resource_filename(identity)
    resources = validate_evidence(catalog, receipt, catalog_hash)
    resource = next((item for item in resources if item["id"] == identity), None)
    if resource is None:
        raise GeometryDecodeError("MG_RESOURCE_MISSING")
    if type(group_offset) is not int or group_offset < 48 or group_offset % 16:
        raise GeometryDecodeError("MG_GROUP_OFFSET")
    reader.verify_set(resources)
    structure = probe_map(resource["size"], partial(reader.read_verified, resource))
    group = next((g for g in structure["groups"] if g["offset"] == group_offset), None)
    if group is None:
        raise GeometryDecodeError("MG_GROUP_MISSING")
    selected = [
        (mesh, submesh, shape)
        for mesh in group["children"]
        for submesh in mesh["children"]
        for shape in submesh["children"]
    ]
    if sum(s["vertex_count"] for _, _, s in selected) > MAX_VERTICES:
        raise GeometryDecodeError("MG_GROUP_BUDGET")
    if any(not 3 <= s["vertex_count"] <= MAX_VERTICES for _, _, s in selected):
        raise GeometryDecodeError("MG_VERTEX_COUNT")
    shapes, decoded_shapes, observations = [], [], []
    for mesh, submesh, shape in selected:
        raw = bytearray()
        while len(raw) < shape["vertex_bytes"]:
            length = min(MAX_RANGE_BYTES, shape["vertex_bytes"] - len(raw))
            part = reader.read_verified(resource, shape["data_offset"] + len(raw), length)
            if type(part) is not bytes or len(part) != length:
                raise ProfileError("MG_READ_CONTRACT", "Incomplete geometry range")
            raw.extend(part)
        geometry = decode_shape(bytes(raw), shape["vertex_count"])
        entry = {
            "mesh_offset": mesh["offset"],
            "submesh_offset": submesh["offset"],
            "shape_offset": shape["offset"],
            "transform_index_unverified": shape["transform_index_unverified"],
            "clut_index_unverified": mesh["clut_index_unverified"],
            "mesh_opaque_halfwords": mesh["opaque_halfwords"],
            "data_offset": shape["data_offset"],
            "data_bytes": shape["vertex_bytes"],
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "vertex_count": len(geometry.vertices),
            "triangle_count": len(geometry.triangles),
            "degenerate_count": len(geometry.degenerate_triangles),
            "skipped_count": len(geometry.skipped_vertices),
        }
        observations.append(entry)
        shapes.append({**entry, **asdict(geometry)})
        decoded_shapes.append((shape["offset"], geometry))
    reader.verify_set(resources)
    report = {
        "schema_version": 1,
        "scope": "ps2_map_group_geometry",
        "recipe": RECIPE,
        "status": "decoded_candidate",
        "evidence": {"catalog_sha256": catalog_hash, "receipt_sha256": receipt_hash},
        "resource": {k: resource[k] for k in ("id", "container_id", "size", "sha256")},
        "group": {k: v for k, v in group.items() if k != "children"},
        "shapes": observations,
        "summary": {
            "shapes": len(shapes),
            "vertices": sum(s["vertex_count"] for s in observations),
            "triangles": sum(s["triangle_count"] for s in observations),
            "degenerate_triangles": sum(s["degenerate_count"] for s in observations),
        },
        "positions": "local_i16_no_transform",
        "uv_reference": "U/32768,1-V/32768_control_bit_retained",
        "packed_attributes": "preserved_not_interpreted",
        "material_binding": "unverified",
        "ps2_visual_comparison": "pending",
        "geometry_3ds": "pending",
        "capabilities": [],
    }
    document = {**report, "shapes": shapes}
    return {
        "geometry.json": (json.dumps(document, sort_keys=True, indent=2) + "\n").encode(),
        "inspection.obj": encode_obj(decoded_shapes),
    }, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog", "receipt", "private-copy", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("catalog-sha256", "receipt-sha256", "resource-id", "run-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--group-offset", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        repository = Path(__file__).resolve().parents[2]
        catalog = load_catalog(args.catalog, args.catalog_sha256)
        receipt = load_catalog(args.receipt, args.receipt_sha256)
        with VerifiedPrivateReader(args.private_copy, repository) as reader:
            files, report = decode_group(
                reader,
                catalog,
                receipt,
                args.catalog_sha256,
                args.receipt_sha256,
                args.resource_id,
                args.group_offset,
            )
        write_geometry_bundle(args.private_root, repository, args.run_id, files, report)
    except (ProfileError, MapProbeError, GeometryDecodeError, OSError) as error:
        code = (
            str(error)
            if isinstance(error, GeometryDecodeError)
            else getattr(error, "code", "MG_IO_ERROR")
        )
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "decoded_candidate", **report["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
