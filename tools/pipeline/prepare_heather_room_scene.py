"""Authenticate A/B room inputs and original Heather; publish exclusive private scene data."""

import argparse
import json
import os
from pathlib import Path

from tools.pipeline.collision_polygon_inputs import PinnedInputs, absolute_path, read_at
from tools.pipeline.heather_room_contacts import read_profile, require
from tools.pipeline.heather_room_scene import REFERENCE_SHA, RENDER_PROFILE, make_scene
from tools.pipeline.intermediate_assets import sha, verify_file
from tools.pipeline.intermediate_json import decode_json, encode_json
from tools.pipeline.prepare_heather_room_contacts import _prepare as contact_inputs
from tools.pipeline.private_files import _inode, _open_directory
from tools.pipeline.private_texture_output import _write_bundle

RIG_NAMES = {"heather.sri"} | {f"texture-{i:02}.rgba" for i in range(13)}
EXTRA_NAMES = {
    "render-profile.json",
    "map.srm",
    "map-view.json",
    "source.map",
    "source.tex",
    "glass-reference.json",
    "glass.rgba",
    "heather-source-manifest.json",
}
CONTACT_NAMES = {"source.cld", "room-profile.json", "polygons.json", "contacts.json"}
OUTPUT_NAMES = RIG_NAMES | EXTRA_NAMES | CONTACT_NAMES


def _rig(root, profile, custody):
    raw = custody.read(root / "manifest.json", 65536)
    require(sha(raw) == profile["heather"]["package_manifest_sha256"], "HRS_RIG_MANIFEST_PIN")
    manifest = decode_json(raw)
    require(
        manifest["appearance"] == "original_normal_game"
        and manifest["model_resource"] == 522
        and manifest["animation_resource"] == 525,
        "HRS_RIG_APPEARANCE",
    )
    require([c["clip_id"] for c in manifest["clips"]] == [101, 109, 113], "HRS_RIG_CLIPS")
    entries = {f["file"]: f for f in manifest["files"]}
    require(
        set(entries) == RIG_NAMES and len(entries) == len(manifest["files"]), "HRS_RIG_INVENTORY"
    )
    files = {
        name: custody.read(
            root / name, 2 * 1024 * 1024, {k: entries[name][k] for k in ("size", "sha256")}
        )
        for name in sorted(entries)
    }
    return files, raw


def prepare(paths, heather_a, heather_b, reference, custody=None):
    custody = custody or PinnedInputs()
    contacts, _ = contact_inputs(paths, custody)
    profile = read_profile(contacts["copy-a"]["room-profile.json"])
    reference = custody.read(absolute_path(str(reference)), 65536)
    require(sha(reference) == REFERENCE_SHA, "HRS_REFERENCE_PIN")
    packages, summaries = {}, []
    for name, root in (("copy-a", heather_a), ("copy-b", heather_b)):
        root = absolute_path(str(root))
        rig, rig_manifest = _rig(root, profile, custody)
        sources = {}
        for role in ("map", "external_texture"):
            pin = profile["resources"][role]
            sources[role] = custody.read(
                absolute_path(str(paths["copies"])) / name / (pin["id"][6:] + ".bin"),
                pin["size"],
                {k: pin[k] for k in ("size", "sha256")},
            )
        files, summary = make_scene(
            sources["map"], sources["external_texture"], reference, profile, rig
        )
        packages[name] = {**files, **contacts[name], "heather-source-manifest.json": rig_manifest}
        summaries.append(summary)
    require(packages["copy-a"] == packages["copy-b"] and summaries[0] == summaries[1], "HRS_AB")
    custody.verify()
    return packages, _report(profile, summaries[0], contacts["copy-a"]["room-profile.json"])


def _report(profile, rig, profile_raw):
    return dict(
        schema_version=1,
        profile="heather-hp34-scene-v1",
        task="HM-T4c.1",
        scope="private_diagnostic_room_data",
        shape_count=profile["render"]["expected_shapes"],
        neutral_shapes=profile["render"]["expected_shapes"] - 2,
        glass_shapes=2,
        vertices=profile["render"]["expected_vertices"],
        triangles=profile["render"]["expected_triangles"],
        rig=rig,
        room_profile_sha256=sha(profile_raw),
        render_profile_sha256=sha(encode_json(RENDER_PROFILE)),
        glass_reference_sha256=REFERENCE_SHA,
        heather_manifest_sha256=profile["heather"]["package_manifest_sha256"],
        runtime_loop_integrated=False,
        physical_validation=False,
        label="CAMARA FIJA PROPIA / 29 FORMAS CON MATERIAL NEUTRO",
    )


