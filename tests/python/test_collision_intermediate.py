"""IR-T7d: authored registries/states, source linkage and private package custody."""

import copy
import json
import shutil
import struct
import subprocess
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE
from tools.pipeline.collision_evidence import IDENTITY, REPORTS, SLOTS, phase
from tools.pipeline.collision_intermediate import (
    BLOB_NAMES,
    OUTPUT_NAMES,
    export_collision,
    make_collision,
    range_entries,
)
from tools.pipeline.collision_registry import REGISTRY_RANGES
from tools.pipeline.intermediate_assets import sha
from tools.pipeline.intermediate_json import decode_json, encode_json
from tools.pipeline.prepare_collision_intermediate import _state_ranges, main, prepare_files
from tools.pipeline.private_texture_output import write_collision_intermediate_bundle


def fingerprint(raw):
    return dict(size=len(raw), sha256=sha(raw))


def authored_ranges(control):
    raw = {name: bytearray(size) for name, (_, size) in REGISTRY_RANGES.items()}
    actors = []
    count = 26 if control else 30
    for i in range(count):
        kind, instance = 0x900 + i, i
        if i == 0:
            kind, instance = 0x100, 0
        elif control and i <= 11:
            kind = 0x20C
        elif not control and i == 1:
            kind = 0x215
        elif not control and 2 <= i <= 4:
            kind, instance = 0x209, 0x18C + i
        elif not control and 5 <= i <= 15:
            kind, instance = 0x20C, i - 4
        address = 0x4481D0 + i * 0x320
        status, function = 0x8008, 0x123400 + i * 4
        actors.append(
            dict(address=address, status=status, kind=kind, instance=instance, function=function)
        )
        struct.pack_into("<I", raw["actors.bin"], i * 0x320 + 4, status)
        struct.pack_into("<HH", raw["actors.bin"], i * 0x320 + 12, kind, instance)
        struct.pack_into("<I", raw["actors.bin"], i * 0x320 + 0xA0, function)
        struct.pack_into(
            "<II",
            raw["actors.bin"],
            i * 0x320 + 0xB8,
            address - 0x320 if i else 0,
            address + 0x320 if i + 1 < count else 0,
        )
    struct.pack_into("<I", raw["actor-head.bin"], 0, actors[0]["address"])
    raw["actors.bin"][-1] = 0xD7  # Inactive actor, retained without interpretation.
    raw["character.bin"][0x2300] = 0xA6
    raw["events.bin"][:] = b"\xa5" * 8192
    banks, worlds = [], []
    owners = [0] + [i for i in range(1, 12) for _ in range(2)] if control else [0, 1]
    for bank in range(2):
        rows = []
        for index, owner in enumerate(owners):
            offset = bank * 0x2400 + index * 0x120
            actor = actors[owner]
            presence, callback = [index % 2, bank + 1], 0x234000 + index * 4
            struct.pack_into("<I", raw["character.bin"], offset + 0x60, actor["address"])
            struct.pack_into("<HH", raw["character.bin"], offset + 0x110, *presence)
            struct.pack_into("<I", raw["character.bin"], offset + 0x11C, callback)
            rows.append(
                dict(
                    index=index,
                    record=0x1D05FE0 + offset,
                    owner=actor["address"],
                    kind=actor["kind"],
                    instance=actor["instance"],
                    presence_words=presence,
                    callback=callback,
                )
            )
        banks.append(rows)
        pointers = [0x100000 + bank * 0x10000 + i * 0x100 for i in range(1 if control else 12)]
        worlds.append(pointers)
        struct.pack_into("<I", raw["world.bin"], bank * 0x44, len(pointers))
        struct.pack_into(f"<{len(pointers)}I", raw["world.bin"], bank * 0x44 + 4, *pointers)
    struct.pack_into("<III", raw["character.bin"], 0x4800, len(owners), len(owners), 1)
    struct.pack_into("<I", raw["world.bin"], 0x88, 0)
    raw["stage.bin"][0] = 0x23
    struct.pack_into("<I", raw["room.bin"], 0, 0xEA if control else 0xEB)
    observation = dict(
        stage=35,
        room=234 if control else 235,
        actors=actors,
        character=dict(selector=1, counts=[len(owners)] * 2, banks=banks),
        world=dict(selector=0, counts=[len(worlds[0])] * 2, banks=worlds),
        events=dict(count=0, entries=[]),
    )
    return {k: bytes(v) for k, v in raw.items()}, observation


