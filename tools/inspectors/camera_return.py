"""RR01-RR07: reproduce a prior writer capture and compare a new session and return."""

import argparse
import json
from pathlib import Path

from tools.inspectors.camera_writer import collect_writer_report
from tools.inspectors.candidate_inventory import publish_report
from tools.inspectors.observation_capture import require
from tools.inspectors.return_compare import compare_writer_pairs
from tools.pipeline.extract_assets import load_catalog
from tools.pipeline.profile import ProfileError


def collect_return_report(
    plan,
    plan_hash,
    origin,
    origin_hash,
    previous,
    previous_hash,
    old_capture_hash,
    old_root,
    capture_hash,
    root,
    repository,
):
    reproduced = collect_writer_report(
        plan, plan_hash, origin, origin_hash, old_capture_hash, old_root, repository
    )
    require(reproduced == previous, "RETURN_PREVIOUS_REPORT")
    current = collect_writer_report(
        plan, plan_hash, origin, origin_hash, capture_hash, root, repository, with_return=True
    )
    require(
        current["session_id"] != previous["session_id"]
        and current["resource"] == previous["resource"],
        "RETURN_SESSION",
    )
    pairs = compare_writer_pairs(previous, current)
    return {
        "schema_version": 1,
        "tool": {"name": "sh3-camera-return", "version": 1},
        "status": "compared_writer_repetition_and_return",
        "evidence": {
            **current["evidence"],
            "previous_report_sha256": previous_hash,
            "previous_capture_sha256": old_capture_hash,
        },
        "previous_session_id": previous["session_id"],
        "previous_reproduced": True,
        "current": current,
        "pair_comparisons": pairs,
        "repetition_equal": any(p["equal"] for p in pairs),
        "return_equal_to_historical": current["return"]["against_historical"]["equal"],
        "execution_authentication": "not_provided",
        "mapping_verified": False,
        "origin_status": "pending",
        "resource_links": [],
        "capabilities": [],
        "f02_07_status": "pending",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("plan", "origin", "previous"):
        parser.add_argument("--" + key, type=Path, required=True)
        parser.add_argument("--" + key + "-sha256", required=True)
    for key in ("capture", "previous-capture"):
        parser.add_argument("--" + key + "-root", type=Path, required=True)
        parser.add_argument("--" + key + "-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(not args.output.exists() and not args.output.is_symlink(), "OUTPUT_EXISTS")
        report = collect_return_report(
            load_catalog(args.plan, args.plan_sha256),
            args.plan_sha256,
            load_catalog(args.origin, args.origin_sha256),
            args.origin_sha256,
            load_catalog(args.previous, args.previous_sha256),
            args.previous_sha256,
            args.previous_capture_sha256,
            args.previous_capture_root,
            args.capture_sha256,
            args.capture_root,
            Path(__file__).resolve().parents[2],
        )
        publish_report(args.output.absolute(), report)
    except (ProfileError, OSError, KeyError, TypeError, ValueError, IndexError) as error:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "code": error.code if isinstance(error, ProfileError) else "RETURN_INPUT_OR_IO",
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "repetition_equal": report["repetition_equal"],
                "return_equal_to_historical": report["return_equal_to_historical"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
