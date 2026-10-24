"""CF-T7d: independent package/fidelity oracle, adversarial packages and isolation."""

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests import collision_polygon_package_oracle as oracle
from tests.cld_polygon_fixtures import resource
from tests.collision_polygon_package_fixtures import (
    link,
    original_inputs,
    package,
    pin,
    seal,
    vectors,
    wire,
)
from tests.collision_polygon_recipe_fixtures import corpus, inputs
from tools.pipeline import collision_polygon_intermediate as adapter
from tools.pipeline import collision_polygon_recipe as recipe
from tools.pipeline import prepare_collision_polygon_intermediate as preparer
from tools.pipeline.collision_polygon_output import read_collision_polygon_bundle

FIXED = vectors()
CP_CASES = [
    case
    for case in json.loads(
        Path("tests/fixtures/synthetic/collision-polygons-v1.json").read_bytes()
    )["cases"]
    if 0 < case["input"]["size"] <= 65536
]


def logical(bundle):
    return {k: v for k, v in bundle.items() if k != "manifest.json"}


def production(bundle):
    return adapter.verify_collision_polygon_bundle(bundle["manifest.json"], logical(bundle))


def independent(bundle):
    return oracle.inspect_package(logical(bundle), bundle["manifest.json"])


def result(read, bundle):
    try:
        files = read(bundle)
    except (adapter.CollisionPolygonIntermediateError, oracle.PackageOracleError) as error:
        assert str(error) == error.code
        return error.code
    assert files == logical(bundle)
    return None


def check(bundle, expected):
    before = bundle.copy()
    assert result(independent, bundle) == result(production, bundle) == expected
    assert bundle == before


@pytest.mark.parametrize("name,bundle,code", FIXED, ids=[c[0] for c in FIXED])
def test_immutable_contract_examples_with_independent_oracle(name, bundle, code):
    check(bundle, code)
    if code is None:
        assert oracle.inspect_package(logical(bundle)) == production(bundle)


def malformed_views():
    return [
        (("origin_xz", 0), 0.0),
        (("origin_words", 0), 0),
        (("groups", 0, "records", 0, "point_count"), 4),
        (("groups", 0, "records", 0, "present"), True),
        (("groups", 0, "records", 0, "word_02"), 0),
        (("groups", 0, "records", 0, "word_04"), 3),
        (("groups", 0, "records", 0, "filter_word"), 0),
        (("groups", 0, "records", 0, "word_0c"), 0),
        (("groups", 0, "records", 0, "vector_words", 3, 3), 0),
        (("groups", 0, "records", 0, "vectors_xyzw", 3, 3), 42.0),
        (("groups", 0, "cells", 0, "indices"), [0, 1, 1]),
        (("groups", 0, "cells", 0, "indices"), [1, 0]),
        (("groups", 1, "records"), []),
        (("groups", 0, "stride"), 48),
        (("source_size",), 1),
        (("unknown_extension",), "not CP"),
    ]


def set_path(tree, path, value):
    for key in path[:-1]:
        tree = tree[key]
    tree[path[-1]] = value


