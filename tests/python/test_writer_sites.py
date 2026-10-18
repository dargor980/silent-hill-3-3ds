"""RW01/02 synthetic MIPS words, never game instructions."""

import json
import struct

import pytest
from test_camera_writer import instruction
from test_observer_acquisition import rejects

from tools.inspectors.writer_sites import discover_sites, site_metadata

START = 0x100000
RETURN = struct.pack("<II", 0x03E00008, 0)
SW = instruction(immediate=0)
CODE = bytes(4) + SW + instruction(4, 1, 2, -2) + SW + RETURN


def test_static_direct_and_conditional_delay_store_loop():
    sites = discover_sites(START, CODE)
    assert [(s.pc, len(s.code)) for s in sites] == [(START + 4, 4), (START + 8, 8)]
    result = site_metadata(START, CODE)
    assert result["site_count"] == 2 and result["direct_count"] == result["delay_pair_count"] == 1
    assert "pc" not in json.dumps(result) and "code=" not in repr(sites[0])


@pytest.mark.parametrize(
    "start,code",
    [
        (True, CODE),
        (START + 1, CODE),
        (0, CODE),
        (START, b""),
        (START, CODE + b"x"),
        (START, bytes(4100)),
        (0x1FFFFFC, CODE),
        (START, bytearray(CODE)),
    ],
)
def test_invalid_code_window(start, code):
    with rejects("WRITES_CODE_RANGE"):
        discover_sites(start, code)


@pytest.mark.parametrize(
    "code,error",
    [
        (SW + bytes(8), "WRITES_RETURN"),
        (struct.pack("<I", 0xFFFFFFFF) + RETURN, "WRITES_UNSUPPORTED"),
        (struct.pack("<I", 0x70000000) + RETURN, "WRITES_UNSUPPORTED"),
        (instruction(3, 0, 0, 0) + bytes(4) + RETURN, "WRITES_FLOW"),
        (struct.pack("<I", 0x00400008) + bytes(4) + RETURN, "WRITES_RETURN"),
        (instruction(4, 0, 0, 100) + bytes(4) + RETURN, "WRITES_TARGET"),
        (instruction(20, 0, 0, 1) + bytes(4) + RETURN, "WRITES_TARGET"),
        (instruction(4, 0, 0, 1) + RETURN, "WRITES_SLOT"),
        (instruction(5, 0, 1, 1) + SW + RETURN, "WRITES_SLOT"),
        (instruction(4, 0, 0, 0) + SW + RETURN, "WRITES_SLOT_TARGET"),
        (instruction(4, 0, 0, -1) + bytes(4) + SW + RETURN, "WRITES_NO_PATH"),
        (bytes(4) + RETURN, "WRITES_NO_PATH"),
    ],
)
def test_reject_unsupported_flow_slot_target_or_missing_path(code, error):
    with rejects(error):
        discover_sites(START, code)


def test_unconditional_branch_skips_unreachable_store_and_accepts_constant_slot():
    code = instruction(4, 0, 0, 2) + instruction(15, 0, 7, 42) + SW + SW + RETURN
    assert [s.pc for s in discover_sites(START, code)] == [START + 12]
