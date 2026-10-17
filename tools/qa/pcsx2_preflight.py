"""IB05: evaluate supplied baseline build prerequisites without running/installing tools."""

import re

SOURCE_COMMIT = "fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3"
MINIMUM_FREE_BYTES = 20 * 1024**3
CHECKS = ("cxx20_compile", "cxx20_run", "metal_compile", "metal_link", "pcsx2_configure")


def evaluate(source_commit, source_clean, free_bytes, checks) -> dict:
    """A successful result does not authenticate evidence or prove a PCSX2 build."""
    if (
        not isinstance(source_commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
        or type(source_clean) is not bool
        or type(free_bytes) is not int
        or not 0 <= free_bytes < 1 << 64
        or not isinstance(checks, dict)
        or set(checks) != set(CHECKS)
        or any(
            code is not None and (type(code) is not int or not -255 <= code <= 255)
            for code in checks.values()
        )
    ):
        raise ValueError("PREFLIGHT_SCHEMA")
    for producer, consumer in (("cxx20_compile", "cxx20_run"), ("metal_compile", "metal_link")):
        if checks[producer] != 0 and checks[consumer] is not None:
            raise ValueError("PREFLIGHT_ORDER")
    blockers = []
    if source_commit != SOURCE_COMMIT:
        blockers.append("source_identity")
    if not source_clean:
        blockers.append("source_dirty")
    if free_bytes < MINIMUM_FREE_BYTES:
        blockers.append("storage_reserve")
    blockers.extend(name for name in CHECKS if checks[name] != 0)
    return {
        "schema_version": 1,
        "status": "blocked" if blockers else "ready_for_baseline_build",
        "source_commit": source_commit,
        "source_clean": source_clean,
        "free_bytes": free_bytes,
        "minimum_free_bytes": MINIMUM_FREE_BYTES,
        "reserve_basis": "project_policy_not_measured_build_size",
        "checks": {
            name: {
                "exit_code": checks[name],
                "status": "not_run"
                if checks[name] is None
                else "passed"
                if checks[name] == 0
                else "failed",
            }
            for name in CHECKS
        },
        "blockers": blockers,
        "pcsx2_build_verified": False,
        "mapping_verified": False,
        "evidence_authentication": "not_provided",
    }
