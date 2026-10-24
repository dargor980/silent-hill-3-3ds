"""CPI02–CPI09/12/14: pure, lossless CLD packages, without host or RAM access."""

import json
import re

from tools.pipeline.decoders.ps2_cld_polygons import CollisionPolygonError, decode_polygons
from tools.pipeline.intermediate_assets import fields, sha, verify_file
from tools.pipeline.intermediate_json import decode_json, encode_json

PROFILE = "ps2-cld-polygons-intermediate-v1"
CONVERTER = "cld-polygons-lossless-v1"
DECODER = "ps2-cld-polygons-v1"
_JSON_LIMIT = 1024 * 1024
_MANIFEST_LIMIT = 256 * 1024
_TOTAL_LIMIT = 40 * 1024 * 1024
_UNSUPPORTED = ("CP_NONPOLYGON_UNSUPPORTED", "CP_VARIANT_UNSUPPORTED")
_CP_CODES = (
    "CP_SIZE",
    "CP_ORIGIN",
    "CP_GROUP_SIZE",
    "CP_GROUP_ALIGNMENT",
    "CP_GROUP_RANGE",
    "CP_GROUP_LAYOUT",
    "CP_POLYGON_BUDGET",
    *_UNSUPPORTED,
    "CP_TERMINATOR",
    "CP_RECORD_PRESENT",
    "CP_COORDINATE",
    "CP_LIST_OFFSET",
    "CP_LIST_TERMINATOR",
    "CP_INDEX",
    "CP_REFERENCE_BUDGET",
)


