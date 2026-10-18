"""Own opening and transfer fixtures, including indistinguishable ABA endpoints."""

import json
import struct
from dataclasses import replace

import pytest
from test_driver_transfer import OBJECT, PAYLOAD, POOL, PROFILE, REQUEST, ROOT, SP
from test_driver_transfer import pause as transfer_pause
from test_observer_acquisition import CYCLE, rejects

from tools.inspectors.catalog_open import CatalogSource, CodeWindow, OpenProfile
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.open_driver import reconcile_open_driver

SOURCE = CatalogSource(
    "a" * 64, "b" * 64, REQUEST.resource_sha256, b"OWN/PACK.DAT", b"own.bin", 65536, 8192, 32
)
code = bytearray(32)
struct.pack_into("<II", code, 8, 3 << 26 | (0x150000 >> 2), 18 << 21 | 5 << 11 | 0x2D)
OPENING = OpenProfile(
    CodeWindow(0x130000, bytes(32)),
    CodeWindow(0x140000, bytes(code)),
    0x130004,
    0x140008,
    0x14001C,
    0x150000,
    0x170000,
    1,
    0,
)
DESCRIPTOR = 0x260000


def opening_pause(**changes):
    defaults = {
        "row": ((8, 0),),
        "values": (
            ("dispatch", OPENING.wrapper.data),
            ("reader", b"cdrom0:/own/pack.dat\0"),
            ("destination", struct.pack("<4I", 0xFFFFFFFE, 1, 0, 0)),
            ("args", struct.pack("<II", SOURCE.offset, SOURCE.size)),
        ),
        "addresses": (
            ("dispatch", OPENING.wrapper.address),
            ("reader", SP + 80),
            ("destination", DESCRIPTOR),
            ("args", SP + 600),
        ),
        "registers": (
            (2, REQUEST.handle),
            (16, 0),
            (17, DESCRIPTOR),
            (18, 1),
            (31, OPENING.open_pc + 8),
        ),
        "pc": OPENING.open_pc + 8,
        "slot": 1,
        "sequence": 1,
        "cycle": CYCLE,
    }
    for key, value in changes.items():
        defaults[key] = defaults[key] + value if isinstance(defaults.get(key), tuple) else value
    labels = {"dispatch": "code", "reader": "path", "destination": "descriptor", "args": "range"}
    return tuple(
        replace(p, label=labels.get(p.label, p.label)) for p in transfer_pause(0, **defaults)
    )


def pair(**changes):
    return tuple(transfer_pause(i, slot=i + 2, sequence=9 + 8 * i, **changes) for i in range(2))


def run(*, stages=None, **kwargs):
    options = dict(
        source=SOURCE,
        opening=OPENING,
        request=REQUEST,
        driver=PROFILE,
        stages=(opening_pause(), *pair()) if stages is None else stages,
        require_continuity=False,
    )
    options.update(kwargs)
    return reconcile_open_driver(**options)


def test_diagnostic_is_deterministic_minimal_and_not_provenance():
    result = run()
    assert result == run()
    assert len(result["points"]) == 24
    assert result["opening_result_and_driver_consistent"]
    assert result["driver_generation_matches_at_endpoints"]
    assert result["read_events_produced"] == 0
    assert result["resource_links"] == result["capabilities"] == []
    for key in (
        "catalog_selection_reconciled",
        "continuous_lifetime_verified",
        "file_identity_verified",
        "cache_origin_verified",
        "disk_read_verified",
        "live_acquisition_verified",
        "source_anchor_reverified",
        "profile_semantics_authenticated",
        "inner_route_verified",
    ):
        assert result[key] is False
    raw = json.dumps(result)
    for private in ("handle", "pc", "pid", "address", "path", "words", "registers"):
        assert f'"{private}":' not in raw
    assert "own/pack.dat" not in raw


def test_default_rejects_lifetime_even_when_endpoints_match():
    # No evidence of the interval is supplied; a reset/restore/ABA can have the same endpoints.
    with rejects("OPEN_DRIVER_LIFETIME_UNPROVEN"):
        reconcile_open_driver(SOURCE, OPENING, REQUEST, PROFILE, (opening_pause(), *pair()))
    with rejects("OPEN_DRIVER_LIFETIME_UNPROVEN"):
        run(require_continuity=True)


