"""Prepare the private textured viewer from verified CM-T5 and CT-T4 inputs."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.pipeline.character_inspection import inspection_character
from tools.pipeline.character_material_inspection import IMAGES, encode_material, material_ranges
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.inspection_inputs import bounded_read, checked, read_build
from tools.pipeline.private_texture_output import write_character_material_inspection_bundle
from tools.qa.gs_material_oracle import require_character_profile

STEM = "sh3_character_material_probe"


def manifest_file(source, manifest, name, limit):
    entries = [f for f in manifest["files"] if f["file"] == name]
    if len(entries) != 1:
        raise ValueError("Missing or duplicate private input")
    raw = checked(bounded_read(source / name, limit), entries[0]["sha256"])
    if len(raw) != entries[0]["size"]:
        raise ValueError("Private input size differs")
    return raw


def prepare_files(
    character_source,
    character_sha,
    mesh_source,
    mesh_sha,
    materials_source,
    materials_sha,
    reference,
    reference_sha,
    build,
):
    old, mesh_manifest, materials_manifest = [
        json.loads(checked(bounded_read(source / "manifest.json", 65536), digest))
        for source, digest in (
            (character_source, character_sha),
            (mesh_source, mesh_sha),
            (materials_source, materials_sha),
        )
    ]
    oracle = json.loads(checked(bounded_read(reference, 131072), reference_sha))
    if (
        old["scope"] != "private_character_inspection"
        or old["clip"] != "0x1449"
        or old["mesh_manifest_sha256"] != mesh_sha
        or mesh_manifest["scope"] != "ps2_character_mesh_candidate"
        or materials_manifest["scope"] != "ps2_character_material_candidate"
        or oracle["schema_version"] != 1
        or oracle["scope"] != "ct_t4_character_material"
        or oracle["status"] != "pass"
        or oracle["provenance"]["guest_writes"] is not False
        or len(oracle["submeshes"]) != 15
        or len(oracle["draws"]) != 3
    ):
        raise ValueError("Unsupported CT-T4/CM-T5 reference")
    for name in ("model", "animation"):
        if (
            mesh_manifest["resources"][name]["sha256"]
            != materials_manifest["resources"][name]["sha256"]
        ):
            raise ValueError("Resource identity differs")
    if mesh_manifest["resources"]["model"]["sha256"] != oracle["provenance"]["mdl_sha256"]:
        raise ValueError("CT-T4 model differs")
    for i, submesh in enumerate(oracle["submeshes"]):
        if submesh["submesh"] != i or submesh["image"] != IMAGES[i]:
            raise ValueError("CT-T4 binding differs")
        require_character_profile({int(k, 16): int(v, 16) for k, v in submesh["registers"].items()})
    clip = manifest_file(character_source, old, "animation.san", 1248)
    character = manifest_file(character_source, old, "character.scm", 100000)
    mesh = json.loads(manifest_file(mesh_source, mesh_manifest, "mesh.json", 4 * 1024 * 1024))
    if inspection_character(mesh, clip) != character:
        raise ValueError("CM-T5 mesh changed")
    materials = json.loads(
        manifest_file(materials_source, materials_manifest, "materials.json", 131072)
    )
    ranges = material_ranges(mesh, materials)
    textures = []
    for i, draw in enumerate(oracle["draws"]):
        raw = manifest_file(materials_source, materials_manifest, f"texture-{i}.rgba", 1048576)
        if draw["image"] != i or hashlib.sha256(raw).hexdigest() != draw["texture_sha256"]:
            raise ValueError("CT-T4 texture differs")
        textures.append(raw)
    material = encode_material(ranges, textures, character)
    artifacts, build_id = read_build(build, STEM)
    vertices, indices = struct.unpack_from("<2I", character, 8)
    files = {
        "animation.san": clip,
        "character.scm": character,
        "character.sct": material,
        f"{STEM}.3dsx": artifacts[f"{STEM}.3dsx"],
        f"{STEM}.smdh": artifacts[f"{STEM}.smdh"],
        "LEEME.txt": (
            f"SH3 - caballo animado con texturas / Build {build_id}\n\n"
            "Extrae sd-card.zip en la raiz de la SD. Conserva los otros visores.\n"
            "Abre SH3 textured character en Homebrew Launcher. No requiere CIA/FBI.\n"
            f"Archivos en /3ds/{STEM}/\n"
            "Tres texturas originales, material opaco, luz neutra, dos caras.\n"
            "No reproduce aun la iluminacion dinamica ni visibilidad VU de PS2.\n"
            "Los texeles alpha cero NO se descartan ni mezclan (CT-T4 ATE=ABE=0).\n"
            "A: pausa. R: avanzar en pausa. L: reiniciar clip.\n"
            "Cruceta: camara. X/Y: zoom. B: reset. START: salir.\n"
            "Prueba tapa y HOME; suelta los controles al regresar.\n"
            "Observa 60 segundos: textura alineada, sin parpadeos ni huecos espurios.\n"
            "Anota Skin CPU, Submit+wait y GPU previous. Submit incluye espera.\n"
            "Preview 25 evaluaciones/s; no acredita cadencia original PS2.\n"
            "Pendientes: iluminacion PS2, mundo, dano 0x144A y muerte 0x144B.\n"
            "Entrega privada. No subir datos al repositorio ni CI.\n"
        ).encode(),
    }
    files["sd-card.zip"] = inspection_archive(files, STEM)
    return files, {
        "schema_version": 1,
        "scope": "private_character_material_inspection",
        "build_id": build_id,
        "character_manifest_sha256": character_sha,
        "mesh_manifest_sha256": mesh_sha,
        "materials_manifest_sha256": materials_sha,
        "runtime_sha256": reference_sha,
        "clip": "0x1449",
        "vertex_count": vertices,
        "triangles": indices // 3,
        "ranges": ranges,
        "gpu_vertex_bytes_per_frame": indices * 36,
        "gpu_texture_bytes": 3 * 1048576,
        "draw_calls": 3,
        "uv": "signed_q12_no_flip",
        "material": "opaque_neutral_light_two_sided",
        "physical_2ds_xl": "pending",
        "dynamic_ps2_lighting": "pending",
        "damage_0x144a": "pending",
        "death_0x144b": "pending",
        "capabilities": [],
        "build_files": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(artifacts.items())},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "character-source",
        "mesh-source",
        "materials-source",
        "reference",
        "build",
        "private-root",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in (
        "character-sha256",
        "mesh-sha256",
        "materials-sha256",
        "reference-sha256",
        "run-id",
    ):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    files, report = prepare_files(
        args.character_source,
        args.character_sha256,
        args.mesh_source,
        args.mesh_sha256,
        args.materials_source,
        args.materials_sha256,
        args.reference,
        args.reference_sha256,
        args.build,
    )
    write_character_material_inspection_bundle(
        args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
    )
    print(json.dumps({"status": "prepared", "build_id": report["build_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
