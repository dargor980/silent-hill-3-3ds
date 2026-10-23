import json

import pytest

from tools.qa.coverage_gate import check_totals, main


def test_low_branch_coverage_cannot_hide_behind_high_line_coverage():
    errors = check_totals(
        {"covered_lines": 100, "num_statements": 100, "covered_branches": 7, "num_branches": 10}
    )
    assert len(errors) == 1
    assert "branch" in errors[0]


def test_both_threshold_boundaries():
    assert (
        check_totals(
            {"covered_lines": 8, "num_statements": 10, "covered_branches": 8, "num_branches": 10}
        )
        == []
    )
    assert (
        len(
            check_totals(
                {
                    "covered_lines": 7,
                    "num_statements": 10,
                    "covered_branches": 8,
                    "num_branches": 10,
                }
            )
        )
        == 1
    )


def test_empty_denominator_is_not_coverage_success():
    assert (
        len(
            check_totals(
                {"covered_lines": 0, "num_statements": 0, "covered_branches": 0, "num_branches": 0}
            )
        )
        == 2
    )


def test_cli_valid_missing_and_malformed_report(tmp_path):
    report = tmp_path / "coverage.json"
    assert main([str(report)]) == 1
    report.write_text("invalid")
    assert main([str(report)]) == 1
    report.write_text(
        json.dumps(
            {
                "totals": {
                    "covered_lines": 10,
                    "num_statements": 10,
                    "covered_branches": 10,
                    "num_branches": 10,
                }
            }
        )
    )
    assert main([str(report)]) == 0


@pytest.mark.parametrize(
    "variant", ["pass", "low_line", "low_branch", "empty", "missing", "invalid"]
)
def test_each_selected_module_must_pass_even_if_global_totals_are_high(tmp_path, capsys, variant):
    passing = dict(covered_lines=100, num_statements=100, covered_branches=100, num_branches=100)
    selected = passing.copy()
    if variant == "low_line":
        selected["covered_lines"] = 79
    elif variant == "low_branch":
        selected["covered_branches"] = 79
    elif variant == "empty":
        selected.update(covered_branches=0, num_branches=0)
    elif variant == "invalid":
        selected = None
    report = dict(
        totals=passing,
        files={"first.py": dict(summary=passing), "second.py": dict(summary=selected)},
    )
    if variant == "missing":
        del report["files"]["second.py"]
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(report))
    assert main([str(path)]) == 0
    assert main([str(path), "--files", "first.py", "second.py"]) == (0 if variant == "pass" else 1)
    output = capsys.readouterr().out
    if variant in ("low_line", "low_branch", "empty"):
        assert "second.py:" in output
