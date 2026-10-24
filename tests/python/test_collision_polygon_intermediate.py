"""CF-T7b: fixed package vectors, bounded reconstruction and pure API behavior."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.cld_polygon_fixtures import resource
from tests.cld_polygon_wire_oracle import identical, observe
from tools.pipeline.collision_polygon_intermediate import (
    CollisionPolygonIntermediateError,
    export_collision_polygons,
    make_collision_polygons,
    verify_collision_polygon_bundle,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures/synthetic/collision-polygons-intermediate-v1.json"
)
VECTORS = json.loads(FIXTURE.read_bytes())
CASES = VECTORS["cases"]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value, manifest=False):
    options = dict(sort_keys=True, allow_nan=False)
    options.update(dict(indent=2) if manifest else dict(separators=(",", ":")))
    return (json.dumps(value, **options) + "\n").encode()


def unpack(case):
    result = {}
    for name, spec in case["files"].items():
        raw = bytes.fromhex(spec["wire_hex"])
        assert (len(raw), sha(raw)) == (spec["size"], spec["sha256"])
        result[name] = raw
    return result


def exported(files):
    return export_collision_polygons(
        files["intermediate.json"],
        {k: v for k, v in files.items() if k not in ("intermediate.json", "manifest.json")},
    )


def verified(files):
    return verify_collision_polygon_bundle(
        files["manifest.json"], {k: v for k, v in files.items() if k != "manifest.json"}
    )


def built(files):
    root = json.loads(files["intermediate.json"])
    return make_collision_polygons(
        root["provenance"],
        [r["catalog_entry"] for r in root["resources"]],
        {r["id"]: r["scene_links"] for r in root["resources"]},
        {r["id"]: files[r["source"]["file"]] for r in root["resources"]},
    )


def rejects(code, function, *args):
    with pytest.raises(CollisionPolygonIntermediateError) as caught:
        function(*args)
    assert caught.value.code == str(caught.value) == code
    assert caught.value.args == (code,)


def test_fixed_vectors_predate_implementation_and_are_unchanged():
    assert (
        sha(FIXTURE.read_bytes())
        == "7101765a39b0b3ccee3930e0f48730af9d6ed8444b3bbd9efdfc131f0ba58446"
    )
    assert len(CASES) == 24


@pytest.mark.parametrize("operation", [exported, verified])
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_fixed_contract_examples(operation, case):
    files = unpack(case)
    before = files.copy()
    if case["expected_code"] is not None:
        rejects(case["expected_code"], operation, files)
    else:
        result = operation(files)
        assert result == {k: v for k, v in files.items() if k != "manifest.json"}
        assert result is not files
        root = json.loads(result["intermediate.json"])
        for row in root["resources"]:
            if row["result"]["view"] is not None:
                identical(
                    json.loads(result[row["result"]["view"]["file"]]),
                    observe(result[row["source"]["file"]]),
                )
    assert files == before


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["expected_code"] is None], ids=lambda c: c["id"]
)
def test_builder_regenerates_exact_package_and_retains_all_classifications(case):
    files = unpack(case)
    assert built(files) == verified(files)
    root = json.loads(files["intermediate.json"])
    sources = {r["id"]: files[r["source"]["file"]] for r in root["resources"]}
    originals = {k: bytes.fromhex(v["wire_hex"]) for k, v in VECTORS["original_sources"].items()}
    assert (sources == originals) == case["original_sources_match"]
    assert (
        wire([r["catalog_entry"] for r in root["resources"]])
        == wire(VECTORS["original_catalog_entries"])
    ) == case["original_catalog_match"]


def own_inputs(count=1, raw=None, *, private=False):
    base = json.loads(unpack(CASES[0])["intermediate.json"])
    provenance = copy.deepcopy(base["provenance"])
    if private:
        provenance["source_identity"] = dict(
            kind="private_eu",
            profile_id="ps2-sles-51434-9a94b95e777dae42",
            image_id="iso:9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91",
            crc=0x5088CCDB,
        )
    raw = resource((0, 0, 0, 0)) if raw is None else raw
    entries, links, sources = [], {}, {}
    for i in range(count):
        ident = f"asset:{i:064x}"
        entry = copy.deepcopy(base["resources"][0]["catalog_entry"])
        entry.update(
            id=ident,
            size=len(raw),
            sha256=sha(raw),
            origin={k: provenance["source_identity"][k] for k in ("profile_id", "image_id")},
        )
        entries.append(entry)
        links[ident] = []
        sources[ident] = raw
    return provenance, entries, links, sources


def scene(slot):
    return dict(
        slot=slot,
        phase="continuous_post_phase",
        state=dict(size=1, sha256="1" * 64),
        receipt=dict(size=1, sha256="2" * 64),
        stage=35,
        room=235,
        resource_pointer=1024,
        query_cell=0,
        pc=0,
        cycle=slot,
    )


def test_copy_ownership_and_no_mutation():
    args = own_inputs(2)
    before = copy.deepcopy(args)
    first, second = make_collision_polygons(*args), make_collision_polygons(*args)
    for actual, expected in zip(args, before, strict=True):
        identical(actual, expected)
    assert first == second and first is not second
    args[1][0]["own_extension"]["values"][0] = False
    first.pop("intermediate.json")
    assert "intermediate.json" in second
    assert (
        json.loads(second["intermediate.json"])["resources"][0]["catalog_entry"]["own_extension"][
            "values"
        ][0]
        is True
    )


@pytest.mark.parametrize("count", [1, 285])
def test_resource_count_boundaries(count):
    args = own_inputs(count)
    files = make_collision_polygons(*args)
    assert len(files) == 1 + 2 * count
    assert exported(files) == files


@pytest.mark.parametrize("count", [0, 286])
def test_resource_count_outside(count):
    rejects("CPI_SCHEMA", make_collision_polygons, *own_inputs(count))


@pytest.mark.parametrize(
    "raw,code",
    [
        (b"x", "CP_SIZE"),
        (resource((0, 0, 0, 0)), None),
        (resource((0, 0, 0, 0), data_start=65168), None),
    ],
)
def test_transport_minimum_and_maximum_preserve_even_rejected_bytes(raw, code):
    args = own_inputs(raw=raw)
    files = make_collision_polygons(*args)
    row = json.loads(files["intermediate.json"])["resources"][0]
    assert row["result"]["decoder_code"] == code
    assert files[row["source"]["file"]] == raw


@pytest.mark.parametrize("raw", [b"", bytes(65537)])
def test_source_transport_bounds(raw):
    rejects("CPI_BUDGET", make_collision_polygons, *own_inputs(raw=raw))


@pytest.mark.parametrize("bad", [None, True, 1, [], "bytes", bytearray(b"{}"), memoryview(b"{}")])
def test_exact_argument_types(bad):
    rejects("CPI_INPUT", export_collision_polygons, bad, {})
    rejects("CPI_INPUT", verify_collision_polygon_bundle, bad, {})
    rejects("CPI_INPUT", make_collision_polygons, bad, [], {}, {})


@pytest.mark.parametrize("bad", [None, [], {1: b"x"}, {"x": bytearray(b"x")}, {"x": None}])
def test_exact_byte_inventory_types(bad):
    rejects("CPI_INPUT", export_collision_polygons, b"{}", bad)
    rejects("CPI_INPUT", verify_collision_polygon_bundle, b"{}", bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "wrong"),
        ("crc", False),
        ("profile_id", None),
        ("image_id", "synthetic:" + "A" * 64),
    ],
)
def test_identity_schema(field, value):
    args = own_inputs()
    args[0]["source_identity"][field] = value
    rejects("CPI_SCHEMA", make_collision_polygons, *args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("container_offset", True),
        ("container_offset", -1),
        ("container_offset", 2**64),
        ("source_name", ""),
        ("source_name", "x" * 257),
        ("size", 1.0),
        ("sha256", "Z" * 64),
        ("container_id", "bad"),
        ("origin", {}),
        ("id", None),
    ],
)
def test_catalog_field_types(field, value):
    args = own_inputs()
    args[1][0][field] = value
    rejects("CPI_JSON" if value == 2**64 else "CPI_SCHEMA", make_collision_polygons, *args)


@pytest.mark.parametrize("value", ["/private/name", "C:\\name", "\\\\server\\name", "file:secret"])
def test_no_host_paths_in_unknown_extensions(value):
    args = own_inputs()
    args[1][0]["extension"] = {value: "safe"}
    rejects("CPI_SCHEMA", make_collision_polygons, *args)


def test_builder_fixes_pins_before_decoder_is_called(monkeypatch):
    import tools.pipeline.collision_polygon_intermediate as module

    args = own_inputs()
    args[1][0]["sha256"] = "0" * 64

    def forbidden(_):
        raise AssertionError("decoder called before provenance")

    monkeypatch.setattr(module, "decode_polygons", forbidden)
    rejects("CPI_PROVENANCE", make_collision_polygons, *args)


@pytest.mark.parametrize("which", ["sources", "links"])
def test_builder_exact_id_inventory(which):
    args = own_inputs()
    args[3 if which == "sources" else 2].clear()
    rejects("CPI_INVENTORY", make_collision_polygons, *args)


def test_private_identity_shaped_synthetic_links_have_no_ram_semantics():
    args = own_inputs(private=True)
    links = args[2][args[1][0]["id"]]
    links.extend(scene(slot) for slot in range(1, 31))
    links[-1].update(
        stage=255,
        room=0xFFFFFFFF,
        pc=0xFFFFFFFF,
        cycle=(1 << 64) - 1,
        query_cell=15,
        resource_pointer=32 * 1024 * 1024 - args[1][0]["size"],
    )
    files = make_collision_polygons(*args)
    assert exported(files) == files
    assert json.loads(files["intermediate.json"])["resources"][0]["scene_links"] == links


@pytest.mark.parametrize(
    "field,value",
    [
        ("slot", True),
        ("slot", 0),
        ("slot", 100),
        ("phase", "new"),
        ("stage", 256),
        ("room", -1),
        ("pc", 2**32),
        ("cycle", -1),
        ("query_cell", 16),
        ("resource_pointer", 0),
        ("resource_pointer", 32 * 1024 * 1024),
        ("receipt", dict(size=16385, sha256="0" * 64)),
        ("state", dict(size=64 * 1024 * 1024 + 1, sha256="0" * 64)),
    ],
)
def test_link_bounds(field, value):
    args = own_inputs(private=True)
    link = scene(2)
    link[field] = value
    args[2][args[1][0]["id"]].append(link)
    rejects("CPI_SCHEMA", make_collision_polygons, *args)


@pytest.mark.parametrize(
    "mode", ["synthetic", "same", "global", "unordered", "over30", "nonaccepted"]
)
def test_link_context_count_and_uniqueness(mode):
    args = own_inputs(2, private=mode != "synthetic", raw=b"x" if mode == "nonaccepted" else None)
    first, second = (args[2][e["id"]] for e in args[1])
    first.append(scene(2))
    if mode == "same":
        first.append(scene(2))
    if mode == "global":
        second.append(scene(2))
    if mode == "unordered":
        first.append(scene(1))
    if mode == "over30":
        first[:] = [scene(s) for s in range(1, 31)]
        second.append(scene(31))
    rejects("CPI_SCHEMA", make_collision_polygons, *args)


def root_padding(root, target):
    chunks = [""]
    root["resources"][0]["catalog_entry"]["padding"] = chunks
    while target - len(wire(root)) > 65536:
        chunks[-1] = "x" * 65536
        chunks.append("")
    chunks[-1] = "x" * (target - len(wire(root)))
    assert len(wire(root)) == target
    return wire(root)


def test_root_byte_boundary_and_aggregate_transport_boundary():
    files = make_collision_polygons(*own_inputs())
    root = json.loads(files["intermediate.json"])
    attachments = {k: v for k, v in files.items() if k != "intermediate.json"}
    boundary = root_padding(root, 1048576)
    assert export_collision_polygons(boundary, attachments)["intermediate.json"] == boundary
    rejects("CPI_BUDGET", export_collision_polygons, root_padding(root, 1048577), attachments)
    large = attachments.copy()
    remaining = 40 * 1024 * 1024 - len(files["intermediate.json"]) - sum(map(len, large.values()))
    while remaining:
        amount = min(1048576, remaining)
        large[f"extra-{len(large)}.bin"] = b"x" * amount
        remaining -= amount
    rejects("CPI_INVENTORY", export_collision_polygons, files["intermediate.json"], large)
    large["extra-last.bin"] = b"x"
    rejects("CPI_BUDGET", export_collision_polygons, files["intermediate.json"], large)


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff",
        b'{"x":NaN}',
        b'{"x":1,"x":1}',
        b" " * 100,
        b'{"x":1e999}',
        b'{"x":"\\ud800"}',
        b"[" * 2000 + b"]" * 2000,
    ],
)
def test_strict_json_errors_are_typed(raw):
    rejects("CPI_JSON", export_collision_polygons, raw, {})


def test_manifest_missing_root_extras_hashes_and_counts():
    files = unpack(CASES[0])
    manifest = json.loads(files.pop("manifest.json"))
    rejects("CPI_INVENTORY", verify_collision_polygon_bundle, wire(manifest, True), {})
    extra = {**files, ".manifest.pending.json": wire(manifest, True)}
    rejects("CPI_INVENTORY", verify_collision_polygon_bundle, wire(manifest, True), extra)
    manifest["files"].reverse()
    rejects("CPI_INVENTORY", verify_collision_polygon_bundle, wire(manifest, True), files)
    manifest["files"].reverse()
    root_entry = next(e for e in manifest["files"] if e["file"] == "intermediate.json")
    root_entry["sha256"] = "0" * 64
    rejects("CPI_HASH", verify_collision_polygon_bundle, wire(manifest, True), files)
    root_entry["sha256"] = sha(files["intermediate.json"])
    manifest["counts"]["accepted"] += 1
    rejects("CPI_PROVENANCE", verify_collision_polygon_bundle, wire(manifest, True), files)
    rejects("CPI_BUDGET", verify_collision_polygon_bundle, b"x" * 262145, files)


def test_error_precedence_across_resources():
    files = unpack(CASES[0])
    files.pop("manifest.json")
    root = json.loads(files["intermediate.json"])
    accepted = next(r for r in root["resources"] if r["result"]["classification"] == "accepted")
    name = accepted["result"]["view"]["file"]
    view = json.loads(files[name])
    view["source_size"] += 1
    files[name] = wire(view)
    accepted["result"]["view"].update(size=len(files[name]), sha256=sha(files[name]))
    bad = next(
        r for r in reversed(root["resources"]) if r["result"]["classification"] == "unsupported"
    )
    assert root["resources"].index(accepted) < root["resources"].index(bad)
    bad["result"]["decoder_code"] = "CP_SIZE"
    files["intermediate.json"] = wire(root)
    rejects("CPI_CLASSIFICATION", exported, files)
    # A hash mismatch outranks both classification and view failures.
    files[accepted["source"]["file"]] = b"x"
    rejects("CPI_HASH", exported, files)


def test_normal_and_optimized_reconstruction_have_no_io():
    script = r"""
