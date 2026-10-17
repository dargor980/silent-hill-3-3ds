"""IB05: prerequisite gate tests with synthetic tool outcomes, no downloads or PCSX2."""

import json

import pytest

from tools.qa.pcsx2_preflight import CHECKS, MINIMUM_FREE_BYTES, SOURCE_COMMIT, evaluate


def inputs():
    return {
        "source_commit": SOURCE_COMMIT,
        "source_clean": True,
        "free_bytes": MINIMUM_FREE_BYTES,
        "checks": dict.fromkeys(CHECKS, 0),
    }


def test_ready_is_only_readiness_and_does_not_mutate_inputs():
    data = inputs()
    before = json.dumps(data)
    result = evaluate(**data)
    assert result["status"] == "ready_for_baseline_build"
    assert result["blockers"] == []
    assert result["pcsx2_build_verified"] is False
    assert result["mapping_verified"] is False
    assert result["evidence_authentication"] == "not_provided"
    assert result["reserve_basis"] == "project_policy_not_measured_build_size"
    assert json.dumps(data) == before


def test_combined_realistic_blockers_remain_distinct():
    data = inputs()
    data["free_bytes"] = 4 * 1024**3
    data["checks"].update(metal_compile=72, metal_link=None, pcsx2_configure=1)
    result = evaluate(**data)
    assert result["status"] == "blocked"
    assert result["blockers"] == [
        "storage_reserve",
        "metal_compile",
        "metal_link",
        "pcsx2_configure",
    ]
    assert result["checks"]["metal_compile"]["status"] == "failed"
    assert result["checks"]["metal_link"]["status"] == "not_run"
    assert result["checks"]["cxx20_run"]["status"] == "passed"


@pytest.mark.parametrize(
    "field,value,blocker",
    [
        ("source_commit", "0" * 40, "source_identity"),
        ("source_clean", False, "source_dirty"),
        ("free_bytes", MINIMUM_FREE_BYTES - 1, "storage_reserve"),
        ("free_bytes", 0, "storage_reserve"),
    ],
)
def test_prerequisite_failure(field, value, blocker):
    data = inputs()
    data[field] = value
    assert evaluate(**data)["blockers"] == [blocker]


@pytest.mark.parametrize("name", CHECKS)
@pytest.mark.parametrize("code", [1, -9, None])
def test_failed_or_missing_check_cannot_pass(name, code):
    data = inputs()
    data["checks"][name] = code
    if name in ("cxx20_compile", "metal_compile"):
        data["checks"]["cxx20_run" if name == "cxx20_compile" else "metal_link"] = None
    result = evaluate(**data)
    assert result["status"] == "blocked"
    assert name in result["blockers"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_commit", None),
        ("source_commit", "A" * 40),
        ("source_commit", "a" * 39),
        ("source_commit", "g" * 40),
        ("source_clean", 1),
        ("source_clean", "true"),
        ("free_bytes", True),
        ("free_bytes", -1),
        ("free_bytes", 1 << 64),
        ("free_bytes", 20.0),
        ("checks", []),
        ("checks", None),
        ("checks", {}),
        ("checks", {**dict.fromkeys(CHECKS, 0), "extra": 0}),
    ],
)
def test_malformed_inputs_fail_closed(field, value):
    data = inputs()
    data[field] = value
    with pytest.raises(ValueError, match="^PREFLIGHT_SCHEMA$"):
        evaluate(**data)


@pytest.mark.parametrize("code", [False, True, "0", 0.0, -256, 256, {}, []])
def test_non_integer_and_out_of_range_status(code):
    data = inputs()
    data["checks"]["pcsx2_configure"] = code
    with pytest.raises(ValueError, match="^PREFLIGHT_SCHEMA$"):
        evaluate(**data)


@pytest.mark.parametrize(
    "producer,consumer", [("cxx20_compile", "cxx20_run"), ("metal_compile", "metal_link")]
)
@pytest.mark.parametrize("code", [1, None])
def test_consumer_cannot_run_after_missing_or_failed_producer(producer, consumer, code):
    data = inputs()
    data["checks"][producer] = code
    assert data["checks"][consumer] == 0
    with pytest.raises(ValueError, match="^PREFLIGHT_ORDER$"):
        evaluate(**data)


def test_all_not_run_is_not_success():
    data = inputs()
    data["checks"] = dict.fromkeys(CHECKS, None)
    result = evaluate(**data)
    assert result["blockers"] == list(CHECKS)
    assert all(item["status"] == "not_run" for item in result["checks"].values())