def archive(
    ranges, slot, *, crc=0x5088CCDB, delay=0, version=VERSION, short_cpu=False, short_ram=False
):
    cpu = 333 + len(b"own.elf")
    internals = bytearray(cpu + (700 if short_cpu else 1160))
    internals[:32] = b"BIOS".ljust(32, b"\0")
    struct.pack_into("<II", internals, 292, crc, len(b"own.elf"))
    internals[300:307] = b"own.elf"
    internals[307] = 1
    internals[308:cpu] = b"cpuRegs".ljust(32, b"\0")
    struct.pack_into("<II", internals, cpu + 676, delay, 0x123400)
    if not short_cpu:
        struct.pack_into("<Q", internals, cpu + 1088, slot * 1000)
    ram = bytearray(RAM_SIZE - int(short_ram))
    for name, (address, size) in REGISTRY_RANGES.items():
        ram[address : address + size] = ranges[name]
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for name, data in (
            (VERSION_MEMBER, version),
            (INTERNALS_MEMBER, internals),
            (RAM_MEMBER, ram),
        ):
            z.writestr(name, data)
    return stream.getvalue()


@pytest.fixture(scope="module")
def corpus():
    captures, blobs, sources, samples, references = [], {}, {}, [], []
    for slot in SLOTS:
        ranges, observation = authored_ranges(slot == 2)
        state = archive(ranges, slot)
        receipt = dict(
            slot=slot,
            pid=123,
            crc=0x5088CCDB,
            pc=0x123400,
            cycle=slot * 1000,
            gpr=[0] * 32,
            delay=False,
            state_sha256=sha(state),
            stage_selector=35,
            guest_writes=False,
            fresh_boot=slot != 36,
            diagnostic_replay=slot == 36,
            state_restores=int(slot == 36),
            opaque=[None, True, 1, 1.0, -0.0, "own metadata"],
        )
        receipt_raw = json.dumps(receipt, indent=2).encode()
        entries = range_entries(slot, ranges)
        capture = dict(
            slot=slot,
            state=fingerprint(state),
            receipt_source=fingerprint(receipt_raw),
            receipt=receipt,
            phase=phase(slot),
            ranges=entries,
            observations=observation,
        )
        captures.append(capture)
        blobs.update({f"capture-{slot:02d}-{k}": v for k, v in ranges.items()})
        sources[f"state-{slot}.p2s"], sources[f"receipt-{slot}.json"] = state, receipt_raw
        banks = [
            [
                dict(
                    record=r["record"],
                    owner=r["owner"],
                    kind=r["kind"],
                    instance=r["instance"],
                    presence=r["presence_words"],
                    callback=r["callback"],
                )
                for r in bank
            ]
            for bank in observation["character"]["banks"]
        ]
        references.append(
            dict(
                slot=slot,
                sha256=sha(state),
                cycle=receipt["cycle"],
                pc=receipt["pc"],
                diagnostic_replay=slot == 36,
                state_restores=int(slot == 36),
                active=1,
                character_banks=banks,
                world_active=0,
                world_banks=observation["world"]["banks"],
                targets=[
                    {**a, "opaque_ai": [-0.0, True]}
                    for a in observation["actors"]
                    if a["kind"] in (0x20C, 0x209)
                ],
                events=[],
            )
        )
        samples.append(
            dict(
                slot=slot,
                phase=phase(slot),
                state_size=len(state),
                state_sha256=sha(state),
                receipt_size=len(receipt_raw),
                receipt_sha256=sha(receipt_raw),
                pc=receipt["pc"],
                cycle=receipt["cycle"],
                room=observation["room"],
                active=1,
                world_active=0,
                active_actor_count=len(observation["actors"]),
                event_count=0,
                character_counts=observation["character"]["counts"],
                world_counts=observation["world"]["counts"],
                raw_ranges=[
                    {**entry, "file": name}
                    for entry, name in zip(entries, REGISTRY_RANGES, strict=True)
                ],
            )
        )
    post = captures[1]["observations"]
    continuity = dict(
        schema="sh3-animation-continuity-observation-v1",
        identity=dict(
            pid=123,
            crc=IDENTITY["crc"],
            overlay_sha256=IDENTITY["overlay_sha256"],
            actor=post["actors"][2],
        ),
        provenance=dict(
            fresh_boot=True,
            guest_writes=False,
            state_restores=0,
            segment_start=8,
            segment_end=35,
            observed_resume_actions=27,
        ),
        samples=[
            dict(
                slot=c["slot"],
                sha256=c["state"]["sha256"],
                sample=dict(cycle=c["receipt"]["cycle"]),
            )
            for c in captures[1:-1]
        ],
        continuous_loop_verified=True,
        natural_initial_selection_verified=True,
        ai_damage_death_transitions_verified=False,
    )
    sources["continuity.json"] = json.dumps(continuity, indent=3).encode()
    collision = dict(
        schema="sh3-carousel-collision-audit-v1",
        elf_sha256=IDENTITY["elf_sha256"],
        overlay_sha256=IDENTITY["overlay_sha256"],
        continuity_report_sha256=sha(sources["continuity.json"]),
        captures=references,
        actor_world_geometry=[
            dict(index=i, instance=instance, banks=[bank[i] for bank in post["world"]["banks"]])
            for i, instance in ((1, 399), (2, 400), (11, 398))
        ],
        observed_impact=False,
        ai_damage_death_transitions_verified=False,
        unknown=dict(flag=True, word=1, real=1.0, negative_zero=-0.0),
    )
    sources["collision.json"] = json.dumps(collision, indent=2).encode()
    alternatives = dict(
        schema="sh3-carousel-alternative-routes-v1",
        elf_sha256=IDENTITY["elf_sha256"],
        overlay_sha256=IDENTITY["overlay_sha256"],
        previous_report_sha256=sha(sources["collision.json"]),
        normal_play_damage_route_identified=False,
        runtime_transition_observed=False,
        vm_interaction=False,
        snapshots=[
            dict(slot=c["slot"], sha256=c["state"]["sha256"], diagnostic_replay=c["slot"] == 36)
            for c in (captures[1], captures[-2], captures[-1])
        ],
    )
    sources["alternatives.json"] = json.dumps(alternatives).encode()
    source_reports = {k: fingerprint(sources[k + ".json"]) for k in REPORTS}
    inventory = dict(
        schema_version=1,
        scope="ir_t7_collision_evidence_inventory",
        status="pass",
        snapshots_rechecked=30,
        elf_sha256=IDENTITY["elf_sha256"],
        overlay_sha256=IDENTITY["overlay_sha256"],
        new_vm_execution=False,
        guest_writes=False,
        original_reports_unchanged=True,
        sources={k: {**v, "file": k + ".json"} for k, v in source_reports.items()},
        samples=samples,
    )
    sources["inventory.json"] = json.dumps(inventory).encode()
    documents = dict(
        collision_reference=collision,
        alternatives_reference=alternatives,
        continuity_reference=continuity,
    )
    provenance = dict(
        source_identity=IDENTITY.copy(),
        source_reports=source_reports,
        inventory_sha256=sha(sources["inventory.json"]),
    )
    return documents, provenance, captures, blobs, sources


