"""Convert a pinned morph MDL to lossless geometry and embedded indexed materials."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tools.pipeline.decode_skeleton_animation import read_pair_payloads
from tools.pipeline.decoders.ps2_indexed import RECIPE, render_indexed
from tools.pipeline.decoders.ps2_morph_materials import decode_morph_materials
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.preview_png import encode_rgba_png
from tools.pipeline.private_texture_output import _write_bundle


def decode_selected(reader, selection):
    payloads, resources, structure = read_pair_payloads(reader, selection)
    decoded = decode_morph_materials(payloads["model"])
    files, textures = {}, []
    for i, image in enumerate(decoded.images):
        files[f"image-{i}.indices"] = image.indices
        for selector, palette in zip(image.selectors, image.palettes, strict=True):
            files[f"image-{i}-selector-{selector}.bin"] = palette
    for i, (source, selector) in enumerate(decoded.geometry.mesh.texture_descriptors):
        image = decoded.images[source]
        files[f"texture-{i}.rgba"] = render_indexed(image, selector, normalize_alpha=False)
        files[f"texture-{i}.png"] = encode_rgba_png(
            image.width, image.height, render_indexed(image, selector, normalize_alpha=True)
        )
        textures.append(
            dict(
                descriptor=i,
                image=source,
                selector=selector,
                width=image.width,
                height=image.height,
                bpp=image.bpp,
            )
        )
    documents = {
        "geometry.json": dict(schema_version=1, **asdict(decoded.geometry)),
        "materials.json": dict(
            schema_version=1,
            recipe=RECIPE,
            sector_offset=decoded.sector_offset,
            image_table=decoded.image_table,
            structure=decoded.structure,
            headers_hex=[h.hex() for h in decoded.headers],
            textures=textures,
            selectors=[i.selectors for i in decoded.images],
        ),
    }
    for name, value in documents.items():
        files[name] = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode()
    mesh = decoded.geometry.mesh
    report = dict(
        schema_version=1,
        scope="ps2_morph_character_candidate",
        status="decoded_candidate",
        selection=selection,
        resources=resources,
        container_structure=structure,
        summary=dict(
            bones=len(mesh.skeleton.parents),
            helpers=len(mesh.helpers),
            submeshes=len(mesh.submeshes),
            vertices=sum(len(p.vertices) for p in mesh.submeshes),
            triangles=sum(len(p.triangles) for p in mesh.submeshes),
            morph_vertices=len(decoded.geometry.base_positions_q4),
            morph_targets=len(decoded.geometry.targets),
            images=len(decoded.images),
            textures=len(textures),
        ),
        orientation="row_major_no_flip",
        alpha=dict(rgba="original_ps2", png="min(255,2*a)"),
        morph_evaluation="not_applied",
        display_groups="all_preserved_selection_requires_runtime_evidence",
        animation="identity_only_use_separate_animation_decoder",
        runtime="requires_separate_audit",
        capabilities=[],
    )
    return files, report


def write_morph_bundle(root, repository, run_id, files, report):
    """Derive the exact output set from the validated public material document."""
    try:
        document = json.loads(files["materials.json"])
        selectors, textures = document["selectors"], document["textures"]
        if not 1 <= len(selectors) <= 16 or not 1 <= len(textures) <= 256:
            raise ValueError("HI_OUTPUT_SET")
        if any(
            not isinstance(s, list)
            or any(type(v) is not int for v in s)
            or s not in ([0, 1, 4, 5], list(range(8)), list(range(16)))
            for s in selectors
        ):
            raise ValueError("HI_OUTPUT_SET")
        expected = {"geometry.json", "materials.json"}
        expected |= {f"image-{i}.indices" for i in range(len(selectors))}
        expected |= {f"image-{i}-selector-{p}.bin" for i, ss in enumerate(selectors) for p in ss}
        expected |= {
            f"texture-{i}.{suffix}" for i in range(len(textures)) for suffix in ("rgba", "png")
        }
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("HI_OUTPUT_SET") from error
    return _write_bundle(root, repository, run_id, files, report, expected)


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
            files, report = decode_selected(reader, selection)
        write_morph_bundle(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
        )
    except (ValueError, OSError) as error:
        print(
            json.dumps(
                dict(
                    status="rejected",
                    code="HI_IO_ERROR"
                    if isinstance(error, OSError)
                    else getattr(error, "code", str(error)),
                )
            )
        )
        return 1
    print(json.dumps(dict(status="decoded_candidate", **report["summary"]), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
