"""Run repository policy checks without network access or original game files."""

import argparse
import re
from pathlib import Path

from tools.qa.custody import check_custody

FORBIDDEN_HEADERS = {"filesystem", "fstream", "iostream", "cstdio", "stdio.h", "unistd.h"}
LAYER_IMPORTS = {
    "domain": {"domain"},
    "ports": {"domain", "ports"},
    "application": {"domain", "ports", "application"},
}


def check_architecture(root: Path) -> list[str]:
    errors = []
    for layer, allowed in LAYER_IMPORTS.items():
        for path in (root / "engine" / layer).rglob("*"):
            if path.suffix not in {".hpp", ".cpp", ".h"}:
                continue
            for include in re.findall(
                r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', path.read_text(), re.MULTILINE
            ):
                parts = include.split("/")
                forbidden = (
                    include in FORBIDDEN_HEADERS
                    or include.startswith(("3ds", "citro", "SDL", "GL/"))
                    or (parts[0] == "sh3" and (len(parts) < 3 or parts[1] not in allowed))
                    or ".." in parts
                )
                if forbidden:
                    errors.append(f"{path.relative_to(root)}: forbidden include {include}")
    return errors


def check_specs(root: Path) -> list[str]:
    base = root / "docs/specs/sh3-3ds"
    requirements = (base / "requirements.md").read_text()
    tasks = (base / "tasks.md").read_text()
    validation = (base / "validation.md").read_text()
    ids = re.findall(r"^- \*\*((?:RF|RNF)\d{2}\.\d{2}) \[[EPDU]\]\*\*", requirements, re.MULTILINE)
    errors = []
    if not ids or len(ids) != len(set(ids)):
        errors.append("Missing or duplicate EARS criteria")
    references = set(re.findall(r"\b(?:RF|RNF)\d{2}\.\d{2}\b", tasks))
    if set(ids) - references:
        errors.append("Criteria without task: " + ", ".join(sorted(set(ids) - references)))
    if references - set(ids):
        errors.append("Tasks reference undefined criteria")
    covered = set()
    for first, last in re.findall(
        r"\| V\d{2} \| ((?:RF|RNF)\d{2}\.\d{2})-((?:RF|RNF)\d{2}\.\d{2}) \|", validation
    ):
        group = first.split(".")[0]
        if group != last.split(".")[0]:
            errors.append("Cross-group validation range")
            continue
        covered.update(
            f"{group}.{number:02}"
            for number in range(int(first.split(".")[1]), int(last.split(".")[1]) + 1)
        )
    if covered != set(ids):
        errors.append("Validation matrix does not cover exactly the EARS criteria")
    for path in (root / "docs").rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            if not (path.parent / target.split("#")[0]).exists():
                errors.append(f"{path.relative_to(root)}: broken local link {target}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    errors = check_architecture(args.root) + check_custody(args.root) + check_specs(args.root)
    for error in errors:
        print(error)
    print(f"Repository checks: {'FAIL' if errors else 'PASS'} ({len(errors)} errors)")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
