"""Authenticate both hp34 copies, then exclusively publish reconstructible private bundles."""

import argparse
import json
import os
from pathlib import Path

from tools.pipeline.collision_polygon_inputs import PinnedInputs, absolute_path, read_at
from tools.pipeline.collision_polygon_recipe import indexed, pick
from tools.pipeline.heather_room_contacts import (
    LIMITS,
    equal,
    make_package,
    read_profile,
    require,
    verify_package,
)
from tools.pipeline.intermediate_assets import fields, sha
from tools.pipeline.intermediate_json import decode_json
from tools.pipeline.private_files import _identity, _inode, _open_directory
from tools.pipeline.private_texture_output import _write_bundle


def _prepare(paths, custody):
    fields(paths, ("profile", "catalog", "receipt", "copies"))
    paths = {k: absolute_path(str(v)) for k, v in paths.items()}
    profile_raw = custody.read(paths["profile"], 16384)
    profile = read_profile(profile_raw)
    documents = {}
    for key, pin in (("catalog", "catalog_sha256"), ("receipt", "extraction_receipt_sha256")):
        raw = custody.read(paths[key], 8 * 1024 * 1024)
        require(sha(raw) == profile[pin], "HRC_PREP_ANCHOR")
        documents[key] = decode_json(raw)
    catalog, receipt = documents["catalog"], documents["receipt"]
    equal(catalog["schema_version"], 1)
    equal(receipt["schema_version"], 1)
    equal(receipt["status"], "verified")
    equal(receipt["catalog_sha256"], profile["catalog_sha256"])
    equal(receipt["source"], catalog["source"])
    equal(receipt["selection"], catalog["selection"])
    entries, records = indexed(catalog["entries"]), indexed(receipt["resources"])
    require(entries.keys() == records.keys(), "HRC_PREP_INVENTORY")
    fields(receipt["copies"], ("copy-a", "copy-b"))
    copies = {name: indexed(rows) for name, rows in receipt["copies"].items()}
    require(all(rows.keys() == records.keys() for rows in copies.values()), "HRC_PREP_INVENTORY")
    sources = {name: {} for name in copies}
    for role, pin in profile["resources"].items():
        entry, record = entries[pin["id"]], records[pin["id"]]
        equal(pick(entry, ("id", "size", "sha256")), pin)
        equal(
            pick(entry, ("id", "size", "sha256", "container_id", "container_offset")),
            pick(record, ("id", "size", "sha256", "container_id", "container_offset")),
        )
        equal(record["file"], pin["id"][6:] + ".bin")
        require(
            type(pin["size"]) is int and 0 < pin["size"] <= 32 * 1024 * 1024,
            "HRC_PREP_RESOURCE_SIZE",
        )
        for name, rows in copies.items():
            equal(
                pick(rows[pin["id"]], ("id", "size", "sha256", "file")),
                pick(record, ("id", "size", "sha256", "file")),
            )
            sources[name][role] = custody.read(
                paths["copies"] / name / record["file"], pin["size"], pick(pin, ("size", "sha256"))
            )
        require(sources["copy-a"][role] == sources["copy-b"][role], "HRC_PREP_AB")
    # All three selected resources in BOTH copies pass before any CLD decoder runs.
    packages = {
        name: make_package(parts["collision"], profile_raw) for name, parts in sources.items()
    }
    require(packages["copy-a"] == packages["copy-b"], "HRC_PREP_AB_PACKAGE")
    report = verify_package(packages["copy-a"])
    require(verify_package(packages["copy-b"]) == report, "HRC_PREP_AB_REPORT")
    custody.verify()
    return packages, report


def prepare_files(paths):
    return _prepare(paths, PinnedInputs())


def _read_bundle(directory, pending=False):
    manifest_name = ".manifest.pending.json" if pending else "manifest.json"
    names = set(os.listdir(directory))
    require(
        names
        in (set(LIMITS) | {manifest_name}, set(LIMITS) | {manifest_name, ".manifest.pending.json"}),
        "HRC_PREP_OUTPUT_SET",
    )
    manifest_raw, manifest_identity = read_at(directory, manifest_name, 16384)
    identities = {manifest_name: manifest_identity}
    if not pending and ".manifest.pending.json" in names:
        other, identity = read_at(directory, ".manifest.pending.json", 16384)
        require(other == manifest_raw, "HRC_PREP_MANIFEST")
        identities[".manifest.pending.json"] = identity
    files = {}
    for name, limit in LIMITS.items():
        files[name], identities[name] = read_at(directory, name, limit)
    report = verify_package(files)
    inventory = [dict(file=k, size=len(v), sha256=sha(v)) for k, v in sorted(files.items())]
    equal(decode_json(manifest_raw), {**report, "files": inventory}, "HRC_PREP_MANIFEST")
    require(set(os.listdir(directory)) == names, "HRC_PREP_OUTPUT_SET")
    for name, identity in identities.items():
        require(
            _identity(os.stat(name, dir_fd=directory, follow_symlinks=False)) == identity,
            "HRC_PREP_OUTPUT_CHANGED",
        )
    return files, report


def read_bundle(path):
    path = absolute_path(str(path))
    directory = _open_directory(path)
    try:
        result = _read_bundle(directory)
        current = _open_directory(path)
        try:
            require(
                _inode(os.fstat(current)) == _inode(os.fstat(directory)), "HRC_PREP_OUTPUT_CHANGED"
            )
        finally:
            os.close(current)
        return result
    finally:
        os.close(directory)


def prepare_and_write(paths, private_root, repository, run_prefix):
    custody = PinnedInputs()
    packages, report = _prepare(paths, custody)
    manifests = {}
    for copy, files in packages.items():

        def before_publish(directory, _manifest, files=files):
            custody.verify()
            actual, result = _read_bundle(directory, pending=True)
            require(actual == files and result == report, "HRC_PREP_READBACK")

        manifests[copy] = _write_bundle(
            private_root,
            repository,
            run_prefix + "-" + copy,
            files,
            report,
            set(LIMITS),
            before_publish=before_publish,
        )
    # Pair acceptance is after both exclusive per-copy commits and final independent opens.
    custody.verify()
    for copy, files in packages.items():
        require(
            read_bundle(private_root / (run_prefix + "-" + copy)) == (files, report),
            "HRC_PREP_PAIR_READBACK",
        )
    return manifests


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("profile", "catalog", "receipt", "copies", "private-root"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--run-prefix", required=True)
    args = parser.parse_args(argv)
    try:
        prepare_and_write(
            {k: getattr(args, k) for k in ("profile", "catalog", "receipt", "copies")},
            args.private_root,
            Path(__file__).resolve().parents[2],
            args.run_prefix,
        )
    except (ValueError, OSError, KeyError, TypeError, IndexError, OverflowError) as error:
        print(json.dumps(dict(status="rejected", error_type=type(error).__name__)))
        return 1
    print(json.dumps(dict(status="prepared", copies=2, blockers=32)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
