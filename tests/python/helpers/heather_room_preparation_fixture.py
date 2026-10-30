"""Invented room with 34 polygons and a clear route; never reads original resources."""

import copy
import hashlib
import json
import struct
from pathlib import Path

from tests.cld_polygon_fixtures import resource


def wire(data):
    return (json.dumps(data, sort_keys=True, indent=2) + "\n").encode()


def pin(raw):
    return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def cld():
    counts = [1, 4, 26, 3]
    raw = bytearray(resource(counts, lists={(g, 0): list(range(n)) for g, n in enumerate(counts)}))
    struct.pack_into("<2f", raw, 0, 100000, 140000)
    struct.pack_into("<I", raw, 28, 0)
    offsets = struct.unpack_from("<5I", raw, 0x160)
    for group, count in enumerate(counts):
        for index in range(count):
            offset = offsets[group] + index * 80
            raw[offset + 1] = 1
            if (group, index) in ((0, 0), (2, 4)):
                y = 0 if group == 0 else -1600
                points = [
                    (x, y, z, 1)
                    for x, z in [
                        (99000, 139000),
                        (101000, 139000),
                        (101000, 141000),
                        (99000, 141000),
                    ]
                ]
            else:
                # All blockers intentionally remote from the authored route at x=230..320.
                x = 99300 + 2 * group + index
                points = [
                    (x, -100, 139400, 1),
                    (x, 0, 139400, 1),
                    (x, 0, 139600, 1),
                    (x, -100, 139600, 1),
                ]
            struct.pack_into("<16f", raw, offset + 16, *(v for p in points for v in p))
    return bytes(raw)


def configured(folder):
    folder.mkdir(parents=True)
    profile = json.loads(
        (Path(__file__).resolve().parents[3] / "schemas/heather-room-profile-v1.json").read_bytes()
    )
    sources = {
        "map": b"own map placeholder",
        "collision": cld(),
        "external_texture": b"own texture placeholder",
    }
    entries = []
    for index, (role, raw) in enumerate(sources.items()):
        entry = dict(
            id="asset:" + hashlib.sha256(role.encode()).hexdigest(),
            **pin(raw),
            container_id="own-container",
            container_offset=100 * index,
        )
        profile["resources"][role] = {k: entry[k] for k in ("id", "size", "sha256")}
        entries.append(entry)
    catalog = dict(
        schema_version=1,
        source={"id": "own-image"},
        selection={"id": "own-selection"},
        entries=entries,
    )
    records = [dict(e, file=e["id"][6:] + ".bin") for e in entries]
    receipt = dict(
        schema_version=1,
        status="verified",
        source=catalog["source"],
        selection=catalog["selection"],
        catalog_sha256=pin(wire(catalog))["sha256"],
        resources=records,
        copies={
            c: [{k: r[k] for k in ("id", "size", "sha256", "file")} for r in records]
            for c in ("copy-a", "copy-b")
        },
    )
    profile["catalog_sha256"] = pin(wire(catalog))["sha256"]
    profile["extraction_receipt_sha256"] = pin(wire(receipt))["sha256"]
    paths = {k: folder / (k + ".json") for k in ("profile", "catalog", "receipt")}
    paths["copies"] = folder / "copies"
    for key, data in (("profile", profile), ("catalog", catalog), ("receipt", receipt)):
        paths[key].write_bytes(wire(data))
    for name in ("copy-a", "copy-b"):
        root = paths["copies"] / name
        root.mkdir(parents=True)
        for raw, record in zip(sources.values(), records, strict=True):
            (root / record["file"]).write_bytes(raw)
    return paths, copy.deepcopy(profile), pin(wire(profile))
