"""Verify a decoded MAP bundle and prepare an exclusive private SGM1 SD delivery."""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from tools.pipeline.decoders.ps2_map_geometry import (
    RECIPE,
    MapVertex,
    decode_shape,
    encode_vertices,
)
from tools.pipeline.geometry_inspection import normalize_shapes
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.inspection_inputs import bounded_read, checked, read_build
from tools.pipeline.private_texture_output import write_geometry_inspection_bundle

GEOMETRY_FIELDS = {"vertices", "triangles", "skipped_vertices", "degenerate_triangles"}


def verified_shapes(document, manifest):
    expected = {
        "schema_version": 1,
        "scope": "ps2_map_group_geometry",
        "recipe": RECIPE,
        "status": "decoded_candidate",
        "positions": "local_i16_no_transform",
        "uv_reference": "U/32768,1-V/32768_control_bit_retained",
        "packed_attributes": "preserved_not_interpreted",
        "material_binding": "unverified",
        "ps2_visual_comparison": "pending",
        "geometry_3ds": "pending",
        "capabilities": [],
    }
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError("Unsupported MG contract")
    if {k: v for k, v in manifest.items() if k not in {"files", "shapes"}} != {
        k: v for k, v in document.items() if k != "shapes"
    }:
        raise ValueError("Geometry metadata differs")
    shapes = document["shapes"]
    if (
        not 1 <= len(shapes) <= 64
        or [{k: v for k, v in s.items() if k not in GEOMETRY_FIELDS} for s in shapes]
        != manifest["shapes"]
    ):
        raise ValueError("Geometry shape inventory differs")
    if sum(len(s["vertices"]) for s in shapes) > 65536:
        raise ValueError("Geometry source budget")
    decoded, offsets = [], set()
    for shape in shapes:
        offset = shape["shape_offset"]
        if type(offset) is not int or offset < 0 or offset % 16 or offset in offsets:
            raise ValueError("Invalid shape identity")
        offsets.add(offset)
        vertices = []
        for value in shape["vertices"]:
            if set(value) != {"position", "uv_words", "packed_attributes"}:
                raise ValueError("Invalid vertex fields")
            for key, length in (("position", 3), ("uv_words", 2), ("packed_attributes", 3)):
                if len(value[key]) != length or any(
                    type(word) is not int or not -32768 <= word <= 32767 for word in value[key]
                ):
                    raise ValueError("Invalid vertex words")
            vertices.append(MapVertex(**{k: tuple(v) for k, v in value.items()}))
        raw = checked(encode_vertices(tuple(vertices)), shape["source_sha256"])
        geometry = decode_shape(raw, shape["vertex_count"])
        if json.loads(json.dumps(asdict(geometry))) != {k: shape[k] for k in GEOMETRY_FIELDS}:
            raise ValueError("Geometry topology differs")
        if (
            shape["data_bytes"] != len(raw)
            or shape["triangle_count"] != len(geometry.triangles)
            or shape["skipped_count"] != len(geometry.skipped_vertices)
            or shape["degenerate_count"] != len(geometry.degenerate_triangles)
        ):
            raise ValueError("Geometry counts differ")
        decoded.append((offset, geometry))
    if manifest["summary"] != {
        "shapes": len(decoded),
        "vertices": sum(len(g.vertices) for _, g in decoded),
        "triangles": sum(len(g.triangles) for _, g in decoded),
        "degenerate_triangles": sum(len(g.degenerate_triangles) for _, g in decoded),
    }:
        raise ValueError("Geometry summary differs")
    return decoded


def prepare_files(decoded: Path, manifest_sha256: str, build: Path) -> tuple:
    manifest = json.loads(checked(bounded_read(decoded / "manifest.json", 65536), manifest_sha256))
    entries = [f for f in manifest["files"] if f["file"] == "geometry.json"]
    if len(entries) != 1:
        raise ValueError("Missing or duplicate geometry")
    raw = checked(bounded_read(decoded / "geometry.json", 8 * 1024 * 1024), entries[0]["sha256"])
    if len(raw) != entries[0]["size"]:
        raise ValueError("Geometry size differs")
    sgm, transform = normalize_shapes(verified_shapes(json.loads(raw), manifest))
    artifacts, build_id = read_build(build, "sh3_geometry_probe")
    files = {
        "geometry.sgm": sgm,
        "sh3_geometry_probe.3dsx": artifacts["sh3_geometry_probe.3dsx"],
        "sh3_geometry_probe.smdh": artifacts["sh3_geometry_probe.smdh"],
        "LEEME.txt": (
            f"SH3 - inspeccion privada de geometria\nBuild: {build_id}\n\n"
            "Extrae sd-card.zip EN LA RAIZ de la SD.\n"
            "Debe quedar /3ds/sh3_geometry_probe/geometry.sgm junto al .3dsx.\n"
            "Abre SH3 geometry inspection desde Homebrew Launcher.\n"
            "Cruceta: orbitar/elevar. X/Y: zoom. B: reset. START: salir.\n"
            "Geometria MAP con checker propio y colores cian/naranja por forma.\n"
            "Escala de inspeccion; matriz, material y fidelidad PS2 pendientes.\n"
            "Prueba tapa y HOME; suelta los controles al volver.\n"
            "Si falla, informa build/error y sal con START.\n"
            "Entrega privada de tu copia: no subir al repositorio ni CI.\n"
        ).encode(),
    }
    files["sd-card.zip"] = inspection_archive(files, "sh3_geometry_probe")
    return files, {
        "schema_version": 1,
        "scope": "private_geometry_inspection",
        "source_manifest_sha256": manifest_sha256,
        "source_geometry_sha256": entries[0]["sha256"],
        "resource": manifest["resource"],
        "summary": manifest["summary"],
        "inspection_transform": transform,
        "build_id": build_id,
        "build_files": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(artifacts.items())},
        "status": "prepared",
        "physical_2ds_xl": "pending",
        "ps2_visual_comparison": "pending",
        "material": "own_checker_and_shape_colors",
        "capabilities": [],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("decoded", "build", "private-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    files, report = prepare_files(args.decoded, args.manifest_sha256, args.build)
    write_geometry_inspection_bundle(
        args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
    )
    print(json.dumps({"status": "prepared", "build_id": report["build_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
