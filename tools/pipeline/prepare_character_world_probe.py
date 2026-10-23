"""Prepare a private fixed-placement viewer from a pinned GC-T4 snapshot."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.inspectors.pcsx2_state import read_state_members
from tools.pipeline.character_inspection import inspection_character
from tools.pipeline.character_world_inspection import encode_world
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.inspection_inputs import bounded_read, checked, read_build
from tools.pipeline.prepare_character_material_probe import manifest_file
from tools.pipeline.private_texture_output import write_character_world_inspection_bundle

STEM = "sh3_character_world_probe"


def extract_instances(reference, state, resources=None):
    if (
        reference["schema_version"] != 1
        or reference["scope"] != "gc_t4_character_world_bounded"
        or reference["status"] != "pass"
        or reference["guest_writes"] is not False
        or reference["instance_observations"] != 84
    ):
        raise ValueError("Unsupported world reference")
    capture = reference["continuous_snapshots"][0]
    if capture["slot"] != 8 or len(capture["actors"]) != 3:
        raise ValueError("Unexpected source capture")
    checked(state, capture["sha256"])
    (ram,) = read_state_members(state, (("eeMemory.bin", 32 * 1024 * 1024),))
    if len(ram) != 32 * 1024 * 1024:
        raise ValueError("Incomplete guest RAM")
    for window in reference["code_windows"]:
        a, n = int(window["address"], 16), window["size"]
        if type(n) is not int or not 0 < a <= len(ram) - n or not 0 < n <= 4096:
            raise ValueError("Invalid code window")
        checked(ram[a : a + n], window["sha256"])
    result = []
    for actor in sorted(capture["actors"], key=lambda a: a["instance"]):
        a = int(actor["address"], 16)
        if (
            not 0x4481D0 <= a < 0x4481D0 + 32 * 0x320
            or (a - 0x4481D0) % 0x320
            or struct.unpack_from("<HH", ram, a + 12) != (0x209, actor["instance"])
            or list(struct.unpack_from("<4f", ram, a + 0x20)) != actor["position"]
            or list(struct.unpack_from("<4f", ram, a + 0x30)) != actor["rotation"]
            or struct.unpack_from("<I", ram, a + 0x278)[0] != actor["counter"]
        ):
            raise ValueError("Instance differs from audit")
        result.append(dict(id=actor["instance"], model=struct.unpack_from("<16f", ram, a + 0x40)))
        if resources is not None:
            for name, offset, adjustment, size in (
                ("model", 0x308, -96, 833712),
                ("animation", 0x30C, 0, 3500),
            ):
                address = struct.unpack_from("<I", ram, a + offset)[0] + adjustment
                if not 0 < address <= len(ram) - size or resources[name]["size"] != size:
                    raise ValueError("Unexpected resident resource")
                checked(ram[address : address + size], resources[name]["sha256"])
    if [r["id"] for r in result] != [0x18E, 0x18F, 0x190]:
        raise ValueError("Unexpected instances")
    return result, capture["actors"][0]["counter"]


def prepare_files(
    material_source, material_sha, mesh_source, reference_path, reference_sha, state_path, build
):
    old = json.loads(checked(bounded_read(material_source / "manifest.json", 65536), material_sha))
    reference = json.loads(checked(bounded_read(reference_path, 131072), reference_sha))
    if old["scope"] != "private_character_material_inspection":
        raise ValueError("Unexpected source viewer")
    mesh_manifest = json.loads(
        checked(bounded_read(mesh_source / "manifest.json", 65536), old["mesh_manifest_sha256"])
    )
    if mesh_manifest["scope"] != "ps2_character_mesh_candidate":
        raise ValueError("Unexpected mesh source")
    state = bounded_read(state_path, 64 * 1024 * 1024)
    instances, counter = extract_instances(reference, state, mesh_manifest["resources"])
    clip = manifest_file(material_source, old, "animation.san", 1248)
    character = manifest_file(material_source, old, "character.scm", 100000)
    material = manifest_file(material_source, old, "character.sct", 3145796)
    mesh = json.loads(manifest_file(mesh_source, mesh_manifest, "mesh.json", 4 * 1024 * 1024))
    if inspection_character(mesh, clip) != character:
        raise ValueError("World model differs from audited resource")
    world = encode_world(instances, counter, character, clip, material)
    artifacts, build_id = read_build(build, STEM)
    files = {
        "animation.san": clip,
        "character.scm": character,
        "character.sct": material,
        "character.scw": world,
        f"{STEM}.3dsx": artifacts[f"{STEM}.3dsx"],
        f"{STEM}.smdh": artifacts[f"{STEM}.smdh"],
        "LEEME.txt": (
            f"SH3 - world placement / Build {build_id}\n\n"
            f"Extrae en la raiz SD. Abre SH3 world placement. Carpeta /3ds/{STEM}/\n"
            "Tres caballos: colocaciones capturadas fijas, animacion sincronizada y luz neutra.\n"
            "A: pausa. R: paso en pausa. L: reinicio Q12=0. Cruceta: camara.\n"
            "X/Y: zoom. B: reset. START: salir. Prueba tapa y HOME.\n"
            "Observa 60 segundos; anota Skin CPU, Place CPU, Submit+wait, GPU previous.\n"
            "Preview 25 evaluaciones/s. Submit incluye espera; no sumar para obtener FPS.\n"
            "No reproduce trayectoria, IA, fases de combate ni iluminacion de escena.\n"
            "Conserva visores anteriores. Recursos privados: no subir a git ni CI.\n"
        ).encode(),
    }
    files["sd-card.zip"] = inspection_archive(files, STEM)
    return files, dict(
        schema_version=1,
        scope="private_character_world_inspection",
        build_id=build_id,
        material_manifest_sha256=material_sha,
        world_reference_sha256=reference_sha,
        source_state_sha256=hashlib.sha256(state).hexdigest(),
        instance_ids=[i["id"] for i in instances],
        reference_counter=counter,
        lighting="neutral",
        placement="fixed_snapshot_shared_clip",
        gpu_vertex_bytes_per_frame=old["gpu_vertex_bytes_per_frame"] * 3,
        gpu_texture_bytes=old["gpu_texture_bytes"],
        draw_calls=9,
        physical_2ds_xl="pending",
        capabilities=[],
        build_files={k: hashlib.sha256(v).hexdigest() for k, v in sorted(artifacts.items())},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("material-source", "mesh-source", "reference", "state", "build", "private-root"):
        parser.add_argument("--" + key, type=Path, required=True)
    for key in ("material-sha256", "reference-sha256", "run-id"):
        parser.add_argument("--" + key, required=True)
    a = parser.parse_args(argv)
    files, report = prepare_files(
        a.material_source,
        a.material_sha256,
        a.mesh_source,
        a.reference,
        a.reference_sha256,
        a.state,
        a.build,
    )
    write_character_world_inspection_bundle(
        a.private_root, Path(__file__).resolve().parents[2], a.run_id, files, report
    )
    print(json.dumps({"status": "prepared", "build_id": report["build_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