def input_config(directory, corpus):
    sources = corpus[-1]
    directory.mkdir()
    for name, raw in sources.items():
        (directory / name).write_bytes(raw)

    def entry(name):
        return dict(path=str(directory / name), **fingerprint(sources[name]))

    return dict(
        reports={k: entry(k + ".json") for k in REPORTS},
        inventory=entry("inventory.json"),
        captures=[
            dict(slot=s, state=entry(f"state-{s}.p2s"), receipt=entry(f"receipt-{s}.json"))
            for s in SLOTS
        ],
    )


@pytest.fixture(scope="module")
def inputs(tmp_path_factory, corpus):
    return input_config(tmp_path_factory.mktemp("collision") / "sources", corpus)


@pytest.fixture(scope="module")
def package(corpus):
    return make_collision(*corpus[:4])


def test_exact_roundtrip_no_aliases_and_opaque_values(corpus, package):
    docs, provenance, captures, blobs, _ = corpus
    before = encode_json([docs, provenance, captures])
    assert set(package) == OUTPUT_NAMES and len(package) == 242
    assert sum(len(v) for v in blobs.values()) == 1571670
    assert export_collision(package["intermediate.json"], blobs) == package
    root = decode_json(package["intermediate.json"])
    assert encode_json(root["documents"]) == encode_json(docs)
    assert encode_json(root["captures"]) == encode_json(captures)
    assert encode_json([docs, provenance, captures]) == before
    assert {k: package[k] for k in BLOB_NAMES} == blobs
    view = decode_json(package["collision-observations.json"])
    assert view["state"] == "observed_registry" and view["capabilities"] == []
    assert view["captures"][0]["observations"]["character"]["counts"] == [23, 23]
    assert view["captures"][-1]["phase"] == "restored_diagnostic"
    root["documents"]["collision_reference"]["unknown"]["flag"] = 42
    assert docs["collision_reference"]["unknown"]["flag"] is True


