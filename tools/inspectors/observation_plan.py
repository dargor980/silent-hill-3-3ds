"""Deterministic observation points from revalidated call-boundary evidence."""

import hashlib
import struct

from tools.inspectors.camera_boundary import survey_boundaries
from tools.inspectors.elf32 import exact_read, parse_elf
from tools.inspectors.inventory import entry_id, validate_image_hash
from tools.inspectors.mips_flow import decode
from tools.pipeline.extract_assets import canonical
from tools.pipeline.profile import ProfileError


def object_hash(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def make_plan(boundary: dict, catalog: dict, hashes: dict, read_slot) -> dict:
    if (
        type(catalog.get("schema_version")) is not int
        or catalog["schema_version"] != 1
        or catalog.get("scope") != "selected_mfa_entries"
        or canonical(catalog.get("source")) != canonical(boundary["source"])
        or catalog.get("capabilities") != []
    ):
        raise ProfileError("OBSERVATION_CATALOG", "Catalog source or scope differs")
    ranges, boundaries = {}, []
    for b in boundary["analysis"]["boundaries"]:
        if b["status"] != "analyzed":
            raise ProfileError("OBSERVATION_BOUNDARY", "Unsupported call boundary")
        identity = object_hash([b["site_address"], b["call_pc"], b["register"]])
        local = []
        for window in (b["caller_window"], b["callee_window"]):
            rid = object_hash(window)
            ranges[rid] = {"id": rid, **window}
            local.append(rid)
        watched = b["capture_plan"]["points"][0]["registers"]
        points = []
        for index, phase in enumerate(("before_call", "entry_after_slot", "return_if_reached")):
            pc = b["capture_plan"]["points"][index]["pc"]
            points.append(
                {
                    "id": object_hash([identity, phase, pc]),
                    "phase": phase,
                    "pc": pc,
                    "registers": watched,
                    "range_id": local[1 if index == 1 else 0],
                }
            )
        deferred = []
        for frontier in b["callee"]["boundaries"]:
            pc = frontier["pc"]
            if not b["callee_window"]["start"] <= pc < b["callee_window"]["end"]:
                deferred.append(frontier)
                continue
            points.append(
                {
                    "id": object_hash([identity, "checkpoint", pc, frontier["kind"]]),
                    "phase": "checkpoint",
                    "pc": pc,
                    "registers": watched,
                    "range_id": local[1],
                }
            )
        slot = decode(read_slot(b["call_pc"] + 4), b["call_pc"] + 4)
        relation = None
        if slot.effect.kind == "copy" and slot.effect.destination == b["register"]:
            relation = {"entry_register": b["register"], "before_register": slot.effect.source}
        boundaries.append(
            {
                "id": identity,
                "register": b["register"],
                "points": points,
                "argument_copy": relation,
                "deferred_points": deferred,
            }
        )
    if len(boundaries) > 16 or len(ranges) > 32 or sum(len(b["points"]) for b in boundaries) > 128:
        raise ProfileError("OBSERVATION_BUDGET", "Plan exceeds observation budget")
    return {
        "schema_version": 1,
        "tool": {"name": "sh3-camera-observation-plan", "version": 1},
        "source": boundary["source"],
        "executable": boundary["executable"],
        "evidence": {
            **boundary["evidence"],
            "boundary_sha256": hashes["boundary"],
            "boundary_repeat_sha256": hashes["boundary_repeat"],
        },
        "catalog_sha256": hashes["catalog"],
        "boundaries": boundaries,
        "code_ranges": [ranges[key] for key in sorted(ranges)],
        "status": "not_performed",
        "capabilities": [],
        "f02_07_status": "pending",
    }


def prepare_plan(reader, profile, documents: dict, image_size: int, hashes: dict) -> dict:
    for name in ("boundary", "boundary_repeat", "catalog"):
        validate_image_hash(hashes[name])
    previous = documents["boundary"]
    if hashes["boundary"] != hashes["boundary_repeat"] or canonical(previous) != canonical(
        documents["boundary_repeat"]
    ):
        raise ProfileError("OBSERVATION_EVIDENCE", "Boundary repetitions differ")
    current = survey_boundaries(
        reader,
        profile,
        documents["probe"],
        documents["consumer"],
        documents["pointer"],
        documents["repeat"],
        image_size,
        hashes,
    )
    if canonical(current) != canonical(previous):
        raise ProfileError("OBSERVATION_EVIDENCE", "Boundary evidence differs from source")
    item = next(
        f
        for f in profile.files
        if entry_id(hashes["image"], profile.profile_id, f.path) == current["executable"]["id"]
    )

    def read(offset, size):
        return reader.read_range(item.path, offset, size)

    mapping = parse_elf(read, item.size)

    def read_slot(pc):
        return struct.unpack(
            "<I", exact_read(read, mapping.file_offset(pc, 4, executable=True), 4)
        )[0]

    return make_plan(current, documents["catalog"], hashes, read_slot)