class CollisionPolygonIntermediateError(ValueError):
    """Stable code only: no payloads, paths or partial package."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _require(condition, code="CPI_SCHEMA"):
    if not condition:
        raise CollisionPolygonIntermediateError(code)


def _fields(value, names):
    try:
        fields(value, names)
    except ValueError:
        raise CollisionPolygonIntermediateError("CPI_SCHEMA") from None


def _integer(value, minimum, maximum):
    _require(type(value) is int and minimum <= value <= maximum)


def _pattern(value, pattern):
    _require(type(value) is str and re.fullmatch(pattern, value) is not None)


def _conventions():
    return dict(
        byte_order="little",
        coordinates="source_untransformed",
        raw_authority="complete_source_buffer",
        view="complete_cp_v1",
        nonaccepted="raw_and_error_only",
        scene_links="historical_reference_only",
        state="structural_observation",
        capabilities=[],
    )


def _encode(value):
    try:
        return encode_json(value)
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise CollisionPolygonIntermediateError("CPI_JSON") from None


def _load(raw, *, manifest=False):
    try:
        tree = decode_json(raw)
        canonical = (
            (json.dumps(tree, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
            if manifest
            else encode_json(tree)
        )
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise CollisionPolygonIntermediateError("CPI_JSON") from None
    _require(raw == canonical, "CPI_JSON")
    return tree


def _same(actual, expected, code="CPI_SCHEMA"):
    # Canonical comparison distinguishes bool/int/float and the sign of zero.
    _require(_encode(actual) == _encode(expected), code)


def _no_host_paths(tree):
    if type(tree) is dict:
        for key, value in tree.items():
            _no_host_paths(key)
            _no_host_paths(value)
    elif type(tree) is list:
        for value in tree:
            _no_host_paths(value)
    elif type(tree) is str:
        _require(not tree.startswith(("/", "\\", "file:")))
        _require(not (len(tree) > 2 and tree[1] == ":" and tree[2] in "/\\"))


def _pin(entry, limit, *, file=False):
    _fields(entry, ("file", "size", "sha256") if file else ("size", "sha256"))
    _integer(entry["size"], 1, limit)
    _pattern(entry["sha256"], "[0-9a-f]{64}")
    if file:
        _require(type(entry["file"]) is str)


def _mapping(value):
    _require(type(value) is dict, "CPI_INPUT")
    _require(all(type(k) is str and type(v) is bytes for k, v in value.items()), "CPI_INPUT")


def _budget(files):
    _require(sum(len(raw) for raw in files.values()) <= _TOTAL_LIMIT, "CPI_BUDGET")
    for name, raw in files.items():
        limit = 65536 if name.startswith("source-") else _JSON_LIMIT
        _require(0 < len(raw) <= limit, "CPI_BUDGET")


def _provenance_schema(provenance):
    _fields(provenance, ("source_identity", "anchors", "scene_evidence"))
    identity = provenance["source_identity"]
    _fields(identity, ("kind", "profile_id", "image_id", "crc"))
    if identity["kind"] == "synthetic":
        _require(identity["profile_id"] == "synthetic-cld-v1" and identity["crc"] is None)
        _pattern(identity["image_id"], "synthetic:[0-9a-f]{64}")
    else:
        _same(
            identity,
            dict(
                kind="private_eu",
                profile_id="ps2-sles-51434-9a94b95e777dae42",
                image_id="iso:9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91",
                crc=0x5088CCDB,
            ),
        )
    _require(provenance["scene_evidence"] == "historical_report_only")
    _fields(provenance["anchors"], ("catalog", "extraction_receipt", "classification_audit"))
    for key, entry in provenance["anchors"].items():
        _pin(entry, (32 if key == "catalog" else 8) * 1024 * 1024)


def _catalog_schema(entry):
    _require(
        type(entry) is dict
        and {"id", "source_name", "container_id", "container_offset", "size", "sha256", "origin"}
        <= entry.keys()
    )
    _pattern(entry["id"], "asset:[0-9a-f]{64}")
    _pattern(entry["container_id"], "entry:[0-9a-f]{64}")
    _pattern(entry["sha256"], "[0-9a-f]{64}")
    _integer(entry["size"], 1, 65536)
    _integer(entry["container_offset"], 0, (1 << 64) - 1)
    _require(type(entry["source_name"]) is str and 1 <= len(entry["source_name"]) <= 256)
    origin = entry["origin"]
    _require(type(origin) is dict and {"profile_id", "image_id"} <= origin.keys())
    _require(all(type(origin[k]) is str for k in ("profile_id", "image_id")))


def _links_schema(row, kind, seen):
    links = row["scene_links"]
    _require(type(links) is list and len(links) <= 30)
    _require(not links or (kind == "private_eu" and row["result"]["classification"] == "accepted"))
    previous = 0
    for link in links:
        _fields(
            link,
            (
                "slot",
                "phase",
                "state",
                "receipt",
                "stage",
                "room",
                "resource_pointer",
                "query_cell",
                "pc",
                "cycle",
            ),
        )
        _integer(link["slot"], 1, 99)
        _require(link["slot"] > previous and link["slot"] not in seen)
        previous = link["slot"]
        seen.add(previous)
        _require(len(seen) <= 30)
        _require(
            link["phase"] in ("control_puzzle", "continuous_post_phase", "restored_diagnostic")
        )
        _pin(link["state"], 64 * 1024 * 1024)
        _pin(link["receipt"], 16384)
        for key, maximum in (
            ("stage", 255),
            ("room", 0xFFFFFFFF),
            ("pc", 0xFFFFFFFF),
            ("cycle", (1 << 64) - 1),
            ("query_cell", 15),
        ):
            _integer(link[key], 0, maximum)
        _integer(link["resource_pointer"], 1, 32 * 1024 * 1024 - row["source"]["size"])


def _root_schema(root):
    _fields(
        root,
        (
            "schema_version",
            "profile",
            "converter",
            "decoder",
            "conventions",
            "provenance",
            "resources",
        ),
    )
    _same(
        {k: root[k] for k in ("schema_version", "profile", "converter", "decoder", "conventions")},
        dict(
            schema_version=1,
            profile=PROFILE,
            converter=CONVERTER,
            decoder=DECODER,
            conventions=_conventions(),
        ),
    )
    _no_host_paths(root)
    _provenance_schema(root["provenance"])
    rows = root["resources"]
    _require(type(rows) is list and 1 <= len(rows) <= 285)
    previous, seen_links = "", set()
    expected = {}
    for row in rows:
        _fields(row, ("id", "catalog_entry", "source", "result", "scene_links"))
        _pattern(row["id"], "asset:[0-9a-f]{64}")
        _require(row["id"] > previous)
        previous = row["id"]
        _catalog_schema(row["catalog_entry"])
        _pin(row["source"], 65536, file=True)
        _require(row["source"]["file"] == f"source-{row['id'][6:]}.bin")
        expected[row["source"]["file"]] = row["source"]
        result = row["result"]
        _fields(result, ("classification", "decoder_code", "view"))
        _require(result["classification"] in ("accepted", "unsupported", "rejected"))
        _require(result["decoder_code"] is None or result["decoder_code"] in _CP_CODES)
        if result["view"] is not None:
            _pin(result["view"], _JSON_LIMIT, file=True)
            _require(result["view"]["file"] == f"polygons-{row['id'][6:]}.json")
            expected[result["view"]["file"]] = result["view"]
        _links_schema(row, root["provenance"]["source_identity"]["kind"], seen_links)
    return expected


def _manifest_schema(manifest):
    constants = dict(
        schema_version=1,
        scope="private_cld_polygons_intermediate",
        profile=PROFILE,
        converter=CONVERTER,
        state="structural_observation",
        capabilities=[],
        new_vm_execution=False,
        collision_response_verified=False,
        scene_link_rechecked=False,
        original_container_rebuild=False,
    )
    _fields(manifest, (*constants, "counts", "files"))
    _same({k: manifest[k] for k in constants}, constants)
    _fields(manifest["counts"], ("resources", "accepted", "unsupported", "rejected"))
    for key, value in manifest["counts"].items():
        _integer(value, 1 if key == "resources" else 0, 285)
    _require(type(manifest["files"]) is list and 1 <= len(manifest["files"]) <= 571)
    for entry in manifest["files"]:
        _pin(
            entry,
            65536
            if type(entry) is dict
            and type(entry.get("file")) is str
            and entry["file"].startswith("source-")
            else _JSON_LIMIT,
            file=True,
        )


def _hash(raw, descriptor):
    try:
        verify_file(raw, descriptor)
    except ValueError:
        raise CollisionPolygonIntermediateError("CPI_HASH") from None


def _decode(raw):
    try:
        return decode_polygons(raw), None
    except CollisionPolygonError as error:
        return None, error.code


def _classification(code):
    return "accepted" if code is None else "unsupported" if code in _UNSUPPORTED else "rejected"


def _provenance(root, manifest=None):
    identity = root["provenance"]["source_identity"]
    for row in root["resources"]:
        entry = row["catalog_entry"]
        _same(
            [entry["id"], entry["size"], entry["sha256"]],
            [row["id"], row["source"]["size"], row["source"]["sha256"]],
            "CPI_PROVENANCE",
        )
        _same(
            {k: entry["origin"][k] for k in ("image_id", "profile_id")},
            {k: identity[k] for k in ("image_id", "profile_id")},
            "CPI_PROVENANCE",
        )
    if manifest is not None:
        counts = {
            kind: sum(r["result"]["classification"] == kind for r in root["resources"])
            for kind in ("accepted", "unsupported", "rejected")
        }
        _same(
            manifest["counts"], dict(resources=len(root["resources"]), **counts), "CPI_PROVENANCE"
        )


def _export(raw, attachments, manifest_raw=None):
    _budget(attachments)
    _require(0 < len(raw) <= _JSON_LIMIT, "CPI_BUDGET")
    _require(len(raw) + sum(map(len, attachments.values())) <= _TOTAL_LIMIT, "CPI_BUDGET")
    files = {**attachments, "intermediate.json": raw}
    if manifest_raw is not None:
        _require(0 < len(manifest_raw) <= _MANIFEST_LIMIT, "CPI_BUDGET")
    root = _load(raw)
    manifest = _load(manifest_raw, manifest=True) if manifest_raw is not None else None
    # Finish JSON checks globally without retaining all decoded view trees.
    for name in sorted(attachments):
        if name.startswith("polygons-") and name.endswith(".json"):
            _load(attachments[name])
    expected = _root_schema(root)
    if manifest is not None:
        _manifest_schema(manifest)
    _require(set(attachments) == set(expected), "CPI_INVENTORY")
    listed = {}
    if manifest is not None:
        _require([e["file"] for e in manifest["files"]] == sorted(files), "CPI_INVENTORY")
        listed = {entry["file"]: entry for entry in manifest["files"]}
        _hash(raw, listed["intermediate.json"])
    for name in sorted(expected):
        _hash(attachments[name], expected[name])
        if listed:
            _hash(attachments[name], listed[name])
    # Two bounded passes enforce classification-before-view precedence across resources.
    for row in root["resources"]:
        view, code = _decode(attachments[row["source"]["file"]])
        result = row["result"]
        _require(
            (result["classification"], result["decoder_code"]) == (_classification(code), code)
            and (result["view"] is not None) == (view is not None),
            "CPI_CLASSIFICATION",
        )
        del view
    rebuilt = {"intermediate.json": raw}
    for row in root["resources"]:
        name = row["source"]["file"]
        rebuilt[name] = attachments[name]
        if row["result"]["view"] is not None:
            view, _ = _decode(attachments[name])
            encoded = _encode(view)
            view_name = row["result"]["view"]["file"]
            _require(encoded == attachments[view_name], "CPI_VIEW")
            rebuilt[view_name] = encoded
            del view
    _provenance(root, manifest)
    return rebuilt


def export_collision_polygons(intermediate_bytes, attachments):
    """Reconstruct all logical files from immutable buffers; never consult sources."""
    _require(type(intermediate_bytes) is bytes, "CPI_INPUT")
    _mapping(attachments)
    return _export(intermediate_bytes, attachments)


def verify_collision_polygon_bundle(manifest_bytes, files):
    """Verify the transport manifest and rebuild logical files, without the manifest."""
    _require(type(manifest_bytes) is bytes, "CPI_INPUT")
    _mapping(files)
    _budget(files)
    _require(0 < len(manifest_bytes) <= _MANIFEST_LIMIT, "CPI_BUDGET")
    _require("intermediate.json" in files, "CPI_INVENTORY")
    return _export(
        files["intermediate.json"],
        {k: v for k, v in files.items() if k != "intermediate.json"},
        manifest_bytes,
    )


def make_collision_polygons(provenance, catalog_entries, scene_links, sources):
    """Derive a package from pinned metadata and complete sources already in memory."""
    _require(
        type(provenance) is dict and type(catalog_entries) is list and type(scene_links) is dict,
        "CPI_INPUT",
    )
    _mapping(sources)
    _require(all(type(k) is str and type(v) is list for k, v in scene_links.items()), "CPI_INPUT")
    _require(
        all(0 < len(raw) <= 65536 for raw in sources.values())
        and sum(len(raw) for raw in sources.values()) <= _TOTAL_LIMIT,
        "CPI_BUDGET",
    )
    # Clone only bounded metadata, preserving unknown fields and exact JSON types.
    metadata = decode_json(
        _encode(dict(provenance=provenance, entries=catalog_entries, links=scene_links))
    )
    catalog_entries, scene_links = metadata["entries"], metadata["links"]
    _require(1 <= len(catalog_entries) <= 285)
    for entry in catalog_entries:
        _catalog_schema(entry)
    ids = [entry["id"] for entry in catalog_entries]
    _require(ids == sorted(set(ids)))
    _require(set(sources) == set(scene_links) == set(ids), "CPI_INVENTORY")
    rows, blobs = [], {}
    for entry in catalog_entries:
        ident = entry["id"]
        name, raw = f"source-{ident[6:]}.bin", sources[ident]
        blobs[name] = raw
        rows.append(
            dict(
                id=ident,
                catalog_entry=entry,
                source=dict(file=name, size=len(raw), sha256=sha(raw)),
                result=dict(classification="accepted", decoder_code=None, view=None),
                scene_links=scene_links[ident],
            )
        )
    root = dict(
        schema_version=1,
        profile=PROFILE,
        converter=CONVERTER,
        decoder=DECODER,
        conventions=_conventions(),
        provenance=metadata["provenance"],
        resources=rows,
    )
    _root_schema(root)
    # Builder verifies supplied source identities before deriving a single view.
    _provenance(root)
    for row in rows:
        view, code = _decode(sources[row["id"]])
        result = dict(classification=_classification(code), decoder_code=code, view=None)
        if view is not None:
            name, raw = f"polygons-{row['id'][6:]}.json", _encode(view)
            _require(len(raw) <= _JSON_LIMIT, "CPI_BUDGET")
            blobs[name] = raw
            result["view"] = dict(file=name, size=len(raw), sha256=sha(raw))
        row["result"] = result
        del view
        _require(sum(len(raw) for raw in blobs.values()) <= _TOTAL_LIMIT, "CPI_BUDGET")
    return export_collision_polygons(_encode(root), blobs)