def change(root, path, value):
    for part in path[:-1]:
        root = root[part]
    root[path[-1]] = value


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), True),
        (("profile",), "other"),
        (("converter",), "other"),
        (("conventions", "world_pointees"), "included"),
        (("captures",), []),
        (("captures", 1, "slot"), 2),
        (("captures", 0, "slot"), 2.0),
        (("captures", 0, "state", "size"), True),
        (("captures", 0, "state", "size"), 67108865),
        (("captures", 0, "state", "sha256"), "A" * 64),
        (("captures", 1, "phase"), "control_puzzle"),
        (("captures", -1, "phase"), "continuous_post_phase"),
        (("captures", 1, "receipt", "crc"), 0),
        (("captures", 1, "receipt", "pid"), 124),
        (("captures", 1, "receipt", "delay"), 0),
        (("captures", 1, "receipt", "guest_writes"), True),
        (("captures", -1, "receipt", "fresh_boot"), True),
        (("captures", -1, "receipt", "state_restores"), 0),
        (("captures", 1, "receipt", "diagnostic_replay"), True),
        (("captures", 1, "receipt", "stage_selector"), 36),
        (("captures", 1, "receipt", "cycle"), True),
        (("captures", 1, "receipt", "pc"), -1),
        (("captures", 1, "receipt", "gpr"), [0] * 31),
        (("captures", 1, "receipt", "gpr", 1), True),
        (("captures", 0, "ranges", 0, "file"), "../escape"),
        (("captures", 0, "ranges", 0, "address"), 0),
        (("captures", 0, "ranges", 0, "size"), 1),
        (("captures", 0, "ranges", 0, "sha256"), "0" * 64),
        (("captures", 0, "ranges"), []),
        (("captures", 0, "observations", "room"), 235),
        (("captures", 0, "observations", "character", "selector"), True),
        (("provenance", "inventory_sha256"), "x"),
        (("provenance", "source_identity", "crc"), 1),
        (("provenance", "source_reports", "collision", "size"), 0),
        (("documents", "collision_reference", "schema"), "wrong"),
        (("documents", "collision_reference", "overlay_sha256"), "0" * 64),
        (("documents", "collision_reference", "observed_impact"), True),
        (("documents", "collision_reference", "continuity_report_sha256"), "0" * 64),
        (("documents", "collision_reference", "captures", 0, "character_banks", 0, 1, "owner"), 0),
        (("documents", "collision_reference", "captures", 0, "targets", 0, "status"), 0),
        (("documents", "collision_reference", "captures", 0, "cycle"), 1),
        (("documents", "collision_reference", "captures", 0, "events"), [0]),
        (("documents", "collision_reference", "actor_world_geometry", 0, "index"), True),
        (("documents", "collision_reference", "actor_world_geometry", 0, "banks"), [1, 2]),
        (("documents", "alternatives_reference", "snapshots", 0, "sha256"), "0" * 64),
        (("documents", "alternatives_reference", "snapshots", -1, "diagnostic_replay"), False),
        (("documents", "continuity_reference", "samples", 0, "sha256"), "0" * 64),
        (("documents", "continuity_reference", "samples", 0, "sample", "cycle"), 1),
        (("documents", "continuity_reference", "identity", "actor", "address"), 0),
        (("documents", "continuity_reference", "provenance", "state_restores"), 1),
        (("documents", "collision_reference", "unknown"), "/Users/secret"),
        (("documents", "collision_reference", "unknown"), "C:\\private"),
        (("documents", "collision_reference", "unknown"), "file:///private"),
    ],
)
def test_reject_inconsistent_metadata(package, corpus, path, value):
    root = decode_json(package["intermediate.json"])
    change(root, path, value)
    with pytest.raises(ValueError):
        export_collision(encode_json(root), corpus[3])


