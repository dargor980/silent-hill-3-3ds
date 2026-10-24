"""CPI oracle from the written contract; no production codec, constants or I/O.

The only non-stdlib dependency is the independent CP wire oracle. Grammar,
transport checks, JSON tree bounds and typed comparisons are separate from
the production adapter. Source fidelity is an explicit second operation.
"""

import hashlib
import json
import math
import re

from tests.cld_polygon_wire_oracle import PolygonOracleError, identical, observe


class PackageOracleError(AssertionError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def demand(value, code="CPI_SCHEMA"):
    if not value:
        raise PackageOracleError(code)


def same(left, right, code="CPI_SCHEMA"):
    try:
        identical(left, right)
    except AssertionError:
        raise PackageOracleError(code) from None


def canonical(value, *, manifest=False):
    options = dict(indent=2) if manifest else dict(separators=(",", ":"))
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, **options) + "\n"
    ).encode()


def fingerprint(raw):
    return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def _json(raw, *, manifest=False):
    def pairs(items):
        result = {}
        for key, value in items:
            demand(key not in result, "CPI_JSON")
            result[key] = value
        return result

    def nonfinite(_):
        raise PackageOracleError("CPI_JSON")

    try:
        tree = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
        pending, nodes, text = [(tree, 0, False)], 0, 0
        while pending:
            item, depth, key = pending.pop()
            nodes += 1
            demand(nodes <= 500000 and depth <= 32, "CPI_JSON")
            kind = type(item)
            if kind is dict:
                for name, value in item.items():
                    pending.extend(((name, depth + 1, True), (value, depth + 1, False)))
            elif kind is list:
                pending.extend((value, depth + 1, False) for value in item)
            elif kind is str:
                demand(len(item) <= (256 if key else 65536), "CPI_JSON")
                text += len(item.encode("utf-8"))
                demand(text <= 8 * 1024 * 1024, "CPI_JSON")
            elif kind is float:
                demand(math.isfinite(item), "CPI_JSON")
            elif kind is int:
                demand(-(2**63) <= item < 2**64, "CPI_JSON")
        demand(canonical(tree, manifest=manifest) == raw, "CPI_JSON")
        return tree
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise PackageOracleError("CPI_JSON") from None


def keys(value, required, *, extensions=False):
    demand(type(value) is dict)
    demand(set(required) <= value.keys() if extensions else set(required) == value.keys())


def number(value, low, high):
    demand(type(value) is int and low <= value <= high)


def pattern(value, expression):
    demand(type(value) is str and re.fullmatch(expression, value) is not None)


def descriptor(value, maximum, *, named=False):
    keys(value, ("size", "sha256", "file") if named else ("size", "sha256"))
    number(value["size"], 1, maximum)
    pattern(value["sha256"], r"[0-9a-f]{64}")
    if named:
        demand(type(value["file"]) is str)


def _host_paths(tree):
    pending = [tree]
    while pending:
        item = pending.pop()
        if type(item) is dict:
            pending.extend(item)
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
        elif type(item) is str:
            demand(not item.startswith(("/", "\\", "file:")))
            demand(not (len(item) > 2 and item[1] == ":" and item[2] in "/\\"))


