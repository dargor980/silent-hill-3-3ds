"""Synthetic lossless sidecars, source custody and reconstruction without source files."""

import copy
import hashlib
import json
import math

import pytest
import test_animation_inspection as animation_tests
import test_character_inspection as mesh_tests

from tools.pipeline import intermediate_json as codec
from tools.pipeline.character_intermediate import (
    SOURCES,
    export_inspection,
    make_intermediate,
    read_intermediate,
)
from tools.pipeline.prepare_character_intermediate import main, prepare_files


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture():
    skeleton, animation = animation_tests.documents()
    mesh, _ = mesh_tests.fixture()
    skeleton["uninterpreted"] = dict(words=[0, 0xFFFFFFFF], signed_zero=-0.0)
    mesh["skeleton"] = {k: copy.deepcopy(v) for k, v in skeleton.items() if k != "schema_version"}
    animation["frames"][75]["extension"] = [True, 1, 1.0, None, "ñ", -0.0]
    mesh["unknown_groups"] = [dict(flag=0x80000000, opaque="0011abcd")]
    docs = dict(skeleton=skeleton, animation=animation, mesh=mesh)
    provenance = {}
    for name, (scope, recipe) in SOURCES.items():
        files = ("skeleton", "animation") if name == "skeleton" else ("mesh",)
        provenance[name] = dict(
            schema_version=1,
            scope=scope,
            recipe=recipe,
            model_id=0x209,
            resources={
                kind: dict(size=size, sha256=sha(bytes(size)), name_bytes_hex="ff00")
                for kind, size in (("model", 64), ("animation", 3500))
            },
            files=[
                dict(
                    file=n + ".json",
                    size=len(json.dumps(docs[n]).encode()),
                    sha256=sha(json.dumps(docs[n]).encode()),
                )
                for n in files
            ],
            unknown_manifest=dict(flags=[2, 5, 6], status="uninterpreted"),
            capabilities=[],
        )
    return docs, provenance


def test_sidecar_preserves_types_unknowns_order_and_omitted_samples():
    docs, provenance = fixture()
    original = copy.deepcopy((docs, provenance))
    raw = make_intermediate(docs, provenance)
    value = json.loads(raw)
    assert value["documents"] == docs and value["provenance"] == provenance
    last = value["documents"]["animation"]["frames"][75]["extension"]
    assert [type(v) for v in last] == [bool, int, float, type(None), str, float]
    assert math.copysign(1, last[-1]) == -1
    assert len(value["documents"]["animation"]["frames"]) == 76
    assert value["documents"]["mesh"]["submeshes"][0]["vertices"][0]["weights_q12"] == [
        2048,
        1023,
        1023,
    ]
    files = export_inspection(raw)
    assert files == export_inspection(files["intermediate.json"])
    assert len(files["animation.san"]) == 1248
    assert files["character.scm"][-6:] == b"\0\0\1\0\2\0"
    assert (docs, provenance) == original
    assert raw == make_intermediate(dict(reversed(list(docs.items()))), provenance)
    docs["mesh"]["unknown_groups"].clear()
    assert read_intermediate(raw)["documents"]["mesh"]["unknown_groups"]


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"[] x",
        b'{"a":1,"a":2}',
        b'{"a":{"x":0,"x":1}}',
        b"NaN",
        b"Infinity",
        b"-Infinity",
        b"1e999",
        b'"\\ud800"',
        b'"\xff"',
        bytearray(b"{}"),
    ],
)
def test_strict_json_rejections(raw):
    with pytest.raises(ValueError):
        codec.decode_json(raw)


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        -(1 << 63) - 1,
        1 << 64,
        (1, 2),
        {1: "key"},
        {("x",): 1},
        set(),
        {"x" * 257: 0},
        "x" * 65537,
        object(),
    ],
)
def test_value_contract(value):
    with pytest.raises(ValueError):
        codec.encode_json(value)


def test_codec_budgets_and_canonical_bytes(monkeypatch):
    assert codec.encode_json({"z": 1, "a": -0.0}) == b'{"a":-0.0,"z":1}\n'
    assert codec.decode_json(b" [null, true, false, 1, 1.0, -0.0] ") == [
        None,
        True,
        False,
        1,
        1.0,
        -0.0,
    ]
    value = 0
    for _ in range(33):
        value = [value]
    with pytest.raises(ValueError):
        codec.encode_json(value)
    with pytest.raises(ValueError):
        codec.decode_json(b"[" * 1500 + b"0" + b"]" * 1500)
    monkeypatch.setattr(codec, "MAX_NODES", 3)
    with pytest.raises(ValueError):
        codec.encode_json([1, 2, 3])
    monkeypatch.setattr(codec, "MAX_BYTES", 8)
    with pytest.raises(ValueError):
        codec.decode_json(b" " * 9)
    with pytest.raises(ValueError):
        codec.encode_json("12345678")