@pytest.mark.parametrize("value", [None, 0, 1, "false"])
def test_policy_has_no_truthiness_bypass(value):
    with rejects("OPEN_DRIVER_POLICY"):
        run(require_continuity=value)


@pytest.mark.parametrize(
    "field,value",
    [("file_size", 65537), ("offset", 8193), ("size", 31), ("resource_sha256", "d" * 64)],
)
def test_source_mismatch(field, value):
    with rejects("OPEN_DRIVER_SOURCE"):
        run(source=replace(SOURCE, **{field: value}))


def test_clamped_request_excluded_and_bad_types_delegated():
    request = replace(REQUEST, file_size=8224, requested=64)
    with rejects("OPEN_DRIVER_SOURCE"):
        run(source=replace(SOURCE, file_size=8224), request=request)
    with rejects("CATALOG_INPUT"):
        run(source=None)
    with rejects("TRANSFER_INPUT"):
        run(driver=None)


@pytest.mark.parametrize("stages", [None, (), [], ((),), ((), (), (), ())])
def test_stage_shape(stages):
    with rejects("OPEN_DRIVER_STAGES"):
        reconcile_open_driver(SOURCE, OPENING, REQUEST, PROFILE, stages, require_continuity=False)


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"pc": OPENING.open_pc + 4}, "OPEN_DRIVER_PC"),
        ({"cycle": CYCLE + 1}, "OPEN_DRIVER_CYCLE"),
        ({"sequence": 2}, "OPEN_DRIVER_IDENTITY"),
        ({"slot": 2}, "OPEN_DRIVER_SLOTS"),
        ({"session": "f" * 32}, "OPEN_DRIVER_IDENTITY"),
        ({"physical": (("object", OBJECT + 4096),)}, "PAUSE_PAGE"),
        ({"physical": (("root", ROOT + 4096),)}, "OPEN_DRIVER_PAGE"),
        ({"addresses": (("root", ROOT + 4),)}, "OPEN_DRIVER_BACKING"),
        ({"pool": ((1, 24),)}, "OPEN_DRIVER_CHANGED"),
        ({"values": (("dispatch", bytes(32)),)}, "OPEN_DRIVER_CODE"),
        ({"addresses": (("dispatch", 0x141000),)}, "OPEN_DRIVER_CODE"),
        ({"values": (("args", bytes(8)),)}, "OPEN_DRIVER_RANGE"),
        ({"values": (("destination", bytes(16)),)}, "OPEN_DRIVER_RESERVATION"),
        ({"values": (("destination", bytes(12)),)}, "OPEN_DRIVER_RESERVATION"),
        ({"row": ((8, 1),)}, "DRIVER_POSITION"),
        ({"row": ((0, 0xFFFFFFFF),)}, "DRIVER_CLOSED_OR_FOREIGN"),
        ({"row": ((4, 5),)}, "DRIVER_GENERATION"),
        ({"row": ((4, 2**31 + 4),)}, "DRIVER_GENERATION"),
        ({"row": ((7, 0),)}, "DRIVER_REFERENCE"),
        ({"row": ((5, 1),)}, "OPEN_DRIVER_INITIAL"),
        ({"row": ((9, 0),)}, "OPEN_DRIVER_INITIAL"),
        ({"row": ((11, 4),)}, "OPEN_DRIVER_INITIAL"),
        ({"row": ((7, 0x270000),)}, "OPEN_DRIVER_OBJECT_CHANGED"),
        ({"row": ((10, 0x280000),)}, "OPEN_DRIVER_OBJECT_CHANGED"),
        ({"row": ((3, 6),)}, "OPEN_DRIVER_OBJECT_CHANGED"),
    ],
)
def test_open_witness_rejections(changes, error):
    with rejects(error):
        run(stages=(opening_pause(**changes), *pair()))


@pytest.mark.parametrize(
    "reg,value",
    [
        (2, 0xFFFFFFFF),
        (2, 9),
        (16, 1),
        (17, DESCRIPTOR + 16),
        (18, 0),
        (29, SP + 1),
        (29, SP + 16),
        (31, OPENING.open_pc + 4),
    ],
)
def test_open_abi(reg, value):
    with rejects("OPEN_DRIVER_ABI"):
        run(stages=(opening_pause(registers=((reg, value),)), *pair()))