def adversarial_packages():
    base = package()
    for index, (path, value) in enumerate(malformed_views()):
        files = base.copy()
        root = json.loads(files["intermediate.json"])
        name = root["resources"][0]["result"]["view"]["file"]
        view = json.loads(files[name])
        set_path(view, path, value)
        files[name] = wire(view)
        yield f"view-{index}", seal(files, root), "CPI_VIEW"
    for field in ("classification", "decoder_code"):
        root = json.loads(base["intermediate.json"])
        root["resources"][0]["result"][field] = (
            "rejected" if field == "classification" else "CP_SIZE"
        )
        yield field, seal(base, root), "CPI_CLASSIFICATION"
    for field, value in (("id", "asset:" + "f" * 64), ("size", 7), ("sha256", "0" * 64)):
        root = json.loads(base["intermediate.json"])
        root["resources"][0]["catalog_entry"][field] = value
        yield "catalog-" + field, seal(base, root), "CPI_PROVENANCE"
    for field in ("profile_id", "image_id"):
        root = json.loads(base["intermediate.json"])
        root["resources"][0]["catalog_entry"]["origin"][field] = "different"
        yield "origin-" + field, seal(base, root), "CPI_PROVENANCE"
    for key in json.loads(base["intermediate.json"]):
        root = json.loads(base["intermediate.json"])
        root.pop(key)
        files = base.copy()
        files["intermediate.json"] = wire(root)
        yield "missing-" + key, files, "CPI_SCHEMA"
    for value in (True, 1.0, 2, "1", None):
        root = json.loads(base["intermediate.json"])
        root["schema_version"] = value
        yield "version-" + repr(value), seal(base, root), "CPI_SCHEMA"
    for field in json.loads(base["intermediate.json"])["conventions"]:
        root = json.loads(base["intermediate.json"])
        root["conventions"][field] = None
        yield "convention-" + field, seal(base, root), "CPI_SCHEMA"
    for field, value in (
        ("container_offset", True),
        ("container_offset", -1),
        ("source_name", ""),
        ("source_name", "x" * 257),
        ("container_id", "entry:" + "A" * 64),
    ):
        root = json.loads(base["intermediate.json"])
        root["resources"][0]["catalog_entry"][field] = value
        yield "entry-" + field + repr(value), seal(base, root), "CPI_SCHEMA"
    for value in ("/own/path", "C:\\own", "\\\\host\\file", "file:own"):
        root = json.loads(base["intermediate.json"])
        root["resources"][0]["catalog_entry"]["extension"] = {value: "own"}
        yield "host-path-" + value, seal(base, root), "CPI_SCHEMA"
    for field in (
        "new_vm_execution",
        "collision_response_verified",
        "scene_link_rechecked",
        "original_container_rebuild",
    ):
        for value in (True, 0):
            files = base.copy()
            manifest = json.loads(files["manifest.json"])
            manifest[field] = value
            files["manifest.json"] = wire(manifest, pretty=True)
            yield "claim-" + field + repr(value), files, "CPI_SCHEMA"
    for target in (
        "intermediate.json",
        next(k for k in base if k.startswith("polygons-")),
        "manifest.json",
    ):
        for i, raw in enumerate(
            (
                b"\xff",
                b'{"a":1,"a":2}',
                b'{"a":NaN}',
                b'{"a":1e999}',
                b'{"a":"\\ud800"}',
                b"[" * 2000 + b"]" * 2000,
            )
        ):
            files = base.copy()
            files[target] = raw
            yield f"json-{target}-{i}", files, "CPI_JSON"
    return


ADVERSARIAL = list(adversarial_packages())


@pytest.mark.parametrize("name,bundle,code", ADVERSARIAL, ids=[c[0] for c in ADVERSARIAL])
def test_coherent_hashes_do_not_hide_semantic_or_grammar_failures(name, bundle, code):
    check(bundle, code)


@pytest.mark.parametrize(
    "field,maximum",
    [
        ("slot", 99),
        ("stage", 255),
        ("room", 2**32 - 1),
        ("pc", 2**32 - 1),
        ("cycle", 2**64 - 1),
        ("query_cell", 15),
    ],
)
@pytest.mark.parametrize("value_kind", ["boolean", "negative", "maximum", "excess"])
def test_scene_link_scalar_boundaries(field, maximum, value_kind):
    files = package(private=True)
    root = json.loads(files["intermediate.json"])
    value = {"boolean": True, "negative": -1, "maximum": maximum, "excess": maximum + 1}[value_kind]
    root["resources"][0]["scene_links"][0][field] = value
    # The shared JSON integer range precedes the schema for a u64 overflow.
    expected = None if value_kind == "maximum" else "CPI_JSON" if value == 2**64 else "CPI_SCHEMA"
    check(seal(files, root), expected)


@pytest.mark.parametrize("count", [0, 1, 30, 31])
def test_scene_link_count_and_duplicate_slots_across_rows(count):
    files = package([resource(), resource()], private=True)
    root = json.loads(files["intermediate.json"])
    root["resources"][0]["scene_links"] = [link(slot) for slot in range(1, count + 1)]
    check(seal(files, root), "CPI_SCHEMA" if count > 30 else None)
    if count:
        root["resources"][1]["scene_links"] = [link(1)]
        check(seal(files, root), "CPI_SCHEMA")