import hashlib,json,sys
from pathlib import Path
from tools.pipeline.collision_polygon_intermediate import (
 make_collision_polygons,export_collision_polygons,verify_collision_polygon_bundle,CollisionPolygonIntermediateError)
fixture=json.loads(Path(sys.argv[1]).read_bytes())
cases=[(c,{k:bytes.fromhex(v['wire_hex']) for k,v in c['files'].items()}) for c in fixture['cases']]
def guard(event,args):
 if event=='open' or event.startswith(('socket.','subprocess.')) or event=='os.system':
  raise RuntimeError('I/O forbidden')
sys.addaudithook(guard)
try:open(sys.argv[1],'rb')
except RuntimeError as error:
 if str(error)!='I/O forbidden':raise
else:raise RuntimeError('I/O guard inactive')
out=[]
for case,files in cases:
 logical={k:v for k,v in files.items() if k!='manifest.json'}
 try:
  result=verify_collision_polygon_bundle(files['manifest.json'],logical)
  attached={k:v for k,v in result.items() if k!='intermediate.json'}
  rebuilt=export_collision_polygons(result['intermediate.json'],attached)
  root=json.loads(result['intermediate.json'])
  made=make_collision_polygons(root['provenance'],[r['catalog_entry'] for r in root['resources']],
   {r['id']:r['scene_links'] for r in root['resources']},
   {r['id']:result[r['source']['file']] for r in root['resources']})
  if result!=logical or made!=result or rebuilt!=result:raise RuntimeError('reconstruction differs')
  out.append([case['id'],None,{k:hashlib.sha256(v).hexdigest() for k,v in result.items()}])
 except CollisionPolygonIntermediateError as error:out.append([case['id'],error.code,None])
 if out[-1][1]!=case['expected_code']:raise RuntimeError('wrong outcome')
