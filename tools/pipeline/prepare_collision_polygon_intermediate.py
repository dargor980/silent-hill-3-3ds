"""Prepare the fixed CF-T6 private polygon corpus; publish only after full readback."""

import argparse
import json
from pathlib import Path

from tools.pipeline import collision_polygon_recipe as recipe
from tools.pipeline.collision_polygon_inputs import PinnedInputs, absolute_path, require
from tools.pipeline.collision_polygon_intermediate import (
    CONVERTER,
    PROFILE,
    make_collision_polygons,
)
from tools.pipeline.collision_polygon_output import write_collision_polygon_bundle
from tools.pipeline.intermediate_assets import fields
from tools.pipeline.intermediate_json import decode_json, encode_json


def _prepare(inputs, custody):
    # Clone bounded configuration, including programmatic callers, before using paths.
    raw = encode_json(inputs)
    require(len(raw) <= 32768)
    inputs = decode_json(raw)
    fields(inputs, (*recipe.LIMITS, "copy_root"))
    copy_root = absolute_path(inputs["copy_root"])
    anchors = {}
    for key in recipe.LIMITS:
        fields(inputs[key], ("path", "size", "sha256"))
        absolute_path(inputs[key]["path"])
        anchors[key] = recipe.pick(inputs[key], ("size", "sha256"))
        # A different historical corpus needs a new recipe, not a silent CLI override.
        recipe.equal(anchors[key], recipe.ANCHORS[key])
    documents = {
        key: decode_json(custody.read(absolute_path(inputs[key]["path"]), limit, anchors[key]))
        for key, limit in recipe.LIMITS.items()
    }
    entries, records, selected, links = recipe.select(documents, anchors)
    sources = {}
    for entry in entries:
        record = records[entry["id"]]
        sources[entry["id"]] = custody.read(
            copy_root / record["file"], 65536, recipe.pick(record, ("size", "sha256"))
        )
    # All source pins and bindings have passed before the first decoder invocation.
    provenance = dict(
        source_identity=recipe.IDENTITY.copy(),
        anchors=anchors,
        scene_evidence="historical_report_only",
    )
    files = make_collision_polygons(provenance, entries, links, sources)
    counts = recipe.verify_outcomes(files, selected, documents["classification_audit"]["summary"])
    custody.verify()
    return files, dict(
        schema_version=1,
        scope="private_cld_polygons_intermediate",
        profile=PROFILE,
        converter=CONVERTER,
        state="structural_observation",
        capabilities=[],
        new_vm_execution=False,
        collision_response_verified=False,
        scene_link_rechecked=False,
        original_container_rebuild=False,
        counts=counts,
    )


def prepare_files(inputs):
    """Validate and reconstruct in memory, without creating any output directory."""
    return _prepare(inputs, PinnedInputs())


def prepare_and_write(inputs_path, private_root, repository, run_id):
    custody = PinnedInputs()
    inputs = decode_json(custody.read(inputs_path, 32768))
    files, report = _prepare(inputs, custody)
    return write_collision_polygon_bundle(
        private_root, repository, run_id, files, report, recheck=custody.verify
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("inputs", "private-root"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        prepare_and_write(
            args.inputs, args.private_root, Path(__file__).resolve().parents[2], args.run_id
        )
    except (ValueError, OSError, KeyError, TypeError, IndexError, OverflowError) as error:
        print(json.dumps(dict(status="rejected", error_type=type(error).__name__)))
        return 1
    print(json.dumps(dict(status="prepared", profile=PROFILE)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
