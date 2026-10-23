"""Lossless decoded character sidecar and repeatable existing SAN/SCM recipes."""

from tools.pipeline.animation_inspection import inspection_clip
from tools.pipeline.character_inspection import inspection_character
from tools.pipeline.inspection_inputs import checked
from tools.pipeline.intermediate_json import decode_json, encode_json

PROFILE = "ps2-character-0209-v1"
CONVERTER = "decoded-character-intermediate-v1"
DECODERS = {
    "skeleton": "ps2-mdl-skeleton-v1",
    "animation": "sh3-ps2-anm-0209-46-v1",
    "mesh": "mdl_v3_unmasked_skip_vif_integer_mesh_v1",
}
CONVENTIONS = {
    "position": "primary_bone_local_q4",
    "normal": "stored_q12_no_normalization",
    "uv": "stored_q12_no_v_flip",
    "weights": "q12_preserve_deficit_no_renormalization",
    "matrices": "column_major_affine",
    "hierarchy": "forest_independent_roots",
    "interpolation": "nlerp_hemisphere_corrected",
    "clip_id": 0x1449,
    "samples_inclusive": [0, 23],
    "period_q12": 98304,
    "observed_increment_q12": 3686,
    "preview_evaluations_per_second": 25,
    "ps2_cadence_equivalence": "not_claimed",
    "world_basis_origin_scale": "separate_from_model_pose",
    "unrepresented": "all_76_samples_and_source_metadata_retained_in_sidecar",
}
SOURCES = {
    "skeleton": ("ps2_skeleton_animation_candidate", "sh3-ps2-anm-0209-46-v1"),
    "mesh": ("ps2_character_mesh_candidate", "mdl_v3_unmasked_skip_vif_integer_mesh_v1"),
}


def fields(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError("Unexpected intermediate fields")


def _validate(value):
    fields(
        value,
        (
            "schema_version",
            "profile",
            "converter",
            "decoders",
            "conventions",
            "documents",
            "provenance",
        ),
    )
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["profile"] != PROFILE
        or value["converter"] != CONVERTER
        or encode_json(value["decoders"]) != encode_json(DECODERS)
        or encode_json(value["conventions"]) != encode_json(CONVENTIONS)
    ):
        raise ValueError("Unsupported character intermediate profile")
    docs, provenance = value["documents"], value["provenance"]
    fields(docs, ("skeleton", "animation", "mesh"))
    fields(provenance, SOURCES)
    try:
        for name, (scope, recipe) in SOURCES.items():
            manifest = provenance[name]
            if (
                type(manifest["schema_version"]) is not int
                or manifest["schema_version"] != 1
                or manifest["scope"] != scope
                or manifest["recipe"] != recipe
                or type(manifest["model_id"]) is not int
                or manifest["model_id"] != 0x209
            ):
                raise ValueError("Unsupported source decoder")
            for resource in ("model", "animation"):
                identity = manifest["resources"][resource]
                other = provenance["skeleton"]["resources"][resource]
                if (
                    type(identity["size"]) is not int
                    or not 0 < identity["size"] <= 16 * 1024 * 1024
                    or (identity["size"], identity["sha256"]) != (other["size"], other["sha256"])
                    or type(identity["sha256"]) is not str
                    or len(identity["sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in identity["sha256"])
                ):
                    raise ValueError("Intermediate resource identity differs")
        for doc in docs.values():
            if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
                raise ValueError("Unsupported decoded schema")
        for name in ("skeleton", "animation"):
            if type(docs[name]["model_id"]) is not int or docs[name]["model_id"] != 0x209:
                raise ValueError("Unexpected decoded model")
        rest = {k: v for k, v in docs["skeleton"].items() if k != "schema_version"}
        if encode_json(rest) != encode_json(docs["mesh"]["skeleton"]):
            raise ValueError("Mesh and animation skeleton differ")
        clip = inspection_clip(docs["skeleton"], docs["animation"])
        mesh = inspection_character(docs["mesh"], clip)
    except (KeyError, IndexError, TypeError, OverflowError) as error:
        raise ValueError("Malformed character intermediate") from error
    return clip, mesh


def make_intermediate(documents, provenance):
    value = dict(
        schema_version=1,
        profile=PROFILE,
        converter=CONVERTER,
        decoders=DECODERS,
        conventions=CONVENTIONS,
        documents=documents,
        provenance=provenance,
    )
    raw = encode_json(value)
    _validate(decode_json(raw))
    return raw


def read_intermediate(raw):
    value = decode_json(raw)
    _validate(value)
    return value


def export_inspection(raw):
    """No source I/O: all original decoded metadata travels with the derived bytes."""
    value = decode_json(raw)
    clip, mesh = _validate(value)
    return {"intermediate.json": encode_json(value), "animation.san": clip, "character.scm": mesh}


def verify_source_document(raw, manifest, name):
    entries = [f for f in manifest["files"] if f["file"] == name]
    if len(entries) != 1 or type(entries[0]["size"]) is not int or len(raw) != entries[0]["size"]:
        raise ValueError("Missing, duplicate or resized source document")
    return decode_json(checked(raw, entries[0]["sha256"]))
