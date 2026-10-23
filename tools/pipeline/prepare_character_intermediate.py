"""Persist a private decoded-character intermediate, with no ISO/runtime access."""

import argparse
import hashlib
import json
from pathlib import Path

from tools.pipeline.character_intermediate import (
    CONVERTER,
    PROFILE,
    export_inspection,
    make_intermediate,
    read_intermediate,
    verify_source_document,
)
from tools.pipeline.inspection_inputs import bounded_read, checked
from tools.pipeline.intermediate_json import MAX_BYTES, decode_json, encode_json
from tools.pipeline.private_texture_output import write_character_intermediate_bundle


def prepare_files(skeleton_source, skeleton_sha, mesh_source, mesh_sha):
    provenance, docs = {}, {}
    for name, source, digest, documents in (
        ("skeleton", skeleton_source, skeleton_sha, ("skeleton", "animation")),
        ("mesh", mesh_source, mesh_sha, ("mesh",)),
    ):
        manifest = decode_json(checked(bounded_read(source / "manifest.json", 65536), digest))
        provenance[name] = manifest
        for document in documents:
            filename = document + ".json"
            raw = bounded_read(source / filename, MAX_BYTES)
            docs[document] = verify_source_document(raw, manifest, filename)
    raw = make_intermediate(docs, provenance)
    decoded = read_intermediate(raw)
    if encode_json(decoded["documents"]) != encode_json(docs):
        raise ValueError("Decoded metadata round-trip differs")
    files = export_inspection(raw)
    if export_inspection(files["intermediate.json"]) != files:
        raise ValueError("Inspection reconstruction differs")
    return files, dict(
        schema_version=1,
        scope="private_character_intermediate",
        profile=PROFILE,
        converter=CONVERTER,
        source_manifests_sha256={"skeleton": skeleton_sha, "mesh": mesh_sha},
        logical_roundtrip=True,
        inspection_regeneration_identical=True,
        source_json_whitespace_preserved=False,
        original_mdl_reconstruction=False,
        original_animation_samples_preserved=len(docs["animation"]["frames"]),
        inspection_samples_inclusive=[0, 23],
        files_sha256={name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        capabilities=[],
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("skeleton-source", "mesh-source", "private-root"):
        parser.add_argument("--" + key, type=Path, required=True)
    for key in ("skeleton-sha256", "mesh-sha256", "run-id"):
        parser.add_argument("--" + key, required=True)
    args = parser.parse_args(argv)
    try:
        files, report = prepare_files(
            args.skeleton_source, args.skeleton_sha256, args.mesh_source, args.mesh_sha256
        )
        write_character_intermediate_bundle(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
        )
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "rejected", "error_type": type(error).__name__}))
        return 1
    print(json.dumps({"status": "prepared", "profile": PROFILE}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