def verify_files(files):
    require(set(files) == OUTPUT_NAMES, "HRS_OUTPUT_SET")
    from tools.pipeline.heather_room_contacts import verify_package

    verify_package({k: files[k] for k in CONTACT_NAMES})
    profile = read_profile(files["room-profile.json"])
    manifest_raw = files["heather-source-manifest.json"]
    require(
        sha(manifest_raw) == profile["heather"]["package_manifest_sha256"], "HRS_RIG_MANIFEST_PIN"
    )
    manifest = decode_json(manifest_raw)
    entries = {row["file"]: row for row in manifest["files"]}
    require(
        set(entries) == RIG_NAMES and len(entries) == len(manifest["files"]), "HRS_RIG_INVENTORY"
    )
    for name in RIG_NAMES:
        verify_file(files[name], entries[name])
    reconstructed, info = make_scene(
        files["source.map"],
        files["source.tex"],
        files["glass-reference.json"],
        profile,
        {k: files[k] for k in RIG_NAMES},
    )
    require(all(files[k] == v for k, v in reconstructed.items()), "HRS_RECONSTRUCTION")
    return info


def read_bundle(path):
    path = absolute_path(str(path))
    directory = _open_directory(path)
    custody = PinnedInputs()
    try:
        names = set(os.listdir(directory))
        require(
            names
            in (
                OUTPUT_NAMES | {"manifest.json"},
                OUTPUT_NAMES | {"manifest.json", ".manifest.pending.json"},
            ),
            "HRS_OUTPUT_SET",
        )
        raw = custody.read(path / "manifest.json", 65536)
        if ".manifest.pending.json" in names:
            require(custody.read(path / ".manifest.pending.json", 65536) == raw, "HRS_MANIFEST")
        files = {name: custody.read(path / name, 8 * 1024 * 1024) for name in OUTPUT_NAMES}
        require(sum(map(len, files.values())) <= 40 * 1024 * 1024, "HRS_PACKAGE_BUDGET")
        rig = verify_files(files)
        report = _report(read_profile(files["room-profile.json"]), rig, files["room-profile.json"])
        manifest = {
            **report,
            "files": [dict(file=k, size=len(v), sha256=sha(v)) for k, v in sorted(files.items())],
        }
        require(decode_json(raw) == manifest, "HRS_MANIFEST")
        custody.verify()
        current = _open_directory(path)
        try:
            require(
                _inode(os.fstat(current)) == _inode(os.fstat(directory))
                and set(os.listdir(current)) == names,
                "HRS_OUTPUT_CHANGED",
            )
        finally:
            os.close(current)
        return files, manifest
    finally:
        os.close(directory)


def publish(paths, heather_a, heather_b, reference, private_root, repository, run_prefix):
    custody = PinnedInputs()
    packages, report = prepare(paths, heather_a, heather_b, reference, custody)
    manifests = {}
    for copy, files in packages.items():

        def verify(directory, _manifest, files=files):
            actual = {name: read_at(directory, name, len(raw))[0] for name, raw in files.items()}
            require(actual == files and verify_files(actual) == report["rig"], "HRS_READBACK")
            custody.verify()

        manifests[copy] = _write_bundle(
            private_root,
            repository,
            run_prefix + "-" + copy,
            files,
            report,
            OUTPUT_NAMES,
            before_publish=verify,
        )
    custody.verify()
    # Compare finalized copies again before accepting the pair.
    for copy, files in packages.items():
        require(
            read_bundle(private_root / (run_prefix + "-" + copy)) == (files, manifests[copy]),
            "HRS_PAIR_READBACK",
        )
    return manifests


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "profile",
        "catalog",
        "receipt",
        "copies",
        "heather-a",
        "heather-b",
        "reference",
        "private-root",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--run-prefix", required=True)
    a = parser.parse_args(argv)
    try:
        result = publish(
            {k: getattr(a, k) for k in ("profile", "catalog", "receipt", "copies")},
            a.heather_a,
            a.heather_b,
            a.reference,
            a.private_root,
            Path(__file__).resolve().parents[2],
            a.run_prefix,
        )
    except (ValueError, OSError, KeyError, TypeError, IndexError, OverflowError) as error:
        print(json.dumps(dict(status="rejected", error_type=type(error).__name__)))
        return 1
    print(json.dumps(dict(status="prepared", copies=len(result), shapes=31, neutral_shapes=29)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
