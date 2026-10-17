"""RNF08.01: repository custody rules and a read-only Git/filesystem adapter."""

import os
import stat
import subprocess
from pathlib import Path, PurePosixPath

PRIVATE_SUFFIXES = {
    ".iso",
    ".mfa",
    ".afs",
    ".irx",
    ".img",
    ".bin",
    ".p2s",
    ".sav",
    ".cia",
    ".3dsx",
    ".elf",
    ".smdh",
}
GENERATED_SUFFIXES = {".bin", ".cia", ".3dsx", ".elf", ".smdh"}
REPORT_SUFFIXES = {".json", ".txt", ".md", ".csv", ".xml"}
ENVIRONMENT_PATHS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "build/linux-venv",
}


def _tracked_violation(path: PurePosixPath) -> bool:
    return (
        path.suffix.lower() in PRIVATE_SUFFIXES
        or (path.parts[:1] == ("binaries",) and path.as_posix() != "binaries/.gitignore")
        or path.parts[:2] == ("reports", "local")
    )


def _local_violation(path: PurePosixPath, kind: str, ignored: bool) -> str | None:
    """Decide from metadata only; no disk access or game-specific identifiers."""
    if kind == "symlink":
        return "Symlink outside excluded environment"
    suffix = path.suffix.lower()
    if kind == "directory":
        return "Binary input is not a regular file" if suffix in PRIVATE_SUFFIXES else None
    if kind != "file":
        return "Non-regular repository entry"
    if path.parts[:1] == ("binaries",):
        if path.as_posix() == "binaries/.gitignore" or (suffix == ".iso" and ignored):
            return None
        return "ISO inbox permits only ignored regular ISO files and .gitignore"
    if path.parts[:2] == ("reports", "local"):
        if suffix in REPORT_SUFFIXES and ignored:
            return None
        return "Local reports must be ignored metadata files"
    if suffix in PRIVATE_SUFFIXES:
        if path.parts[:1] == ("build",) and suffix in GENERATED_SUFFIXES:
            return None
        return "Private/generated binary outside its permitted location"
    return None


def _git_paths(root: Path, *args: str) -> set[str]:
    output = subprocess.run(
        ["git", "-C", str(root), "ls-files", *args], check=True, capture_output=True
    ).stdout.decode("utf-8")
    return set(output.split("\0")) - {""}


def check_custody(root: Path) -> list[str]:
    """Inspect the index and lstat metadata, without opening data or following links."""
    errors = []
    ignored = set()
    if (root / ".git").exists():
        try:
            tracked = _git_paths(root, "--cached", "-z")
            ignored = _git_paths(
                root,
                "--others",
                "--ignored",
                "--exclude-standard",
                "-z",
                "--",
                "binaries",
                "reports/local",
            )
        except (OSError, UnicodeError, subprocess.CalledProcessError):
            errors.append("Cannot verify Git custody of local private data")
        else:
            for name in sorted(tracked):
                if _tracked_violation(PurePosixPath(name)):
                    errors.append(f"Private/generated data tracked by Git: {name}")

    def walk_error(error: OSError) -> None:
        errors.append("Cannot inspect repository directory metadata")

    for directory, directories, files in os.walk(root, followlinks=False, onerror=walk_error):
        parent = Path(directory)
        directories[:] = [
            name
            for name in directories
            if (parent / name).relative_to(root).as_posix() not in ENVIRONMENT_PATHS
        ]
        files = [
            name
            for name in files
            if (parent / name).relative_to(root).as_posix() not in ENVIRONMENT_PATHS
        ]
        for name in sorted(directories + files):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            try:
                mode = path.lstat().st_mode
            except OSError:
                errors.append(f"Cannot inspect repository entry metadata: {relative}")
                continue
            if stat.S_ISLNK(mode):
                kind = "symlink"
            elif stat.S_ISDIR(mode):
                kind = "directory"
            elif stat.S_ISREG(mode):
                kind = "file"
            else:
                kind = "special"
            violation = _local_violation(PurePosixPath(relative), kind, relative in ignored)
            if violation:
                errors.append(f"{violation}: {relative}")
    return errors
