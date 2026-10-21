"""Verify decoded private pixels/build and prepare a new private SD delivery."""

import argparse
import hashlib
import json
from pathlib import Path

from tools.pipeline.inspection_inputs import bounded_read as bounded_read
from tools.pipeline.inspection_inputs import checked, read_build
from tools.pipeline.private_texture_output import write_inspection_bundle
from tools.pipeline.texture_inspection import (
    PIXEL_BYTES,
    encode_stx,
    normalize_ps2_alpha,
    sd_archive,
)

BUILD_FILES = {
    "sh3_texture_probe.elf",
    "sh3_texture_probe.3dsx",
    "sh3_texture_probe.smdh",
    "build-id.txt",
    "toolchain-packages.txt",
    "sdk-image.txt",
}


def prepare_files(decoded: Path, manifest_sha256: str, palette: int, build: Path) -> tuple:
    if type(palette) is not int or palette not in range(4):
        raise ValueError("Choose a palette from 0 to 3")
    raw_manifest = checked(bounded_read(decoded / "manifest.json", 65536), manifest_sha256)
    manifest = json.loads(raw_manifest)
    if (
        manifest["schema_version"] != 1
        or manifest["scope"] != "ps2_indexed_texture_decode"
        or manifest["recipe"] != "sh3-ps2-indexed8-four-cluts-v1"
        or manifest["status"] != "decoded_candidate"
        or manifest["orientation"] != "row_major_no_flip"
        or manifest["alpha"]["rgba"] != "original_ps2"
        or manifest["block"]["width"] != 256
        or manifest["block"]["height"] != 256
    ):
        raise ValueError("Unsupported decoded texture")
    name = f"palette-{palette}.rgba"
    matches = [entry for entry in manifest["files"] if entry["file"] == name]
    if len(matches) != 1 or matches[0]["size"] != PIXEL_BYTES:
        raise ValueError("Missing, duplicate or invalid RGBA entry")
    rgba = checked(bounded_read(decoded / name, PIXEL_BYTES), matches[0]["sha256"])
    normalized = normalize_ps2_alpha(rgba)
    palettes = [entry for entry in manifest["palettes"] if entry["ordinal"] == palette]
    if len(palettes) != 1:
        raise ValueError("Invalid palette metadata")
    checked(normalized, palettes[0]["preview_rgba_sha256"])
    artifacts, build_id = read_build(build, "sh3_texture_probe")
    instructions = (
        f"SH3 - inspeccion privada de textura\nBuild: {build_id}\nPaleta: {palette}\n\n"
        "Extrae sd-card.zip en la raiz de la SD y conserva la carpeta 3ds.\n"
        "Abre SH3 texture inspection desde Homebrew Launcher.\n"
        "No requiere FBI/CIA. Conserva la demo sintetica en su carpeta anterior.\n"
        "Cruceta: orbitar/elevar. X/Y: zoom. B: restablecer. START: salir.\n"
        "Debe verse una textura sobre un panel, con fondo azul oscuro.\n"
        "Vista RGB opaca: alpha, material, UV y fidelidad PS2 no acreditados.\n"
        "Si falla la carga, informa el error y usa START para salir.\n"
        "Prueba tambien cerrar/abrir tapa y HOME, sin mantener botones al volver.\n"
        "Conserva build, resultado, duracion y observaciones de esta prueba.\n"
        "Entrega privada: contiene un derivado de tu copia; no subir al repositorio/CI.\n"
    ).encode()
    files = {
        "texture.stx": encode_stx(normalized),
        "sh3_texture_probe.3dsx": artifacts["sh3_texture_probe.3dsx"],
        "sh3_texture_probe.smdh": artifacts["sh3_texture_probe.smdh"],
        "LEEME.txt": instructions,
    }
    files["sd-card.zip"] = sd_archive(files)
    report = {
        "schema_version": 1,
        "scope": "private_texture_inspection",
        "source_manifest_sha256": manifest_sha256,
        "resource": manifest["resource"],
        "source_rgba_sha256": matches[0]["sha256"],
        "normalized_rgba_sha256": hashlib.sha256(normalized).hexdigest(),
        "palette": palette,
        "build_id": build_id,
        "build_files": {
            key: hashlib.sha256(value).hexdigest() for key, value in sorted(artifacts.items())
        },
        "status": "prepared",
        "physical_2ds_xl": "pending",
        "original_material": "pending",
        "display": "opaque_rgb_own_panel",
        "capabilities": [],
    }
    return files, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("decoded", "build", "private-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--palette", required=True, type=int)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    files, report = prepare_files(args.decoded, args.manifest_sha256, args.palette, args.build)
    write_inspection_bundle(
        args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
    )
    print(json.dumps({"status": "prepared", "build_id": report["build_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