def _grammar(root):
    keys(
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
    same(
        [root[k] for k in ("schema_version", "profile", "converter", "decoder")],
        [1, "ps2-cld-polygons-intermediate-v1", "cld-polygons-lossless-v1", "ps2-cld-polygons-v1"],
    )
    same(
        root["conventions"],
        dict(
            byte_order="little",
            coordinates="source_untransformed",
            raw_authority="complete_source_buffer",
            view="complete_cp_v1",
            nonaccepted="raw_and_error_only",
            scene_links="historical_reference_only",
            state="structural_observation",
            capabilities=[],
        ),
    )
    _host_paths(root)
    provenance = root["provenance"]
    keys(provenance, ("source_identity", "anchors", "scene_evidence"))
    same(provenance["scene_evidence"], "historical_report_only")
    identity = provenance["source_identity"]
    keys(identity, ("kind", "profile_id", "image_id", "crc"))
    if identity["kind"] == "synthetic":
        same([identity["profile_id"], identity["crc"]], ["synthetic-cld-v1", None])
        pattern(identity["image_id"], r"synthetic:[0-9a-f]{64}")
    else:
        same(
            identity,
            dict(
                kind="private_eu",
                profile_id="ps2-sles-51434-9a94b95e777dae42",
                image_id="iso:9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91",
                crc=0x5088CCDB,
            ),
        )
    keys(provenance["anchors"], ("catalog", "extraction_receipt", "classification_audit"))
    for name, pin in provenance["anchors"].items():
        descriptor(pin, (32 if name == "catalog" else 8) * 1024 * 1024)
    rows = root["resources"]
    demand(type(rows) is list and 1 <= len(rows) <= 285)
    inventory, ids, slots = {}, [], set()
    for row in rows:
        keys(row, ("id", "catalog_entry", "source", "result", "scene_links"))
        pattern(row["id"], r"asset:[0-9a-f]{64}")
        ids.append(row["id"])
        entry = row["catalog_entry"]
        keys(
            entry,
            ("id", "source_name", "container_id", "container_offset", "size", "sha256", "origin"),
            extensions=True,
        )
        pattern(entry["id"], r"asset:[0-9a-f]{64}")
        pattern(entry["container_id"], r"entry:[0-9a-f]{64}")
        pattern(entry["sha256"], r"[0-9a-f]{64}")
        number(entry["size"], 1, 65536)
        number(entry["container_offset"], 0, 2**64 - 1)
        demand(type(entry["source_name"]) is str and 1 <= len(entry["source_name"]) <= 256)
        keys(entry["origin"], ("profile_id", "image_id"), extensions=True)
        demand(all(type(entry["origin"][k]) is str for k in ("profile_id", "image_id")))
        descriptor(row["source"], 65536, named=True)
        same(row["source"]["file"], "source-" + row["id"][6:] + ".bin")
        inventory[row["source"]["file"]] = row["source"]
        result = row["result"]
        keys(result, ("classification", "decoder_code", "view"))
        demand(result["classification"] in ("accepted", "unsupported", "rejected"))
        demand(
            result["decoder_code"]
            in (
                None,
                "CP_SIZE",
                "CP_ORIGIN",
                "CP_GROUP_SIZE",
                "CP_GROUP_ALIGNMENT",
                "CP_GROUP_RANGE",
                "CP_GROUP_LAYOUT",
                "CP_POLYGON_BUDGET",
                "CP_NONPOLYGON_UNSUPPORTED",
                "CP_TERMINATOR",
                "CP_RECORD_PRESENT",
                "CP_VARIANT_UNSUPPORTED",
                "CP_COORDINATE",
                "CP_LIST_OFFSET",
                "CP_LIST_TERMINATOR",
                "CP_INDEX",
                "CP_REFERENCE_BUDGET",
            )
        )
        if result["view"] is not None:
            descriptor(result["view"], 1048576, named=True)
            same(result["view"]["file"], "polygons-" + row["id"][6:] + ".json")
            inventory[result["view"]["file"]] = result["view"]
        links = row["scene_links"]
        demand(type(links) is list and len(links) <= 30)
        demand(
            not links
            or (identity["kind"] == "private_eu" and result["classification"] == "accepted")
        )
        previous = 0
        for link in links:
            keys(
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
            number(link["slot"], 1, 99)
            demand(link["slot"] > previous and link["slot"] not in slots)
            previous = link["slot"]
            slots.add(previous)
            demand(len(slots) <= 30)
            demand(
                link["phase"] in ("control_puzzle", "continuous_post_phase", "restored_diagnostic")
            )
            descriptor(link["state"], 64 * 1024 * 1024)
            descriptor(link["receipt"], 16384)
            for field, maximum in (
                ("stage", 255),
                ("room", 2**32 - 1),
                ("pc", 2**32 - 1),
                ("cycle", 2**64 - 1),
                ("query_cell", 15),
            ):
                number(link[field], 0, maximum)
            number(link["resource_pointer"], 1, 32 * 1024 * 1024 - row["source"]["size"])
    demand(ids == sorted(set(ids)))
    return inventory


def _manifest(tree):
    constants = dict(
        schema_version=1,
        scope="private_cld_polygons_intermediate",
        profile="ps2-cld-polygons-intermediate-v1",
        converter="cld-polygons-lossless-v1",
        state="structural_observation",
        capabilities=[],
        new_vm_execution=False,
        collision_response_verified=False,
        scene_link_rechecked=False,
        original_container_rebuild=False,
    )
    keys(tree, (*constants, "counts", "files"))
    same({k: tree[k] for k in constants}, constants)
    keys(tree["counts"], ("resources", "accepted", "unsupported", "rejected"))
    for name, count in tree["counts"].items():
        number(count, 1 if name == "resources" else 0, 285)
    demand(type(tree["files"]) is list and 1 <= len(tree["files"]) <= 571)
    for pin in tree["files"]:
        keys(pin, ("file", "size", "sha256"))
        demand(type(pin["file"]) is str)
        descriptor(pin, 65536 if pin["file"].startswith("source-") else 1048576, named=True)


def _observation(raw):
    try:
        return observe(raw), None, "accepted"
    except PolygonOracleError as error:
        return (
            None,
            error.code,
            (
                "unsupported"
                if error.code in ("CP_NONPOLYGON_UNSUPPORTED", "CP_VARIANT_UNSUPPORTED")
                else "rejected"
            ),
        )


def inspect_package(files, manifest=None):
    """Rebuild from supplied bytes; optional manifest adds transport verification."""
    demand(type(files) is dict, "CPI_INPUT")
    demand(all(type(k) is str and type(v) is bytes for k, v in files.items()), "CPI_INPUT")
    demand(manifest is None or type(manifest) is bytes, "CPI_INPUT")
    demand(sum(map(len, files.values())) <= 40 * 1024 * 1024, "CPI_BUDGET")
    for name, raw in files.items():
        demand(0 < len(raw) <= (65536 if name.startswith("source-") else 1048576), "CPI_BUDGET")
    if manifest is not None:
        demand(0 < len(manifest) <= 262144, "CPI_BUDGET")
    demand("intermediate.json" in files, "CPI_INVENTORY")
    root = _json(files["intermediate.json"])
    transport = _json(manifest, manifest=True) if manifest is not None else None
    for name in sorted(files):
        if name.startswith("polygons-") and name.endswith(".json"):
            _json(files[name])
    inventory = _grammar(root)
    if transport is not None:
        _manifest(transport)
    demand(set(files) == set(inventory) | {"intermediate.json"}, "CPI_INVENTORY")
    listed = {}
    if transport is not None:
        demand([p["file"] for p in transport["files"]] == sorted(files), "CPI_INVENTORY")
        listed = {p["file"]: p for p in transport["files"]}
        same(
            fingerprint(files["intermediate.json"]),
            {k: listed["intermediate.json"][k] for k in ("size", "sha256")},
            "CPI_HASH",
        )
    for name, pin in sorted(inventory.items()):
        same(fingerprint(files[name]), {k: pin[k] for k in ("size", "sha256")}, "CPI_HASH")
        if listed:
            same(
                fingerprint(files[name]),
                {k: listed[name][k] for k in ("size", "sha256")},
                "CPI_HASH",
            )
    # Classification is a global stage. Never let an earlier view hide a later CP error.
    for row in root["resources"]:
        view, code, kind = _observation(files[row["source"]["file"]])
        same(
            [
                row["result"]["classification"],
                row["result"]["decoder_code"],
                row["result"]["view"] is None,
            ],
            [kind, code, view is None],
            "CPI_CLASSIFICATION",
        )
        del view
    rebuilt = {"intermediate.json": files["intermediate.json"]}
    for row in root["resources"]:
        name = row["source"]["file"]
        rebuilt[name] = files[name]
        if row["result"]["view"] is not None:
            view = observe(files[name])
            target = row["result"]["view"]["file"]
            same(_json(files[target]), view, "CPI_VIEW")
            rebuilt[target] = canonical(view)
            del view
    counts = dict(resources=len(root["resources"]), accepted=0, unsupported=0, rejected=0)
    identity = root["provenance"]["source_identity"]
    for row in root["resources"]:
        entry = row["catalog_entry"]
        same(
            [entry[k] for k in ("id", "size", "sha256")],
            [row["id"], row["source"]["size"], row["source"]["sha256"]],
            "CPI_PROVENANCE",
        )
        same(
            [entry["origin"][k] for k in ("profile_id", "image_id")],
            [identity[k] for k in ("profile_id", "image_id")],
            "CPI_PROVENANCE",
        )
        counts[row["result"]["classification"]] += 1
    if transport is not None:
        same(transport["counts"], counts, "CPI_PROVENANCE")
    return rebuilt


def compare_sources(files, entries, sources, provenance, scene_links):
    """Separate external fidelity check, including opaque bytes and unknown metadata."""
    inspect_package(files)
    root = _json(files["intermediate.json"])
    same(root["provenance"], provenance, "CPI_PROVENANCE")
    same([r["catalog_entry"] for r in root["resources"]], entries, "CPI_PROVENANCE")
    same({r["id"]: r["scene_links"] for r in root["resources"]}, scene_links, "CPI_PROVENANCE")
    same(
        {r["id"]: files[r["source"]["file"]] for r in root["resources"]}, sources, "CPI_PROVENANCE"
    )
