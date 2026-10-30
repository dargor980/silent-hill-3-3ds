"""Invented MAP and CSM1 uploads for the material inventory, no game data."""

import copy
import hashlib
import json
import struct

import pytest

from tests.python.test_texture_probe import own_block, own_file
from tools.inspectors import map_material_candidates as module
from tools.inspectors.map_material_candidates import inspect_candidates


def fixture(*, same=False):
    # External group then two internal groups, each with two distinct selectors.
    meshes = [(0,), (0, 1), (0, 14)]
    offsets, cursor = [], 304
    for selectors in meshes:
        offsets.append(cursor)
        cursor += 48 + 208 * len(selectors)
    raw = bytearray(cursor)
    struct.pack_into("<I", raw, 0, 0xFFFFFFFF)
    struct.pack_into("<I", raw, 24, 80)
    struct.pack_into("<3I", raw, 28, 0, offsets[0], offsets[1])
    struct.pack_into("<4H", raw, 64, 3, 0, 2, 1)
    struct.pack_into("<3I", raw, 80, 0, 32, 224)
    struct.pack_into("<16f", raw, 112, *[int(i % 5 == 0) for i in range(16)])
    for i, (start, selectors) in enumerate(zip(offsets, meshes, strict=True)):
        following = offsets[i + 1] if i < 2 else 0
        struct.pack_into(
            "<6IH",
            raw,
            start,
            following,
            48,
            48 + 208 * len(selectors),
            0,
            2 if i == 0 else 3,
            i,
            len(selectors),
        )
        for j, selector in enumerate(selectors):
            mesh = start + 48 + j * 208
            struct.pack_into(
                "<4I4H",
                raw,
                mesh,
                mesh + 208 if j + 1 < len(selectors) else 0,
                48,
                208,
                0,
                selector,
                1,
                0,
                3,
            )
            struct.pack_into("<4I", raw, mesh + 48, 0, 48, 160, 0)
            struct.pack_into("<7I", raw, mesh + 96, 0, 64, 112, 0, 3, 1, 0)

    def block(count, tag):
        b = bytearray(own_block(width=128, height=64, count=count))
        b[80 : 80 + 8192] = bytes(range(256)) * 32
        b[-count * 1024 :] = bytes(
            v for y in range(count * 4) for x in range(64) for v in (x, y, 17 if same else tag, 128)
        )
        return bytes(b)

    external = own_file(block(4, 17))
    raw.extend(own_file(block(4, 23), block(16, 37)))
    return bytes(raw), external, cursor, offsets


