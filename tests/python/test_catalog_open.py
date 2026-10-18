"""Own catalog, code pins, state and wire fixtures; no game code or strings."""

import hashlib
import json
import struct
import zipfile
from dataclasses import replace
from functools import lru_cache

import pytest
from test_observer_acquisition import CYCLE, PLAN, rejects
from test_observer_capture import packed
from test_pcsx2_state import CPU, own_archive, own_internals

from tools.inspectors.catalog_open import (
    CatalogSource,
    CodeWindow,
    OpenProfile,
    reconcile_catalog_open,
)
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.observer_series import SeriesPoint
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE

ROOT, HEAP, CONFIG, TABLE, QUERY, SP = 0x200000, 0x202000, 0x180000, 0x210000, 0x220000, 0x230000
ROW, RECORD = TABLE + 48, ROOT + 48
PREFIX, NAME = b"cdrom0:/own/pack.dat%", b"own.bin"
SOURCE = CatalogSource("a" * 64, "b" * 64, "c" * 64, b"OWN/PACK.DAT", NAME, 65536, 8192, 32)
wrapper = bytearray(424)
struct.pack_into("<II", wrapper, 0xB4, (3 << 26) | (0x120000 >> 2), (18 << 21) | (5 << 11) | 0x2D)
PROFILE = OpenProfile(
    CodeWindow(0x100000, bytes(560)),
    CodeWindow(0x110000, bytes(wrapper)),
    0x100154,
    0x1100B4,
    0x11018C,
    0x120000,
    CONFIG,
    1,
    0,
)


@lru_cache(maxsize=96)
def pause(
    index,
    *,
    values=(),
    addresses=(),
    registers=(),
    physical=(),
    sequence=None,
    slot=None,
    cycle=None,
    pc=None,
):
    pcs = (PROFILE.selected_pc, PROFILE.open_pc, PROFILE.open_pc + 8, PROFILE.completed_pc)
    pc = pcs[index] if pc is None else pc
    cycle = CYCLE + index + 1 if cycle is None else cycle
    seq = (1, 8, 13, 18)[index] if sequence is None else sequence
    regions = {
        "code": (PROFILE.resolver.address, PROFILE.resolver.data)
        if index == 0
        else (PROFILE.wrapper.address, PROFILE.wrapper.data),
        "config": (CONFIG, struct.pack("<3I", 16, ROOT, TABLE)),
    }
    if index == 0:
        regions.update(
            {
                "directory": (ROOT, struct.pack("<4I", 0x4000, HEAP, 4, 0)),
                "record": (
                    RECORD,
                    struct.pack("<4I", HEAP + 256, HEAP + 512, SOURCE.offset, SOURCE.size),
                ),
                "prefix": (HEAP + 256, PREFIX + b"\0"),
                "name": (HEAP + 512, NAME + b"\0"),
                "request": (QUERY, PREFIX + NAME + b"\0"),
            }
        )
    else:
        row = (7, 2, SOURCE.offset, SOURCE.size) if index == 3 else (0xFFFFFFFE, 1, 12, 24)
        regions.update(
            {
                "descriptor": (ROW, struct.pack("<4I", *row)),
                "path": (SP + 80, PREFIX[:-1] + b"\0"),
                "range": (SP + 600, struct.pack("<2I", SOURCE.offset, SOURCE.size)),
            }
        )
    for label, value in values:
        regions[label] = (regions[label][0], value)
    for label, address in addresses:
        regions[label] = (address, regions[label][1])
    gpr = [0] * 32
    if index == 0:
        for reg, value in {
            9: RECORD,
            16: SP + 80,
            19: 512,
            20: QUERY + len(PREFIX),
            21: QUERY,
            22: SP + 600,
            23: SP + 604,
            29: SP - 176,
        }.items():
            gpr[reg] = value
    else:
        for reg, value in {
            4: SP + 80,
            5: 999,
            6: 0,
            16: 7 if index == 3 else 0,
            17: ROW,
            18: 1,
            19: QUERY,
            29: SP,
            31: pcs[index],
        }.items():
            gpr[reg] = value
        gpr[2] = (0, 0, 7, 35)[index]
    for reg, value in registers:
        gpr[reg] = value
    internal = bytearray(own_internals(pc)).ljust(CPU + 1160, b"\0")
    struct.pack_into("<I", internal, 292, PLAN.crc)
    struct.pack_into("<Q", internal, CPU + 1088, cycle)
    for reg, value in enumerate(gpr):
        struct.pack_into("<I", internal, CPU + 16 * reg, value)
    ram = bytearray(RAM_SIZE)
    backing = dict(physical)
    for label, (virtual, data) in regions.items():
        offset = backing.get(label, virtual)
        ram[offset : offset + len(data)] = data
    raw = own_archive(
        [(VERSION_MEMBER, VERSION), (INTERNALS_MEMBER, bytes(internal)), (RAM_MEMBER, bytes(ram))],
        zipfile.ZIP_DEFLATED,
    )
    points = []
    for i, (label, (virtual, data)) in enumerate(regions.items()):
        request = replace(
            PLAN.request,
            sequence=seq + i,
            expected_pc=pc,
            virtual_start=virtual,
            size=len(data),
            expected_offset=backing.get(label, virtual),
        )
        context = replace(
            PLAN.context, sequence=seq + i, state_sha256=hashlib.sha256(raw).hexdigest()
        )
        plan = replace(
            PLAN, request=request, context=context, slot=index + 1 if slot is None else slot
        )
        packet = bytearray(packed(request))
        for start in (61, 149):
            struct.pack_into("<Q", packet, start + 12, cycle)
        packet[237:] = data
        points.append(SeriesPoint(label, plan, raw, (bytes(packet),) * 3))
    return tuple(points)


