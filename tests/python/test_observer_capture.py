"""OB02/04/08 decoder negatives use independently packed synthetic input."""

import json
import struct
from dataclasses import replace

import pytest

from tools.inspectors.effective_mapping import MappingContext
from tools.inspectors.observation_capture import ProfileError
from tools.inspectors.observer_capture import ObserverRequest, decode_reply

REQUEST = ObserverRequest("01" + "00" * 15, 1, 0x100000, 0x1FF0, 32, 0xFF0)
CONTEXT = MappingContext(REQUEST.session_id, "a" * 64, "b" * 64, 1, "c" * 64)


def packed(request=REQUEST, status=0, alias=0):
    size = 0 if status else request.size
    header = struct.pack(
        "<4sBBH16s8I",
        b"SH3O",
        1,
        status,
        0,
        bytes.fromhex(request.session_id),
        request.sequence,
        request.expected_pc,
        request.virtual_start,
        request.size,
        request.expected_offset,
        size,
        request.expected_offset + alias if not status else 0,
        int(not alias) if not status else 0,
    )
    end = request.virtual_start + request.size
    count = (end - 1) // 4096 - request.virtual_start // 4096 + 1
    bias = (0x10000000 + request.expected_offset + alias - request.virtual_start) % 2**64
    sample = struct.pack(
        "<QIQQQIIII",
        42,
        request.expected_pc,
        0x10000004D,
        0x10000000,
        0x20000000,
        32 * 1024 * 1024,
        1,
        0x44556677,
        count,
    )
    for i in range(2):
        sample += struct.pack(
            "<IIQ",
            request.virtual_start // 4096 + i if i < count else 0,
            0,
            bias if i < count else 0,
        )
    sample += bytes(4)
    data = bytes((i ^ 0x5A) & 255 for i in range(size))
    body = header + (bytes(176) if status else sample * 2) + data
    return struct.pack("<IB", 5 + len(body), 0) + body


def altered(packet, offset, fmt, value):
    result = bytearray(packet)
    struct.pack_into("<" + fmt, result, offset, value)
    return bytes(result)


def rejects(packet, code):
    with pytest.raises(ProfileError) as error:
        decode_reply(packet, REQUEST, CONTEXT)
    assert error.value.code == code


def test_request_independent_wire_oracle():
    expected = bytes.fromhex(
        "2c000000e0010000010000000000000000000000000000000100000000001000f01f000020000000f00f0000"
    )
    assert REQUEST.encode() == expected


@pytest.mark.parametrize(
    ("start", "size"), [(0, 1), (0x1FF0, 32), (0xFFFFF000, 4096), (0xFFFFFFFF, 1)]
)
def test_valid_boundaries_and_private_metadata(start, size):
    request = replace(REQUEST, virtual_start=start, size=size)
    value = decode_reply(packed(request), request, CONTEXT)
    assert value.data == bytes((i ^ 0x5A) & 255 for i in range(size))
    assert value.pid == 42 and value.pc == request.expected_pc and value.cycle == 0x10000004D
    assert value.game_crc == 0x44556677 and value.mapping.matches_expected_backing
    metadata = value.metadata()
    assert not metadata["state_binding_verified"] and not metadata["live_acquisition_verified"]
    assert "268435456" not in json.dumps(metadata)
    assert "ee_main" not in repr(value) and "data=" not in repr(value)


def test_alias_is_preserved_without_accepting_expected_backing():
    result = decode_reply(packed(alias=16), REQUEST, CONTEXT)
    assert result.mapping.physical_offset == REQUEST.expected_offset + 16
    assert not result.mapping.matches_expected_backing


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_id", "0" * 32),
        ("session_id", "zz" * 16),
        ("session_id", None),
        ("sequence", 0),
        ("sequence", 257),
        ("sequence", True),
        ("expected_pc", 1),
        ("expected_pc", -4),
        ("expected_pc", 2**32),
        ("virtual_start", -1),
        ("virtual_start", 2**32 - 1),
        ("size", 0),
        ("size", 4097),
        ("size", True),
        ("expected_offset", -1),
        ("expected_offset", 32 * 1024 * 1024),
    ],
)
def test_invalid_requests(field, value):
    with pytest.raises(ProfileError):
        replace(REQUEST, **{field: value}).encode()


@pytest.mark.parametrize(
    "packet",
    [None, bytearray(5), b"", bytes(4), bytes(4334)],
    ids=["none", "mutable", "empty", "short", "long"],
)
def test_invalid_packet_type_or_size(packet):
    rejects(packet, "OBSERVER_LENGTH")