@pytest.mark.parametrize(
    "path",
    [
        b"cdrom0:/own/else.dat\0",
        b"host:/own/pack.dat\0",
        b"cdrom0:/own/pack.dat",
        b"cdrom0:/own/pack.dat\0\0",
        b"cdrom0:/own/../own/pack.dat\0",
    ],
)
def test_path_not_inferred_from_equal_size(path):
    with rejects("OPEN_DRIVER_PATH"):
        run(stages=(opening_pause(values=(("reader", path),)), *pair()))


def test_uppercase_path_and_async_flag_are_consistency_only():
    opened = opening_pause(
        values=(("reader", b"cdrom0:/OWN/PACK.DAT\0"),), row=((5, 1),), registers=((18, 0x2001),)
    )
    result = run(opening=replace(OPENING, flags=0x2001), stages=(opened, *pair(row=((5, 1),))))
    assert result["opening_result_and_driver_consistent"] and not result["inner_route_verified"]


def test_region_order_and_identity():
    points = tuple(replace(p, label="other") if p.label == "code" else p for p in opening_pause())
    with rejects("OPEN_DRIVER_REGIONS"):
        run(stages=(points, *pair()))
    points = tuple(
        replace(p, plan=replace(p.plan, context=replace(p.plan.context, process_sha256="e" * 64)))
        for p in opening_pause()
    )
    with rejects("OPEN_DRIVER_IDENTITY"):
        run(stages=(points, *pair()))


def test_visible_reopen_generation_rejected_even_if_later_pair_is_valid():
    reopened = replace(REQUEST, handle=9)
    later = pair(request=reopened, row=((4, 5),))
    with rejects("OPEN_DRIVER_ABI"):
        run(request=reopened, stages=(opening_pause(), *later))


def test_preexisting_cached_payload_still_cannot_establish_lifetime():
    later = pair(row=((11, 4),), values=(("destination", PAYLOAD),))
    result = run(stages=(opening_pause(), *later))
    assert result["initial_cache_index_matches"] and result["destination_preexisting"]
    with rejects("OPEN_DRIVER_LIFETIME_UNPROVEN"):
        run(stages=(opening_pause(), *later), require_continuity=True)


def test_budget_includes_opening_and_all_three_cycles():
    opened = opening_pause(sequence=233)
    later = tuple(
        transfer_pause(
            i, slot=i + 2, sequence=241 + 8 * i, cycle=CYCLE + 1 if i == 0 else CYCLE + MAX_CYCLES
        )
        for i in range(2)
    )
    result = run(stages=(opened, *later))
    assert result["points"][-1]["sequence"] == 256
    with rejects("MAPPING_CONTEXT"):
        run(
            stages=(
                opening_pause(sequence=234),
                transfer_pause(0, slot=2, sequence=242),
                transfer_pause(1, slot=3, sequence=250),
            )
        )


def test_root_profile_and_transfer_validation_remain_mandatory():
    points = pair(addresses=(("root", ROOT + 4),))
    opened = opening_pause(addresses=(("root", ROOT + 4),))
    with rejects("TRANSFER_ROOT"):
        run(stages=(opened, *points))
    with rejects("TRANSFER_PAYLOAD"):
        run(
            stages=(
                opening_pause(),
                transfer_pause(0, sequence=9, slot=2),
                transfer_pause(1, sequence=17, slot=3, values=(("destination", bytes(32)),)),
            )
        )


def test_pool_pointer_must_not_change():
    with rejects("OPEN_DRIVER_CHANGED"):
        run(stages=(opening_pause(values=(("root", struct.pack("<I", POOL + 16)),)), *pair()))


def test_total_cycle_budget_not_only_transfer_pair_budget():
    later = tuple(
        transfer_pause(i, slot=i + 2, sequence=9 + 8 * i, cycle=CYCLE + MAX_CYCLES + i)
        for i in range(2)
    )
    with rejects("OPEN_DRIVER_CYCLE"):
        run(stages=(opening_pause(), *later))


def test_shared_page_across_different_labels_cannot_remap():
    opened = opening_pause(physical=(("reader", SP + 80 + 4096), ("args", SP + 600 + 4096)))
    with rejects("OPEN_DRIVER_PAGE"):
        run(stages=(opened, *pair()))
