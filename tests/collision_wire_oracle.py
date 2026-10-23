"""IR-T7e test oracle: stdlib only, independent of production and fixture builders.

Constants are transcribed from schemas/collision-intermediate-v1.md. This
checks retained observations, not collision shapes, execution or damage.
"""

import hashlib
import json
import math
import zipfile
from io import BytesIO

SLOTS = [2, *range(8, 37)]
RANGES = (
    ("character.bin", 0x1D05FE0, 18444),
    ("world.bin", 0x1D04560, 140),
    ("events.bin", 0x1D000F0, 8192),
    ("event-count.bin", 0x1D02130, 4),
    ("actors.bin", 0x4481D0, 25600),
    ("actor-head.bin", 0x44E5D4, 4),
    ("stage.bin", 0x1CFB851, 1),
    ("room.bin", 0x1CB5770, 4),
)


def check(condition, label):
    if not condition:
        raise AssertionError(label)


def identical(actual, expected):
    """Type-sensitive tree comparison, including the sign of floating zero."""
    check(type(actual) is type(expected), "JSON type")
    if type(expected) is dict:
        check(actual.keys() == expected.keys(), "JSON keys")
        for key in expected:
            identical(actual[key], expected[key])
    elif type(expected) is list:
        check(len(actual) == len(expected), "JSON length")
        for a, b in zip(actual, expected, strict=True):
            identical(a, b)
    elif type(expected) is float:
        check(math.isfinite(actual) and math.isfinite(expected), "JSON finite")
        check(actual.hex() == expected.hex(), "JSON float")
    else:
        check(actual == expected, "JSON value")


def fingerprint(raw):
    return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def load(raw):
    check(type(raw) is bytes and 0 < len(raw) <= 8 * 1024 * 1024, "JSON budget")

    def pairs(items):
        result = {}
        for key, value in items:
            check(key not in result, "JSON duplicate")
            result[key] = value
        return result

    def nonfinite(_):
        raise AssertionError("JSON finite")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def word(raw, offset=0, width=4):
    check(0 <= offset and offset + width <= len(raw), "word bounds")
    return int.from_bytes(raw[offset : offset + width], "little")


def observe(buffers):
    """Decode via a complete actor-slot table before traversing its links."""
    check(set(buffers) == {n for n, _, _ in RANGES}, "range names")
    for name, _, length in RANGES:
        check(type(buffers[name]) is bytes and len(buffers[name]) == length, "range length")
    pool = buffers["actors.bin"]
    table = {}
    for index in range(32):
        base = index * 800
        address = 0x4481D0 + base
        table[address] = dict(
            actor=dict(
                address=address,
                status=word(pool, base + 4),
                kind=word(pool, base + 12, 2),
                instance=word(pool, base + 14, 2),
                function=word(pool, base + 160),
            ),
            previous=word(pool, base + 184),
            following=word(pool, base + 188),
        )
    address, previous, actors, visited = word(buffers["actor-head.bin"]), 0, [], set()
    while address:
        check(address in table and address not in visited, "actor address/cycle")
        row = table[address]
        check(row["previous"] == previous, "actor previous")
        actors.append(row["actor"])
        visited.add(address)
        previous, address = address, row["following"]
    character = buffers["character.bin"]
    counts = [word(character, 18432), word(character, 18436)]
    selector = word(character, 18440)
    check(max(counts) <= 32 and selector < 2, "character bounds")
    banks = []
    for bank in range(2):
        rows = []
        for index in range(counts[bank]):
            base = bank * 9216 + index * 288
            owner = word(character, base + 96)
            check(owner in visited, "owner")
            actor = table[owner]["actor"]
            rows.append(
                dict(
                    index=index,
                    record=0x1D05FE0 + base,
                    owner=owner,
                    kind=actor["kind"],
                    instance=actor["instance"],
                    presence_words=[word(character, base + 272, 2), word(character, base + 274, 2)],
                    callback=word(character, base + 284),
                )
            )
        banks.append(rows)
    world = buffers["world.bin"]
    world_counts = [word(world), word(world, 68)]
    world_selector = word(world, 136)
    check(max(world_counts) <= 16 and world_selector < 2, "world bounds")
    pointers = [
        [word(world, bank * 68 + 4 + i * 4) for i in range(world_counts[bank])] for bank in range(2)
    ]
    check(all(0 < p <= 33554352 for bank in pointers for p in bank), "world pointer")
    check(word(buffers["event-count.bin"]) == 0, "unsupported events")
    return dict(
        stage=word(buffers["stage.bin"], width=1),
        room=word(buffers["room.bin"]),
        actors=actors,
        character=dict(selector=selector, counts=counts, banks=banks),
        world=dict(selector=world_selector, counts=world_counts, banks=pointers),
        events=dict(count=0, entries=[]),
    )


