"""IR-T7c fixtures contain only constructed bytes, independent of game files."""

import copy
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from tools.pipeline.collision_registry import (
    REGISTRY_RANGES,
    CollisionRegistryError,
    decode_registry,
)

# Deliberately spelled out from the contract, not from decoder constants.
LAYOUT = {
    "character.bin": (0x01D05FE0, 18444),
    "world.bin": (0x01D04560, 140),
    "events.bin": (0x01D000F0, 8192),
    "event-count.bin": (0x01D02130, 4),
    "actors.bin": (0x004481D0, 25600),
    "actor-head.bin": (0x0044E5D4, 4),
    "stage.bin": (0x01CFB851, 1),
    "room.bin": (0x01CB5770, 4),
}


def word(ranges, name, offset, value):
    raw = bytearray(ranges[name])
    struct.pack_into("<I", raw, offset, value)
    ranges[name] = bytes(raw)


def put_actor(ranges, slot, previous, following, kind=0x209, instance=398):
    raw = bytearray(ranges["actors.bin"])
    base = slot * 800
    struct.pack_into("<I", raw, base + 4, 0x80000001)
    struct.pack_into("<HH", raw, base + 12, kind, instance)
    struct.pack_into("<I", raw, base + 160, 0xFEDCBA98)
    struct.pack_into("<II", raw, base + 184, previous, following)
    ranges["actors.bin"] = bytes(raw)


def put_character(ranges, bank, index, owner, presence, callback):
    raw = bytearray(ranges["character.bin"])
    offset = bank * 9216 + index * 288
    struct.pack_into("<I", raw, offset + 96, owner)
    struct.pack_into("<2H", raw, offset + 272, *presence)
    struct.pack_into("<I", raw, offset + 284, callback)
    ranges["character.bin"] = bytes(raw)


