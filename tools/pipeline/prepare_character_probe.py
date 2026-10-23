"""Prepare a private animated mesh with CM-T4 and continuity provenance."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.pipeline.character_inspection import inspection_character
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.inspection_inputs import bounded_read, checked, read_build
from tools.pipeline.prepare_animation_probe import read_verified_clip
from tools.pipeline.private_texture_output import write_character_inspection_bundle


def prepare_files(
    source, source_sha, reference, reference_sha, mesh_source, mesh_sha, runtime, runtime_sha, build
):
    clip, animation_manifest = read_verified_clip(source, source_sha, reference, reference_sha)
    manifest = json.loads(checked(bounded_read(mesh_source / "manifest.json", 65536), mesh_sha))
    oracle = json.loads(checked(bounded_read(runtime, 131072), runtime_sha))
    if (
        manifest["scope"] != "ps2_character_mesh_candidate"
        or manifest["model_id"] != 0x209
        or manifest["recipe"] != "mdl_v3_unmasked_skip_vif_integer_mesh_v1"
        or oracle["schema_version"] != 1
        or oracle["scope"] != "cm_t4_bounded_character_skinning"
        or oracle["status"] != "pass"
        or oracle["vertex_samples"] != 500
        or oracle["distinct_vertices"] != 125
        or len(oracle["poses"]) != 4
        or oracle["provenance"]["guest_writes"] is not False
        or oracle["gs"]["resident_tail_packet_exact"] is not True
    ):
        raise ValueError("Unsupported CM-T4 reference")
    for name, key in (("model", "mdl_sha256"), ("animation", "anm_sha256")):
        digest = manifest["resources"][name]["sha256"]
        if (
            digest != animation_manifest["resources"][name]["sha256"]
            or digest != oracle["provenance"][key]
        ):
            raise ValueError("Character resource identity differs")
    entries = [f for f in manifest["files"] if f["file"] == "mesh.json"]
    if len(entries) != 1 or entries[0]["sha256"] != oracle["provenance"]["mesh_sha256"]:
        raise ValueError("Missing or mismatched mesh")
    raw = checked(bounded_read(mesh_source / "mesh.json", 4 * 1024 * 1024), entries[0]["sha256"])
    if len(raw) != entries[0]["size"]:
        raise ValueError("Mesh size differs")
    character = inspection_character(json.loads(raw), clip)
    artifacts, build_id = read_build(build, "sh3_character_probe")
    vertices, indices = struct.unpack_from("<2I", character, 8)
    files = {
        "animation.san": clip,
        "character.scm": character,
        "sh3_character_probe.3dsx": artifacts["sh3_character_probe.3dsx"],
        "sh3_character_probe.smdh": artifacts["sh3_character_probe.smdh"],
        "LEEME.txt": (
            f"SH3 - malla animada 0x0209 / clip 0x1449\nBuild: {build_id}\n\n"
            "Extrae sd-card.zip en la raiz de la SD.\n"
            "Abre SH3 character inspection en Homebrew Launcher.\n"
            "Archivos en /3ds/sh3_character_probe/\n"
            f"Malla: {vertices} vertices, {indices // 3} triangulos.\n"
            "Sombreado propio de inspeccion, sin texturas originales.\n"
            "A: pausa. R: avanzar en pausa. L: reiniciar clip.\n"
            "Cruceta: camara. X/Y: zoom. B: reset. START: salir.\n"
            "Prueba tapa y HOME; suelta los controles al regresar.\n"
            "Observa 60 segundos y anota tiempos CPU/GPU mostrados.\n"
            "Submit+wait incluye espera GPU, no es coste puro de copia.\n"
            "Preview 25 evaluaciones/s, sin equivalencia de cadencia PS2.\n"
            "CM-T4 verifico directamente 2/15 submallas.\n"
            "Pendientes: materiales, mundo, dano 0x144A y muerte 0x144B.\n"
            "Conserva los otros visores. No requiere CIA/FBI.\n"
            "Entrega privada; no subir datos al repositorio ni CI.\n"
        ).encode(),
    }
    files["sd-card.zip"] = inspection_archive(files, "sh3_character_probe")
    return files, {
        "schema_version": 1,
        "scope": "private_character_inspection",
        "build_id": build_id,
        "source_manifest_sha256": source_sha,
        "continuity_sha256": reference_sha,
        "mesh_manifest_sha256": mesh_sha,
        "runtime_sha256": runtime_sha,
        "clip": "0x1449",
        "vertex_count": vertices,
        "triangles": indices // 3,
        "gpu_vertex_bytes_per_frame": indices * 36,
        "draw_calls": 1,
        "preview_evaluations_per_second": 25,
        "material": "own_two_sided_inspection",
        "pcsx2_verified_submeshes": [4, 5],
        "physical_2ds_xl": "pending",
        "damage_0x144a": "pending",
        "death_0x144b": "pending",
        "capabilities": [],
        "build_files": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(artifacts.items())},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "reference", "mesh-source", "runtime", "build", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("source-sha256", "reference-sha256", "mesh-sha256", "runtime-sha256", "run-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    files, report = prepare_files(
        args.source,
        args.source_sha256,
        args.reference,
        args.reference_sha256,
        args.mesh_source,
        args.mesh_sha256,
        args.runtime,
        args.runtime_sha256,
        args.build,
    )
    write_character_inspection_bundle(
        args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
    )
    print(json.dumps({"status": "prepared", "build_id": report["build_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