def test_complete_inventory_selectors_deduplication_and_no_payload():
    raw, ext, at, offsets = fixture()
    before = (raw, ext)
    v = inspect_candidates(raw, ext, at)
    assert (raw, ext) == before
    assert v["material_binding"] == "unverified" and v["capabilities"] == []
    assert v["runtime_comparison"] == "pending"
    assert v["summary"] == dict(groups=3, meshes=5, shapes=5, candidate_combinations=5)
    assert [g["group_offset"] for g in v["groups"]] == offsets
    assert [m["selector_candidate"] for g in v["groups"] for m in g["meshes"]] == [0, 0, 1, 0, 14]
    assert all(m["opaque_halfwords"] == [1, 0, 3] for g in v["groups"] for m in g["meshes"])
    assert [b["selectors"] for b in v["blocks"]] == [[0, 1, 4, 5], [0, 1, 4, 5], list(range(16))]
    assert v["budget"] == dict(
        all_variants_rgba_bytes=24 * 32768,
        candidate_rgba_bytes=5 * 32768,
        unique_candidate_rgba_bytes=5 * 32768,
        unique_candidate_images=5,
        max_staging_bytes=32768,
    )
    # Literal CSM1 source coordinates for selector 14; no decoder-derived expectation.
    colors = bytes(
        c
        for index in range(256)
        for c in (
            32 + (index % 8) + ((index // 16) % 2) * 8,
            48 + ((index // 8) % 2) + (index // 32) * 2,
            37,
            128,
        )
    )
    palette = next(p for p in v["blocks"][2]["palettes"] if p["selector"] == 14)
    assert palette["palette_sha256"] == hashlib.sha256(colors).hexdigest()
    assert palette["alpha"] == dict(
        min=128, max=128, zero_pixels=0, full_ps2_pixels=8192, above_ps2_pixels=0
    )
    assert "J" * 20 not in json.dumps(v) and "pixels_rgba" not in json.dumps(v)
    assert inspect_candidates(raw, ext, at) == v


def test_exact_dedup_preserves_separate_source_combinations():
    raw, ext, at, _ = fixture(same=True)
    v = inspect_candidates(raw, ext, at)
    assert v["summary"]["candidate_combinations"] == 5
    assert v["budget"]["unique_candidate_images"] == 3
    assert v["budget"]["unique_candidate_rgba_bytes"] == 3 * 32768
    assert len(v["images"][0]["uses"]) == 3


def test_equal_pixels_with_different_dimensions_are_distinct_images():
    raw, _, at, _ = fixture()
    external = own_file(own_block(width=128, height=128))
    internal = own_file(own_block(width=256, height=64), own_block(width=256, height=64, count=16))
    v = inspect_candidates(raw[:at] + internal, external, at)
    assert v["budget"]["unique_candidate_images"] == 2
    assert v["images"][0]["rgba_sha256"] == v["images"][1]["rgba_sha256"]
    assert (v["images"][0]["width"], v["images"][1]["width"]) == (128, 256)
    assert [len(i["uses"]) for i in v["images"]] == [1, 4]


@pytest.mark.parametrize("selector", [4, 5])
def test_four_unit_upload_accepts_actual_cbp_selectors(selector):
    source, ext, at, groups = fixture()
    raw = bytearray(source)
    struct.pack_into("<H", raw, groups[1] + 48 + 16, selector)
    v = inspect_candidates(bytes(raw), ext, at)
    assert v["groups"][1]["meshes"][0]["selector_candidate"] == selector


@pytest.mark.parametrize("alpha", [0, 64, 255])
def test_alpha_statistics_preserve_ps2_values_without_material_inference(alpha):
    raw, source, at, _ = fixture()
    ext = bytearray(source)
    ext[-4096 + 3 :: 4] = bytes([alpha]) * 1024
    v = inspect_candidates(raw, bytes(ext), at)
    p = v["blocks"][0]["palettes"][0]
    assert p["alpha"] == dict(
        min=alpha,
        max=alpha,
        zero_pixels=8192 if alpha == 0 else 0,
        full_ps2_pixels=0,
        above_ps2_pixels=8192 if alpha > 128 else 0,
    )
    assert v["material_binding"] == "unverified"


@pytest.mark.parametrize("budget", ["MAX_VARIANT_BYTES", "MAX_CANDIDATE_BYTES"])
def test_budget_rejected_before_decoding(budget, monkeypatch):
    raw, ext, at, _ = fixture()
    monkeypatch.setattr(module, budget, 1)
    monkeypatch.setattr(module, "decode_indexed", lambda *a: pytest.fail("Unexpected decoding"))
    with pytest.raises(ValueError, match="HRM_BUDGET"):
        inspect_candidates(raw, ext, at)


@pytest.mark.parametrize("value", [None, True, -1, 0, 305, 10**9])
def test_invalid_section(value):
    raw, ext, _, _ = fixture()
    with pytest.raises(ValueError, match="HRM_SECTION"):
        inspect_candidates(raw, ext, value)


@pytest.mark.parametrize("target", ["map", "external"])
def test_input_types(target):
    raw, ext, at, _ = fixture()
    with pytest.raises(ValueError, match="HRM_INPUT"):
        inspect_candidates(
            bytearray(raw) if target == "map" else raw,
            bytearray(ext) if target == "external" else ext,
            at,
        )


@pytest.mark.parametrize(
    "kind",
    [
        "section_overlap",
        "roots",
        "type",
        "external_id",
        "gap",
        "duplicate",
        "selector_2",
        "selector_16",
        "bpp",
        "extra_external",
    ],
)
def test_rejects_unproven_variant_without_partial_report(kind):
    original, ext, at, groups = fixture()
    raw = bytearray(original)
    if kind == "section_overlap":
        at = groups[-1]
    elif kind == "roots":
        struct.pack_into("<3I", raw, 28, groups[0], 0, 0)
        struct.pack_into("<4H", raw, 64, 3, 3, 0, 0)
    elif kind == "type":
        struct.pack_into("<I", raw, groups[1] + 16, 7)
    elif kind == "external_id":
        struct.pack_into("<I", raw, groups[0] + 20, 1)
    elif kind == "gap":
        struct.pack_into("<I", raw, groups[2] + 20, 3)
    elif kind == "duplicate":
        struct.pack_into("<I", raw, groups[2] + 20, 1)
    elif kind == "selector_2":
        struct.pack_into("<H", raw, groups[1] + 48 + 16, 2)
    elif kind == "selector_16":
        struct.pack_into("<H", raw, groups[2] + 48 + 16, 16)
    elif kind == "bpp":
        raw = raw[:at] + own_file(own_block(4, 128, 128), own_block(4, 128, 128, count=16))
    elif kind == "extra_external":
        ext = own_file(own_block(width=128, height=64), own_block(width=128, height=64))
    saved = copy.deepcopy(raw)
    with pytest.raises(ValueError):
        inspect_candidates(bytes(raw), ext, at)
    assert raw == saved