def blank():
    # Nonzero residual bytes, including patterns that could represent NaNs.
    ranges = {k: (b"\xff\xff\xc0\x7f" * ((n + 3) // 4))[:n] for k, (_, n) in LAYOUT.items()}
    ranges["stage.bin"] = b"\x23"
    for name, offset, value in (
        ("room.bin", 0, 0xEB),
        ("actor-head.bin", 0, 0),
        ("event-count.bin", 0, 0),
        ("character.bin", 18432, 0),
        ("character.bin", 18436, 0),
        ("character.bin", 18440, 0),
        ("world.bin", 0, 0),
        ("world.bin", 68, 0),
        ("world.bin", 136, 0),
    ):
        word(ranges, name, offset, value)
    return ranges


@pytest.fixture
def sample():
    ranges = blank()
    first, second = 0x00448B30, 0x004481D0
    word(ranges, "actor-head.bin", 0, first)
    put_actor(ranges, 3, 0, second, kind=0x20C, instance=1012)
    put_actor(ranges, 0, first, 0)
    for offset, value in ((18432, 2), (18436, 1), (18440, 1)):
        word(ranges, "character.bin", offset, value)
    put_character(ranges, 0, 0, first, [0, 65535], 0xDEADBEEF)
    put_character(ranges, 0, 1, first, [3, 7], 0xA1B2C3D4)
    put_character(ranges, 1, 0, second, [1, 0], 0x01020304)
    for offset, value in (
        (0, 3),
        (4, 0x1000),
        (8, 0x1000),
        (12, 0x01FFFFB0),
        (68, 2),
        (72, 1),
        (76, second),
        (136, 0),
    ):
        word(ranges, "world.bin", offset, value)
    return ranges


def test_known_values_order_duplicate_owners_and_world_pointer_separation(sample):
    before = sample.copy()
    value = decode_registry(sample)
    assert value == {
        "stage": 35,
        "room": 235,
        "actors": [
            {
                "address": 0x00448B30,
                "status": 0x80000001,
                "kind": 524,
                "instance": 1012,
                "function": 0xFEDCBA98,
            },
            {
                "address": 0x004481D0,
                "status": 0x80000001,
                "kind": 521,
                "instance": 398,
                "function": 0xFEDCBA98,
            },
        ],
        "character": {
            "selector": 1,
            "counts": [2, 1],
            "banks": [
                [
                    {
                        "index": 0,
                        "record": 0x01D05FE0,
                        "owner": 0x00448B30,
                        "kind": 524,
                        "instance": 1012,
                        "presence_words": [0, 65535],
                        "callback": 0xDEADBEEF,
                    },
                    {
                        "index": 1,
                        "record": 0x01D06100,
                        "owner": 0x00448B30,
                        "kind": 524,
                        "instance": 1012,
                        "presence_words": [3, 7],
                        "callback": 0xA1B2C3D4,
                    },
                ],
                [
                    {
                        "index": 0,
                        "record": 0x01D083E0,
                        "owner": 0x004481D0,
                        "kind": 521,
                        "instance": 398,
                        "presence_words": [1, 0],
                        "callback": 0x01020304,
                    }
                ],
            ],
        },
        "world": {
            "selector": 0,
            "counts": [3, 2],
            "banks": [[4096, 4096, 33554352], [1, 0x004481D0]],
        },
        "events": {"count": 0, "entries": []},
    }
    assert sample == before
    assert all(sample[k] is before[k] for k in sample)
    assert json.loads(json.dumps(value, allow_nan=False)) == value
    assert type(value["character"]["banks"][0][0]["presence_words"][0]) is int
    # Outputs own their collections; callers cannot change input or later decodes through them.
    expected = copy.deepcopy(value)
    value["character"]["counts"][0] = 9
    value["character"]["banks"][0][0]["presence_words"][0] = 8
    value["actors"][0]["kind"] = 1
    value["world"]["banks"][0].clear()
    assert decode_registry(sample) == expected


@pytest.mark.parametrize("room", [0xEA, 0xEB])
def test_empty_registries_keep_residual_bytes_opaque(room):
    ranges = blank()
    word(ranges, "room.bin", 0, room)
    before = ranges.copy()
    assert decode_registry(ranges) == dict(
        stage=0x23,
        room=room,
        actors=[],
        character=dict(selector=0, counts=[0, 0], banks=[[], []]),
        world=dict(selector=0, counts=[0, 0], banks=[[], []]),
        events=dict(count=0, entries=[]),
    )
    assert ranges == before and any(ranges["events.bin"])


@pytest.mark.parametrize("count", [1, 32])
@pytest.mark.parametrize("selector", [0, 1])
def test_actor_and_bank_capacities_accept_endpoints(count, selector):
    ranges = blank()
    # Reverse pool order, including the final slot; same kind/instance must not merge actors.
    slots = list(reversed(range(32)))[:count]
    addresses = [0x4481D0 + slot * 800 for slot in slots]
    word(ranges, "actor-head.bin", 0, addresses[0])
    for i, slot in enumerate(slots):
        put_actor(
            ranges,
            slot,
            addresses[i - 1] if i else 0,
            addresses[i + 1] if i + 1 < count else 0,
            kind=65535,
            instance=65535,
        )
    for bank in range(2):
        word(ranges, "character.bin", 18432 + bank * 4, count)
        word(ranges, "world.bin", bank * 68, 16)
        for i, owner in enumerate(addresses):
            put_character(ranges, bank, i, owner, [65535, 65534], 0xFFFFFFFF)
        for i in range(16):
            word(ranges, "world.bin", bank * 68 + 4 + i * 4, 0x1000 + i)
    word(ranges, "character.bin", 18440, selector)
    word(ranges, "world.bin", 136, selector)
    value = decode_registry(ranges)
    assert [a["address"] for a in value["actors"]] == addresses
    assert value["character"]["counts"] == [count, count]
    assert value["world"]["counts"] == [16, 16]
    for bank in value["character"]["banks"]:
        assert [r["owner"] for r in bank] == addresses
        assert all(r["presence_words"] == [65535, 65534] for r in bank)
    assert value["world"]["banks"] == [list(range(4096, 4112))] * 2
    assert value["character"]["selector"] == value["world"]["selector"] == selector


def test_opaque_byte_changes_do_not_change_observation(sample):
    baseline = decode_registry(sample)
    mutated = sample.copy()
    # Actor body, inactive actor, opaque character field, inactive bank entry,
    # unused world pointer and event storage; all are preserved by the caller.
    for name, offset in (
        ("actors.bin", 3 * 800 + 0x19C),
        ("actors.bin", 800),
        ("character.bin", 0),
        ("character.bin", 2 * 288 + 96),
        ("world.bin", 4 + 3 * 4),
        ("events.bin", 0),
    ):
        word(mutated, name, offset, 0xFFFFFFFF)
    assert decode_registry(mutated) == baseline
    assert mutated != sample
    assert decode_registry(sample) == baseline


def test_contract_ranges_are_immutable_and_exact():
    assert dict(REGISTRY_RANGES) == LAYOUT
    assert sum(n for _, n in REGISTRY_RANGES.values()) == 52389
    with pytest.raises(TypeError):
        REGISTRY_RANGES["world.bin"] = (0, 0)


@pytest.mark.parametrize("bad", [None, [], (), True, "ranges", 8])
def test_rejects_wrong_container(bad):
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(bad)
    assert error.value.code == str(error.value) == "CR_RANGES"


@pytest.mark.parametrize("change", ["missing", "extra", "alias", "integer_key"])
def test_rejects_inventory(sample, change):
    if change == "missing":
        del sample["events.bin"]
    elif change == "extra":
        sample["unknown.bin"] = b"x"
    else:
        raw = sample.pop("events.bin")
        sample["../events.bin" if change == "alias" else 1] = raw
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_RANGES"


@pytest.mark.parametrize("name", LAYOUT)
@pytest.mark.parametrize("change", ["short", "long", "mutable"])
def test_rejects_each_range_before_unpacking(sample, name, change):
    raw = sample[name]
    sample[name] = (
        raw[:-1] if change == "short" else (raw + b"x" if change == "long" else bytearray(raw))
    )
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == ("CR_RANGE_TYPE" if change == "mutable" else "CR_RANGE_SIZE")


@pytest.mark.parametrize("bad", [None, True, 4, "bytes", [0, 0, 0, 0], memoryview(bytes(4))])
def test_rejects_implicit_byte_coercion(sample, bad):
    sample["event-count.bin"] = bad
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_RANGE_TYPE"


@pytest.mark.parametrize("bank", [0, 1])
@pytest.mark.parametrize("value", [33, 0xFFFFFFFF])
def test_rejects_character_counts_in_both_banks(sample, bank, value):
    word(sample, "character.bin", 18432 + bank * 4, value)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_CHARACTER_COUNT"


@pytest.mark.parametrize("bank", [0, 1])
@pytest.mark.parametrize("value", [17, 0xFFFFFFFF])
def test_rejects_world_counts_in_both_banks(sample, bank, value):
    word(sample, "world.bin", bank * 68, value)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_WORLD_COUNT"


@pytest.mark.parametrize(
    "name,offset,code",
    [
        ("character.bin", 18440, "CR_CHARACTER_SELECTOR"),
        ("world.bin", 136, "CR_WORLD_SELECTOR"),
    ],
)
@pytest.mark.parametrize("value", [2, 0xFFFFFFFF])
def test_rejects_selectors(sample, name, offset, code, value):
    word(sample, name, offset, value)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == code


@pytest.mark.parametrize("name,offset", [("actor-head.bin", 0), ("actors.bin", 3 * 800 + 188)])
@pytest.mark.parametrize("value", [0x4481CF, 0x4481D4, 0x44E5D0, 0xFFFFFFFF])
def test_rejects_actor_links_outside_or_misaligned(sample, name, offset, value):
    word(sample, name, offset, value)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_ACTOR_ADDRESS"


@pytest.mark.parametrize("offset", [184, 3 * 800 + 184])
def test_rejects_previous_link_inconsistency(sample, offset):
    word(sample, "actors.bin", offset, 1)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_ACTOR_PREVIOUS"


@pytest.mark.parametrize("offset,value", [(3 * 800 + 188, 0x448B30), (188, 0x448B30)])
def test_rejects_self_or_multi_actor_cycles(sample, offset, value):
    word(sample, "actors.bin", offset, value)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_ACTOR_CYCLE"


@pytest.mark.parametrize("bank", [0, 1])
@pytest.mark.parametrize("value", [0, 0x4481D4, 0x4484F0, 0xFFFFFFFF])
def test_rejects_unlinked_owner_even_inside_actor_pool(sample, bank, value):
    word(sample, "character.bin", bank * 9216 + 96, value)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_CHARACTER_OWNER"


@pytest.mark.parametrize("bank", [0, 1])
@pytest.mark.parametrize("value", [0, 0x01FFFFB1, 0xFFFFFFFF])
def test_rejects_world_pointer_bounds_in_both_banks(sample, bank, value):
    word(sample, "world.bin", bank * 68 + 4, value)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_WORLD_POINTER"


@pytest.mark.parametrize(
    "value,code",
    [
        (1, "CR_EVENTS_UNSUPPORTED"),
        (128, "CR_EVENTS_UNSUPPORTED"),
        (129, "CR_EVENT_COUNT"),
        (0xFFFFFFFF, "CR_EVENT_COUNT"),
    ],
)
def test_rejects_nonempty_queue_distinct_from_invalid_count(sample, value, code):
    word(sample, "event-count.bin", 0, value)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == code


@pytest.mark.parametrize("stage", [0, 0x24, 255])
def test_rejects_wrong_stage(sample, stage):
    sample["stage.bin"] = bytes([stage])
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_STAGE"


@pytest.mark.parametrize("room", [0, 0xE9, 0xEC, 0xFFFFFFFF])
def test_rejects_wrong_room(sample, room):
    word(sample, "room.bin", 0, room)
    with pytest.raises(CollisionRegistryError) as error:
        decode_registry(sample)
    assert error.value.code == "CR_ROOM"


@pytest.mark.parametrize(
    "name,offset,value,code",
    [
        ("character.bin", 18436, 33, "CR_CHARACTER_COUNT"),
        ("event-count.bin", 0, 1, "CR_EVENTS_UNSUPPORTED"),
    ],
)
def test_validation_remains_enabled_under_python_optimization(sample, name, offset, value, code):
    word(sample, name, offset, value)
    script = """
import json, sys
from tools.pipeline.collision_registry import CollisionRegistryError, decode_registry
ranges = {k: bytes.fromhex(v) for k,v in json.load(sys.stdin).items()}
try:
    decode_registry(ranges)
except CollisionRegistryError as error:
    print(error.code)
else:
    raise SystemExit(1)
"""
    result = subprocess.run(
        [sys.executable, "-O", "-c", script],
        input=json.dumps({k: v.hex() for k, v in sample.items()}),
        capture_output=True,
        text=True,
        timeout=10,
        cwd=Path(__file__).resolve().parents[2],
        check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == code, result.stderr
