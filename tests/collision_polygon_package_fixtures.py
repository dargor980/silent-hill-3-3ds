"""Own CPI packages/mutations, independent of production, retaining fixed CF-T7a vectors."""

import copy
import hashlib
import json
from pathlib import Path

from tests.cld_polygon_fixtures import resource
from tests.cld_polygon_wire_oracle import PolygonOracleError, observe


def wire(value, *, pretty=False):
    options = dict(indent=2) if pretty else dict(separators=(",", ":"))
    return (json.dumps(value, sort_keys=True, allow_nan=False, **options) + "\n").encode()


def pin(raw):
    return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def vectors():
    path = Path(__file__).parent / "fixtures/synthetic/collision-polygons-intermediate-v1.json"
    data = json.loads(path.read_bytes())
    return [
        (
            case["id"],
            {k: bytes.fromhex(v["wire_hex"]) for k, v in case["files"].items()},
            case["expected_code"],
        )
        for case in data["cases"]
    ]


def seal(bundle, root):
    """Rehash all descriptors without repairing semantic metadata or view trees."""
    bundle = bundle.copy()
    for row in root["resources"]:
        row["source"].update(pin(bundle[row["source"]["file"]]))
        if row["result"]["view"] is not None:
            row["result"]["view"].update(pin(bundle[row["result"]["view"]["file"]]))
    bundle["intermediate.json"] = wire(root)
    manifest = json.loads(bundle["manifest.json"])
    manifest["counts"] = dict(
        resources=len(root["resources"]),
        **{
            kind: sum(r["result"]["classification"] == kind for r in root["resources"])
            for kind in ("accepted", "unsupported", "rejected")
        },
    )
    manifest["files"] = [
        dict(file=k, **pin(v)) for k, v in sorted(bundle.items()) if k != "manifest.json"
    ]
    bundle["manifest.json"] = wire(manifest, pretty=True)
    return bundle


def link(slot=2):
    return dict(
        slot=slot,
        phase="control_puzzle",
        stage=35,
        room=234,
        resource_pointer=1024,
        query_cell=0,
        pc=0,
        cycle=slot,
        state=dict(size=1, sha256="1" * 64),
        receipt=dict(size=1, sha256="2" * 64),
    )


def package(buffers=None, *, private=False):
    base = vectors()[0][1]
    root = json.loads(base["intermediate.json"])
    template = root["resources"][0]
    identity = root["provenance"]["source_identity"]
    if private:
        identity.update(
            kind="private_eu",
            profile_id="ps2-sles-51434-9a94b95e777dae42",
            image_id="iso:9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91",
            crc=0x5088CCDB,
        )
    if buffers is None:
        buffers = [resource((2, 1, 0, 0), lists={(0, 0): [1, 0, 1]}, data_start=512)]
    root["resources"] = []
    files = {"manifest.json": base["manifest.json"]}
    for index, raw in enumerate(buffers):
        row = copy.deepcopy(template)
        ident = f"asset:{index:064x}"
        row["id"] = ident
        row["catalog_entry"].update(
            id=ident,
            **pin(raw),
            source_name=f"own-{index}.cld",
            unrecognized=dict(typed=[1, 1.0, True, -0.0], label="own field"),
            origin={k: identity[k] for k in ("image_id", "profile_id")},
        )
        name = "source-" + ident[6:] + ".bin"
        row["source"] = dict(file=name, **pin(raw))
        files[name] = raw
        try:
            view, code, kind = observe(raw), None, "accepted"
        except PolygonOracleError as error:
            view, code = None, error.code
            kind = (
                "unsupported"
                if code in ("CP_NONPOLYGON_UNSUPPORTED", "CP_VARIANT_UNSUPPORTED")
                else "rejected"
            )
        row["result"] = dict(classification=kind, decoder_code=code, view=None)
        row["scene_links"] = []
        if view is not None:
            target = "polygons-" + ident[6:] + ".json"
            files[target] = wire(view)
            row["result"]["view"] = dict(file=target, **pin(files[target]))
            if private and index == 0:
                row["scene_links"] = [link()]
        root["resources"].append(row)
    return seal(files, root)


def original_inputs(bundle):
    root = json.loads(bundle["intermediate.json"])
    return (
        [r["catalog_entry"] for r in root["resources"]],
        {r["id"]: bundle[r["source"]["file"]] for r in root["resources"]},
        root["provenance"],
        {r["id"]: r["scene_links"] for r in root["resources"]},
    )
