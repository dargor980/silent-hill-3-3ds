"""Prepare an independent private viewer with a verified static lighting preset."""

import argparse
import hashlib
import json
from pathlib import Path

from tools.pipeline.character_inspection import inspection_character
from tools.pipeline.character_lighting_inspection import encode_lighting
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.inspection_inputs import bounded_read, checked, read_build
from tools.pipeline.prepare_character_material_probe import manifest_file
from tools.pipeline.private_texture_output import write_character_lighting_inspection_bundle

STEM = "sh3_character_lighting_probe"


def prepare_files(
    material_source,
    material_sha,
    mesh_source,
    mesh_sha,
    preset_path,
    preset_sha,
    reference_path,
    reference_sha,
    build,
):
    old = json.loads(checked(bounded_read(material_source / "manifest.json", 65536), material_sha))
    mesh_manifest = json.loads(
        checked(bounded_read(mesh_source / "manifest.json", 65536), mesh_sha)
    )
    preset = json.loads(checked(bounded_read(preset_path, 16384), preset_sha))
    reference = json.loads(checked(bounded_read(reference_path, 131072), reference_sha))
    if (
        old["scope"] != "private_character_material_inspection"
        or old["mesh_manifest_sha256"] != mesh_sha
        or mesh_manifest["scope"] != "ps2_character_mesh_candidate"
        or preset["schema_version"] != 1
        or preset["scope"] != "captured_character_lighting_preset"
        or preset["li_report_sha256"] != reference_sha
        or reference["status"] != "pass"
        or reference["scope"] != "li_mode2_type10_character_lighting"
        or len(reference["poses"]) != 4
        or reference["provenance"]["new_guest_writes"] is not False
        or reference["provenance"]["mdl_sha256"] != mesh_manifest["resources"]["model"]["sha256"]
    ):
        raise ValueError("Unsupported lighting provenance")
    pose = reference["poses"][-1]
    for p, r in [
        ("input_sha256", "input_sha256"),
        ("output_sha256", "output_sha256"),
        ("draw_parameters_sha256", "draw_parameters_sha256"),
        ("reference_counter", "counter"),
    ]:
        if preset[p] != pose[r]:
            raise ValueError("Lighting capture differs")
    clip = manifest_file(material_source, old, "animation.san", 1248)
    character = manifest_file(material_source, old, "character.scm", 100000)
    material = manifest_file(material_source, old, "character.sct", 3145796)
    mesh_raw = manifest_file(mesh_source, mesh_manifest, "mesh.json", 4 * 1024 * 1024)
    if hashlib.sha256(mesh_raw).hexdigest() != reference["provenance"]["mesh_sha256"]:
        raise ValueError("Lighting mesh differs")
    mesh = json.loads(mesh_raw)
    if inspection_character(mesh, clip) != character:
        raise ValueError("Lighting model differs")
    lighting = encode_lighting(preset, mesh, character, clip, material)
    artifacts, build_id = read_build(build, STEM)
    files = {
        "animation.san": clip,
        "character.scm": character,
        "character.sct": material,
        "character.scl": lighting,
        f"{STEM}.3dsx": artifacts[f"{STEM}.3dsx"],
        f"{STEM}.smdh": artifacts[f"{STEM}.smdh"],
        "LEEME.txt": (
            f"SH3 - iluminacion capturada / Build {build_id}\n\n"
            "Extrae sd-card.zip en la raiz de la SD. Conserva los visores anteriores.\n"
            "Abre SH3 captured lighting en Homebrew Launcher. No requiere CIA/FBI.\n"
            f"Archivos en /3ds/{STEM}/\n"
            "Preset fijo de una captura: la luz se recalcula con la animacion.\n"
            "No sigue la camara de inspeccion. Dos caras; material opaco.\n"
            "SELECT: alternar luces capturadas / luz neutra.\n"
            "A: pausa. R: paso en pausa. L: reiniciar. Cruceta: camara.\n"
            "X/Y: zoom. B: reset. START: salir. Prueba tapa y HOME.\n"
            "Observa 60 segundos en cada modo; Q12 debe avanzar sin bloqueos.\n"
            "Anota Skin CPU, Light CPU, Submit+wait y GPU previous.\n"
            "Submit incluye espera; los tiempos no se suman para calcular FPS.\n"
            "Preview 25 evaluaciones/s; no acredita cadencia original PS2.\n"
            "Pendientes: luces entre escenas, sombras, mundo, dano y muerte.\n"
            "Entrega privada: no subir recursos al repositorio ni CI.\n"
        ).encode(),
    }
    files["sd-card.zip"] = inspection_archive(files, STEM)
    return files, dict(
        schema_version=1,
        scope="private_character_lighting_inspection",
        build_id=build_id,
        material_manifest_sha256=material_sha,
        mesh_manifest_sha256=mesh_sha,
        preset_sha256=preset_sha,
        runtime_sha256=reference_sha,
        reference_counter=preset["reference_counter"],
        lighting="fixed_capture_preset_recomputed_per_pose",
        physical_2ds_xl="pending",
        scene_light_selection="pending",
        gpu_vertex_bytes_per_frame=old["gpu_vertex_bytes_per_frame"],
        gpu_texture_bytes=old["gpu_texture_bytes"],
        lighting_scratch_limit_bytes=24576,
        build_files={k: hashlib.sha256(v).hexdigest() for k, v in sorted(artifacts.items())},
        capabilities=[],
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("material-source", "mesh-source", "preset", "reference", "build", "private-root"):
        parser.add_argument("--" + key, type=Path, required=True)
    for key in ("material-sha256", "mesh-sha256", "preset-sha256", "reference-sha256", "run-id"):
        parser.add_argument("--" + key, required=True)
    a = parser.parse_args(argv)
    files, report = prepare_files(
        a.material_source,
        a.material_sha256,
        a.mesh_source,
        a.mesh_sha256,
        a.preset,
        a.preset_sha256,
        a.reference,
        a.reference_sha256,
        a.build,
    )
    write_character_lighting_inspection_bundle(
        a.private_root, Path(__file__).resolve().parents[2], a.run_id, files, report
    )
    print(json.dumps({"status": "prepared", "build_id": report["build_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