def run(source=SOURCE, profile=PROFILE, stages=None):
    return reconcile_catalog_open(
        source, profile, tuple(pause(i) for i in range(4)) if stages is None else stages
    )


def changed(index, **kwargs):
    return tuple(pause(i, **kwargs) if i == index else pause(i) for i in range(4))


def test_complete_supplied_selection_open_and_generation():
    result = run()
    assert result == run() and len(result["points"]) == 22
    assert result["catalog_entry_and_open_consistent"] and result["pinned_code_matches"]
    assert result["resource_size"] == SOURCE.size and result["read_events_produced"] == 0
    assert result["resource_links"] == result["capabilities"] == []
    for key in (
        "source_anchor_reverified",
        "profile_semantics_authenticated",
        "callee_execution_verified",
        "file_identity_verified",
        "driver_object_identified",
        "position_verified",
        "disk_read_verified",
        "live_acquisition_verified",
    ):
        assert result[key] is False
    encoded = json.dumps(result)
    assert all(
        text not in encoded
        for text in ("own.bin", "pack.dat", '"pid":', '"pc":', '"path":', '"token":')
    )
    assert repr(SOURCE) == object.__repr__(SOURCE) and repr(PROFILE) == object.__repr__(PROFILE)


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"source": None}, "CATALOG_INPUT"),
        ({"profile": None}, "CATALOG_INPUT"),
        ({"source": replace(SOURCE, catalog_sha256="A" * 64)}, "CATALOG_HASH"),
        ({"source": replace(SOURCE, container_sha256=None)}, "CATALOG_HASH"),
        ({"source": replace(SOURCE, resource_sha256="bad")}, "CATALOG_HASH"),
        ({"source": replace(SOURCE, file_size=True)}, "CATALOG_RANGE"),
        ({"source": replace(SOURCE, offset=-1)}, "CATALOG_RANGE"),
        ({"source": replace(SOURCE, offset=65536)}, "CATALOG_RANGE"),
        ({"source": replace(SOURCE, size=4097)}, "CATALOG_RANGE"),
        ({"source": replace(SOURCE, size=0)}, "CATALOG_RANGE"),
    ],
)
def test_source_types_hashes_and_ranges(kwargs, error):
    with rejects(error):
        run(**kwargs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("iso_path", "OWN/PACK.DAT"),
        ("iso_path", b"own/pack.dat"),
        ("iso_path", b"../PACK.DAT"),
        ("iso_path", b"A/./PACK.DAT"),
        ("iso_path", b"/PACK.DAT"),
        ("iso_path", b"A//PACK.DAT"),
        ("iso_path", b"A%PACK.DAT"),
        ("iso_path", b"A\0.DAT"),
        ("iso_path", b"A" * 256),
        ("name", None),
        ("name", b""),
        ("name", b".."),
        ("name", b"a/b"),
        ("name", b"x%y"),
        ("name", b"a\nb"),
        ("name", b"x" * 256),
    ],
)
def test_reject_ambiguous_paths(field, value):
    with rejects("CATALOG_PATH"):
        run(source=replace(SOURCE, **{field: value}))


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("resolver", None, "OPEN_CODE"),
        ("wrapper", CodeWindow(0x110001, bytes(wrapper)), "OPEN_CODE"),
        ("resolver", CodeWindow(-4, bytes(560)), "OPEN_CODE"),
        ("resolver", CodeWindow(0x100000, b""), "OPEN_CODE"),
        ("resolver", CodeWindow(0x100000, bytes(13)), "OPEN_CODE"),
        ("resolver", CodeWindow(0x100000, bytes(4100)), "OPEN_CODE"),
        ("selected_pc", True, "OPEN_PC"),
        ("selected_pc", 0x100155, "OPEN_PC"),
        ("completed_pc", 0x1100BC, "OPEN_PC"),
        ("open_pc", 0x1101A4, "OPEN_PC"),
        ("target", -1, "OPEN_TARGET"),
        ("target", 0x120001, "OPEN_ALIGNMENT"),
        ("target", 0x120004, "OPEN_CALL_SHAPE"),
        ("config_address", CONFIG + 1, "OPEN_ALIGNMENT"),
        ("flags", -1, "OPEN_FLAGS"),
        ("mode", True, "OPEN_MODE"),
        ("wrapper", CodeWindow(0x110000, bytes(424)), "OPEN_CALL_SHAPE"),
    ],
)
def test_profile_rejections(field, value, error):
    with rejects(error):
        run(profile=replace(PROFILE, **{field: value}))


