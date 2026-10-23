"""IR19/23/24: pure linkage of collision observations and historical evidence."""

from collections import Counter

from tools.pipeline.intermediate_assets import digest, fields
from tools.pipeline.intermediate_json import encode_json

SLOTS = (2, *range(8, 36), 36)
REPORTS = ("collision", "alternatives", "continuity")
IDENTITY = dict(
    profile_id="ps2-sles-51434-9a94b95e777dae42",
    crc=0x5088CCDB,
    elf_sha256="cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789",
    overlay_sha256="414142dad62fefc1cbd0d6684c05ba5d3331dd445949a11e5301470250683bde",
)
REPORT_LIMIT = 1024 * 1024
RECEIPT_LIMIT = 16384
STATE_LIMIT = 64 * 1024 * 1024


def require(condition):
    if not condition:
        raise ValueError("Collision evidence differs")


def equal(actual, expected):
    # Python equality alone accepts True == 1, 1.0 == 1 and -0.0 == 0.0.
    require(encode_json(actual) == encode_json(expected))


def integer(value, low, high):
    require(type(value) is int and low <= value <= high)
    return value


def pick(value, keys):
    require(type(value) is dict and all(k in value for k in keys))
    return {k: value[k] for k in keys}


def ordered(rows, slots):
    require(type(rows) is list and len(rows) == len(slots))
    equal([pick(row, ("slot",))["slot"] for row in rows], list(slots))


def phase(slot):
    return (
        "control_puzzle"
        if slot == 2
        else ("restored_diagnostic" if slot == 36 else "continuous_post_phase")
    )


def pin(entry, limit):
    fields(entry, ("size", "sha256"))
    integer(entry["size"], 1, limit)
    digest(entry["sha256"])


def no_host_paths(value):
    if type(value) is dict:
        for key, item in value.items():
            no_host_paths(key)
            no_host_paths(item)
    elif type(value) is list:
        for item in value:
            no_host_paths(item)
    elif type(value) is str:
        require(not value.startswith(("/", "\\", "file:")))
        require(not (len(value) > 2 and value[1] == ":" and value[2] in "/\\"))


def validate_references(documents, provenance):
    fields(documents, (key + "_reference" for key in REPORTS))
    fields(provenance, ("source_identity", "source_reports", "inventory_sha256"))
    equal(provenance["source_identity"], IDENTITY)
    digest(provenance["inventory_sha256"])
    sources = provenance["source_reports"]
    fields(sources, REPORTS)
    for source in sources.values():
        pin(source, REPORT_LIMIT)
    collision, alternatives, continuity = [documents[k + "_reference"] for k in REPORTS]
    for doc, schema in zip(
        (collision, alternatives, continuity),
        (
            "sh3-carousel-collision-audit-v1",
            "sh3-carousel-alternative-routes-v1",
            "sh3-animation-continuity-observation-v1",
        ),
        strict=True,
    ):
        equal(pick(doc, ("schema",)), dict(schema=schema))
    for doc in (collision, alternatives):
        equal(
            pick(doc, ("elf_sha256", "overlay_sha256")),
            pick(IDENTITY, ("elf_sha256", "overlay_sha256")),
        )
    equal(collision["continuity_report_sha256"], sources["continuity"]["sha256"])
    equal(alternatives["previous_report_sha256"], sources["collision"]["sha256"])
    equal(
        pick(collision, ("observed_impact", "ai_damage_death_transitions_verified")),
        dict(observed_impact=False, ai_damage_death_transitions_verified=False),
    )
    equal(
        pick(
            alternatives,
            (
                "normal_play_damage_route_identified",
                "runtime_transition_observed",
                "vm_interaction",
            ),
        ),
        dict(
            normal_play_damage_route_identified=False,
            runtime_transition_observed=False,
            vm_interaction=False,
        ),
    )
    equal(
        pick(
            continuity,
            (
                "continuous_loop_verified",
                "natural_initial_selection_verified",
                "ai_damage_death_transitions_verified",
            ),
        ),
        dict(
            continuous_loop_verified=True,
            natural_initial_selection_verified=True,
            ai_damage_death_transitions_verified=False,
        ),
    )
    equal(
        pick(continuity["identity"], ("crc", "overlay_sha256")),
        pick(IDENTITY, ("crc", "overlay_sha256")),
    )
    integer(continuity["identity"]["pid"], 1, 0xFFFFFFFF)
    equal(
        pick(
            continuity["provenance"],
            (
                "fresh_boot",
                "state_restores",
                "guest_writes",
                "segment_start",
                "segment_end",
                "observed_resume_actions",
            ),
        ),
        dict(
            fresh_boot=True,
            state_restores=0,
            guest_writes=False,
            segment_start=8,
            segment_end=35,
            observed_resume_actions=27,
        ),
    )
    ordered(collision["captures"], SLOTS)
    ordered(alternatives["snapshots"], (8, 35, 36))
    ordered(continuity["samples"], range(8, 36))
    return collision, alternatives, continuity