@pytest.mark.parametrize("target,maximum", [("state", 64 * 1024 * 1024), ("receipt", 16384)])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_historical_pin_boundaries(target, maximum, delta):
    files = package(private=True)
    root = json.loads(files["intermediate.json"])
    root["resources"][0]["scene_links"][0][target]["size"] = maximum + delta
    check(seal(files, root), "CPI_SCHEMA" if delta > 0 else None)


@pytest.mark.parametrize("count", [0, 1, 285, 286])
def test_resource_boundaries_and_identical_payloads_with_distinct_ids(count):
    files = package([resource((0, 0, 0, 0))] * count)
    check(files, None if 1 <= count <= 285 else "CPI_SCHEMA")
    if count > 1:
        root = json.loads(files["intermediate.json"])
        root["resources"][1] = copy.deepcopy(root["resources"][0])
        check(seal(files, root), "CPI_SCHEMA")


@pytest.mark.parametrize("size", [0, 1, 751, 752, 65536, 65537])
def test_transport_preserves_rejected_as_well_as_accepted_sources(size):
    # Oversized/empty inputs can be represented for negative transport controls only.
    raw = resource((0, 0, 0, 0), data_start=65168) if size == 65536 else bytes(size)
    files = package([raw])
    check(files, "CPI_BUDGET" if size in (0, 65537) else None)


@pytest.mark.parametrize("case", CP_CASES, ids=lambda c: c["id"])
def test_original_cp_error_vectors_retain_exact_first_code_and_complete_bytes(case):
    raw = bytes.fromhex(case["input"]["wire_hex"])
    files = package([raw])
    check(files, None)
    row = json.loads(files["intermediate.json"])["resources"][0]
    assert row["result"]["decoder_code"] == (
        None if case["expect"] == "accept" else case["expected_code"]
    )
    if case["expect"] == "accept":
        oracle.identical(json.loads(files[row["result"]["view"]["file"]]), case["expected"])
    assert files[row["source"]["file"]] == raw


@pytest.mark.parametrize(
    "value", [None, [], True, {1: b"x"}, {"x": bytearray(b"x")}, {"x": memoryview(b"x")}]
)
def test_exact_inventory_types_match_without_coercion(value):
    for read, error in (
        (oracle.inspect_package, oracle.PackageOracleError),
        (
            lambda files: adapter.verify_collision_polygon_bundle(b"{}", files),
            adapter.CollisionPolygonIntermediateError,
        ),
    ):
        with pytest.raises(error, match="CPI_INPUT"):
            read(value)


@pytest.mark.parametrize(
    "loss", ["padding", "unknown_catalog", "catalog_type", "unknown_origin", "anchor", "scene_link"]
)
def test_self_consistent_loss_is_rejected_only_by_external_fidelity(loss):
    files = package(private=True)
    originals = original_inputs(files)
    root = json.loads(files["intermediate.json"])
    row = root["resources"][0]
    if loss == "padding":
        name = row["source"]["file"]
        raw = files[name]
        files[name] = raw[:400] + bytes([raw[400] ^ 1]) + raw[401:]
        row["catalog_entry"].update(pin(files[name]))
    elif loss == "unknown_catalog":
        del row["catalog_entry"]["unrecognized"]
    elif loss == "catalog_type":
        row["catalog_entry"]["unrecognized"]["typed"][0] = True
    elif loss == "unknown_origin":
        originals[0][0]["origin"]["unknown"] = [1, -0.0]
    elif loss == "anchor":
        root["provenance"]["anchors"]["catalog"]["sha256"] = "f" * 64
    else:
        row["scene_links"][0]["cycle"] += 1
    files = seal(files, root)
    check(files, None)
    with pytest.raises(oracle.PackageOracleError, match="CPI_PROVENANCE"):
        oracle.compare_sources(logical(files), *originals)


