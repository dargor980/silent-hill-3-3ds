"""Prepare a private material viewer from verified geometry, texture and capture metadata."""

import argparse
import hashlib
import json
from pathlib import Path

from tools.pipeline.decoders.ps2_map_geometry import encode_vertices
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.inspection_inputs import bounded_read, checked, read_build
from tools.pipeline.material_inspection import material_geometry, material_texture
from tools.pipeline.prepare_geometry_probe import verified_shapes
from tools.pipeline.private_texture_output import write_material_inspection_bundle


def read_json(path, digest):
    return json.loads(checked(bounded_read(path, 65536), digest))


def prepare_files(
    geometry, geometry_sha, texture, texture_sha, reference_path, reference_sha, build
):
    gm = read_json(geometry / "manifest.json", geometry_sha)
    tm = read_json(texture / "manifest.json", texture_sha)
    ref = read_json(reference_path, reference_sha)
    if ref["schema_version"] != 1 or ref["scope"] != "mr_t4d_material_reference":
        raise ValueError("Unsupported material reference")
    if (
        tm["scope"] != "ps2_indexed_texture_decode"
        or tm["recipe"] != "sh3-ps2-indexed8-four-cluts-v1"
        or tm["orientation"] != "row_major_no_flip"
        or tm["alpha"]["rgba"] != "original_ps2"
        or tm["block"]["width"] != 256
        or tm["block"]["height"] != 256
        or ref["geometry_manifest_sha256"] != geometry_sha
        or ref["texture_manifest_sha256"] != texture_sha
    ):
        raise ValueError("Material source identity differs")

    def payload(root, manifest, name, limit):
        entries = [item for item in manifest["files"] if item["file"] == name]
        if len(entries) != 1:
            raise ValueError("Missing or duplicate material input")
        data = checked(bounded_read(root / name, limit), entries[0]["sha256"])
        if len(data) != entries[0]["size"]:
            raise ValueError("Material input size differs")
        return data

    shapes = verified_shapes(
        json.loads(payload(geometry, gm, "geometry.json", 8 * 1024 * 1024)), gm
    )
    for item in ref["shapes"]:
        matches = [g for offset, g in shapes if offset == item["shape_offset"]]
        if len(matches) != 1:
            raise ValueError("Unknown material shape")
        checked(encode_vertices(matches[0].vertices), item["source_sha256"])
    rgba = payload(texture, tm, "palette-0.rgba", 256 * 256 * 4)
    checked(rgba, ref["texture_rgba_sha256"])
    mesh, transform = material_geometry(shapes, ref)
    artifacts, build_id = read_build(build, "sh3_material_probe")
    files = {
        "geometry.sgm": mesh,
        "texture.stx": material_texture(rgba),
        "sh3_material_probe.3dsx": artifacts["sh3_material_probe.3dsx"],
        "sh3_material_probe.smdh": artifacts["sh3_material_probe.smdh"],
        "LEEME.txt": (
            f"SH3 - inspeccion de material\nBuild: {build_id}\n\n"
            "Extrae sd-card.zip EN LA RAIZ de la SD.\n"
            "Abre SH3 material inspection desde Homebrew Launcher.\n"
            "Carpeta: /3ds/sh3_material_probe/ (con ambos archivos .sgm y .stx).\n"
            "Deben verse dos paneles texturados y la cuadricula del fondo a traves.\n"
            "Cruceta: orbitar/elevar. X/Y: zoom. B: reset. START: salir.\n"
            "Prueba tapa y HOME; suelta controles al volver.\n"
            "Modelo original; escala/camara de inspeccion; luz y niebla capturadas.\n"
            "No es una escena jugable ni equivalencia exacta del GS.\n"
            "Informa build, aspecto de ambos paneles, controles, duracion y errores.\n"
            "No requiere CIA/FBI. Conserva los otros visores.\n"
            "Entrega privada de tu copia; no subir al repositorio o CI.\n"
        ).encode(),
    }
    files["sd-card.zip"] = inspection_archive(files, "sh3_material_probe")
    return files, {
        "schema_version": 1,
        "scope": "private_material_inspection",
        "build_id": build_id,
        "geometry_manifest_sha256": geometry_sha,
        "texture_manifest_sha256": texture_sha,
        "reference_sha256": reference_sha,
        "transform": transform,
        "physical_2ds_xl": "pending",
        "ps2_pixel_equivalence": "not_claimed",
        "capabilities": [],
        "build_files": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(artifacts.items())},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("geometry", "texture", "reference", "build", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("geometry-sha256", "texture-sha256", "reference-sha256", "run-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    files, report = prepare_files(
        args.geometry,
        args.geometry_sha256,
        args.texture,
        args.texture_sha256,
        args.reference,
        args.reference_sha256,
        args.build,
    )
    write_material_inspection_bundle(
        args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
    )
    print(json.dumps({"status": "prepared", "build_id": report["build_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
