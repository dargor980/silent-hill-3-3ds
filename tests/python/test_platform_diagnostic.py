"""PD08: independent fixed vectors and adversarial frames; no authenticated peer."""

import struct
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest

from tools.inspectors.platform_diagnostic import (
    MAX_U64,
    DiagnosticEpochs,
    DiagnosticExpectation,
    DiagnosticFormatError,
    DiagnosticRequest,
    IdentityProfile,
    RejectionReason,
    UnverifiedDiagnosticRejection,
    UnverifiedPlatformDiagnostic,
    decode_platform_diagnostic,
    encode_diagnostic_request,
)
from tools.inspectors.process_diagnostic import Fact, Observation

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "tests/fixtures/platform-diagnostic-v2"
REQUEST = DiagnosticRequest(bytes(range(1, 17)), 0x0102030405060708)
EXPECTATION = DiagnosticExpectation(
    IdentityProfile.MACOS_PLATFORM_SLICES_V2, *[bytes([v]) * 32 for v in (3, 4, 5)]
)
OBSERVED = bytes.fromhex((VECTORS / "observed.hex").read_text())
REJECTED = bytes.fromhex((VECTORS / "rejected.hex").read_text())


def decode(data=OBSERVED, **kwargs):
    return decode_platform_diagnostic(
        data,
        expectation=kwargs.get("expectation", EXPECTATION),
        request=kwargs.get("request", REQUEST),
    )


def alter(offset, value, base=OBSERVED):
    return base[:offset] + value + base[offset + len(value) :]


def test_independent_vector_and_explicit_scope():
    assert encode_diagnostic_request(REQUEST) == bytes.fromhex(
        (VECTORS / "request.hex").read_text()
    )
    r = decode()
    assert type(r) is UnverifiedPlatformDiagnostic and not isinstance(r, Observation)
    assert r.request == REQUEST and r.expectation == EXPECTATION
    assert r.scope == "application_headers" and r.platform_assumed is True
    assert (r.pid, r.birth_ns, r.provider_nonce) == (
        0x12345678,
        0x1020304050607080,
        bytes(range(17, 33)),
    )
    assert (r.file_objects, r.classified_images) == (bytes([1]) * 32, bytes([2]) * 32)
    assert (r.loader_revision, r.application_images, r.platform_images) == (
        0x0807060504030201,
        26,
        621,
    )
    assert r.facts == (Fact.UNKNOWN, Fact.SATISFIED, Fact.VIOLATED) * 6
    assert r.epochs == DiagnosticEpochs(11, 12, 13, 14)
    assert not {"capabilities", "admitted", "verified", "read_ram"} & {f.name for f in fields(r)}
    with pytest.raises(FrozenInstanceError):
        r.pid = 1


def test_every_truncation_and_extensions():
    for base in (OBSERVED, REJECTED):
        for n in range(len(base)):
            with pytest.raises(DiagnosticFormatError, match="size"):
                decode(base[:n])
        for data in (base + b"\0", base + base, bytearray(base), None, "x" * 294):
            with pytest.raises(DiagnosticFormatError, match="size"):
                decode(data)


@pytest.mark.parametrize("offset", range(8))
def test_each_magic_byte(offset):
    with pytest.raises(DiagnosticFormatError, match="version"):
        decode(alter(offset, bytes([OBSERVED[offset] ^ 1])))


@pytest.mark.parametrize("offset", [13, 14, 15])
def test_reserved_bytes(offset):
    with pytest.raises(DiagnosticFormatError, match="reserved"):
        decode(alter(offset, b"\1"))


@pytest.mark.parametrize("offset", range(16, 40))
def test_every_challenge_or_sequence_byte_is_bound(offset):
    for base in (OBSERVED, REJECTED):
        with pytest.raises(DiagnosticFormatError, match="correlation"):
            decode(alter(offset, bytes([base[offset] ^ 1]), base))


@pytest.mark.parametrize(
    ("offset", "values", "error"),
    [
        (8, [0, 3, 255], "status"),
        (9, [0, 1, 3, 255], "profile"),
        (10, [0, 2, 255], "scope"),
        (11, [0, 2, 255], "scope"),
        (12, [1, 255], "scope"),
    ],
)
def test_mixed_versions_profiles_and_union(offset, values, error):
    for v in values:
        with pytest.raises(DiagnosticFormatError, match=error):
            decode(alter(offset, bytes([v])))


@pytest.mark.parametrize(
    ("offset", "value", "error"),
    [
        (40, struct.pack("<I", 0), "process"),
        (40, struct.pack("<I", 0x80000000), "process"),
        (44, bytes(8), "process"),
        (52, bytes(16), "process"),
        *[(i, bytes(32), "digest") for i in range(68, 228, 32)],
        *[(i, b"z" * 32, "evidence") for i in (132, 164, 196)],
        (228, bytes(8), "revision"),
        (228, struct.pack("<Q", MAX_U64), "revision"),
        (236, struct.pack("<II", 0, 1), "counts"),
        (236, struct.pack("<II", 2049, 0), "counts"),
        (236, struct.pack("<II", 1, 2048), "counts"),
        (236, struct.pack("<II", 26, 0xFFFFFFFF), "counts"),
    ],
)
def test_invalid_inventory(offset, value, error):
    with pytest.raises(DiagnosticFormatError, match=error):
        decode(alter(offset, value))


