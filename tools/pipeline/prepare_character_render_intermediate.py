"""Import pinned CT/LI/GC inputs into a self-contained private intermediate bundle."""

import argparse
import json
from pathlib import Path

from tools.pipeline.character_intermediate import fields
from tools.pipeline.character_render_intermediate import (
    BLOB_LIMITS,
    CONVERTER,
    PROFILE,
    SOURCES,
    export_render,
    inventory,
    make_render,
    sha,
    verify_file,
)
from tools.pipeline.inspection_inputs import bounded_read, checked
from tools.pipeline.intermediate_json import MAX_BYTES, decode_json
from tools.pipeline.prepare_character_world_probe import extract_instances
from tools.pipeline.private_texture_output import write_character_render_intermediate_bundle


def prepare_files(inputs):
    fields(inputs, SOURCES)
    for entry in inputs.values():
        fields(entry, ("path", "sha256"))
        if type(entry["path"]) is not str or not Path(entry["path"]).is_absolute():
            raise ValueError("Expected absolute private input path")

    def read(key, limit, filename=None):
        item = inputs[key]
        path = Path(item["path"])
        return checked(bounded_read(path / filename if filename else path, limit), item["sha256"])

    base_manifest = decode_json(read("base", 65536, "manifest.json"))
    materials_manifest = decode_json(read("materials", 65536, "manifest.json"))
    entries = inventory(materials_manifest)
    base_raw = verify_file(
        bounded_read(Path(inputs["base"]["path"]) / "intermediate.json", MAX_BYTES),
        base_manifest,
        "intermediate.json",
    )
    base = decode_json(base_raw)
    source = Path(inputs["materials"]["path"])
    materials_raw = verify_file(
        bounded_read(source / "materials.json", 131072), materials_manifest, "materials.json"
    )
    blobs = {
        name: verify_file(
            bounded_read(source / name, entries[name]["size"]), materials_manifest, name
        )
        for name in BLOB_LIMITS
    }
    docs = {
        name: decode_json(read(name, 131072))
        for name in (
            "material_reference",
            "lighting_preset",
            "lighting_reference",
            "world_reference",
        )
    }
    instances, counter = extract_instances(
        docs["world_reference"],
        read("world_state", 64 * 1024 * 1024),
        base["provenance"]["mesh"]["resources"],
    )
    docs["world_placements"] = dict(
        instances=[dict(id=i["id"], model=list(i["model"])) for i in instances],
        reference_counter=counter,
    )
    docs["materials"] = decode_json(materials_raw)
    provenance = dict(
        base_manifest=base_manifest,
        materials_manifest=materials_manifest,
        source_sha256={key: inputs[key]["sha256"] for key in SOURCES},
    )
    files = make_render(base, docs, provenance, blobs)
    if files != export_render(files["intermediate.json"], {k: files[k] for k in BLOB_LIMITS}):
        raise ValueError("Render intermediate reconstruction differs")
    return files, dict(
        schema_version=1,
        scope="private_character_render_intermediate",
        profile=PROFILE,
        converter=CONVERTER,
        source_sha256=provenance["source_sha256"],
        logical_roundtrip=True,
        inspection_regeneration_identical=True,
        original_blobs_preserved=len(blobs),
        lighting_and_world="separate_inspection_variants",
        original_mdl_or_state_rebuild=False,
        capabilities=[],
        files_sha256={k: sha(v) for k, v in files.items()},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("inputs", "private-root"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        files, report = prepare_files(decode_json(bounded_read(args.inputs, 16384)))
        write_character_render_intermediate_bundle(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
        )
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({"status": "rejected", "error_type": type(error).__name__}))
        return 1
    print(json.dumps({"status": "prepared", "profile": PROFILE}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
