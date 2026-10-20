"""IP09: provider-port doubles; these tests do not attest a live PCSX2 process."""

from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest

from tools.inspectors.process_diagnostic import (
    CONDITIONS,
    Artifact,
    DiagnosticGuard,
    Fact,
    IdentityUnavailable,
    Observation,
    State,
)

ARTIFACT = Artifact("a" * 64, (("Contents/MacOS/PCSX2", "b" * 64),))
OBSERVATION = Observation(
    42, 123456789, bytes(range(16)), ARTIFACT, "c" * 64, "d" * 64, 1, 2, 3, 4, 5
)
PROFILE = (Fact.UNKNOWN,) * len(CONDITIONS)


class Probe:
    def __init__(self, value=OBSERVATION):
        self.value = value
        self.calls = 0

    def sample(self):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def started():
    probe = Probe()
    guard = DiagnosticGuard(ARTIFACT, probe)
    assert guard.begin().state == State.OBSERVING
    return guard, probe


def assert_discarded(guard, probe, reason):
    report = guard.report
    assert (report.state, report.reason) == (State.DISCARDED, reason)
    assert report.unknown == report.violated == ()
    probe.value = OBSERVATION  # Restoring values must not revive discarded evidence.
    calls = probe.calls
    assert guard.begin() == guard.finish(PROFILE) == guard.cancel() == report
    assert probe.calls == calls


@pytest.mark.parametrize("fact", list(Fact))
def test_diagnostic_reports_all_facts_without_authority(fact):
    guard, probe = started()
    report = guard.finish((fact,) * len(CONDITIONS))
    assert report.state == State.COMPLETE and report.reason == "diagnostic_only"
    assert report.unknown == (CONDITIONS if fact == Fact.UNKNOWN else ())
    assert report.violated == (CONDITIONS if fact == Fact.VIOLATED else ())
    assert {f.name for f in fields(report)} == {"state", "reason", "unknown", "violated"}
    probe.value = None
    assert guard.begin() == guard.finish(()) == guard.cancel() == report
    assert probe.calls == 2  # A completed result is historical, never refreshed/rearmed.
    with pytest.raises(FrozenInstanceError):
        report.reason = "allowed"


def test_mixed_profile_keeps_vif_and_writers_rejected():
    guard, _ = started()
    profile = tuple(
        Fact.VIOLATED if name == "vif_dynarec_disabled" else Fact.UNKNOWN for name in CONDITIONS
    )
    report = guard.finish(profile)
    assert report.violated == ("vif_dynarec_disabled",)
    assert len(report.unknown) == 17
    assert "rdebug_excluded" in report.unknown


@pytest.mark.parametrize("field", [f.name for f in fields(Observation) if f.name != "artifact"])
def test_each_identity_change_discards_even_with_same_pid_and_bytes(field):
    guard, probe = started()
    before = getattr(OBSERVATION, field)
    after = (
        before + 1 if type(before) is int else (b"x" * 16 if type(before) is bytes else "e" * 64)
    )
    probe.value = replace(OBSERVATION, **{field: after})
    guard.finish(PROFILE)
    assert_discarded(guard, probe, "identity_changed")


@pytest.mark.parametrize("when", ["begin", "finish"])
@pytest.mark.parametrize("value", [None, {}, IdentityUnavailable("private path")])
def test_missing_or_client_metadata_cannot_supply_identity(when, value):
    probe = Probe()
    guard = DiagnosticGuard(ARTIFACT, probe)
    if when == "finish":
        guard.begin()
    probe.value = value
    guard.begin() if when == "begin" else guard.finish(PROFILE)
    assert_discarded(guard, probe, "identity_unavailable")


