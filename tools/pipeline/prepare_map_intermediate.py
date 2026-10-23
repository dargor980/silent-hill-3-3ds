"""Prepare an exclusive private static MAP/material intermediate from pinned inputs."""

import argparse
import json
from pathlib import Path

from tools.pipeline.inspection_inputs import bounded_read, checked
from tools.pipeline.intermediate_assets import fields, inventory, sha, verify_file
from tools.pipeline.intermediate_json import decode_json
from tools.pipeline.map_intermediate import (
    BLOB_NAMES,
    CONVERTER,
    GEOMETRY_LIMITS,
    PROFILE,
    SOURCES,
    TEXTURE_EXACT,
    TEXTURE_LIMITS,
    export_map,
    make_map,
)
from tools.pipeline.private_texture_output import write_map_intermediate_bundle


def prepare_files(inputs):
    fields(inputs, SOURCES)
    for entry in inputs.values():
        fields(entry, ("path", "sha256"))
        if type(entry["path"]) is not str or not Path(entry["path"]).is_absolute():
            raise ValueError("Expected absolute map input path")

    def read(key, limit, filename=None):
        item = inputs[key]
        path = Path(item["path"])
        return checked(bounded_read(path / filename if filename else path, limit), item["sha256"])

    gm = decode_json(read("geometry", 65536, "manifest.json"))
    tm = decode_json(read("texture", 65536, "manifest.json"))
    ge = inventory(gm, GEOMETRY_LIMITS)
    te = inventory(tm, TEXTURE_LIMITS, TEXTURE_EXACT)

    def payload(key, name, entry):
        return verify_file(bounded_read(Path(inputs[key]["path"]) / name, entry["size"]), entry)

    docs = dict(
        geometry=decode_json(payload("geometry", "geometry.json", ge["geometry.json"])),
        material_reference=decode_json(read("reference", 131072)),
        gs_report=decode_json(read("gs_report", 131072)),
        pixels_report=decode_json(read("pixels_report", 131072)),
    )
    blobs = {"inspection.obj": payload("geometry", "inspection.obj", ge["inspection.obj"])}
    blobs.update({name: payload("texture", name, entry) for name, entry in te.items()})
    provenance = dict(
        geometry_manifest=gm,
        texture_manifest=tm,
        source_sha256={key: inputs[key]["sha256"] for key in SOURCES},
    )
    files = make_map(docs, provenance, blobs)
    if files != export_map(files["intermediate.json"], {k: files[k] for k in BLOB_NAMES}):
        raise ValueError("Map reconstruction differs")
    return files, dict(
        schema_version=1,
        scope="private_map_intermediate",
        profile=PROFILE,
        converter=CONVERTER,
        source_sha256=provenance["source_sha256"],
        logical_roundtrip=True,
        inspection_regeneration_identical=True,
        original_sidecars_preserved=len(blobs),
        capabilities=[],
        original_map_rebuild=False,
        new_ps2_or_hardware_execution=False,
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
        write_map_intermediate_bundle(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
        )
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({"status": "rejected", "error_type": type(error).__name__}))
        return 1
    print(json.dumps({"status": "prepared", "profile": PROFILE}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