@pytest.mark.parametrize("fault", range(len(malformed_views())))
def test_shared_decoder_fault_cannot_fool_the_independent_oracle(monkeypatch, fault):
    files = package()
    entries, sources, provenance, links = original_inputs(files)
    real = adapter.decode_polygons

    def faulty(raw):
        view = real(raw)
        path, value = malformed_views()[fault]
        set_path(view, path, value)
        return view

    monkeypatch.setattr(adapter, "decode_polygons", faulty)
    wrong = adapter.make_collision_polygons(provenance, entries, links, sources)
    # Builder and exporter share the faulty decoder, so their round-trip still passes.
    assert (
        adapter.export_collision_polygons(
            wrong["intermediate.json"], {k: v for k, v in wrong.items() if k != "intermediate.json"}
        )
        == wrong
    )
    with pytest.raises(oracle.PackageOracleError, match="CPI_VIEW"):
        oracle.inspect_package(wrong)


def test_shared_error_mapping_fault_is_detected(monkeypatch):
    files = package([resource(group4_count=1)])
    entries, sources, provenance, links = original_inputs(files)

    def wrong(_):
        raise adapter.CollisionPolygonError("CP_SIZE")

    monkeypatch.setattr(adapter, "decode_polygons", wrong)
    wrong_files = adapter.make_collision_polygons(provenance, entries, links, sources)
    with pytest.raises(oracle.PackageOracleError, match="CPI_CLASSIFICATION"):
        oracle.inspect_package(wrong_files)


def test_shared_serializer_metadata_loss_needs_external_fidelity(monkeypatch):
    files = package()
    entries, sources, provenance, links = original_inputs(files)
    real = adapter.encode_json

    def faulty(value):
        def drop(item):
            if type(item) is dict:
                return {k: drop(v) for k, v in item.items() if k != "unrecognized"}
            if type(item) is list:
                return [drop(v) for v in item]
            return item

        return real(drop(value))

    monkeypatch.setattr(adapter, "encode_json", faulty)
    wrong = adapter.make_collision_polygons(provenance, entries, links, sources)
    assert oracle.inspect_package(wrong) == wrong  # Internally coherent; external loss remains.
    with pytest.raises(oracle.PackageOracleError, match="CPI_PROVENANCE"):
        oracle.compare_sources(wrong, entries, sources, provenance, links)


@pytest.mark.parametrize("kind", ["unsupported", "rejected"])
def test_coherent_omission_of_nonaccepted_resources_fails_source_fidelity(kind):
    files = package([resource(), resource(group4_count=1), b"own truncated CLD"])
    originals = original_inputs(files)
    root = json.loads(files["intermediate.json"])
    row = next(r for r in root["resources"] if r["result"]["classification"] == kind)
    root["resources"].remove(row)
    del files[row["source"]["file"]]
    files = seal(files, root)
    check(files, None)
    with pytest.raises(oracle.PackageOracleError, match="CPI_PROVENANCE"):
        oracle.compare_sources(logical(files), *originals)


@pytest.mark.parametrize("extra", [False, True])
def test_aggregate_transport_boundary_before_inventory(extra):
    files = package()
    remaining = 40 * 1024 * 1024 - sum(map(len, logical(files).values()))
    while remaining:
        amount = min(remaining, 1048576)
        files[f"extra-{len(files)}"] = b"x" * amount
        remaining -= amount
    if extra:
        files["extra-last"] = b"x"
    check(files, "CPI_BUDGET" if extra else "CPI_INVENTORY")


def sized_tree(tree, target):
    parts = []
    tree["padding"] = parts
    while len(wire(tree)) < target:
        remaining = target - len(wire(tree))
        if remaining > 65539:
            parts.append("x" * 65536)
        else:
            parts.append("x" * (remaining - (3 if parts else 2)))
    assert len(wire(tree)) == target
    return wire(tree)