@pytest.mark.parametrize(
    ("offset", "fmt", "value", "code"),
    [
        (0, "I", 5, "LENGTH"),
        (4, "B", 1, "ENVELOPE"),
        (5, "I", 0, "VERSION"),
        (9, "B", 2, "VERSION"),
        (10, "B", 13, "STATUS"),
        (11, "H", 1, "RESERVED"),
        (13, "B", 2, "ECHO"),
        (29, "I", 2, "ECHO"),
        (33, "I", 0, "ECHO"),
        (37, "I", 0, "ECHO"),
        (41, "I", 1, "ECHO"),
        (45, "I", 0, "ECHO"),
        (49, "I", 31, "LENGTH"),
        (53, "I", 0, "MAPPING"),
        (57, "I", 2, "MATCH"),
        (57, "I", 0, "MAPPING"),
    ],
)
def test_bad_header(offset, fmt, value, code):
    rejects(altered(packed(), offset, fmt, value), "OBSERVER_" + code)


@pytest.mark.parametrize(
    ("offset", "fmt", "value", "code"),
    [
        (0, "Q", 0, "OBSERVER_IDENTITY"),
        (8, "I", 0, "OBSERVER_IDENTITY"),
        (12, "Q", 78, "OBSERVER_IDENTITY"),
        (20, "Q", 0, "MAPPING_BACKING"),
        (28, "Q", 1, "MAPPING_TABLE"),
        (36, "I", 0, "MAPPING_BACKING"),
        (40, "I", 0, "OBSERVER_FLAGS"),
        (40, "I", 3, "OBSERVER_FLAGS"),
        (40, "I", 5, "OBSERVER_FLAGS"),
        (44, "I", 99, "OBSERVER_IDENTITY"),
        (48, "I", 0, "OBSERVER_COVERAGE"),
        (48, "I", 3, "OBSERVER_COVERAGE"),
        (52, "I", 99, "MAPPING_COVERAGE"),
        (56, "I", 1, "OBSERVER_RESERVED"),
        (60, "Q", 0, "MAPPING_UNSTABLE"),
        (68, "I", 99, "MAPPING_COVERAGE"),
        (72, "I", 1, "OBSERVER_RESERVED"),
        (84, "I", 1, "OBSERVER_RESERVED"),
    ],
)
@pytest.mark.parametrize("sample", [61, 149])
def test_bad_snapshot(offset, fmt, value, code, sample):
    rejects(altered(packed(), sample + offset, fmt, value), code)


@pytest.mark.parametrize("offset", [68, 76])
def test_single_page_unused_slot_rejected(offset):
    request = replace(REQUEST, size=1)
    packet = altered(packed(request), 61 + offset, "I", 1)
    with pytest.raises(ProfileError) as error:
        decode_reply(packet, request, CONTEXT)
    assert error.value.code == "OBSERVER_COVERAGE"


@pytest.mark.parametrize("code", range(1, 13))
def test_error_status_never_yields_observation(code):
    expected = (
        "REQUEST",
        "PAUSE",
        "SAVE_PENDING",
        "ANCHORS",
        "PC",
        "HANDLER",
        "OUTSIDE_RAM",
        "NONCONTIGUOUS",
        "UNSTABLE",
        "READ",
        "CONTENT",
        "TIMEOUT",
    )
    rejects(packed(status=code), "OBSERVER_" + expected[code - 1])


@pytest.mark.parametrize("offset", [49, 53, 57, 61, 148, 149, 236])
def test_failure_with_private_payload_is_malformed(offset):
    rejects(altered(packed(status=12), offset, "B", 1), "OBSERVER_ERROR_PAYLOAD")


def test_pine_failure_and_malformed_failure():
    rejects(struct.pack("<IB", 5, 255), "OBSERVER_PINE_REJECTED")
    rejects(struct.pack("<IBB", 6, 255, 0), "OBSERVER_LENGTH")
    rejects(struct.pack("<IB", 5, 0), "OBSERVER_ENVELOPE")


@pytest.mark.parametrize("delta", [-1, 1])
def test_truncation_and_trailing_data(delta):
    original = packed()
    packet = original[:-1] if delta < 0 else original + b"x"
    rejects(altered(packet, 0, "I", len(packet)), "OBSERVER_LENGTH")


@pytest.mark.parametrize(
    "context", [None, replace(CONTEXT, sequence=2), replace(CONTEXT, session_id="02" * 16)]
)
def test_context_binding(context):
    with pytest.raises(ProfileError):
        decode_reply(packed(), REQUEST, context)


def test_wrong_request_type():
    with pytest.raises(ProfileError) as error:
        decode_reply(packed(), {}, CONTEXT)
    assert error.value.code == "OBSERVER_REQUEST"