def inspect_package(files, manifest=None):
    expected_names = {f"capture-{s:02d}-{n}" for s in SLOTS for n, _, _ in RANGES}
    expected_names.update(("intermediate.json", "collision-observations.json"))
    check(set(files) == expected_names, "file inventory")
    root = load(files["intermediate.json"])
    identical(root["schema_version"], 1)
    identical(root["profile"], "ps2-collision-registry-v1")
    identical(root["converter"], "captured-eu-collision-registry-intermediate-v1")
    identical(
        root["conventions"],
        dict(
            endian="little",
            words=["u16", "u32"],
            addresses="ee_provenance_only",
            banks="both_in_original_order",
            physical_coordinates="undefined",
            events="empty_only",
            world_pointees="excluded",
            callbacks="opaque_integers",
        ),
    )
    identical([c["slot"] for c in root["captures"]], SLOTS)
    view_captures = []
    for capture in root["captures"]:
        slot = capture["slot"]
        identical(
            capture["phase"],
            "control_puzzle"
            if slot == 2
            else ("restored_diagnostic" if slot == 36 else "continuous_post_phase"),
        )
        entries, buffers = [], {}
        for name, address, size in RANGES:
            filename = f"capture-{slot:02d}-{name}"
            raw = files[filename]
            check(len(raw) == size, "block size")
            buffers[name] = raw
            entries.append(dict(file=filename, address=address, **fingerprint(raw)))
        identical(capture["ranges"], entries)
        derived = observe(buffers)
        identical(capture["observations"], derived)
        identical(derived["stage"], 35)
        identical(derived["room"], 234 if slot == 2 else 235)
        identical(derived["character"]["counts"], [23, 23] if slot == 2 else [2, 2])
        identical(derived["world"]["counts"], [1, 1] if slot == 2 else [12, 12])
        identical(len(derived["actors"]), 26 if slot == 2 else 30)
        view_captures.append({k: capture[k] for k in ("slot", "phase", "state", "observations")})
    identical(
        load(files["collision-observations.json"]),
        dict(
            schema_version=1,
            profile="ps2-collision-registry-v1",
            state="observed_registry",
            capabilities=[],
            captures=view_captures,
        ),
    )
    if manifest is not None:
        identical(manifest["files"], [dict(file=n, **fingerprint(files[n])) for n in sorted(files)])
        identical(manifest["state"], "observed_registry")
        identical(manifest["capabilities"], [])
        for flag in (
            "new_vm_execution",
            "original_state_rebuild",
            "world_pointees_included",
            "collision_response_verified",
            "damage_transitions_verified",
        ):
            identical(manifest[flag], False)
    return dict(captures=30, blocks=240, raw_bytes=1571670, files=242)


def _compare_state(files, capture, raw):
    identical(capture["state"], fingerprint(raw))
    check(len(raw) <= 64 * 1024 * 1024, "ZIP budget")
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        check(len(archive.namelist()) == len(set(archive.namelist())), "ZIP duplicate")

        def member(name, maximum):
            check(archive.getinfo(name).file_size <= maximum, "ZIP member budget")
            with archive.open(name) as stream:
                return stream.read(maximum + 1)

        version = member("PCSX2 Savestate Version.id", 36)
        check(version == b"\0\0\x59\x9a" + b"v2.8.2".ljust(32, b"\0"), "state version")
        internals = member("PCSX2 Internal Structures.dat", 4 * 1024 * 1024)
        check(internals[:32] == b"BIOS".ljust(32, b"\0"), "BIOS tag")
        check(word(internals, 292) == 0x5088CCDB, "CRC")
        length = word(internals, 296)
        check(1 <= length <= 1024 and internals[300 + length] == 1, "ELF identity")
        cpu = 333 + length
        check(internals[cpu - 32 : cpu] == b"cpuRegs".ljust(32, b"\0"), "CPU tag")
        receipt = capture["receipt"]
        identical(receipt["crc"], word(internals, 292))
        identical(receipt["pc"], word(internals, cpu + 680))
        check(word(internals, cpu + 676) == 0, "CPU delay")
        identical(receipt["delay"], False)
        identical(receipt["cycle"], word(internals, cpu + 1088, 8))
        identical(receipt["gpr"], [word(internals, cpu + r * 16) for r in range(32)])
        ram = member("eeMemory.bin", 33554432)
        check(len(ram) == 33554432, "RAM size")
        for name, address, size in RANGES:
            check(
                files[f"capture-{capture['slot']:02d}-{name}"] == ram[address : address + size],
                "source block bytes",
            )


def compare_sources(files, read_source):
    """read_source(name) is injected; no filenames from the intermediate are opened.

    Names: inventory.json, {collision,alternatives,continuity}.json and
    state-N.p2s/receipt-N.json. One archive is consumed before requesting another.
    """
    summary = inspect_package(files)
    root = load(files["intermediate.json"])
    for name in ("collision", "alternatives", "continuity"):
        raw = read_source(name + ".json")
        identical(root["provenance"]["source_reports"][name], fingerprint(raw))
        identical(root["documents"][name + "_reference"], load(raw))
    raw = read_source("inventory.json")
    identical(root["provenance"]["inventory_sha256"], fingerprint(raw)["sha256"])
    inventory = load(raw)
    identical([s["slot"] for s in inventory["samples"]], SLOTS)
    for capture, sample in zip(root["captures"], inventory["samples"], strict=True):
        slot = capture["slot"]
        raw = read_source(f"receipt-{slot}.json")
        identical(capture["receipt_source"], fingerprint(raw))
        identical(capture["receipt"], load(raw))
        identical(capture["state"], dict(size=sample["state_size"], sha256=sample["state_sha256"]))
        identical(
            capture["receipt_source"],
            dict(size=sample["receipt_size"], sha256=sample["receipt_sha256"]),
        )
        identical(capture["phase"], sample["phase"])
        identical(
            sample["raw_ranges"],
            [
                {**e, "file": name}
                for e, (name, _, _) in zip(capture["ranges"], RANGES, strict=True)
            ],
        )
        _compare_state(files, capture, read_source(f"state-{slot}.p2s"))
    return {**summary, "source_reports": 3, "source_receipts": 30, "source_states": 30}
