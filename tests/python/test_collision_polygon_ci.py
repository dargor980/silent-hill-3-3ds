"""CF-T7d CI contract and independent per-module coverage gate controls."""

import json
import shlex
from pathlib import Path

import pytest
import yaml

from tools.qa.coverage_gate import main

NEW_MODULES = (
    "tools/pipeline/collision_polygon_intermediate.py",
    "tools/pipeline/collision_polygon_inputs.py",
    "tools/pipeline/collision_polygon_recipe.py",
    "tools/pipeline/collision_polygon_output.py",
    "tools/pipeline/prepare_collision_polygon_intermediate.py",
)


def quality_steps():
    workflow = yaml.load(Path(".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    return workflow["jobs"]["quality"]["steps"]


def individual_gate():
    commands = [
        shlex.split(line) for step in quality_steps() for line in step.get("run", "").splitlines()
    ]
    gates = [c for c in commands if c[:3] == ["python", "-m", "tools.qa.coverage_gate"]]
    assert (
        gates.count(["python", "-m", "tools.qa.coverage_gate", "build/python-coverage.json"]) == 1
    )
    collision = [g for g in gates if NEW_MODULES[0] in g]
    assert len(collision) == 1
    gate = collision[0]
    assert gate[3:5] == ["build/python-coverage.json", "--files"]
    assert len(gate[5:]) == len(set(gate[5:])) == 10
    assert set(NEW_MODULES) <= set(gate[5:])
    return gate[5:]


def test_quality_keeps_full_discovery_helpers_gates_and_reports():
    individual_gate()
    steps = quality_steps()
    test_step = next(s for s in steps if s.get("name") == "Python tests and coverage gate")
    command = shlex.split(test_step["run"].splitlines()[0])
    assert command == [
        "python",
        "-m",
        "pytest",
        "--cov=tools",
        "--cov-report=xml:build/python-coverage.xml",
        "--cov-report=json:build/python-coverage.json",
        "--cov-report=term-missing",
        "--junitxml=build/pytest.xml",
    ]
    upload = next(s for s in steps if s.get("with", {}).get("name") == "python-test-reports")
    assert upload["if"] == "always()"
    assert set(upload["with"]["path"].splitlines()) == {
        "build/python-coverage.xml",
        "build/python-coverage.json",
        "build/pytest.xml",
    }
    lint = next(s for s in steps if s.get("name") == "Lint and formatting")
    for command in lint["run"].splitlines():
        tokens = shlex.split(command)
        assert {
            "tests/collision_polygon_package_oracle.py",
            "tests/collision_polygon_package_fixtures.py",
            "tests/collision_polygon_recipe_fixtures.py",
        } <= set(tokens)


@pytest.mark.parametrize("module", NEW_MODULES)
@pytest.mark.parametrize(
    "fault,expected",
    [
        ("exact_80", 0),
        ("lines_79", 1),
        ("branches_79", 1),
        ("missing", 1),
        ("empty", 1),
        ("invalid", 1),
    ],
)
def test_each_module_gate_cannot_be_hidden_by_good_global_coverage(
    tmp_path, capsys, module, fault, expected
):
    names = individual_gate()
    good = dict(covered_lines=100, num_statements=100, covered_branches=100, num_branches=100)
    report = dict(totals=good, files={k: dict(summary=good.copy()) for k in names})
    if fault == "missing":
        del report["files"][module]
    elif fault == "invalid":
        report["files"][module]["summary"] = None
    else:
        row = report["files"][module]["summary"]
        row.update(covered_lines=80, covered_branches=80)
        if fault == "lines_79":
            row["covered_lines"] = 79
        elif fault == "branches_79":
            row["covered_branches"] = 79
        elif fault == "empty":
            row.update(covered_lines=0, num_statements=0, covered_branches=0, num_branches=0)
    path = tmp_path / "measured-control.json"
    path.write_text(json.dumps(report))
    assert main([str(path)]) == 0
    capsys.readouterr()
    assert main([str(path), "--files", *names]) == expected
    message = capsys.readouterr().out
    if fault in ("lines_79", "branches_79", "empty"):
        assert module in message
