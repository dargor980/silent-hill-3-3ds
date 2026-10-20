"""PD v2: bounded wire validation for PT v2, without peer authentication.

These types deliberately cannot stand in for process_diagnostic.Observation.
Decoding and matching local expectations do not make provider assertions trusted.
"""

import struct
from dataclasses import dataclass
from enum import IntEnum

from tools.inspectors.process_diagnostic import CONDITIONS, Fact

REQUEST_SIZE = 32
RESPONSE_SIZE = 294
IMAGE_CAPACITY = 2048
REQUEST_MAGIC = b"SH3PDQ02"
RESPONSE_MAGIC = b"SH3PDR02"
MAX_U64 = (1 << 64) - 1


class IdentityProfile(IntEnum):
    MACOS_PLATFORM_SLICES_V2 = 2


class RejectionReason(IntEnum):
    CONFIGURATION = 1
    INVENTORY = 2
    IDENTITY_CHANGED = 3
    PEER_LOST = 4
    DEADLINE = 5
    CANCELLED = 6
    PROTOCOL = 7
    LIFECYCLE = 8
    UNAVAILABLE = 9


class DiagnosticFormatError(ValueError):
    """Malformed wire, unsupported contract, or mismatched local expectation."""


@dataclass(frozen=True)
class DiagnosticRequest:
    challenge: bytes
    sequence: int


@dataclass(frozen=True)
class DiagnosticExpectation:
    profile: IdentityProfile
    policy_evidence: bytes
    application_evidence: bytes
    platform_evidence: bytes


@dataclass(frozen=True)
class DiagnosticEpochs:
    host: int
    pine: int
    vu: int
    gs: int


@dataclass(frozen=True)
class UnverifiedPlatformDiagnostic:
    request: DiagnosticRequest
    expectation: DiagnosticExpectation
    scope: str
    platform_assumed: bool
    pid: int
    birth_ns: int
    provider_nonce: bytes
    file_objects: bytes
    classified_images: bytes
    loader_revision: int
    application_images: int
    platform_images: int
    facts: tuple[Fact, ...]
    epochs: DiagnosticEpochs


@dataclass(frozen=True)
class UnverifiedDiagnosticRejection:
    request: DiagnosticRequest
    reason: RejectionReason


def _require(condition, reason):
    if not condition:
        raise DiagnosticFormatError(reason)


def _nonzero_bytes(value, size):
    return type(value) is bytes and len(value) == size and any(value)


def _counter(value):
    return type(value) is int and 0 < value < MAX_U64


def _request(value):
    _require(
        type(value) is DiagnosticRequest
        and _nonzero_bytes(value.challenge, 16)
        and _counter(value.sequence),
        "request",
    )


def _expectation(value):
    _require(
        type(value) is DiagnosticExpectation
        and type(value.profile) is IdentityProfile
        and value.profile == IdentityProfile.MACOS_PLATFORM_SLICES_V2
        and all(
            _nonzero_bytes(d, 32)
            for d in (value.policy_evidence, value.application_evidence, value.platform_evidence)
        ),
        "configuration",
    )


def encode_diagnostic_request(request: DiagnosticRequest) -> bytes:
    _request(request)
    return REQUEST_MAGIC + request.challenge + struct.pack("<Q", request.sequence)


def decode_platform_diagnostic(
    data: bytes, *, expectation: DiagnosticExpectation, request: DiagnosticRequest
) -> UnverifiedPlatformDiagnostic | UnverifiedDiagnosticRejection:
    """Parse exactly one frame. Caller still must authenticate/bind the channel.

    No fallback, stream accumulation, replay protection, or lifecycle monitoring
    happens here. A session owner must make any error terminal before retrying.
    """
    _expectation(expectation)
    _request(request)
    _require(type(data) is bytes and len(data) == RESPONSE_SIZE, "size")
    _require(data[:8] == RESPONSE_MAGIC, "version")
    _require(data[13:16] == bytes(3), "reserved")
    _require(
        data[16:32] == request.challenge
        and struct.unpack_from("<Q", data, 32)[0] == request.sequence,
        "correlation",
    )
    status, profile, scope, assumed, reason = data[8:13]
    if status == 2:
        _require(profile == scope == assumed == 0 and not any(data[40:]), "rejection_payload")
        _require(reason in RejectionReason._value2member_map_, "rejection_reason")
        return UnverifiedDiagnosticRejection(request, RejectionReason(reason))
    _require(status == 1, "status")
    _require(profile == expectation.profile, "profile")
    _require(scope == assumed == 1 and reason == 0, "scope")
    pid, birth_ns = struct.unpack_from("<IQ", data, 40)
    nonce = data[52:68]
    _require(0 < pid <= 0x7FFFFFFF and birth_ns > 0 and any(nonce), "process")
    digests = tuple(data[i : i + 32] for i in range(68, 228, 32))
    _require(all(any(d) for d in digests), "digest")
    _require(
        digests[2:]
        == (
            expectation.policy_evidence,
            expectation.application_evidence,
            expectation.platform_evidence,
        ),
        "evidence",
    )
    revision, application, platform = struct.unpack_from("<QII", data, 228)
    _require(_counter(revision), "revision")
    _require(
        1 <= application <= IMAGE_CAPACITY and platform <= IMAGE_CAPACITY - application, "counts"
    )
    raw_facts = data[244:262]
    _require(len(raw_facts) == len(CONDITIONS) and all(f <= 2 for f in raw_facts), "facts")
    facts = tuple((Fact.UNKNOWN, Fact.SATISFIED, Fact.VIOLATED)[f] for f in raw_facts)
    epochs = struct.unpack_from("<4Q", data, 262)
    if any(epochs):
        _require(all(_counter(e) for e in epochs), "epochs")
    else:
        _require(not any(raw_facts), "unbound_facts")
    return UnverifiedPlatformDiagnostic(
        request,
        expectation,
        "application_headers",
        True,
        pid,
        birth_ns,
        nonce,
        digests[0],
        digests[1],
        revision,
        application,
        platform,
        facts,
        DiagnosticEpochs(*epochs),
    )
