"""Filesystem adapter and CLI for read-only edition identification."""

import argparse
import hashlib
import json
from pathlib import Path

from tools.pipeline.profile import (
    GameProfile,
    ProfileError,
    parse_profile,
    safe_relative_path,
    verify_profile,
)

MAX_PROFILE_BYTES = 1024 * 1024


def load_profile(path: Path) -> GameProfile:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_PROFILE_BYTES + 1)
        if len(raw) > MAX_PROFILE_BYTES:
            raise ProfileError("INVALID_PROFILE", "Profile exceeds 1 MiB")
        return parse_profile(json.loads(raw))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProfileError("PROFILE_READ_ERROR", "Cannot read a valid profile JSON") from error


class LocalFileInspector:
    def __init__(self, root: Path):
        if root.is_symlink():
            raise ProfileError("INVALID_PATH", "Symlinks are not valid data roots")
        self.root = root.resolve()
        if not self.root.is_dir():
            raise ProfileError("DATA_ROOT_ERROR", "Data root is not a directory")

    def inspect(self, relative_path: str) -> tuple[int, str]:
        relative_path = safe_relative_path(relative_path)
        candidate = self.root
        for part in relative_path.split("/"):
            candidate = candidate / part
            if candidate.is_symlink():
                raise ProfileError("INVALID_PATH", "Symlinks are not valid profile inputs")
        if not candidate.resolve().is_relative_to(self.root):
            raise ProfileError("INVALID_PATH", "Input escapes data root")
        if not candidate.is_file():
            raise ProfileError("MISSING_FILE", f"Missing regular file: {relative_path}")
        digest = hashlib.sha256()
        total = 0
        try:
            before = candidate.stat()
            with candidate.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    total += len(chunk)
                    digest.update(chunk)
            after = candidate.stat()
        except OSError as error:
            raise ProfileError("READ_ERROR", f"Cannot read: {relative_path}") from error
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ino,
        ):
            raise ProfileError("INPUT_CHANGED", f"Input changed while reading: {relative_path}")
        return total, digest.hexdigest()


def verify_local(profile: GameProfile, root: Path, repository: Path) -> None:
    if profile.platform != "synthetic" and (
        root.resolve().is_relative_to(repository.resolve())
        or repository.resolve().is_relative_to(root.resolve())
    ):
        raise ProfileError("PRIVATE_DATA_IN_REPO", "PS2 data must be outside the repository")
    verify_profile(profile, LocalFileInspector(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        profile = load_profile(args.profile)
        repository = Path(__file__).resolve().parents[2]
        verify_local(profile, args.data_root, repository)
    except ProfileError as error:
        print(json.dumps({"status": "rejected", "code": error.code, "message": str(error)}))
        return 1
    print(
        json.dumps(
            {
                "status": "identified",
                "profile": profile.profile_id,
                "files": len(profile.files),
                "extraction": "not_performed",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
