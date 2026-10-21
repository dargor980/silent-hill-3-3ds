"""Acquire MDL images and explicit submesh bindings into a private inspection bundle."""

import argparse
import hashlib
import json
import zlib
from pathlib import Path

from tools.inspectors.texture_probe import TextureProbeError
from tools.pipeline.decode_skeleton_animation import PairReader, read_pair_payloads
from tools.pipeline.decoders.ps2_character_materials import (
    CharacterMaterialError,
    decode_character_materials,
)
from tools.pipeline.decoders.ps2_character_mesh import CharacterMeshError
from tools.pipeline.decoders.ps2_character_vif import CharacterVifError
from tools.pipeline.decoders.ps2_indexed8 import TextureDecodeError, render_palette
from tools.pipeline.decoders.ps2_skeleton import SkeletonDecodeError
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.preview_png import encode_rgba_png
from tools.pipeline.private_texture_output import write_character_material_bundle
from tools.pipeline.profile import ProfileError


def decode_selected_materials(reader: PairReader, selection: dict) -> tuple[dict[str, bytes], dict]:
    payloads, resources, structure = read_pair_payloads(reader, selection)
    decoded = decode_character_materials(payloads["model"])
    files, textures = {}, []
    for i, image in enumerate(decoded.images):
        files[f"image-{i}.indices"] = image.indices
        for p, palette in enumerate(image.palettes):
            files[f"image-{i}-palette-{p}.bin"] = palette
    for i, (image_index, palette) in enumerate(decoded.mesh.texture_descriptors):
        image = decoded.images[image_index]
        rgba = render_palette(image, palette, normalize_alpha=False)
        preview = render_palette(image, palette, normalize_alpha=True)
        files[f"texture-{i}.rgba"] = rgba
        files[f"texture-{i}.png"] = encode_rgba_png(image.width, image.height, preview)
        textures.append(
            {
                "descriptor": i,
                "image": image_index,
                "palette": palette,
                "width": image.width,
                "height": image.height,
                "alpha_min": min(rgba[3::4]),
                "alpha_max": max(rgba[3::4]),
                "preview_rgba_sha256": hashlib.sha256(preview).hexdigest(),
            }
        )
    bindings = [
        {
            "submesh": i,
            "offset": part.offset,
            "descriptor": part.texture_index,
            "image": decoded.mesh.texture_descriptors[part.texture_index][0],
            "palette": decoded.mesh.texture_descriptors[part.texture_index][1],
            "blend_partition": part.blend_partition,
            "header_words": part.header_words,
            "material_type_candidate": part.header_words[16] & 0xFFFF,
            "display_group_candidate": part.header_words[16] >> 16,
        }
        for i, part in enumerate(decoded.mesh.submeshes)
    ]
    document = {
        "schema_version": 1,
        "model_id": decoded.mesh.skeleton.model_id,
        "file_header_words": decoded.mesh.skeleton.file_header_words,
        "model_header_words": decoded.mesh.skeleton.model_header_words,
        "sector_offset": decoded.sector_offset,
        "image_table_words": decoded.image_table,
        "texture_descriptors": decoded.mesh.texture_descriptors,
        "texture_structure": decoded.structure,
        "headers": decoded.headers,
        "textures": textures,
        "bindings": bindings,
    }
    files["materials.json"] = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode()
    return files, {
        "schema_version": 1,
        "scope": "ps2_character_material_candidate",
        "status": "decoded_candidate",
        "selection": selection,
        "resources": resources,
        "container_structure": structure,
        "recipe": "mdl_identity_images_psmt8_four_cluts_v1",
        "descriptor_palette_policy": "zero_only_other_gs_selectors_unverified",
        "summary": {
            "images": len(decoded.images),
            "textures": len(textures),
            "submeshes": len(bindings),
            "dimensions": [[t.width, t.height] for t in decoded.images],
            "referenced_palettes": sorted({p for _, p in decoded.mesh.texture_descriptors}),
        },
        "alpha": {"rgba": "original_ps2", "png": "min(255,2*a)", "loss": "png_alpha_saturation"},
        "orientation": "row_major_no_flip",
        "zlib_version": zlib.ZLIB_RUNTIME_VERSION,
        "pending": ["runtime_gs_material", "textured_mesh_viewer", "physical_textured_mesh"],
        "capabilities": [],
    }


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
            files, report = decode_selected_materials(reader, selection)
        manifest = write_character_material_bundle(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
        )
    except (
        ProfileError,
        SkeletonDecodeError,
        CharacterMeshError,
        CharacterVifError,
        CharacterMaterialError,
        TextureProbeError,
        TextureDecodeError,
        OSError,
    ) as error:
        code = "CT_IO_ERROR" if isinstance(error, OSError) else getattr(error, "code", str(error))
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "decoded_candidate", **manifest["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
