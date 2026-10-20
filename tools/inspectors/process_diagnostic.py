"""IP01-09: one-use diagnostic consumer; the native provider probe is still pending.

No value in this module authenticates a peer or grants a capture capability.
Only a provider adapter may implement IdentityProbe; client metadata is not a probe.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Protocol

CONDITIONS = (
    "cpu_thread",
    "cpu_boundary",
    "paused",
    "implementations_settled",
    "ee_interpreter",
    "iop_interpreter",
    "vu0_interpreter",
    "vu1_interpreter",
    "ee_cache_disabled",
    "fastmem_disabled",
    "mtvu_disabled",
    "vif_dynarec_disabled",
    "raintegration_disabled",
    "pine_excluded",
    "rdebug_excluded",
    "gs_drained",
    "vu_drained",
    "other_writers_excluded",
)


class Fact(Enum):
    UNKNOWN = "unknown"
    SATISFIED = "satisfied"
    VIOLATED = "violated"


class State(Enum):
    IDLE = "idle"
    OBSERVING = "observing"
    COMPLETE = "complete"
    DISCARDED = "discarded"


@dataclass(frozen=True)
class Artifact:
    evidence_sha256: str
    # Complete approved bundle manifest, including its executable; canonical order.
    images: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Observation:
    pid: int
    birth_ns: int
    provider_nonce: bytes
    artifact: Artifact
    # Canonical inventories produced/validated by the provider, NOT caller hashes.
    file_objects_sha256: str
    loaded_images_sha256: str
    loader_revision: int
    host_epoch: int
    pine_generation: int
    vu_generation: int
    gs_generation: int


class IdentityUnavailable(Exception):
    """The adapter could not prove a stable, complete identity observation."""


class IdentityProbe(Protocol):
    def sample(self) -> Observation | None:
        """Validate native identity, mappings and file objects; return None on loss.

        Implementations must own the provider channel, reject client assertions,
        and observe loader/lifecycle transitions even if values later revert.
        """
        ...


@dataclass(frozen=True)
class Report:
    state: State = State.IDLE
    reason: str = ""
    violated: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()


def _digest(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _counter(value):
    return type(value) is int and 0 < value < (1 << 64) - 1


def _artifact(value):
    if type(value) is not Artifact or not _digest(value.evidence_sha256):
        return False
    images = value.images
    if type(images) is not tuple or not 1 <= len(images) <= 256:
        return False
    names = []
    for image in images:
        if type(image) is not tuple or len(image) != 2:
            return False
        name, digest = image
        if type(name) is not str or not 1 <= len(name) <= 512 or not _digest(digest):
            return False
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or str(path) != name or "\\" in name:
            return False
        if any(ord(c) < 32 or ord(c) == 127 for c in name) or name == ".":
            return False
        names.append(name)
    return names == sorted(set(names))


def _observation(value):
    if type(value) is not Observation or not _artifact(value.artifact):
        return False
    return (
        all(
            _counter(getattr(value, name))
            for name in (
                "pid",
                "birth_ns",
                "loader_revision",
                "host_epoch",
                "pine_generation",
                "vu_generation",
                "gs_generation",
            )
        )
        and type(value.provider_nonce) is bytes
        and len(value.provider_nonce) == 16
        and any(value.provider_nonce)
        and _digest(value.file_objects_sha256)
        and _digest(value.loaded_images_sha256)
    )


class DiagnosticGuard:
    """Single owner, single interval; no stored profile survives a failed check."""

    def __init__(self, artifact: Artifact, probe: IdentityProbe):
        self._artifact = artifact
        self._probe = probe
        self._baseline = None
        self._report = Report()

    @property
    def report(self):
        return self._report

    def _discard(self, reason):
        if self._report.state not in (State.COMPLETE, State.DISCARDED):
            self._baseline = None
            self._report = Report(State.DISCARDED, reason)
        return self._report

    def _sample(self):
        try:
            value = self._probe.sample()
        except IdentityUnavailable:
            value = None
        except Exception:
            self._discard("probe_error")
            raise
        if not _observation(value):
            self._discard("identity_unavailable")
            return None
        if value.artifact != self._artifact:
            self._discard("artifact_changed")
            return None
        return value

    def begin(self):
        if self._report.state != State.IDLE:
            return self._discard("protocol")
        if not _artifact(self._artifact):
            return self._discard("artifact_invalid")
        baseline = self._sample()
        if baseline is not None:
            self._baseline = baseline
            self._report = Report(State.OBSERVING)
        return self._report

    def finish(self, profile: tuple[Fact, ...]):
        if self._report.state != State.OBSERVING:
            return self._discard("protocol")
        if (
            type(profile) is not tuple
            or len(profile) != len(CONDITIONS)
            or any(type(fact) is not Fact for fact in profile)
        ):
            return self._discard("profile_invalid")
        current = self._sample()
        if current is None:
            return self._report
        if current != self._baseline:
            return self._discard("identity_changed")
        self._baseline = None
        self._report = Report(
            State.COMPLETE,
            "diagnostic_only",
            tuple(
                name
                for name, fact in zip(CONDITIONS, profile, strict=True)
                if fact == Fact.VIOLATED
            ),
            tuple(
                name for name, fact in zip(CONDITIONS, profile, strict=True) if fact == Fact.UNKNOWN
            ),
        )
        return self._report

    def cancel(self):
        return self._discard("cancelled")