@pytest.mark.parametrize(
    "variant",
    [
        "missing",
        "extra",
        "mutable",
        "opaque_byte",
        "short",
        "range_extra",
        "root_extra",
        "document_missing",
    ],
)
def test_reject_corrupt_or_extra_inputs(package, corpus, variant):
    root, blobs = decode_json(package["intermediate.json"]), dict(corpus[3])
    key = "capture-02-events.bin"
    if variant == "missing":
        del blobs[key]
    elif variant == "extra":
        blobs["extra.bin"] = b"x"
    elif variant == "mutable":
        blobs[key] = bytearray(blobs[key])
    elif variant == "opaque_byte":
        blobs[key] = b"x" + blobs[key][1:]
    elif variant == "short":
        blobs[key] = blobs[key][:-1]
    elif variant == "range_extra":
        root["captures"][0]["ranges"][0]["extra"] = 1
    elif variant == "root_extra":
        root["extra"] = 1
    else:
        del root["documents"]["continuity_reference"]["samples"]
    with pytest.raises(ValueError):
        export_collision(encode_json(root), blobs)


def test_duplicate_state_and_nonmonotone_continuity(package, corpus):
    root = decode_json(package["intermediate.json"])
    root["captures"][2]["state"] = root["captures"][1]["state"]
    with pytest.raises(ValueError):
        export_collision(encode_json(root), corpus[3])
    root = decode_json(package["intermediate.json"])
    root["captures"][2]["receipt"]["cycle"] = 1
    root["documents"]["collision_reference"]["captures"][2]["cycle"] = 1
    root["documents"]["continuity_reference"]["samples"][1]["sample"]["cycle"] = 1
    with pytest.raises(ValueError):
        export_collision(encode_json(root), corpus[3])


def test_prepare_matches_pure_package_and_bounded_read_pins(inputs, package):
    files, report = prepare_files(inputs)
    assert files == package
    assert report["capture_count"] == 30 and report["original_sidecars_preserved"] == 240
    for key in (
        "new_vm_execution",
        "original_state_rebuild",
        "world_pointees_included",
        "collision_response_verified",
        "damage_transitions_verified",
    ):
        assert report[key] is False
    assert report["capabilities"] == []
    assert "/Users/" not in files["intermediate.json"].decode()