@pytest.mark.parametrize("extra", [False, True])
def test_root_view_and_manifest_physical_limits(extra):
    files = package()
    root = json.loads(files["intermediate.json"])
    entry = root["resources"][0]["catalog_entry"]
    desired = len(wire(entry)) + 1048576 + int(extra) - len(wire(root))
    sized_tree(entry, desired)
    root_files = seal(files, root)
    check(root_files, "CPI_BUDGET" if extra else None)
    name = root["resources"][0]["result"]["view"]["file"]
    view_files = files.copy()
    view_files[name] = sized_tree(json.loads(files[name]), 1048576 + int(extra))
    check(
        seal(view_files, json.loads(files["intermediate.json"])),
        "CPI_BUDGET" if extra else "CPI_VIEW",
    )
    manifest_files = files.copy()
    # Exact physical limit is not itself an error; this noncanonical JSON then fails JSON.
    manifest_files["manifest.json"] = b" " * (262144 + int(extra) - 2) + b"{}"
    check(manifest_files, "CPI_BUDGET" if extra else "CPI_JSON")


def node_count(tree):
    if type(tree) is dict:
        return 1 + sum(1 + node_count(v) for v in tree.values())
    if type(tree) is list:
        return 1 + sum(node_count(v) for v in tree)
    return 1


@pytest.mark.parametrize("boundary", ["nodes", "depth", "key", "string", "integer"])
@pytest.mark.parametrize("extra", [False, True])
def test_json_tree_limits(boundary, extra):
    files = package()
    root = json.loads(files["intermediate.json"])
    entry = root["resources"][0]["catalog_entry"]
    if boundary == "nodes":
        entry["nodes"] = []
        entry["nodes"] = [0] * (500000 + int(extra) - node_count(root))
    elif boundary == "depth":
        tree = 0
        for _ in range(28 + int(extra)):
            tree = [tree]
        entry["nested"] = tree
    elif boundary == "key":
        entry["k" * (256 + int(extra))] = 0
    elif boundary == "string":
        entry["text"] = "x" * (65536 + int(extra))
    else:
        entry["integer"] = 2**64 - 1 + int(extra)
    check(seal(files, root), "CPI_JSON" if extra else None)


def test_stage_precedence_across_resources_and_view_order():
    files = package([resource(), resource(group4_count=1)])
    root = json.loads(files["intermediate.json"])
    first, second = root["resources"]
    view_name = first["result"]["view"]["file"]
    view = json.loads(files[view_name])
    view["source_size"] = 0
    files[view_name] = wire(view)
    first["catalog_entry"]["sha256"] = "0" * 64
    second["result"]["decoder_code"] = "CP_SIZE"
    files = seal(files, root)
    check(files, "CPI_CLASSIFICATION")
    second["result"]["decoder_code"] = "CP_NONPOLYGON_UNSUPPORTED"
    check(seal(files, root), "CPI_VIEW")
    bad_hash = files.copy()
    bad_hash[first["source"]["file"]] = b"x"
    check(bad_hash, "CPI_HASH")
    bad_hash["unexpected"] = b"x"
    check(bad_hash, "CPI_INVENTORY")
    bad_hash[view_name] = b"broken json"
    check(bad_hash, "CPI_JSON")
    bad_hash["unexpected"] = b"x" * 1048577
    check(bad_hash, "CPI_BUDGET")


