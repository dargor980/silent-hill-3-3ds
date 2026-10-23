"""Pure render sidecar: original CT blobs plus separate LI/GC inspection variants."""

import hashlib

from tools.pipeline.character_intermediate import export_inspection, fields
from tools.pipeline.character_lighting_inspection import encode_lighting
from tools.pipeline.character_material_inspection import IMAGES, encode_material, material_ranges
from tools.pipeline.character_world_inspection import encode_world
from tools.pipeline.decoders.ps2_indexed8 import IndexedTexture, render_palette
from tools.pipeline.inspection_inputs import checked
from tools.pipeline.intermediate_json import decode_json, encode_json
from tools.qa.gs_material_oracle import require_character_profile

PROFILE = "ps2-character-0209-render-v1"
CONVERTER = "decoded-character-render-intermediate-v1"
CONVENTIONS = {
    "materials_decoder": "mdl_identity_images_psmt8_four_cluts_v1",
    "textures_decoder": "sh3-ps2-indexed8-four-cluts-v1",
    "inspection_recipes": ["SAN1", "SCM1", "SCT1", "SCL1", "SCW1"],
    "rgba": "original_ps2_alpha_0_128_row_major_no_flip",
    "png": "preserved_preview_min_255_2a_alpha_saturation",
    "palettes": "four_preserved_only_zero_drawn",
    "material": "opaque_ate_abe_zero_two_sided_bilinear_clamp_signed_q12_uv",
    "lighting": "mode2_type10_fixed_capture_recomputed_per_pose",
    "placements": "three_fixed_snapshot_shared_clip_neutral_light",
    "world_basis": "diag_1_minus1_minus1_after_model_preserve_w_shared_origin_scale",
    "composition": "lighting_and_world_are_separate_inspection_variants",
    "unrepresented": "all_decoded_fields_and_blobs_retained_no_original_mdl_or_state_rebuild",
}
SOURCES = (
    "base",
    "materials",
    "material_reference",
    "lighting_preset",
    "lighting_reference",
    "world_reference",
    "world_state",
)
DOCUMENTS = (
    "materials",
    "material_reference",
    "lighting_preset",
    "lighting_reference",
    "world_reference",
    "world_placements",
)
BLOB_LIMITS = {}
for _image in range(3):
    BLOB_LIMITS[f"image-{_image}.indices"] = 262144
    for _palette in range(4):
        BLOB_LIMITS[f"image-{_image}-palette-{_palette}.bin"] = 1024
    BLOB_LIMITS[f"texture-{_image}.rgba"] = 1048576
    BLOB_LIMITS[f"texture-{_image}.png"] = 1048576