@pytest.mark.parametrize("stages", [[], (), ((),), ((),) * 5])
def test_stage_count_and_type(stages):
    with rejects("OPEN_STAGES"):
        run(stages=stages)


@pytest.mark.parametrize(
    "index,kwargs,error",
    [
        (1, {"slot": 1}, "OPEN_SLOTS"),
        (1, {"sequence": 9}, "OPEN_IDENTITY"),
        (1, {"cycle": CYCLE + 1}, "OPEN_CYCLE"),
        (3, {"cycle": CYCLE + MAX_CYCLES + 2}, "OPEN_CYCLE"),
        (0, {"pc": PROFILE.selected_pc + 4}, "OPEN_PC"),
        (0, {"values": (("code", bytes([1]) + bytes(559)),)}, "OPEN_CODE"),
        (0, {"addresses": (("config", CONFIG + 16),)}, "OPEN_CONFIG"),
        (1, {"physical": (("config", CONFIG + 4096),)}, "OPEN_BACKING"),
        (1, {"values": (("config", struct.pack("<3I", 15, ROOT, TABLE)),)}, "OPEN_CHANGED"),
        (0, {"values": (("directory", bytes(15)),)}, "CATALOG_LAYOUT"),
        (
            0,
            {"values": (("directory", struct.pack("<4I", 0x4000, HEAP, 0, 0)),)},
            "CATALOG_DIRECTORY",
        ),
        (
            0,
            {"values": (("directory", struct.pack("<4I", 0x4000, HEAP, 4, 5)),)},
            "CATALOG_DIRECTORY",
        ),
        (
            0,
            {"values": (("directory", struct.pack("<4I", 0x4000, ROOT, 4, 0)),)},
            "CATALOG_DIRECTORY",
        ),
        (0, {"registers": ((9, RECORD + 16),)}, "CATALOG_SELECTION"),
        (0, {"addresses": (("record", ROOT + 16 * 5),)}, "CATALOG_SELECTION"),
        (
            0,
            {
                "values": (
                    (
                        "record",
                        struct.pack("<4I", HEAP + 256, HEAP + 512, SOURCE.offset + 1, SOURCE.size),
                    ),
                )
            },
            "CATALOG_RANGE",
        ),
        (0, {"values": (("prefix", b"cdrom0:/own/evil.dat%\0"),)}, "CATALOG_NAMES"),
        (0, {"values": (("name", b"OWN.bin\0"),)}, "CATALOG_NAMES"),
        (0, {"addresses": (("prefix", HEAP + 257),)}, "CATALOG_STRING_POINTER"),
        (0, {"values": (("request", PREFIX + b"bad.bin\0"),)}, "CATALOG_REQUEST"),
        (0, {"registers": ((20, QUERY),)}, "OPEN_RESOLVER_FRAME"),
        (0, {"registers": ((29, SP - 160),)}, "OPEN_RESOLVER_FRAME"),
        (2, {"registers": ((17, ROW + 16),)}, "OPEN_FRAME"),
        (2, {"registers": ((29, SP + 16),)}, "OPEN_FRAME"),
        (2, {"values": (("path", b"cdrom0:/own/evil.dat\0"),)}, "OPEN_CHANGED"),
        (1, {"registers": ((4, SP),)}, "OPEN_ARGUMENTS"),
        (1, {"registers": ((6, 1),)}, "OPEN_ARGUMENTS"),
        (2, {"registers": ((31, PROFILE.open_pc),)}, "OPEN_ARGUMENTS"),
        (
            2,
            {"values": (("descriptor", struct.pack("<4I", 0xFFFFFFFE, 2, 12, 24)),)},
            "OPEN_CHANGED",
        ),
        (2, {"registers": ((2, 0xFFFFFFFF),)}, "OPEN_RESULT"),
        (3, {"registers": ((16, 8),)}, "OPEN_RESULT"),
        (
            3,
            {"values": (("descriptor", struct.pack("<4I", 8, 2, SOURCE.offset, SOURCE.size)),)},
            "OPEN_GENERATION",
        ),
        (
            3,
            {
                "values": (
                    ("descriptor", struct.pack("<4I", 0xFFFFFFFF, 2, SOURCE.offset, SOURCE.size)),
                )
            },
            "DESCRIPTOR_CLOSED_OR_RESERVED",
        ),
        (3, {"registers": ((2, 19),)}, "DESCRIPTOR_GENERATION"),
        (
            3,
            {"values": (("descriptor", struct.pack("<4I", 7, 2, SOURCE.offset, SOURCE.size - 1)),)},
            "DESCRIPTOR_RANGE",
        ),
    ],
)
def test_capture_rejections(index, kwargs, error):
    with rejects(error):
        run(stages=changed(index, **kwargs))


