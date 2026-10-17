"""Inspect one explicit private copy against pinned catalog and extraction evidence."""

import argparse
import json
import os
from pathlib import Path

from tools.inspectors.candidates import collect_candidates
from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.private_files import _open_directory, _owned_stream
from tools.pipeline.profile import ProfileError
from tools.pipeline.transfer import write_all


def publish_report(path: Path, report: dict) -> None:
    raw = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    parent = _open_directory(path.parent)
    try:
        staging = "." + path.name + ".pending.json"
        fd = os.open(
            staging,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            mode=0o600,
            dir_fd=parent,
        )
        with _owned_stream(fd, "wb") as stream:
            write_all(stream, raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(staging, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
    finally:
        os.close(parent)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("catalog", "receipt", "private-copy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("catalog-sha256", "receipt-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ProfileError("OUTPUT_EXISTS", "Candidate report already exists")
        catalog = load_catalog(args.catalog, args.catalog_sha256)
        receipt = load_catalog(args.receipt, args.receipt_sha256)
        with VerifiedPrivateReader(
            args.private_copy, Path(__file__).resolve().parents[2]
        ) as reader:
            report = collect_candidates(
                reader, catalog, receipt, args.catalog_sha256, args.receipt_sha256
            )
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError) as error:
        code = error.code if isinstance(error, ProfileError) else "CANDIDATE_IO_ERROR"
        print(json.dumps({"status": "rejected", "code": code}))
        return 1
    print(json.dumps({"status": "inventoried", **report["summary"], "f02_07_status": "pending"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
