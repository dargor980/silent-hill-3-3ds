"""Prepare the private verified 0x1449 skeleton viewer; damage/death remain pending."""

import argparse
import hashlib
import json
from pathlib import Path

from tools.pipeline.animation_inspection import inspection_clip
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.inspection_inputs import bounded_read, checked, read_build
from tools.pipeline.private_texture_output import write_animation_inspection_bundle


def read_verified_clip(source, source_sha, reference, reference_sha):
    manifest = json.loads(checked(bounded_read(source / "manifest.json", 65536), source_sha))
    ref = json.loads(checked(bounded_read(reference, 131072), reference_sha))
    if (
        manifest["scope"] != "ps2_skeleton_animation_candidate"
        or manifest["recipe"] != "sh3-ps2-anm-0209-46-v1"
        or manifest["model_id"] != 0x209
        or ref["schema"] != "sh3-animation-continuity-observation-v1"
        or ref["continuous_loop_verified"] is not True
        or ref["natural_initial_selection_verified"] is not True
        or (ref["identity"]["start"], ref["identity"]["end"], ref["identity"]["loop"])
        != (0, 23, True)
        or ref["identity"]["actor"]["kind"] != 0x209
        or not ref["selections"]
        or any(s["clip"] != 0x1449 for s in ref["selections"])
        or len(ref["samples"]) != 28
        or any(s["sample"]["increment"] != 3686 for s in ref["samples"])
        or ref["provenance"]["state_restores"] != 0
    ):
        raise ValueError("Unsupported continuity reference")
    for name in ("model", "animation"):
        if ref["identity"][name + "_sha256"] != manifest["resources"][name]["sha256"]:
            raise ValueError("Reference resource identity differs")

    def payload(name):
        entries = [f for f in manifest["files"] if f["file"] == name]
        if len(entries) != 1:
            raise ValueError("Missing or duplicate animation input")
        data = checked(bounded_read(source / name, 262144), entries[0]["sha256"])
        if len(data) != entries[0]["size"]:
            raise ValueError("Animation input size differs")
        return json.loads(data)

    clip = inspection_clip(payload("skeleton.json"), payload("animation.json"))
    return clip, manifest


def prepare_files(source, source_sha, reference, reference_sha, build):
    clip, _ = read_verified_clip(source, source_sha, reference, reference_sha)
    artifacts, build_id = read_build(build, "sh3_animation_probe")
    files = {
        "animation.san": clip,
        "sh3_animation_probe.3dsx": artifacts["sh3_animation_probe.3dsx"],
        "sh3_animation_probe.smdh": artifacts["sh3_animation_probe.smdh"],
        "LEEME.txt": (
            f"SH3 - inspeccion de animacion 0x1449\nBuild: {build_id}\n\n"
            "Extrae sd-card.zip en la raiz de la SD.\n"
            "Abre SH3 animation inspection en Homebrew Launcher.\n"
            "Datos: /3ds/sh3_animation_probe/animation.san\n"
            "Veras tres juegos de ejes y un enlace, no la malla del caballo.\n"
            "Ejes: rojo X, verde Y, azul Z. Dos raices independientes.\n"
            "A: pausa. R: avanzar en pausa. L: reiniciar clip.\n"
            "Cruceta: camara. X/Y: zoom. B: reset camara. START: salir.\n"
            "Prueba tapa y HOME; suelta todos los controles al regresar.\n"
            "Preview: 25 evaluaciones/s, no cadencia PS2 medida.\n"
            "Pendientes: dano 0x144A, muerte 0x144B, malla y skinning.\n"
            "Conserva los otros visores. No requiere CIA/FBI.\n"
            "Entrega privada de tu copia; no subir al repositorio ni CI.\n"
        ).encode(),
    }
    files["sd-card.zip"] = inspection_archive(files, "sh3_animation_probe")
    return files, {
        "schema_version": 1,
        "scope": "private_animation_inspection",
        "build_id": build_id,
        "source_manifest_sha256": source_sha,
        "continuity_sha256": reference_sha,
        "clip": "0x1449",
        "frames": [0, 23],
        "increment_q12": 3686,
        "preview_evaluations_per_second": 25,
        "ps2_cadence_equivalence": "not_claimed",
        "physical_2ds_xl": "pending",
        "damage_0x144a": "pending",
        "death_0x144b": "pending",
        "mesh_skinning": "pending",
        "capabilities": [],
        "build_files": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(artifacts.items())},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "reference", "build", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("source-sha256", "reference-sha256", "run-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    files, report = prepare_files(
        args.source, args.source_sha256, args.reference, args.reference_sha256, args.build
    )
    write_animation_inspection_bundle(
        args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
    )
    print(json.dumps({"status": "prepared", "build_id": report["build_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