def test_boundaries_are_valid():
    data = alter(40, struct.pack("<IQ", 0x7FFFFFFF, MAX_U64))
    data = alter(228, struct.pack("<QII", MAX_U64 - 1, 2048, 0), data)
    assert decode(data).application_images == 2048
    assert decode(alter(236, struct.pack("<II", 1, 2047), data)).platform_images == 2047


@pytest.mark.parametrize("offset", range(244, 262))
def test_each_unknown_wire_fact_rejected(offset):
    for v in (3, 255):
        with pytest.raises(DiagnosticFormatError, match="facts"):
            decode(alter(offset, bytes([v])))


@pytest.mark.parametrize("fact", range(3))
def test_all_facts_remain_diagnostic_even_when_satisfied(fact):
    r = decode(alter(244, bytes([fact]) * 18))
    assert r.facts == ((Fact.UNKNOWN, Fact.SATISFIED, Fact.VIOLATED)[fact],) * 18
    assert type(r) is UnverifiedPlatformDiagnostic


@pytest.mark.parametrize("offset", [262, 270, 278, 286])
def test_partial_or_exhausted_epochs(offset):
    for value in (0, MAX_U64):
        with pytest.raises(DiagnosticFormatError, match="epochs"):
            decode(alter(offset, struct.pack("<Q", value)))


def test_absent_vm_cannot_claim_runtime_facts():
    no_vm = alter(244, bytes(50))
    r = decode(no_vm)
    assert r.epochs == DiagnosticEpochs(0, 0, 0, 0) and r.facts == (Fact.UNKNOWN,) * 18
    for offset in range(244, 262):
        for fact in (1, 2):
            with pytest.raises(DiagnosticFormatError, match="unbound_facts"):
                decode(alter(offset, bytes([fact]), no_vm))


def test_rejection_has_no_observation_and_no_partial_payload():
    assert decode(REJECTED) == UnverifiedDiagnosticRejection(REQUEST, RejectionReason.CANCELLED)
    for reason in range(256):
        frame = alter(12, bytes([reason]), REJECTED)
        if 1 <= reason <= 9:
            assert decode(frame).reason == RejectionReason(reason)
        else:
            with pytest.raises(DiagnosticFormatError, match="rejection_reason"):
                decode(frame)
    for offset in (*range(9, 12), *range(40, 294)):
        with pytest.raises(DiagnosticFormatError, match="rejection_payload"):
            decode(alter(offset, b"\1", REJECTED))


@pytest.mark.parametrize(
    "input_request",
    [
        None,
        {},
        replace(REQUEST, challenge=bytes(16)),
        replace(REQUEST, challenge=b"x" * 15),
        replace(REQUEST, challenge=b"x" * 17),
        replace(REQUEST, challenge=bytearray(16)),
        *[replace(REQUEST, sequence=v) for v in (0, -1, True, MAX_U64, MAX_U64 + 1, "1")],
    ],
)
def test_local_request_validation(input_request):
    with pytest.raises(DiagnosticFormatError, match="request"):
        encode_diagnostic_request(input_request)
    with pytest.raises(DiagnosticFormatError, match="request"):
        decode(request=input_request)


@pytest.mark.parametrize(
    "expectation",
    [
        None,
        {},
        *[replace(EXPECTATION, profile=v) for v in (0, 1, 2, True, 255)],
        *[
            replace(EXPECTATION, **{f: v})
            for f in ("policy_evidence", "application_evidence", "platform_evidence")
            for v in (bytes(32), b"x" * 31, b"x" * 33, "x" * 32)
        ],
    ],
)
def test_local_expectation_cannot_be_implicit_or_empty(expectation):
    with pytest.raises(DiagnosticFormatError, match="configuration"):
        decode(expectation=expectation)


def test_decoder_has_no_replay_or_peer_claim():
    # The future session owner must enforce single use and authenticate the peer.
    assert decode() == decode()


@pytest.mark.parametrize(("application", "platform"), [(1, 1024), (43, 1026), (1, 2047), (2048, 0)])
def test_v2_common_count_vectors(application, platform):
    data = bytes.fromhex((VECTORS / f"counts-{application}-{platform}.hex").read_text())
    result = decode(data)
    assert (result.application_images, result.platform_images) == (application, platform)


@pytest.mark.parametrize("name", ["observed", "rejected"])
def test_v1_response_is_not_reinterpreted(name):
    old = ROOT / "tests/fixtures/platform-diagnostic" / f"{name}.hex"
    with pytest.raises(DiagnosticFormatError, match="version"):
        decode(bytes.fromhex(old.read_text()))