def test_independent_end_to_end_private_shaped_recipe_and_detached_sources(tmp_path, monkeypatch):
    data = corpus()
    config, anchors = inputs(tmp_path.resolve() / "own", data)
    monkeypatch.setattr(recipe, "ANCHORS", anchors)
    manifest = preparer.prepare_and_write(
        Path(config["copy_root"]).parent / "inputs.json",
        tmp_path.resolve(),
        Path.cwd(),
        "published",
    )
    path = tmp_path.resolve() / "published"
    files = {
        p.name: p.read_bytes()
        for p in path.iterdir()
        if p.name not in ("manifest.json", ".manifest.pending.json")
    }
    raw = (path / "manifest.json").read_bytes()
    assert independent({**files, "manifest.json": raw}) == files
    # Every expected field comes from original inputs, never from the adapter's root.
    docs = data[0]
    expected_links = {r["id"]: [] for r in docs["catalog"]["entries"]}
    for capture in docs["classification_audit"]["captures"]:
        projected = {
            k: capture[k]
            for k in ("slot", "phase", "room", "resource_pointer", "query_cell", "pc", "cycle")
        }
        projected["stage"] = 35
        for name in ("state", "receipt"):
            projected[name] = {k: capture[name][k] for k in ("size", "sha256")}
        expected_links[capture["resource_id"]].append(projected)
    expected = (
        docs["catalog"]["entries"],
        {r["id"]: data[1][r["file"]] for r in docs["extraction_receipt"]["resources"]},
        dict(
            source_identity=dict(
                kind="private_eu",
                crc=0x5088CCDB,
                image_id=docs["catalog"]["source"]["id"],
                profile_id=docs["catalog"]["source"]["profile"]["id"],
            ),
            anchors=anchors,
            scene_evidence="historical_report_only",
        ),
        expected_links,
    )
    oracle.compare_sources(files, *expected)
    assert manifest["counts"] == dict(resources=285, accepted=2, unsupported=282, rejected=1)
    Path(config["copy_root"]).parent.rename(tmp_path / "detached")
    assert read_collision_polygon_bundle(path) == (raw, oracle.inspect_package(files, raw))


def test_oracle_and_builders_do_not_import_production_or_each_other():
    paths = {
        "tests/collision_polygon_package_oracle.py": {
            "hashlib",
            "json",
            "math",
            "re",
            "tests.cld_polygon_wire_oracle",
        },
        "tests/collision_polygon_package_fixtures.py": {
            "copy",
            "hashlib",
            "json",
            "pathlib",
            "tests.cld_polygon_wire_oracle",
            "tests.cld_polygon_fixtures",
        },
    }
    for name, allowed in paths.items():
        tree = ast.parse(Path(name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.module in allowed and node.level == 0


@pytest.mark.parametrize("reader", ["oracle", "production"])
@pytest.mark.parametrize("optimized", [False, True])
def test_normal_and_optimized_corpus_isolated_from_io_and_production_imports(reader, optimized):
    cases = FIXED + ADVERSARIAL
    script = """
import hashlib, json, sys
reader = sys.argv[1]
if reader == 'oracle':
    class Block:
        def find_spec(self,name,*args):
            if name == 'tools' or name.startswith('tools.'):
                raise RuntimeError('production import')
    sys.meta_path.insert(0,Block())
    from tests.collision_polygon_package_oracle import inspect_package, PackageOracleError
    error = PackageOracleError
    read = lambda files, manifest: inspect_package(files,manifest)
else:
    from tools.pipeline.collision_polygon_intermediate import (
        verify_collision_polygon_bundle, CollisionPolygonIntermediateError)
    error = CollisionPolygonIntermediateError
    read = lambda files, manifest: verify_collision_polygon_bundle(manifest,files)
cases = [{k:bytes.fromhex(v) for k,v in bundle.items()} for bundle in json.load(sys.stdin)]
def guard(event,args):
    if event == 'open' or event.startswith(('socket.','subprocess.')) or event == 'os.system':
        raise RuntimeError('forbidden IO')
sys.addaudithook(guard)
try: open('must-not-open')
except RuntimeError: pass
else: raise RuntimeError('guard disabled')
results=[]
for files in cases:
    manifest=files.pop('manifest.json')
    before=dict(files)
    try: rebuilt=read(files,manifest)
    except error as caught:
        if str(caught)!=caught.code: raise RuntimeError('error text')
        results.append(caught.code)
    else:
        if rebuilt != files: raise RuntimeError('changed reconstruction')
        results.append(None)
    if files != before: raise RuntimeError('input mutation')
print(json.dumps(results))
"""
    result = subprocess.run(
        [sys.executable, *(["-O"] if optimized else []), "-c", script, reader],
        input=json.dumps([{k: v.hex() for k, v in b.items()} for _, b, _ in cases]),
        text=True,
        capture_output=True,
        timeout=60,
        check=True,
    )
    assert json.loads(result.stdout) == [c[2] for c in cases]