@pytest.mark.parametrize(
    "path,value",
    [
        (("reports", "collision", "path"), "relative"),
        (("inventory", "size"), True),
        (("reports", "collision", "sha256"), "0" * 64),
        (("inventory", "sha256"), "0" * 64),
        (("captures", 0, "state", "size"), 1),
        (("captures", 0, "receipt", "sha256"), "1" * 64),
        (("captures", 0, "slot"), 8),
        (("captures",), []),
        (("reports",), {}),
    ],
)
def test_input_pin_and_config_rejections(inputs, path, value):
    config = copy.deepcopy(inputs)
    change(config, path, value)
    with pytest.raises(ValueError):
        prepare_files(config)


@pytest.mark.parametrize(
    "variant", ["crc", "version", "delay", "pc", "cycle", "gpr", "short_cpu", "short_ram"]
)
def test_state_vs_receipt_and_state_contract(corpus, variant):
    ranges, _ = authored_ranges(False)
    receipt = copy.deepcopy(corpus[2][1]["receipt"])
    kwargs = {}
    if variant == "crc":
        kwargs["crc"] = 1
    elif variant == "version":
        kwargs["version"] = b"x" * 36
    elif variant == "delay":
        kwargs["delay"] = 1
    elif variant in ("short_cpu", "short_ram"):
        kwargs[variant] = True
    elif variant == "gpr":
        receipt["gpr"][0] = 1
    else:
        receipt[variant] += 1
    with pytest.raises(ValueError):
        _state_ranges(archive(ranges, 8, **kwargs), receipt)


