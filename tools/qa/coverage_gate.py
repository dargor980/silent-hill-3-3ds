"""Check line and branch coverage independently from coverage.py JSON output."""

import argparse
import json
from pathlib import Path


def check_totals(totals: dict, minimum: float = 80.0) -> list[str]:
    errors = []
    for label, hit, total in (
        ("line", "covered_lines", "num_statements"),
        ("branch", "covered_branches", "num_branches"),
    ):
        measured = totals[hit]
        available = totals[total]
        if not 0 <= measured <= available or available <= 0:
            errors.append(f"Invalid or empty {label} coverage denominator")
        elif 100.0 * measured / available < minimum:
            errors.append(f"{label} coverage {100.0 * measured / available:.2f}% < {minimum}%")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--files", nargs="+", help="Require the gate for each exact report file")
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text())
        if args.files:
            errors = [
                f"{name}: {error}"
                for name in args.files
                for error in check_totals(report["files"][name]["summary"])
            ]
        else:
            errors = check_totals(report["totals"])
    except (OSError, ValueError, KeyError, TypeError):
        errors = ["Missing or invalid coverage report"]
    for error in errors:
        print(error)
    print(f"Line/branch coverage gate: {'FAIL' if errors else 'PASS'}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
