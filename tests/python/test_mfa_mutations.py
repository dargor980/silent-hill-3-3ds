"""H01/H02: reproducible own-sector mutations with explicit rejection oracles."""

import hashlib
import json
import random
import struct

import pytest
from test_asset_catalog import MemoryAssets, collect, fixture_files, selection_data
from test_mfa import Sectors, sector

from tools.inspectors import asset_catalog, asset_selection, mfa
from tools.inspectors.asset_selection import load_selection
from tools.pipeline import extract_assets
from tools.pipeline.profile import ProfileError

SEEDS = (1706, 51434)
LAYOUTS = (("b8", 184, "ALT.MFA"), ("d8", 216, "B0.MFA"))
MUTATIONS = (
    ("count_zero", "MFA_TABLE"),
    ("count_uint32_max", "MFA_TABLE"),
    ("block_uint32_max", "MFA_BLOCK_RANGE"),
    ("name_in_table", "MFA_NAME"),
    ("offset_uint32_max", "MFA_PAYLOAD_RANGE"),
    ("offset_plus_size_wrap32", "MFA_PAYLOAD_RANGE"),
    ("traversal", "MFA_PATH"),
    ("case_collision", "MFA_DUPLICATE_PATH"),
    ("overlap", "MFA_OVERLAP"),
    ("unsupported_name", "MFA_NAME"),
)


def own_chain(seed, toc, mutation, block):
    rng = random.Random(seed)
    lengths = [rng.randint(1, 15) for _ in range(3)]
    headers = []
    for index in range(2):
        names = tuple(f"own/{seed}/{index}/{letter}" for letter in "abc")
        ranges = [(i * 32, length) for i, length in enumerate(lengths)]
        if index == block:
            if mutation == "traversal":
                names = ("../escape", *names[1:])
            if mutation == "case_collision":
                names = (names[0], names[0].upper(), names[2])
            if mutation == "overlap":
                ranges[1] = (lengths[0] - 1, lengths[1])
        header_toc = toc if index == 0 else 8
        raw = bytearray(sector(names, toc=header_toc, ranges=ranges))
        if index == block:
            fields = {
                "count_zero": (0, 0),
                "count_uint32_max": (0, 0xFFFFFFFF),
                "block_uint32_max": (4, 0xFFFFFFFF),
                "name_in_table": (8, header_toc),
                "offset_uint32_max": (12, 0xFFFFFFFF),
            }
            if mutation in fields:
                offset, value = fields[mutation]
                struct.pack_into("<I", raw, header_toc + offset, value)
            if mutation == "offset_plus_size_wrap32":
                struct.pack_into("<I", raw, header_toc + 12, 0xFFFFFFF0)
                struct.pack_into("<I", raw, header_toc + 20, 0x40)
            if mutation == "unsupported_name":
                name_offset = struct.unpack_from("<I", raw, header_toc + 8)[0]
                raw[name_offset] = 0xFF
        headers.append(bytes(raw))
    return headers


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("layout,toc,path", LAYOUTS)
@pytest.mark.parametrize("block", [0, 1])
@pytest.mark.parametrize("mutation,code", MUTATIONS)
def test_seeded_mutations_have_exact_errors_and_no_partial_hashes(
    seed, layout, toc, path, block, mutation, code
):
    headers = own_chain(seed, toc, mutation, block)
    assert headers == own_chain(seed, toc, mutation, block)
    reader = Sectors({i * 4096: data for i, data in enumerate(headers)})
    with pytest.raises(mfa.MfaError) as caught:
        mfa.parse_layout(reader, 8192, layout)
    assert caught.value.code == code
    assert reader.calls == [(i * 4096, 2048) for i in range(block + 1)]
    files = fixture_files()
    files[path] = b"".join(header + bytes(2048) for header in headers)
    assets = MemoryAssets(files)
    report = collect(reader=assets)
    rejected = next(c for c in report["containers"] if c["path"] == path)
    assert rejected["result"]["code"] == code and rejected["result"]["status"] == "unknown"
    assert not any(entry["container_id"] == rejected["id"] for entry in report["entries"])
    assert not any(name == path for name, _, _ in assets.resource_reads)


@pytest.mark.parametrize("layout,toc,path", LAYOUTS)
@pytest.mark.parametrize("budget", ["MAX_BLOCKS", "MAX_ENTRIES"])
def test_parser_budget_boundary_accepts_exactly_then_rejects_next(
    layout, toc, path, budget, monkeypatch
):
    monkeypatch.setattr(mfa, budget, 2)
    two = {0: sector(("own/a",), toc=toc), 4096: sector(("own/b",), toc=8)}
    assert len(mfa.parse_layout(Sectors(two), 8192, layout).entries) == 2
    reader = Sectors({**two, 8192: sector(("own/c",), toc=8)})
    with pytest.raises(mfa.MfaError) as caught:
        mfa.parse_layout(reader, 12288, layout)
    assert caught.value.code == "MFA_LIMIT"
    expected = 2 if budget == "MAX_BLOCKS" else 3
    assert len(reader.calls) == expected


def test_global_catalog_budget_boundary(monkeypatch):
    monkeypatch.setattr(asset_catalog, "MAX_ASSETS", 5)
    assert collect()["summary"]["entry_count"] == 5
    monkeypatch.setattr(asset_catalog, "MAX_ASSETS", 4)
    reader = MemoryAssets(fixture_files())
    with pytest.raises(ProfileError) as caught:
        collect(reader=reader)
    assert caught.value.code == "CATALOG_LIMIT"
    assert not any(path == "B0.MFA" for path, _, _ in reader.resource_reads)


@pytest.mark.parametrize("kind", ["catalog", "selection"])
def test_json_byte_limit_exactly_at_and_one_byte_over(tmp_path, monkeypatch, kind):
    raw = json.dumps(
        selection_data(fixture_files()) if kind == "selection" else {"own": True}
    ).encode()
    path = tmp_path / "own.json"
    path.write_bytes(raw)
    module = asset_selection if kind == "selection" else extract_assets
    constant = "MAX_SELECTION_BYTES" if kind == "selection" else "MAX_CATALOG_BYTES"

    def load():
        return (
            load_selection(path)
            if kind == "selection"
            else extract_assets.load_catalog(path, hashlib.sha256(raw).hexdigest())
        )

    monkeypatch.setattr(module, constant, len(raw))
    assert load() is not None
    monkeypatch.setattr(module, constant, len(raw) - 1)
    with pytest.raises(ProfileError) as caught:
        load()
    assert caught.value.code == ("INVALID_SELECTION" if kind == "selection" else "INVALID_CATALOG")


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("layout,toc,path", LAYOUTS)
def test_unmutated_controls_are_valid_complete_chains(seed, layout, toc, path):
    headers = own_chain(seed, toc, "none", 1)
    reader = Sectors({i * 4096: header for i, header in enumerate(headers)})
    index = mfa.parse_layout(reader, 8192, layout)
    assert len(index.entries) == index.summary["entry_count"] == 6
    assert index.summary["block_count"] == 2
    assert reader.calls == [(0, 2048), (4096, 2048)]
    assert all(e.offset >= 2048 and e.offset + e.size <= 8192 for e in index.entries)
