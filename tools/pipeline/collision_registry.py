"""IR-T7c: bounded EU collision registries, without I/O or collision response.

The returned observation is a derived view, not a lossless replacement for
the eight input buffers. Callers retain those immutable buffers for IR-T7d.
World pointers and callbacks remain guest integers and are never followed.
"""

import struct
from types import MappingProxyType

RECIPE = "ps2-eu-collision-registry-v1"
REGISTRY_RANGES = MappingProxyType(
    {
        "character.bin": (0x01D05FE0, 0x480C),
        "world.bin": (0x01D04560, 0x8C),
        "events.bin": (0x01D000F0, 0x2000),
        "event-count.bin": (0x01D02130, 4),
        "actors.bin": (0x004481D0, 0x6400),
        "actor-head.bin": (0x0044E5D4, 4),
        "stage.bin": (0x01CFB851, 1),
        "room.bin": (0x01CB5770, 4),
    }
)
_ACTOR_STRIDE = 0x320
_CHARACTER_STRIDE = 0x120
_CHARACTER_BANK_SIZE = 0x2400
_WORLD_BANK_SIZE = 0x44
_RAM_SIZE = 32 * 1024 * 1024


class CollisionRegistryError(ValueError):
    """Stable rejection code; no guest values or payloads in the message."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _u32(raw: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<I", raw, offset)[0]


def _validate_ranges(ranges: dict[str, bytes]) -> None:
    if (
        type(ranges) is not dict
        or len(ranges) != len(REGISTRY_RANGES)
        or any(type(k) is not str for k in ranges)
        or set(ranges) != set(REGISTRY_RANGES)
    ):
        raise CollisionRegistryError("CR_RANGES")
    for name, (_, size) in REGISTRY_RANGES.items():
        raw = ranges[name]
        if type(raw) is not bytes:
            raise CollisionRegistryError("CR_RANGE_TYPE")
        if len(raw) != size:
            raise CollisionRegistryError("CR_RANGE_SIZE")


def _actors(pool: bytes, current: int) -> list[dict]:
    base, size = REGISTRY_RANGES["actors.bin"]
    previous, seen, rows = 0, set(), []
    while current:
        offset = current - base
        if not 0 <= offset < size or offset % _ACTOR_STRIDE:
            raise CollisionRegistryError("CR_ACTOR_ADDRESS")
        if current in seen:
            raise CollisionRegistryError("CR_ACTOR_CYCLE")
        if _u32(pool, offset + 0xB8) != previous:
            raise CollisionRegistryError("CR_ACTOR_PREVIOUS")
        seen.add(current)
        kind, instance = struct.unpack_from("<HH", pool, offset + 0xC)
        rows.append(
            dict(
                address=current,
                status=_u32(pool, offset + 4),
                kind=kind,
                instance=instance,
                function=_u32(pool, offset + 0xA0),
            )
        )
        previous, current = current, _u32(pool, offset + 0xBC)
    return rows


def _characters(raw: bytes, actors: list[dict]) -> dict:
    counts = list(struct.unpack_from("<2I", raw, 2 * _CHARACTER_BANK_SIZE))
    selector = _u32(raw, 2 * _CHARACTER_BANK_SIZE + 8)
    if any(count > 32 for count in counts):
        raise CollisionRegistryError("CR_CHARACTER_COUNT")
    if selector not in (0, 1):
        raise CollisionRegistryError("CR_CHARACTER_SELECTOR")
    by_address = {actor["address"]: actor for actor in actors}
    banks = []
    for bank, count in enumerate(counts):
        rows = []
        for index in range(count):
            offset = bank * _CHARACTER_BANK_SIZE + index * _CHARACTER_STRIDE
            owner = _u32(raw, offset + 0x60)
            if owner not in by_address:
                raise CollisionRegistryError("CR_CHARACTER_OWNER")
            actor = by_address[owner]
            rows.append(
                dict(
                    index=index,
                    record=REGISTRY_RANGES["character.bin"][0] + offset,
                    owner=owner,
                    kind=actor["kind"],
                    instance=actor["instance"],
                    presence_words=list(struct.unpack_from("<2H", raw, offset + 0x110)),
                    callback=_u32(raw, offset + 0x11C),
                )
            )
        banks.append(rows)
    return dict(selector=selector, counts=counts, banks=banks)


def _world(raw: bytes) -> dict:
    counts = [_u32(raw, bank * _WORLD_BANK_SIZE) for bank in range(2)]
    selector = _u32(raw, 2 * _WORLD_BANK_SIZE)
    if any(count > 16 for count in counts):
        raise CollisionRegistryError("CR_WORLD_COUNT")
    if selector not in (0, 1):
        raise CollisionRegistryError("CR_WORLD_SELECTOR")
    banks = []
    for bank, count in enumerate(counts):
        pointers = list(struct.unpack_from(f"<{count}I", raw, bank * _WORLD_BANK_SIZE + 4))
        # Historical audit lookahead bounds, not a decoded geometry record size.
        if any(not 0 < pointer <= _RAM_SIZE - 0x50 for pointer in pointers):
            raise CollisionRegistryError("CR_WORLD_POINTER")
        banks.append(pointers)
    return dict(selector=selector, counts=counts, banks=banks)


def decode_registry(ranges: dict[str, bytes]) -> dict:
    """Decode exactly eight immutable ranges; leave all opaque bytes untouched.

    Stage/room establish only structural scope. Capture identity, provenance,
    hashes, phase-specific counts and reference matching belong to IR-T7d.
    """
    _validate_ranges(ranges)
    stage, room = ranges["stage.bin"][0], _u32(ranges["room.bin"])
    if stage != 0x23:
        raise CollisionRegistryError("CR_STAGE")
    if room not in (0xEA, 0xEB):
        raise CollisionRegistryError("CR_ROOM")
    event_count = _u32(ranges["event-count.bin"])
    if event_count > 128:
        raise CollisionRegistryError("CR_EVENT_COUNT")
    if event_count:
        raise CollisionRegistryError("CR_EVENTS_UNSUPPORTED")
    actors = _actors(ranges["actors.bin"], _u32(ranges["actor-head.bin"]))
    return dict(
        stage=stage,
        room=room,
        actors=actors,
        character=_characters(ranges["character.bin"], actors),
        world=_world(ranges["world.bin"]),
        events=dict(count=0, entries=[]),
    )
