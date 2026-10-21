"""Decode a pinned character MDL into a private, unverified mesh candidate."""

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from tools.pipeline.decode_skeleton_animation import PairReader, read_pair_payloads
from tools.pipeline.decoders.ps2_character_mesh import CharacterMeshError
from tools.pipeline.decoders.ps2_character_mesh import decode_character_mesh as decode_mesh
from tools.pipeline.decoders.ps2_character_vif import CharacterVifError
from tools.pipeline.decoders.ps2_skeleton import SkeletonDecodeError
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.private_texture_output import write_character_mesh_bundle
from tools.pipeline.profile import ProfileError


def decode_selected_mesh(reader: PairReader, selection: dict) -> tuple[dict[str, bytes], dict]:
    payloads, resources, structure = read_pair_payloads(reader, selection)
    mesh = decode_mesh(payloads["model"])
    vertices = [vertex for part in mesh.submeshes for vertex in part.vertices]
    report = {
        "schema_version": 1,
        "scope": "ps2_character_mesh_candidate",
        "status": "decoded_candidate",
        "selection": selection,
        "resources": resources,
        "container_structure": structure,
        "model_id": mesh.skeleton.model_id,
        "recipe": "mdl_v3_unmasked_skip_vif_integer_mesh_v1",
        "summary": {
            "bones": len(mesh.skeleton.parents),
            "helpers": len(mesh.helpers),
            "submeshes": len(mesh.submeshes),
            "blend_submeshes": sum(part.blend_partition for part in mesh.submeshes),
            "vertices": len(vertices),
            "triangles": sum(len(part.triangles) for part in mesh.submeshes),
            "suppressed_commands": sum(part.suppressed_commands for part in mesh.submeshes),
            "degenerate_triangles": sum(part.degenerate_triangles for part in mesh.submeshes),
            "influence_counts": dict(sorted(Counter(len(v.bones) for v in vertices).items())),
            "weight_sums_q12": dict(sorted(Counter(sum(v.weights_q12) for v in vertices).items())),
            "referenced_textures": sorted({part.texture_index for part in mesh.submeshes}),
        },
        "position_space": "primary_bone_local_q4_candidate",
        "normals": "stored_q12_sign_and_transform_unverified",
        "uv": "stored_q12_no_v_flip",
        "weight_policy": "preserve_integer_deficit_no_renormalization",
        "pending": [
            "runtime_skinning_and_helpers",
            "runtime_winding_and_normals",
            "model_materials_and_textures",
            "world_and_3ds_basis",
            "animated_mesh_viewer",
            "damage_and_death_transitions",
        ],
        "capabilities": [],
    }
    raw = (
        json.dumps({"schema_version": 1, **asdict(mesh)}, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode()
    return {"mesh.json": raw}, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("iso", "selection", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("selection-sha256", "run-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        selection = load_catalog(args.selection, args.selection_sha256)
        with IsoImage(args.iso) as reader:
            files, report = decode_selected_mesh(reader, selection)
        manifest = write_character_mesh_bundle(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
        )
    except (
        ProfileError,
        SkeletonDecodeError,
        CharacterMeshError,
        CharacterVifError,
        OSError,
    ) as error:
        code = "CM_IO_ERROR" if isinstance(error, OSError) else getattr(error, "code", str(error))
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "decoded_candidate", **manifest["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