def test_recycled_generation_with_consistent_final_token_still_rejected():
    with rejects("OPEN_GENERATION"):
        run(
            stages=changed(
                3,
                values=(("descriptor", struct.pack("<4I", 7, 3, SOURCE.offset, SOURCE.size)),),
                registers=((2, 51),),
            )
        )


@pytest.mark.parametrize(
    "label,data,error",
    [
        ("descriptor", struct.pack("<4I", 0xFFFFFFFF, 1, 12, 24), "OPEN_RESERVATION"),
        ("descriptor", bytes(12), "OPEN_BACKING"),
        ("path", b"cdrom0:/own/evil.dat\0", "OPEN_PATH"),
        ("range", struct.pack("<2I", SOURCE.offset + 1, SOURCE.size), "OPEN_RANGE"),
    ],
)
def test_consistent_wrong_values_across_later_pauses(label, data, error):
    with rejects(error):
        run(
            stages=tuple(
                pause(i, values=((label, data),))
                if i and (label != "descriptor" or i < 3)
                else pause(i)
                for i in range(4)
            )
        )


def test_mixed_process_and_wrong_labels():
    stages = list(tuple(pause(i) for i in range(4)))
    stages[2] = tuple(
        replace(p, plan=replace(p.plan, context=replace(p.plan.context, process_sha256="e" * 64)))
        for p in stages[2]
    )
    with rejects("OPEN_IDENTITY"):
        run(stages=tuple(stages))
    stages[2] = tuple(
        replace(p, label="other" if i == 0 else p.label) for i, p in enumerate(pause(2))
    )
    with rejects("OPEN_REGIONS"):
        run(stages=tuple(stages))


def test_last_cycle_and_regional_sequence_boundaries():
    assert run(stages=changed(3, cycle=CYCLE + 1 + MAX_CYCLES))["catalog_entry_and_open_consistent"]
    stages = tuple(pause(i, sequence=(235, 242, 247, 252)[i]) for i in range(4))
    assert run(stages=stages)["points"][-1]["sequence"] == 256
    with pytest.raises(ValueError):
        run(stages=tuple(pause(i, sequence=(236, 243, 248, 253)[i]) for i in range(4)))


def test_same_range_and_name_cannot_bind_another_container():
    with rejects("CATALOG_NAMES"):
        run(source=replace(SOURCE, iso_path=b"OWN/EVIL.DAT"))


def test_supplied_hashes_are_carried_without_pretending_to_reverify_sources():
    result = run(source=replace(SOURCE, container_sha256="d" * 64))
    assert result["container_sha256"] == "d" * 64 and not result["source_anchor_reverified"]


def test_shared_page_translation_cannot_change_between_pauses():
    with rejects("OPEN_PAGE"):
        run(stages=changed(2, physical=(("path", SP + 80 + 4096), ("range", SP + 600 + 4096))))


def test_zero_length_descriptor_config_is_not_inferred_from_cpu():
    stages = tuple(pause(i, values=(("config", bytes(11)),)) for i in range(4))
    with rejects("CATALOG_LAYOUT"):
        run(stages=stages)


def test_catalog_string_pointer_must_belong_to_string_heap():
    data = struct.pack("<4I", 0x4000, HEAP + 257, 4, 0)
    with rejects("CATALOG_STRING_POINTER"):
        run(stages=changed(0, values=(("directory", data),)))


def test_combined_request_must_fit_resolver_buffer():
    with rejects("CATALOG_PATH"):
        run(source=replace(SOURCE, iso_path=b"A" * 255, name=b"b" * 255))
