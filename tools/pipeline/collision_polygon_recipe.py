"""CPI01/07/08: join the fixed EU catalog, extraction and historical CF-T6 audit."""

import json
import re

from tools.pipeline.collision_polygon_inputs import require
from tools.pipeline.intermediate_assets import fields, sha
from tools.pipeline.intermediate_json import decode_json, encode_json

IDENTITY = dict(
    kind="private_eu",
    profile_id="ps2-sles-51434-9a94b95e777dae42",
    image_id="iso:9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91",
    crc=0x5088CCDB,
)
ANCHORS = {
    "catalog": dict(
        size=1838826,
        sha256="39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d",
    ),
    "extraction_receipt": dict(
        size=1848367,
        sha256="74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943",
    ),
    "classification_audit": dict(
        size=1261623,
        sha256="319f9770751c525d93b1593e067d43ad755b7783a2b674316d7131b3c7d44a40",
    ),
}
LIMITS = dict(
    catalog=32 * 1024 * 1024,
    extraction_receipt=8 * 1024 * 1024,
    classification_audit=8 * 1024 * 1024,
)


def pick(value, keys):
    require(type(value) is dict and set(keys) <= value.keys())
    return {k: value[k] for k in keys}


def equal(actual, expected):
    require(encode_json(actual) == encode_json(expected))


def indexed(rows):
    require(type(rows) is list)
    result = {}
    for row in rows:
        ident = pick(row, ("id",))["id"]
        require(
            type(ident) is str
            and re.fullmatch(r"asset:[0-9a-f]{64}", ident) is not None
            and ident not in result
        )
        result[ident] = row
    return result


def select(documents, anchors):
    """Preserve whole catalog rows; historical paths are never copied into packages."""
    catalog, receipt, audit = [documents[k] for k in LIMITS]
    equal(catalog["schema_version"], 1)
    equal(receipt["schema_version"], 1)
    equal(receipt["status"], "verified")
    equal(receipt["source"], catalog["source"])
    equal(receipt["selection"], catalog["selection"])
    equal(receipt["catalog_sha256"], anchors["catalog"]["sha256"])
    equal(catalog["source"]["id"], IDENTITY["image_id"])
    equal(catalog["source"]["sha256"], IDENTITY["image_id"][4:])
    equal(catalog["source"]["profile"]["id"], IDENTITY["profile_id"])
    equal(
        pick(
            audit,
            ("schema", "status", "profile", "capabilities", "new_vm_execution", "guest_writes"),
        ),
        dict(
            schema="sh3-cld-polygons-private-audit-v1",
            status="pass",
            profile="ps2-cld-polygons-v1",
            capabilities=[],
            new_vm_execution=False,
            guest_writes=False,
        ),
    )
    # Historical report paths locate no inputs: only their recorded size/hash is used.
    for key in ("catalog", "extraction_receipt"):
        require(any(pick(pin, ("size", "sha256")) == anchors[key] for pin in audit["input_pins"]))
    entries, records, selected = [
        indexed(rows) for rows in (catalog["entries"], receipt["resources"], audit["resources"])
    ]
    require(
        set(entries) == set(records) and len(selected) == 285 and selected.keys() <= entries.keys()
    )
    equal(list(selected), sorted(selected))
    fields(receipt["copies"], ("copy-a", "copy-b"))
    copies = [indexed(receipt["copies"][key]) for key in ("copy-a", "copy-b")]
    require(all(set(copy) == set(records) for copy in copies))
    keys = ("id", "size", "sha256", "container_id", "container_offset")
    for ident, old in selected.items():
        entry, record = entries[ident], records[ident]
        equal(pick(entry, keys), pick(record, keys))
        equal(pick(entry, (*keys, "source_name")), pick(old, (*keys, "source_name")))
        equal(entry["origin"]["image_id"], IDENTITY["image_id"])
        equal(entry["origin"]["profile_id"], IDENTITY["profile_id"])
        equal(record["file"], ident[6:] + ".bin")
        equal(old["source_file"], record["file"])
        for copy in copies:
            equal(
                pick(copy[ident], ("id", "size", "sha256", "file")),
                pick(record, ("id", "size", "sha256", "file")),
            )
        require(old["ab_bytes_equal"] is True and old["ab_errors_equal"] is True)
        require(type(old["copies"]) is list and len(old["copies"]) == 2)
        equal([c["copy"] for c in old["copies"]], ["copy-a", "copy-b"])
        for copy in old["copies"]:
            require(copy["oracle_match"] is True)
            equal(copy["classification"], old["classification"])
            equal(copy["decoder_error"], copy["oracle_error"])
        equal(
            {k: v for k, v in old["copies"][0].items() if k != "copy"},
            {k: v for k, v in old["copies"][1].items() if k != "copy"},
        )
        require(old["ab_views_equal"] is (True if old["classification"] == "accepted" else None))
    links = historical_links(audit["captures"], selected)
    return [entries[k] for k in selected], {k: records[k] for k in selected}, selected, links


def historical_links(captures, selected):
    require(type(captures) is list)
    equal([c["slot"] for c in captures], [2, *range(8, 37)])
    links = {k: [] for k in selected}
    for capture in captures:
        slot = capture["slot"]
        entry = selected[capture["resource_id"]]
        equal(entry["source_name"], "tp1e.cld" if slot == 2 else "tp1d.cld")
        equal(capture["resource_sha256"], entry["sha256"])
        equal(capture["classification"], "accepted")
        equal(capture["view_sha256"], entry["copies"][0]["view_sha256"])
        require(
            all(
                capture[k] is True
                for k in (
                    "oracle_match",
                    "registration_loader_query_match",
                    "full_resource_bytes_match",
                    "complete_view_matches_source",
                )
            )
        )
        equal(
            capture["phase"],
            "control_puzzle"
            if slot == 2
            else "restored_diagnostic"
            if slot == 36
            else "continuous_post_phase",
        )
        equal(capture["room"], 0xEA if slot == 2 else 0xEB)
        equal(capture["resource_pointer"], 0x185FA00 if slot == 2 else 0x163FA00)
        equal(capture["query_cell"], 0)
        link = pick(
            capture, ("slot", "phase", "room", "resource_pointer", "query_cell", "pc", "cycle")
        )
        link.update(
            stage=0x23,
            state=pick(capture["state"], ("size", "sha256")),
            receipt=pick(capture["receipt"], ("size", "sha256")),
        )
        links[entry["id"]].append(link)
    return links


def verify_outcomes(files, selected, summary):
    root = decode_json(files["intermediate.json"])
    counts = dict(accepted=0, unsupported=0, rejected=0)
    for row in root["resources"]:
        old = selected[row["id"]]["copies"][0]
        result = row["result"]
        equal(result["classification"], old["classification"])
        equal(result["decoder_code"], old["decoder_error"])
        counts[result["classification"]] += 1
        view_sha = None
        if result["view"] is not None:
            view = decode_json(files[result["view"]["file"]])
            # CF-T6 hashes pretty JSON; stored CPI views use compact canonical JSON.
            view_sha = sha(
                (json.dumps(view, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
            )
        equal(view_sha, old["view_sha256"])
    equal(counts, summary["classifications"])
    equal(summary["resources"], len(selected))
    equal(summary["bytes_per_copy"], sum(r["size"] for r in selected.values()))
    return dict(resources=len(selected), **counts)
