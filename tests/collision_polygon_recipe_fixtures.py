"""Own 285-resource recipe, without private data or production constants/imports."""

import copy
import hashlib
import json

from tests.cld_polygon_fixtures import resource
from tests.cld_polygon_wire_oracle import PolygonOracleError, observe


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(tree):
    return (json.dumps(tree, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def pin(raw):
    return dict(size=len(raw), sha256=sha(raw))


def corpus():
    identity = dict(
        image_id="iso:9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91",
        profile_id="ps2-sles-51434-9a94b95e777dae42",
    )
    source = dict(
        id=identity["image_id"],
        sha256=identity["image_id"][4:],
        profile=dict(id=identity["profile_id"]),
    )
    entries, records, audited, sources = [], [], [], {}
    counts = dict(accepted=0, unsupported=0, rejected=0)
    for i in range(285):
        ident = f"asset:{i:064x}"
        raw = resource((0, 0, 0, 0), group4_count=0 if i < 2 else 1)
        if i == 284:
            raw = b"own truncated CLD"
        try:
            view, code = observe(raw), None
        except PolygonOracleError as error:
            view, code = None, error.code
        kind = "accepted" if code is None else "unsupported" if i != 284 else "rejected"
        counts[kind] += 1
        entry = dict(
            id=ident,
            source_name=("tp1e.cld" if i == 0 else "tp1d.cld" if i == 1 else f"own-{i}.cld"),
            container_id="entry:" + "a" * 64,
            container_offset=i * 4096,
            **pin(raw),
            origin={**identity, "own_extension": [False, -0.0, 7]},
            unrecognized=dict(value="must survive", version=3),
        )
        record = {k: entry[k] for k in ("id", "size", "sha256", "container_id", "container_offset")}
        record["file"] = ident[6:] + ".bin"
        outcome = dict(
            classification=kind,
            decoder_error=code,
            oracle_error=code,
            oracle_match=True,
            view_sha256=None if view is None else sha(wire(view)),
        )
        audited.append(
            dict(
                **{k: v for k, v in entry.items() if k not in ("origin", "unrecognized")},
                source_file=record["file"],
                classification=kind,
                copies=[dict(copy=c, **outcome) for c in ("copy-a", "copy-b")],
                ab_bytes_equal=True,
                ab_errors_equal=True,
                ab_views_equal=True if view is not None else None,
            )
        )
        entries.append(entry)
        records.append(record)
        sources[record["file"]] = raw
    catalog = dict(
        schema_version=1, source=source, selection=dict(schema_version=1), entries=entries
    )
    receipt = dict(
        schema_version=1,
        status="verified",
        source=source,
        selection=catalog["selection"],
        catalog_sha256=sha(wire(catalog)),
        resources=records,
        copies={
            c: [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in records]
            for c in ("copy-a", "copy-b")
        },
    )
    captures = []
    for slot in (2, *range(8, 37)):
        entry = audited[0 if slot == 2 else 1]
        captures.append(
            dict(
                slot=slot,
                phase="control_puzzle"
                if slot == 2
                else "restored_diagnostic"
                if slot == 36
                else "continuous_post_phase",
                state=dict(path="/unavailable/historical/state", **pin(f"state-{slot}".encode())),
                receipt=dict(
                    path="/unavailable/historical/receipt", **pin(f"receipt-{slot}".encode())
                ),
                cycle=slot * 1000,
                pc=0x82000,
                room=0xEA if slot == 2 else 0xEB,
                resource_id=entry["id"],
                resource_pointer=0x185FA00 if slot == 2 else 0x163FA00,
                resource_sha256=entry["sha256"],
                classification="accepted",
                view_sha256=entry["copies"][0]["view_sha256"],
                query_cell=0,
                registration_loader_query_match=True,
                full_resource_bytes_match=True,
                complete_view_matches_source=True,
                oracle_match=True,
            )
        )
    audit = dict(
        schema="sh3-cld-polygons-private-audit-v1",
        status="pass",
        profile="ps2-cld-polygons-v1",
        capabilities=[],
        new_vm_execution=False,
        guest_writes=False,
        input_pins=[
            dict(path="/unused/" + str(i), **pin(wire(d))) for i, d in enumerate((catalog, receipt))
        ],
        resources=audited,
        captures=captures,
        summary=dict(
            classifications=counts,
            resources=285,
            bytes_per_copy=sum(len(raw) for raw in sources.values()),
        ),
    )
    return dict(catalog=catalog, extraction_receipt=receipt, classification_audit=audit), sources


def inputs(root, data, *, copy_name="copy-a"):
    docs, sources = copy.deepcopy(data)
    root.mkdir(parents=True)
    copy_root = root / copy_name
    copy_root.mkdir()
    for name, raw in sources.items():
        (copy_root / name).write_bytes(raw)
    config, anchors = dict(copy_root=str(copy_root)), {}
    for key, doc in docs.items():
        path = root / (key + ".json")
        raw = wire(doc)
        path.write_bytes(raw)
        anchors[key] = pin(raw)
        config[key] = dict(path=str(path), **pin(raw))
    (root / "inputs.json").write_bytes(wire(config))
    return config, anchors
