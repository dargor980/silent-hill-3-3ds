"""Prepare a private collision intermediate from pinned historical states and reports."""

import argparse
import json
import struct
from pathlib import Path

from tools.inspectors.observer_state import (
    CPU_BYTES,
    CYCLE_OFFSET,
    MAX_ACQUISITION_INTERNALS,
    MAX_CPU_PREFIX,
)
from tools.inspectors.pcsx2_state import (
    INTERNALS_MEMBER,
    VERSION_MEMBER,
    decode_ee_state,
    read_state_members,
)
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE
from tools.pipeline.collision_evidence import (
    IDENTITY,
    RECEIPT_LIMIT,
    REPORT_LIMIT,
    REPORTS,
    SLOTS,
    STATE_LIMIT,
    equal,
    ordered,
    phase,
    pick,
    pin,
    require,
)
from tools.pipeline.collision_intermediate import (
    BLOB_NAMES,
    CONVERTER,
    PROFILE,
    export_collision,
    make_collision,
    range_entries,
)
from tools.pipeline.collision_registry import REGISTRY_RANGES, decode_registry
from tools.pipeline.inspection_inputs import bounded_read
from tools.pipeline.intermediate_assets import fields, sha, verify_file
from tools.pipeline.intermediate_json import decode_json
from tools.pipeline.private_texture_output import write_collision_intermediate_bundle


def _input_pin(entry, limit):
    fields(entry, ("path", "size", "sha256"))
    require(type(entry["path"]) is str and Path(entry["path"]).is_absolute())
    result = pick(entry, ("size", "sha256"))
    pin(result, limit)
    return result


def _read(entry, limit):
    fingerprint = _input_pin(entry, limit)
    return verify_file(bounded_read(Path(entry["path"]), fingerprint["size"]), fingerprint)


def _state_ranges(raw, receipt):
    version, internals, ram = read_state_members(
        raw,
        (
            (VERSION_MEMBER, 36),
            (INTERNALS_MEMBER, MAX_ACQUISITION_INTERNALS),
            (RAM_MEMBER, RAM_SIZE),
        ),
    )
    cpu = decode_ee_state(version, internals[:MAX_CPU_PREFIX], IDENTITY["crc"])
    start = 333 + struct.unpack_from("<I", internals, 296)[0]
    require(len(internals) >= start + CPU_BYTES and len(ram) == RAM_SIZE)
    cycle = struct.unpack_from("<Q", internals, start + CYCLE_OFFSET)[0]
    equal(
        pick(receipt, ("pc", "delay", "cycle", "gpr")),
        dict(pc=cpu.pc, delay=cpu.delay_slot, cycle=cycle, gpr=list(cpu.gpr_low32)),
    )
    return {
        name: ram[address : address + size] for name, (address, size) in REGISTRY_RANGES.items()
    }


def _inventory(inputs, source):
    equal(
        pick(
            source,
            (
                "schema_version",
                "scope",
                "status",
                "snapshots_rechecked",
                "elf_sha256",
                "overlay_sha256",
                "new_vm_execution",
                "guest_writes",
                "original_reports_unchanged",
            ),
        ),
        dict(
            schema_version=1,
            scope="ir_t7_collision_evidence_inventory",
            status="pass",
            snapshots_rechecked=30,
            **pick(IDENTITY, ("elf_sha256", "overlay_sha256")),
            new_vm_execution=False,
            guest_writes=False,
            original_reports_unchanged=True,
        ),
    )
    ordered(source["samples"], SLOTS)
    for key in REPORTS:
        equal(
            _input_pin(inputs["reports"][key], REPORT_LIMIT),
            pick(source["sources"][key], ("size", "sha256")),
        )
    for item, sample in zip(inputs["captures"], source["samples"], strict=True):
        fields(item, ("slot", "state", "receipt"))
        equal(item["slot"], sample["slot"])
        for key, limit in (("state", STATE_LIMIT), ("receipt", RECEIPT_LIMIT)):
            equal(
                _input_pin(item[key], limit),
                dict(size=sample[key + "_size"], sha256=sample[key + "_sha256"]),
            )


def _capture(item, sample):
    receipt = decode_json(_read(item["receipt"], RECEIPT_LIMIT))
    ranges = _state_ranges(_read(item["state"], STATE_LIMIT), receipt)
    observation = decode_registry(ranges)
    slot = item["slot"]
    entries = range_entries(slot, ranges)
    equal(
        sample["raw_ranges"],
        [{**entry, "file": name} for entry, name in zip(entries, REGISTRY_RANGES, strict=True)],
    )
    equal(
        pick(
            sample,
            (
                "phase",
                "pc",
                "cycle",
                "room",
                "active",
                "world_active",
                "character_counts",
                "world_counts",
                "event_count",
                "active_actor_count",
            ),
        ),
        dict(
            phase=phase(slot),
            **pick(receipt, ("pc", "cycle")),
            room=observation["room"],
            active=observation["character"]["selector"],
            world_active=observation["world"]["selector"],
            character_counts=observation["character"]["counts"],
            world_counts=observation["world"]["counts"],
            event_count=observation["events"]["count"],
            active_actor_count=len(observation["actors"]),
        ),
    )
    capture = dict(
        slot=slot,
        state=pick(item["state"], ("size", "sha256")),
        receipt_source=pick(item["receipt"], ("size", "sha256")),
        receipt=receipt,
        phase=phase(slot),
        ranges=entries,
        observations=observation,
    )
    return capture, {f"capture-{slot:02d}-{name}": raw for name, raw in ranges.items()}


def prepare_files(inputs):
    fields(inputs, ("reports", "inventory", "captures"))
    fields(inputs["reports"], REPORTS)
    ordered(inputs["captures"], SLOTS)
    source = decode_json(_read(inputs["inventory"], REPORT_LIMIT))
    _inventory(inputs, source)
    documents = {
        key + "_reference": decode_json(_read(inputs["reports"][key], REPORT_LIMIT))
        for key in REPORTS
    }
    provenance = dict(
        source_identity=IDENTITY.copy(),
        inventory_sha256=inputs["inventory"]["sha256"],
        source_reports={key: pick(inputs["reports"][key], ("size", "sha256")) for key in REPORTS},
    )
    captures, blobs = [], {}
    # Only one archive and one RAM buffer live in _capture at a time.
    for item, sample in zip(inputs["captures"], source["samples"], strict=True):
        capture, ranges = _capture(item, sample)
        captures.append(capture)
        blobs.update(ranges)
    files = make_collision(documents, provenance, captures, blobs)
    require(
        files == export_collision(files["intermediate.json"], {k: files[k] for k in BLOB_NAMES})
    )
    return files, dict(
        schema_version=1,
        scope="private_collision_intermediate",
        profile=PROFILE,
        converter=CONVERTER,
        state="observed_registry",
        source_reports=provenance["source_reports"],
        inventory_sha256=provenance["inventory_sha256"],
        capture_count=len(captures),
        original_sidecars_preserved=len(blobs),
        logical_roundtrip=True,
        observation_regeneration_identical=True,
        new_vm_execution=False,
        original_state_rebuild=False,
        world_pointees_included=False,
        collision_response_verified=False,
        damage_transitions_verified=False,
        capabilities=[],
        files_sha256={k: sha(v) for k, v in files.items()},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("inputs", "private-root"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        files, report = prepare_files(decode_json(bounded_read(args.inputs, 32768)))
        write_collision_intermediate_bundle(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id, files, report
        )
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({"status": "rejected", "error_type": type(error).__name__}))
        return 1
    print(json.dumps({"status": "prepared", "profile": PROFILE}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
