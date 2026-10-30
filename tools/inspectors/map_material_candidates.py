"""HRM01-HRM07: metadata-only hypothesis, never a runtime material binding."""

from tools.inspectors.map_probe import MAX_MAP_BYTES, probe_map
from tools.inspectors.map_render_probe import probe_render_metadata
from tools.inspectors.texture_probe import MAX_TEXTURE_BYTES, probe_texture
from tools.pipeline.decoders.ps2_indexed import decode_indexed, render_indexed
from tools.pipeline.intermediate_assets import sha

MAX_VARIANT_BYTES = 64 * 1024 * 1024
MAX_CANDIDATE_BYTES = 32 * 1024 * 1024


def require(condition, code):
    if not condition:
        raise ValueError(code)


def inspect_candidates(raw_map, raw_external, embedded_offset):
    require(
        type(raw_map) is bytes
        and type(raw_external) is bytes
        and len(raw_map) <= MAX_MAP_BYTES
        and len(raw_external) <= MAX_TEXTURE_BYTES,
        "HRM_INPUT",
    )
    require(
        type(embedded_offset) is int
        and 80 <= embedded_offset <= len(raw_map) - 32
        and embedded_offset % 16 == 0,
        "HRM_SECTION",
    )
    structure = probe_map(len(raw_map), lambda o, n: raw_map[o : o + n])
    require(
        max(g["offset"] + g["size"] for g in structure["groups"]) <= embedded_offset, "HRM_SECTION"
    )
    render = probe_render_metadata(len(raw_map), lambda o, n: raw_map[o : o + n])
    roots = render["counted_roots"]
    require(
        roots[0]["declared_count"] == 0
        and roots[1]["declared_count"] == 1
        and 1 <= roots[2]["declared_count"] <= 7,
        "HRM_ROOTS",
    )
    payloads = {"external": raw_external, "embedded": raw_map[embedded_offset:]}
    catalogs = {
        bank: probe_texture(len(raw), lambda o, n, raw=raw: raw[o : o + n])
        for bank, raw in payloads.items()
    }
    require(
        len(catalogs["external"]["blocks"]) == 1
        and len(catalogs["embedded"]["blocks"]) == roots[2]["declared_count"],
        "HRM_BLOCKS",
    )
    block_by_id = {}
    for bank, catalog in catalogs.items():
        for b in catalog["blocks"]:
            require(b["bpp"] == 8, "HRM_TRANSFER")
            block_by_id[f"{bank}:{b['ordinal']}"] = b
    groups, combinations = [], set()
    by_offset = {g["offset"]: g for g in structure["groups"]}
    for slot, bank in ((1, "external"), (2, "embedded")):
        for ordinal, offset in enumerate(roots[slot]["group_offsets"]):
            g = by_offset[offset]
            require(
                (g["opaque_word_16"], g["opaque_word_20"])
                == ((2, 0) if bank == "external" else (3, ordinal + 1)),
                "HRM_GROUP_INDEX",
            )
            key = f"{bank}:{ordinal}"
            count = block_by_id[key]["clut"]["declared_count"]
            selectors = (0, 1, 4, 5) if count == 4 else tuple(range(count))
            meshes = []
            for mesh in g["children"]:
                selector = mesh["clut_index_unverified"]
                require(selector in selectors, "HRM_SELECTOR")
                combinations.add((key, selector))
                meshes.append(
                    dict(
                        mesh_offset=mesh["offset"],
                        selector_candidate=selector,
                        opaque_halfwords=mesh["opaque_halfwords"],
                        shape_offsets=[
                            s["offset"] for sub in mesh["children"] for s in sub["children"]
                        ],
                    )
                )
            groups.append(
                dict(
                    group_offset=offset,
                    root_slot=slot,
                    group_words=[g["opaque_word_16"], g["opaque_word_20"]],
                    block_candidate=key,
                    meshes=meshes,
                )
            )
    all_bytes = sum(
        b["width"] * b["height"] * 4 * b["clut"]["declared_count"] for b in block_by_id.values()
    )
    selected_bytes = sum(
        block_by_id[key]["width"] * block_by_id[key]["height"] * 4 for key, _ in combinations
    )
    require(all_bytes <= MAX_VARIANT_BYTES and selected_bytes <= MAX_CANDIDATE_BYTES, "HRM_BUDGET")
    blocks, images, exact_images = [], [], []
    for key, b in block_by_id.items():
        bank = key.split(":")[0]
        raw = payloads[bank]
        indices, clut = b["indices"], b["clut"]
        image = decode_indexed(
            b["width"],
            b["height"],
            b["bpp"],
            raw[indices["offset"] : indices["offset"] + indices["size"]],
            raw[clut["data_offset"] : clut["data_offset"] + clut["size"]],
        )
        palettes = []
        for selector, palette in zip(image.selectors, image.palettes, strict=True):
            rgba = render_indexed(image, selector, normalize_alpha=False)
            alpha = rgba[3::4]
            row = dict(
                selector=selector,
                palette_sha256=sha(palette),
                rgba_sha256=sha(rgba),
                rgba_bytes=len(rgba),
                candidate_used=(key, selector) in combinations,
                alpha=dict(
                    min=min(alpha),
                    max=max(alpha),
                    zero_pixels=alpha.count(0),
                    full_ps2_pixels=alpha.count(128),
                    above_ps2_pixels=sum(a > 128 for a in alpha),
                ),
            )
            if row["candidate_used"]:
                candidate = (image.width, image.height, rgba)
                # Hashes describe the report; exact bytes and dimensions decide deduplication.
                if candidate not in exact_images:
                    exact_images.append(candidate)
                    images.append(
                        dict(
                            width=image.width,
                            height=image.height,
                            rgba_sha256=row["rgba_sha256"],
                            rgba_bytes=len(rgba),
                            uses=[],
                        )
                    )
                index = exact_images.index(candidate)
                row["candidate_image"] = index
                images[index]["uses"].append(dict(block=key, selector=selector))
            palettes.append(row)
        blocks.append(
            dict(
                key=key,
                source=bank,
                header_offset=b["header_offset"],
                source_header_offset=b["header_offset"]
                + (embedded_offset if bank == "embedded" else 0),
                header_sha256=b["header_sha256"],
                texture_id_uninterpreted=b["texture_id"],
                width=image.width,
                height=image.height,
                bpp=image.bpp,
                clut=clut,
                indices_sha256=sha(image.indices),
                selectors=list(image.selectors),
                palettes=palettes,
            )
        )
    return dict(
        schema_version=1,
        method="hp34-material-candidates-v1",
        hypothesis="external_slot1_block0_embedded_slot2_word20_minus_one",
        material_binding="unverified",
        runtime_comparison="pending",
        capabilities=[],
        source_map_sha256=sha(raw_map),
        source_external_sha256=sha(raw_external),
        embedded_offset=embedded_offset,
        groups=groups,
        blocks=blocks,
        images=images,
        summary=dict(
            groups=len(groups),
            meshes=structure["summary"]["mesh_count"],
            shapes=structure["summary"]["shape_count"],
            candidate_combinations=len(combinations),
        ),
        budget=dict(
            all_variants_rgba_bytes=all_bytes,
            candidate_rgba_bytes=selected_bytes,
            unique_candidate_rgba_bytes=sum(i["rgba_bytes"] for i in images),
            unique_candidate_images=len(images),
            max_staging_bytes=max(i["rgba_bytes"] for i in images),
        ),
    )