def test_private_cli_source_free_reconstruction_and_exclusive_writer(
    tmp_path, corpus, package, capsys
):
    inputs = input_config(tmp_path / "sources", corpus)
    config = tmp_path / "inputs.json"
    config.write_bytes(encode_json(inputs))
    private = tmp_path / "private"
    private.mkdir()
    args = ["--inputs", str(config), "--private-root", str(private), "--run-id", "own-test"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "prepared"
    directory = private / "own-test"
    manifest = json.loads((directory / "manifest.json").read_bytes())
    assert set(p.name for p in directory.iterdir()) == OUTPUT_NAMES | {
        "manifest.json",
        ".manifest.pending.json",
    }
    for entry in manifest["files"]:
        assert fingerprint((directory / entry["file"]).read_bytes()) == {
            k: entry[k] for k in ("size", "sha256")
        }
    assert directory.stat().st_mode & 0o777 == 0o700
    assert (directory / "intermediate.json").stat().st_mode & 0o777 == 0o600
    before = (directory / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        write_collision_intermediate_bundle(private, Path.cwd(), "own-test", package, {})
    assert (directory / "manifest.json").read_bytes() == before
    shutil.rmtree(tmp_path / "sources")
    config.unlink()
    restored = export_collision(
        (directory / "intermediate.json").read_bytes(),
        {k: (directory / k).read_bytes() for k in BLOB_NAMES},
    )
    assert restored == package
    assert main(args) == 1
    assert json.loads(capsys.readouterr().out) == {
        "status": "rejected",
        "error_type": "FileNotFoundError",
    }


def test_symlink_source_rejected(inputs, tmp_path):
    config = copy.deepcopy(inputs)
    link = tmp_path / "linked.json"
    link.symlink_to(config["inventory"]["path"])
    config["inventory"]["path"] = str(link)
    with pytest.raises((ValueError, OSError)):
        prepare_files(config)


@pytest.mark.parametrize(
    "path,value",
    [
        (("samples", 0, "raw_ranges", 0, "sha256"), "0" * 64),
        (("samples", 0, "raw_ranges", 0, "address"), 0),
        (("samples", 0, "phase"), "continuous_post_phase"),
        (("samples", 0, "character_counts"), [2, 2]),
        (("samples", 0, "active_actor_count"), 25),
        (("samples", 0, "pc"), 0),
        (("samples", 0, "cycle"), True),
        (("samples", 0, "room"), 235),
        (("samples", 0, "state_sha256"), "0" * 64),
        (("samples", 0, "receipt_sha256"), "0" * 64),
        (("sources", "collision", "sha256"), "0" * 64),
        (("guest_writes",), True),
        (("schema_version",), True),
        (("scope",), "wrong"),
        (("snapshots_rechecked",), 29),
    ],
)
def test_inventory_is_crosschecked_not_just_hashed(inputs, tmp_path, path, value):
    config = copy.deepcopy(inputs)
    inventory = json.loads(Path(config["inventory"]["path"]).read_bytes())
    change(inventory, path, value)
    raw = encode_json(inventory)
    altered = tmp_path / "altered.json"
    altered.write_bytes(raw)
    config["inventory"] = dict(path=str(altered), **fingerprint(raw))
    with pytest.raises(ValueError):
        prepare_files(config)


def test_old_puzzle_actors_are_checked_in_post_phase(package, corpus):
    root = decode_json(package["intermediate.json"])
    rows = root["documents"]["collision_reference"]["captures"][1]["targets"]
    assert len(rows) == 14
    old = next(r for r in rows if r["kind"] == 0x20C)
    old["status"] ^= 1
    with pytest.raises(ValueError):
        export_collision(encode_json(root), corpus[3])


@pytest.mark.parametrize(
    "variant",
    [
        "character_count",
        "world_count",
        "wrong_owner_kind",
        "wrong_phase_room",
        "world_duplicate",
        "target_instance",
    ],
)
def test_consistent_rehashed_bytes_still_must_obey_phase(package, corpus, variant):
    # Recompute the observation deliberately: reject semantically inconsistent
    # but internally hashed bytes, rather than relying on a stale derived view.
    from tools.pipeline.collision_registry import decode_registry

    root, blobs = decode_json(package["intermediate.json"]), dict(corpus[3])
    capture = root["captures"][1]
    ranges = {name: bytearray(blobs[f"capture-08-{name}"]) for name in REGISTRY_RANGES}
    if variant == "character_count":
        struct.pack_into("<I", ranges["character.bin"], 0x4800, 1)
    elif variant == "world_count":
        struct.pack_into("<I", ranges["world.bin"], 0, 11)
    elif variant == "wrong_owner_kind":
        # Second row now belongs to Heather too, not Alessa.
        struct.pack_into("<I", ranges["character.bin"], 0x120 + 0x60, 0x4481D0)
    elif variant == "wrong_phase_room":
        struct.pack_into("<I", ranges["room.bin"], 0, 0xEA)
    elif variant == "world_duplicate":
        struct.pack_into("<I", ranges["world.bin"], 8, 0x100000)
    else:
        struct.pack_into("<H", ranges["actors.bin"], 4 * 0x320 + 0xE, 0x18F)
    ranges = {k: bytes(v) for k, v in ranges.items()}
    observation = decode_registry(ranges)
    capture["observations"] = observation
    capture["ranges"] = range_entries(8, ranges)
    blobs.update({f"capture-08-{k}": v for k, v in ranges.items()})
    reference = root["documents"]["collision_reference"]["captures"][1]
    reference["character_banks"] = [
        [
            dict(
                record=r["record"],
                owner=r["owner"],
                kind=r["kind"],
                instance=r["instance"],
                presence=r["presence_words"],
                callback=r["callback"],
            )
            for r in bank
        ]
        for bank in observation["character"]["banks"]
    ]
    reference["world_banks"] = observation["world"]["banks"]
    reference["targets"] = [a for a in observation["actors"] if a["kind"] in (0x20C, 0x209)]
    with pytest.raises(ValueError):
        export_collision(encode_json(root), blobs)


def test_cli_module_optimized_rejects_without_publishing(tmp_path):
    config = tmp_path / "invalid.json"
    config.write_bytes(b"{}")
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-m",
            "tools.pipeline.prepare_collision_intermediate",
            "--inputs",
            str(config),
            "--private-root",
            str(tmp_path),
            "--run-id",
            "rejected",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1 and result.stderr == ""
    assert json.loads(result.stdout) == dict(status="rejected", error_type="ValueError")
    assert not (tmp_path / "rejected").exists()
