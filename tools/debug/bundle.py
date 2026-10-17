"""Bind an ELF and 3DSX from one build; verify without executing either file."""

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path

FILES = ("sh3_diagnostic.3dsx", "sh3_diagnostic.elf")
MANIFEST = "debug-bundle.json"


class BundleError(ValueError):
    """Invalid identity or incomplete/mismatched evidence."""


def validate_id(build_id: str) -> None:
    if not isinstance(build_id, str) or not re.fullmatch(r"[0-9a-f]{12}", build_id):
        raise BundleError("INVALID_BUILD_ID")


def fingerprint(path: Path) -> dict:
    # Reject special files before opening (notably FIFOs) and do not follow symlinks.
    if not stat.S_ISREG(path.lstat().st_mode):
        raise BundleError(f"NOT_REGULAR: {path.name}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            size += len(chunk)
            digest.update(chunk)
    if size == 0:
        raise BundleError(f"EMPTY: {path.name}")
    return {"bytes": size, "sha256": digest.hexdigest()}


def create(directory: Path, build_id: str) -> dict:
    """Called only after a successful build, not to repair a failed verification."""
    validate_id(build_id)
    document = {
        "schema_version": 1,
        "build_id": build_id,
        "files": {name: fingerprint(directory / name) for name in FILES},
    }
    # Exclusive creation preserves earlier evidence if a directory is reused.
    with (directory / MANIFEST).open("x", encoding="utf-8") as output:
        output.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return document


def verify(directory: Path, manifest: Path, expected_build_id: str) -> dict:
    validate_id(expected_build_id)
    if not stat.S_ISREG(manifest.lstat().st_mode) or manifest.stat().st_size > 4096:
        raise BundleError("INVALID_MANIFEST_FILE")
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "build_id", "files"}
        or type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or not isinstance(document["files"], dict)
        or set(document["files"]) != set(FILES)
    ):
        raise BundleError("INVALID_MANIFEST")
    if document["build_id"] != expected_build_id:
        raise BundleError("BUILD_ID_MISMATCH")
    for name in FILES:
        entry = document["files"][name]
        if (
            not isinstance(entry, dict)
            or set(entry) != {"bytes", "sha256"}
            or type(entry["bytes"]) is not int
            or entry["bytes"] <= 0
            or not isinstance(entry["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        ):
            raise BundleError("INVALID_FILE_ENTRY")
        if fingerprint(directory / name) != entry:
            raise BundleError(f"ARTIFACT_MISMATCH: {name}")
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--build-id", required=True, help="ID recorded for the build/session")
    parser.add_argument("--manifest", type=Path, help="Recorded manifest (verify only)")
    args = parser.parse_args(argv)
    if args.action == "create" and args.manifest is not None:
        parser.error("--manifest applies only to verify")
    try:
        if args.action == "create":
            create(args.directory, args.build_id)
        else:
            verify(args.directory, args.manifest or args.directory / MANIFEST, args.build_id)
    except (OSError, ValueError) as error:
        # No traceback or file contents; this tool operates on synthetic build artifacts.
        print(f"debug-bundle: FAIL ({error})")
        return 1
    print(f"debug-bundle: PASS build={args.build_id} action={args.action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