@pytest.mark.parametrize("field", ["evidence_sha256", "images"])
@pytest.mark.parametrize("when", ["begin", "finish"])
def test_changed_executable_dependency_or_evidence_cannot_bind(field, when):
    probe = Probe()
    guard = DiagnosticGuard(ARTIFACT, probe)
    if when == "finish":
        guard.begin()
    value = "e" * 64 if field == "evidence_sha256" else (("Contents/MacOS/PCSX2", "e" * 64),)
    probe.value = replace(OBSERVATION, artifact=replace(ARTIFACT, **{field: value}))
    guard.begin() if when == "begin" else guard.finish(PROFILE)
    assert_discarded(guard, probe, "artifact_changed")


@pytest.mark.parametrize(
    "images",
    [
        (),
        [],
        (("a",),),
        ((1, "a" * 64),),
        (("a", "invalid"),),
        (("/a", "a" * 64),),
        (("../a", "a" * 64),),
        (("a//b", "a" * 64),),
        (("a\\b", "a" * 64),),
        (("a\0b", "a" * 64),),
        ((".", "a" * 64),),
        (("a" * 513, "a" * 64),),
        (("", "a" * 64),),
        (("a", "a" * 64),) * 2,
        (("z", "a" * 64), ("a", "b" * 64)),
        tuple((str(i), "a" * 64) for i in range(257)),
    ],
)
def test_malformed_artifact_is_rejected_before_probe(images):
    probe = Probe()
    guard = DiagnosticGuard(replace(ARTIFACT, images=images), probe)
    guard.begin()
    assert_discarded(guard, probe, "artifact_invalid")
    assert probe.calls == 0


@pytest.mark.parametrize("artifact", [None, {}, replace(ARTIFACT, evidence_sha256="A" * 64)])
def test_invalid_artifact_type_or_receipt(artifact):
    probe = Probe()
    guard = DiagnosticGuard(artifact, probe)
    guard.begin()
    assert_discarded(guard, probe, "artifact_invalid")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (name, value)
        for name in (
            "pid",
            "birth_ns",
            "loader_revision",
            "host_epoch",
            "pine_generation",
            "vu_generation",
            "gs_generation",
        )
        for value in (0, -1, True, (1 << 64) - 1)
    ]
    + [("provider_nonce", value) for value in (b"", bytes(16), b"x" * 17, "x" * 16)]
    + [("file_objects_sha256", "?" * 64), ("loaded_images_sha256", ""), ("artifact", None)],
)
def test_incomplete_invalid_or_exhausted_observation(field, value):
    guard, probe = started()
    probe.value = replace(OBSERVATION, **{field: value})
    guard.finish(PROFILE)
    assert_discarded(guard, probe, "identity_unavailable")


@pytest.mark.parametrize("profile", [(), list(PROFILE), ("satisfied",) * 18, (True,) * 18])
def test_malformed_profile_does_not_leave_evidence(profile):
    guard, probe = started()
    guard.finish(profile)
    assert_discarded(guard, probe, "profile_invalid")
    assert probe.calls == 1


@pytest.mark.parametrize("action", ["early_finish", "duplicate_begin", "cancel"])
def test_protocol_and_cancellation_are_terminal(action):
    probe = Probe()
    guard = DiagnosticGuard(ARTIFACT, probe)
    if action != "early_finish":
        guard.begin()
    if action == "early_finish":
        guard.finish(PROFILE)
    elif action == "duplicate_begin":
        guard.begin()
    else:
        guard.cancel()
    assert_discarded(guard, probe, "cancelled" if action == "cancel" else "protocol")


def test_unexpected_adapter_bug_discards_then_surfaces_for_diagnosis():
    guard, probe = started()
    probe.value = RuntimeError("adapter bug")
    with pytest.raises(RuntimeError, match="adapter bug"):
        guard.finish(PROFILE)
    assert_discarded(guard, probe, "probe_error")


def test_ap_names_match_native_contract():
    root = Path(__file__).resolve().parents[2]
    native = (root / "tools/observer/include/sh3_observer/admission.hpp").read_text()
    enum = native.split("enum class AdmissionCondition : std::uint8_t {", 1)[1].split("};", 1)[0]
    assert tuple(item.strip() for item in enum.split(",")) == (*CONDITIONS, "count")