OUTPUT_NAMES = set(BLOB_LIMITS) | {
    "intermediate.json",
    "animation.san",
    "character.scm",
    "character.sct",
    "character.scl",
    "character.scw",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(manifest):
    """Exact CT file names, bounded sizes; no source-controlled filesystem paths."""
    entries = manifest["files"]
    names = [entry["file"] for entry in entries]
    if len(names) != 22 or set(names) != set(BLOB_LIMITS) | {"materials.json"}:
        raise ValueError("Unsupported CT inventory")
    for entry in entries:
        name, size, digest = entry["file"], entry["size"], entry["sha256"]
        limit = BLOB_LIMITS.get(name, 131072)
        if (
            type(size) is not int
            or not 0 < size <= limit
            or (name.endswith((".indices", ".bin", ".rgba")) and size != limit)
            or type(digest) is not str
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("Invalid CT inventory entry")
    return {entry["file"]: entry for entry in entries}


def verify_file(raw, manifest, name):
    entries = [entry for entry in manifest["files"] if entry["file"] == name]
    if (
        len(entries) != 1
        or type(raw) is not bytes
        or type(entries[0]["size"]) is not int
        or len(raw) != entries[0]["size"]
    ):
        raise ValueError("Intermediate dependency size differs")
    return checked(raw, entries[0]["sha256"])


def _references(value, files):
    base, docs, provenance = value["base"], value["documents"], value["provenance"]
    pins = provenance["source_sha256"]
    manifest = provenance["materials_manifest"]
    old = provenance["base_manifest"]
    if old["scope"] != "private_character_intermediate" or old["profile"] != base["profile"]:
        raise ValueError("Unsupported base provenance")
    for name in ("intermediate.json", "animation.san", "character.scm"):
        verify_file(files[name], old, name)
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["scope"] != "ps2_character_material_candidate"
        or manifest["recipe"] != CONVENTIONS["materials_decoder"]
        or type(docs["materials"]["schema_version"]) is not int
        or docs["materials"]["schema_version"] != 1
        or type(docs["materials"]["model_id"]) is not int
        or docs["materials"]["model_id"] != 0x209
    ):
        raise ValueError("Unsupported material provenance")
    resources = base["provenance"]["mesh"]["resources"]
    for name in ("model", "animation"):
        a, b = manifest["resources"][name], resources[name]
        if type(a["size"]) is not int or (a["size"], a["sha256"]) != (b["size"], b["sha256"]):
            raise ValueError("Render resource identity differs")
    ct = docs["material_reference"]
    if (
        type(ct["schema_version"]) is not int
        or ct["schema_version"] != 1
        or ct["scope"] != "ct_t4_character_material"
        or ct["status"] != "pass"
        or ct["provenance"]["guest_writes"] is not False
        or ct["provenance"]["mdl_sha256"] != resources["model"]["sha256"]
        or len(ct["submeshes"]) != 15
        or len(ct["draws"]) != 3
    ):
        raise ValueError("Unsupported material reference")
    for i, part in enumerate(ct["submeshes"]):
        if (
            type(part["submesh"]) is not int
            or part["submesh"] != i
            or type(part["image"]) is not int
            or part["image"] != IMAGES[i]
        ):
            raise ValueError("CT binding differs")
        if type(part["registers"]) is not dict:
            raise ValueError("Invalid GS register map")
        registers = {int(k, 16): int(v, 16) for k, v in part["registers"].items()}
        if len(registers) != len(part["registers"]):
            raise ValueError("Aliased GS register keys")
        require_character_profile(registers)
    preset, li = docs["lighting_preset"], docs["lighting_reference"]
    (mesh_entry,) = [e for e in base["provenance"]["mesh"]["files"] if e["file"] == "mesh.json"]
    if (
        type(preset["schema_version"]) is not int
        or preset["schema_version"] != 1
        or preset["scope"] != "captured_character_lighting_preset"
        or preset["li_report_sha256"] != pins["lighting_reference"]
        or li["status"] != "pass"
        or li["scope"] != "li_mode2_type10_character_lighting"
        or len(li["poses"]) != 4
        or li["provenance"]["new_guest_writes"] is not False
        or li["provenance"]["mdl_sha256"] != resources["model"]["sha256"]
        or li["provenance"]["mesh_sha256"] != mesh_entry["sha256"]
    ):
        raise ValueError("Unsupported lighting reference")
    for key, target in (
        ("input_sha256", "input_sha256"),
        ("output_sha256", "output_sha256"),
        ("draw_parameters_sha256", "draw_parameters_sha256"),
        ("reference_counter", "counter"),
    ):
        if preset[key] != li["poses"][-1][target]:
            raise ValueError("Lighting capture differs")
    gc, world = docs["world_reference"], docs["world_placements"]
    fields(world, ("instances", "reference_counter"))
    capture = gc["continuous_snapshots"][0]
    if (
        type(gc["schema_version"]) is not int
        or gc["schema_version"] != 1
        or gc["scope"] != "gc_t4_character_world_bounded"
        or gc["status"] != "pass"
        or gc["guest_writes"] is not False
        or gc["instance_observations"] != 84
        or capture["slot"] != 8
        or capture["sha256"] != pins["world_state"]
        or len(capture["actors"]) != 3
        or [i["id"] for i in world["instances"]] != [398, 399, 400]
    ):
        raise ValueError("Unsupported world reference")
    for actor, instance in zip(
        sorted(capture["actors"], key=lambda a: a["instance"]), world["instances"], strict=True
    ):
        fields(instance, ("id", "model"))
        if (
            actor["instance"] != instance["id"]
            or actor["counter"] != world["reference_counter"]
            or actor["position"] != instance["model"][12:]
        ):
            raise ValueError("World placement differs from capture")


def _textures(value, blobs):
    entries = inventory(value["provenance"]["materials_manifest"])
    fields(blobs, BLOB_LIMITS)
    for name, raw in blobs.items():
        if type(raw) is not bytes or len(raw) != entries[name]["size"]:
            raise ValueError("Invalid render blob extent")
        checked(raw, entries[name]["sha256"])
    textures = value["documents"]["materials"]["textures"]
    if len(textures) != 3:
        raise ValueError("Expected three texture descriptors")
    result = []
    for i, (texture, draw) in enumerate(
        zip(textures, value["documents"]["material_reference"]["draws"], strict=True)
    ):
        image = IndexedTexture(
            512,
            512,
            blobs[f"image-{i}.indices"],
            tuple(blobs[f"image-{i}-palette-{p}.bin"] for p in range(4)),
        )
        rgba = render_palette(image, 0, normalize_alpha=False)
        integers = [
            texture[k]
            for k in ("descriptor", "image", "palette", "width", "height", "alpha_min", "alpha_max")
        ]
        if (
            rgba != blobs[f"texture-{i}.rgba"]
            or type(draw["image"]) is not int
            or draw["image"] != i
            or draw["texture_sha256"] != sha(rgba)
            or any(type(x) is not int for x in integers)
            or integers != [i, i, 0, 512, 512, min(rgba[3::4]), max(rgba[3::4])]
            or texture["preview_rgba_sha256"] != sha(render_palette(image, 0, normalize_alpha=True))
        ):
            raise ValueError("Texture semantics differ")
        result.append(rgba)
    return result


def export_render(raw, blobs):
    """Reconstruct from the owned sidecar/blobs only; never read source paths."""
    value = decode_json(raw)
    fields(
        value,
        (
            "schema_version",
            "profile",
            "converter",
            "conventions",
            "base",
            "documents",
            "provenance",
        ),
    )
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["profile"] != PROFILE
        or value["converter"] != CONVERTER
        or encode_json(value["conventions"]) != encode_json(CONVENTIONS)
    ):
        raise ValueError("Unsupported render intermediate")
    fields(value["documents"], DOCUMENTS)
    fields(value["provenance"], ("base_manifest", "materials_manifest", "source_sha256"))
    fields(value["provenance"]["source_sha256"], SOURCES)
    for digest in value["provenance"]["source_sha256"].values():
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("Invalid source digest")
    try:
        files = export_inspection(encode_json(value["base"]))
        _references(value, files)
        textures = _textures(value, blobs)
        docs, mesh = value["documents"], value["base"]["documents"]["mesh"]
        scm, san = files["character.scm"], files["animation.san"]
        for binding in docs["materials"]["bindings"]:
            if any(
                type(binding[k]) is not int
                for k in ("submesh", "image", "descriptor", "palette", "offset")
            ):
                raise ValueError("Invalid material binding type")
        sct = encode_material(material_ranges(mesh, docs["materials"]), textures, scm)
        files["character.sct"] = sct
        files["character.scl"] = encode_lighting(docs["lighting_preset"], mesh, scm, san, sct)
        world = docs["world_placements"]
        files["character.scw"] = encode_world(
            world["instances"], world["reference_counter"], scm, san, sct
        )
    except (KeyError, TypeError, IndexError, OverflowError) as error:
        raise ValueError("Malformed render intermediate") from error
    return {**files, **blobs, "intermediate.json": encode_json(value)}


def make_render(base, documents, provenance, blobs):
    raw = encode_json(
        dict(
            schema_version=1,
            profile=PROFILE,
            converter=CONVERTER,
            conventions=CONVENTIONS,
            base=base,
            documents=documents,
            provenance=provenance,
        )
    )
    return export_render(raw, blobs)
