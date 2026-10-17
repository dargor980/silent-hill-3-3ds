import json

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