@pytest.mark.parametrize(
    "change",
    [
        "root",
        "version",
        "bool_version",
        "profile",
        "converter",
        "decoders",
        "conventions",
        "convention_type",
        "doc_set",
        "source_set",
        "recipe",
        "scope",
        "decoder_version",
        "manifest_model",
        "resource_size",
        "resource_hash",
        "resource_hash_type",
        "identity",
        "doc_version",
        "model",
        "mesh_skeleton",
        "missing_field",
        "non_mapping",
        "short_matrix",
        "bad_index",
        "short_samples",
        "bad_weight",
    ],
)
def test_intermediate_rejects_incoherent_profile(change):
    docs, provenance = fixture()
    v = json.loads(make_intermediate(docs, provenance))
    d, p = v["documents"], v["provenance"]
    if change == "root":
        v["extension"] = 1
    elif change == "version":
        v["schema_version"] = 2
    elif change == "bool_version":
        v["schema_version"] = True
    elif change == "profile":
        v["profile"] = "other"
    elif change == "converter":
        v["converter"] = "future"
    elif change == "decoders":
        v["decoders"]["skeleton"] = "future"
    elif change == "conventions":
        v["conventions"]["weights"] = "renormalize"
    elif change == "convention_type":
        v["conventions"]["clip_id"] = 5193.0
    elif change == "doc_set":
        del d["animation"]
    elif change == "source_set":
        del p["mesh"]
    elif change in ("recipe", "scope"):
        p["mesh"][change] = "other"
    elif change == "decoder_version":
        p["mesh"]["schema_version"] = True
    elif change == "manifest_model":
        p["mesh"]["model_id"] = 0x210
    elif change == "resource_size":
        p["mesh"]["resources"]["model"]["size"] = True
    elif change == "resource_hash":
        p["skeleton"]["resources"]["model"]["sha256"] = "x" * 64
    elif change == "resource_hash_type":
        for item in p.values():
            item["resources"]["model"]["sha256"] = 0
    elif change == "identity":
        p["mesh"]["resources"]["model"]["sha256"] = "0" * 64
    elif change == "doc_version":
        d["mesh"]["schema_version"] = True
    elif change == "model":
        d["animation"]["model_id"] = True
    elif change == "mesh_skeleton":
        d["mesh"]["skeleton"]["uninterpreted"]["words"].reverse()
    elif change == "missing_field":
        del d["mesh"]["helpers"]
    elif change == "non_mapping":
        d["mesh"] = None
    elif change == "short_matrix":
        d["mesh"]["helper_matrix_words"][0] = []
    elif change == "bad_index":
        d["mesh"]["submeshes"][0]["triangles"][0][0] = 99
    elif change == "short_samples":
        d["animation"]["frames"].pop()
    else:
        d["mesh"]["submeshes"][0]["vertices"][0]["weights_q12"][0] = 1
    with pytest.raises(ValueError):
        read_intermediate(codec.encode_json(v))


@pytest.fixture
def bundle(tmp_path):
    docs, provenance = fixture()
    args = []
    for name in ("skeleton", "mesh"):
        source = tmp_path / name
        source.mkdir()
        for entry in provenance[name]["files"]:
            document = entry["file"].removesuffix(".json")
            (source / entry["file"]).write_text(json.dumps(docs[document]))
        raw = json.dumps(provenance[name]).encode()
        (source / "manifest.json").write_bytes(raw)
        args.extend((source, sha(raw)))
    return args


def test_private_cli_roundtrip_without_originals(bundle, tmp_path):
    first, report = prepare_files(*bundle)
    assert report["original_animation_samples_preserved"] == 76
    root = tmp_path / "private"
    root.mkdir()
    argv = [
        "--skeleton-source",
        str(bundle[0]),
        "--skeleton-sha256",
        bundle[1],
        "--mesh-source",
        str(bundle[2]),
        "--mesh-sha256",
        bundle[3],
        "--private-root",
        str(root),
        "--run-id",
        "synthetic",
    ]
    assert main(argv) == 0
    dest = root / "synthetic"
    existing = {p.name: p.read_bytes() for p in dest.iterdir()}
    assert main(argv) == 1
    assert existing == {p.name: p.read_bytes() for p in dest.iterdir()}
    for source in (bundle[0], bundle[2]):
        for p in source.iterdir():
            p.unlink()
    reconstructed = export_inspection((dest / "intermediate.json").read_bytes())
    assert reconstructed == first
    assert main(argv) == 1


@pytest.mark.parametrize(
    "change", ["sha", "size", "missing", "duplicate", "file_hash", "symlink", "json_duplicate"]
)
def test_import_custody_failures(bundle, change, tmp_path):
    if change == "sha":
        bundle[1] = "0" * 64
    else:
        source = bundle[2]
        manifest = json.loads((source / "manifest.json").read_text())
        if change == "size":
            manifest["files"][0]["size"] += 1
        elif change == "missing":
            manifest["files"] = []
        elif change == "duplicate":
            manifest["files"] *= 2
        elif change == "file_hash":
            manifest["files"][0]["sha256"] = "0" * 64
        elif change == "symlink":
            (source / "mesh.json").rename(tmp_path / "target.json")
            (source / "mesh.json").symlink_to(tmp_path / "target.json")
        else:
            raw = b'{"schema_version":1,"schema_version":1}'
            (source / "mesh.json").write_bytes(raw)
            manifest["files"][0].update(size=len(raw), sha256=sha(raw))
        raw = json.dumps(manifest).encode()
        (source / "manifest.json").write_bytes(raw)
        bundle[3] = sha(raw)
    with pytest.raises((ValueError, OSError)):
        prepare_files(*bundle)


def test_aggregate_text_limit(monkeypatch):
    monkeypatch.setattr(codec, "MAX_BYTES", 8)
    with pytest.raises(ValueError, match="text budget"):
        codec.encode_json(["12345", "6789"])


def test_invalid_key_unicode_and_cycle():
    with pytest.raises(ValueError):
        codec.encode_json({"\ud800": 1})
    cycle = []
    cycle.append(cycle)
    with pytest.raises(ValueError):
        codec.encode_json(cycle)
