"""IR21/22/24/27: lossless collision registry package, with no filesystem access."""

from tools.pipeline.collision_evidence import (
    SLOTS,
    equal,
    no_host_paths,
    require,
    validate_capture_links,
)
from tools.pipeline.collision_registry import REGISTRY_RANGES, decode_registry
from tools.pipeline.intermediate_assets import fields, sha, verify_file
from tools.pipeline.intermediate_json import decode_json, encode_json

PROFILE = "ps2-collision-registry-v1"
CONVERTER = "captured-eu-collision-registry-intermediate-v1"
CONVENTIONS = dict(
    endian="little",
    words=["u16", "u32"],
    addresses="ee_provenance_only",
    banks="both_in_original_order",
    physical_coordinates="undefined",
    events="empty_only",
    world_pointees="excluded",
    callbacks="opaque_integers",
)
BLOB_NAMES = frozenset(f"capture-{s:02d}-{name}" for s in SLOTS for name in REGISTRY_RANGES)
OUTPUT_NAMES = BLOB_NAMES | {"intermediate.json", "collision-observations.json"}


def make_collision(documents, provenance, captures, blobs):
    return export_collision(
        encode_json(
            dict(
                schema_version=1,
                profile=PROFILE,
                converter=CONVERTER,
                conventions=CONVENTIONS,
                documents=documents,
                provenance=provenance,
                captures=captures,
            )
        ),
        blobs,
    )


def _export(root, blobs):
    fields(
        root,
        (
            "schema_version",
            "profile",
            "converter",
            "conventions",
            "documents",
            "provenance",
            "captures",
        ),
    )
    equal(
        {k: root[k] for k in ("schema_version", "profile", "converter", "conventions")},
        dict(schema_version=1, profile=PROFILE, converter=CONVERTER, conventions=CONVENTIONS),
    )
    no_host_paths(root)
    fields(blobs, BLOB_NAMES)
    captures = root["captures"]
    require(type(captures) is list and len(captures) == len(SLOTS))
    for slot, capture in zip(SLOTS, captures, strict=True):
        fields(
            capture,
            ("slot", "state", "receipt_source", "receipt", "phase", "ranges", "observations"),
        )
        equal(capture["slot"], slot)
        ranges = capture["ranges"]
        require(type(ranges) is list and len(ranges) == len(REGISTRY_RANGES))
        decoded_ranges = {}
        for entry, (name, (address, size)) in zip(ranges, REGISTRY_RANGES.items(), strict=True):
            fields(entry, ("file", "address", "size", "sha256"))
            filename = f"capture-{slot:02d}-{name}"
            equal(
                {k: entry[k] for k in ("file", "address", "size")},
                dict(file=filename, address=address, size=size),
            )
            decoded_ranges[name] = verify_file(blobs[filename], entry)
        equal(capture["observations"], decode_registry(decoded_ranges))
    validate_capture_links(captures, root["documents"], root["provenance"])
    view = dict(
        schema_version=1,
        profile=PROFILE,
        state="observed_registry",
        capabilities=[],
        captures=[{k: c[k] for k in ("slot", "phase", "state", "observations")} for c in captures],
    )
    return {
        **blobs,
        "intermediate.json": encode_json(root),
        "collision-observations.json": encode_json(view),
    }


def export_collision(raw, blobs):
    """Rebuild only the retained ranges and observations; never follow guest pointers."""
    try:
        return _export(decode_json(raw), blobs)
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("Malformed collision intermediate") from error


def range_entries(slot, ranges):
    """Build metadata for fixed names; the exporter subsequently validates every byte."""
    return [
        dict(
            file=f"capture-{slot:02d}-{name}", address=address, size=size, sha256=sha(ranges[name])
        )
        for name, (address, size) in REGISTRY_RANGES.items()
    ]