print(json.dumps(out,sort_keys=True))
"""
    outputs = []
    for flags in ([], ["-O"]):
        completed = subprocess.run(
            [sys.executable, *flags, "-c", script, str(FIXTURE)],
            capture_output=True,
            text=True,
            check=True,
        )
        outputs.append(json.loads(completed.stdout))
    assert outputs[0] == outputs[1] and len(outputs[0]) == 24


@pytest.mark.parametrize(
    "field,limit",
    [
        ("catalog", 32 * 1024 * 1024),
        ("extraction_receipt", 8 * 1024 * 1024),
        ("classification_audit", 8 * 1024 * 1024),
    ],
)
def test_anchor_limits_and_opaque_fields(field, limit):
    args = own_inputs()
    args[0]["anchors"][field]["size"] = limit
    files = make_collision_polygons(*args)
    assert exported(files) == files
    args[0]["anchors"][field]["size"] = limit + 1
    rejects("CPI_SCHEMA", make_collision_polygons, *args)


@pytest.mark.parametrize("value", [None, {}, 1, True, "CP_INPUT", "CP_UNKNOWN"])
def test_malformed_or_unreachable_result_codes(value):
    files = make_collision_polygons(*own_inputs())
    root = json.loads(files["intermediate.json"])
    root["resources"][0]["result"]["decoder_code"] = value
    files["intermediate.json"] = wire(root)
    if value is None:
        assert exported(files) == files
    else:
        rejects("CPI_SCHEMA", exported, files)


def test_view_descriptor_transport_boundaries_and_json_precedence():
    files = make_collision_polygons(*own_inputs())
    root = json.loads(files["intermediate.json"])
    view_name = root["resources"][0]["result"]["view"]["file"]
    # At the physical boundary transport passes; an invalid JSON view fails at CPI_JSON.
    files[view_name] = b"x" * 1048576
    rejects("CPI_JSON", exported, files)
    files[view_name] += b"x"
    rejects("CPI_BUDGET", exported, files)
    files[view_name] = b"[]\n"
    root["resources"][0]["result"]["view"]["size"] = 1048577
    files["intermediate.json"] = wire(root)
    rejects("CPI_SCHEMA", exported, files)
    # Metadata error in root must not hide a JSON error in a later view.
    root["profile"] = "wrong"
    files["intermediate.json"] = wire(root)
    files[view_name] = b"invalid json"
    rejects("CPI_JSON", exported, files)


def test_manifest_boundary_and_bad_keys_before_inventory():
    files = make_collision_polygons(*own_inputs())
    rejects("CPI_JSON", verify_collision_polygon_bundle, b"x" * 262144, files)
    rejects("CPI_BUDGET", verify_collision_polygon_bundle, b"x" * 262145, files)
    originals = unpack(CASES[0])
    manifest = json.loads(originals.pop("manifest.json"))
    manifest["files"][0]["file"] = []
    rejects("CPI_SCHEMA", verify_collision_polygon_bundle, wire(manifest, True), originals)
    manifest["files"][0] = {"unexpected": 1}
    rejects("CPI_SCHEMA", verify_collision_polygon_bundle, wire(manifest, True), originals)


def test_builder_preserves_errors_and_rejects_non_json_metadata():
    args = own_inputs()
    args[1][0]["extension"] = {1, 2}
    rejects("CPI_JSON", make_collision_polygons, *args)
    args = own_inputs()
    args[1][0]["origin"]["image_id"] = "synthetic:" + "0" * 64
    rejects("CPI_PROVENANCE", make_collision_polygons, *args)


def test_source_inventory_types_are_checked_before_coercion():
    class Trap:
        def __bytes__(self):
            raise AssertionError("coercion")

        def __len__(self):
            raise AssertionError("length before type")

    args = own_inputs()
    args[3][args[1][0]["id"]] = Trap()
    rejects("CPI_INPUT", make_collision_polygons, *args)
    rejects("CPI_INPUT", export_collision_polygons, b"{}", {"source": Trap()})