def validate_receipt(capture, identity):
    receipt, slot = capture["receipt"], capture["slot"]
    equal(capture["phase"], phase(slot))
    pin(capture["state"], STATE_LIMIT)
    pin(capture["receipt_source"], RECEIPT_LIMIT)
    equal(
        pick(
            receipt,
            (
                "slot",
                "crc",
                "pid",
                "state_sha256",
                "delay",
                "guest_writes",
                "diagnostic_replay",
                "fresh_boot",
                "state_restores",
                "stage_selector",
            ),
        ),
        dict(
            slot=slot,
            crc=IDENTITY["crc"],
            pid=identity["pid"],
            state_sha256=capture["state"]["sha256"],
            delay=False,
            guest_writes=False,
            diagnostic_replay=slot == 36,
            fresh_boot=slot != 36,
            state_restores=int(slot == 36),
            stage_selector=0x23,
        ),
    )
    integer(receipt["pc"], 0, 0xFFFFFFFF)
    integer(receipt["cycle"], 0, (1 << 64) - 1)
    require(type(receipt["gpr"]) is list and len(receipt["gpr"]) == 32)
    for value in receipt["gpr"]:
        integer(value, 0, 0xFFFFFFFF)


def validate_phase(observation, slot, reference, geometry):
    control = slot == 2
    equal(observation["room"], 0xEA if control else 0xEB)
    equal(observation["character"]["counts"], [23, 23] if control else [2, 2])
    equal(observation["world"]["counts"], [1, 1] if control else [12, 12])
    equal(len(observation["actors"]), 26 if control else 30)
    equal(observation["character"]["selector"], reference["active"])
    equal(observation["world"]["selector"], reference["world_active"])
    equal(observation["world"]["banks"], reference["world_banks"])
    equal(observation["events"]["entries"], reference["events"])
    projected = [
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
    equal(projected, reference["character_banks"])
    target_kind = 0x20C if control else 0x209
    targets = [a for a in observation["actors"] if a["kind"] == target_kind]
    equal(len(targets), 11 if control else 3)
    keys = ("address", "status", "kind", "instance", "function")
    require(type(reference["targets"]) is list)
    # Historical targets include the old puzzle actors still in the active list.
    # Their presence is separate from ownership in the character registry.
    equal(
        [a for a in observation["actors"] if a["kind"] in (0x20C, 0x209)],
        [pick(t, keys) for t in reference["targets"]],
    )
    for bank in observation["character"]["banks"]:
        expected = {0x100: 1, 0x20C: 22} if control else {0x100: 1, 0x215: 1}
        require(Counter(r["kind"] for r in bank) == expected)
        if control:
            require(
                Counter(r["owner"] for r in bank if r["kind"] == 0x20C)
                == {t["address"]: 2 for t in targets}
            )
    if not control:
        equal(sorted(t["instance"] for t in targets), [0x18E, 0x18F, 0x190])
        require(type(geometry) is list and len(geometry) == 3)
        equal(sorted(g["instance"] for g in geometry), [0x18E, 0x18F, 0x190])
        for g in geometry:
            index = integer(g["index"], 0, 11)
            equal(g["banks"], [bank[index] for bank in observation["world"]["banks"]])


def validate_capture_links(captures, documents, provenance):
    collision, alternatives, continuity = validate_references(documents, provenance)
    ordered(captures, SLOTS)
    require(len({c["state"]["sha256"] for c in captures}) == len(SLOTS))
    previous_cycle = -1
    for capture, ref in zip(captures, collision["captures"], strict=True):
        validate_receipt(capture, continuity["identity"])
        receipt, slot = capture["receipt"], capture["slot"]
        equal(
            pick(ref, ("slot", "sha256", "cycle", "pc", "diagnostic_replay", "state_restores")),
            dict(
                slot=slot,
                sha256=capture["state"]["sha256"],
                **pick(receipt, ("cycle", "pc", "diagnostic_replay", "state_restores")),
            ),
        )
        validate_phase(capture["observations"], slot, ref, collision["actor_world_geometry"])
        if 8 <= slot <= 35:
            sample = continuity["samples"][slot - 8]
            equal(sample["sha256"], capture["state"]["sha256"])
            equal(sample["sample"]["cycle"], receipt["cycle"])
            require(receipt["cycle"] > previous_cycle)
            previous_cycle = receipt["cycle"]
            actor = continuity["identity"]["actor"]
            matches = [
                a for a in capture["observations"]["actors"] if a["address"] == actor["address"]
            ]
            equal(matches, [actor])
        for snapshot in alternatives["snapshots"]:
            if snapshot["slot"] == slot:
                equal(
                    pick(snapshot, ("sha256", "diagnostic_replay")),
                    dict(sha256=capture["state"]["sha256"], diagnostic_replay=slot == 36),
                )
