"""Publish identified private SD copies from authenticated HRS/HRR sources and ARM code."""

import argparse
import json
import os
from pathlib import Path

from tools.pipeline.collision_polygon_inputs import PinnedInputs, read_at
from tools.pipeline.heather_room_contacts import require
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.inspection_inputs import read_build
from tools.pipeline.intermediate_assets import sha
from tools.pipeline.intermediate_json import decode_json, encode_json
from tools.pipeline.prepare_heather_room_runtime import runtime_descriptor
from tools.pipeline.prepare_heather_room_scene import read_bundle
from tools.pipeline.private_texture_output import _write_bundle

STEM = "sh3_heather_room"
RUNTIME_NAMES = {"scene.srr", "map.srm", "glass.rgba", "heather.sri"} | {
    f"texture-{i:02}.rgba" for i in range(13)
}


def inventory(files):
    return [dict(file=n, size=len(v), sha256=sha(v)) for n, v in sorted(files.items())]


def read_runtime(scene, runtime, custody):
    if (runtime / "material-profile.json").exists():
        from tools.pipeline.prepare_heather_room_materials import read_runtime as read_materials

        return read_materials(scene, runtime, custody)
    files, parent = read_bundle(scene)
    expected = {
        **files,
        "scene.srr": runtime_descriptor(files),
        "source-scene-manifest.json": encode_json(parent),
    }
    names = set(os.listdir(runtime))
    require(
        names
        in (
            set(expected) | {"manifest.json"},
            set(expected) | {"manifest.json", ".manifest.pending.json"},
        ),
        "HRD_RUNTIME_SET",
    )
    actual = {n: custody.read(runtime / n, 8 * 1024 * 1024) for n in expected}
    require(actual == expected, "HRD_RUNTIME_CONTENT")
    raw = custody.read(runtime / "manifest.json", 65536)
    require(
        decode_json(raw)
        == dict(
            schema_version=1,
            task="HM-T4c.2",
            scope="private_room_runtime_data",
            source_manifest_sha256=sha(encode_json(parent)),
            packaged_executable=False,
            physical_validation=False,
            files=inventory(actual),
        ),
        "HRD_RUNTIME_MANIFEST",
    )
    if ".manifest.pending.json" in names:
        require(custody.read(runtime / ".manifest.pending.json", 65536) == raw, "HRD_PENDING")
    return actual, raw


def source_names(repository):
    return sorted(
        f for f in (repository / "engine").rglob("*") if f.suffix in (".cpp", ".hpp", ".pica")
    ) + [repository / "CMakeLists.txt"]


def verified_build(build, repository, custody, stem=STEM):
    artifacts, identity = read_build(build, stem)
    custody.read(build / "SHA256SUMS", 4096)
    for name, raw in artifacts.items():
        require(custody.read(build / name, 16 * 1024 * 1024) == raw, "HRD_BUILD_CHANGED")
    names = source_names(repository)
    computed = sha("".join(sha(custody.read(f, 2 * 1024 * 1024)) for f in names).encode())[:12]
    require(computed == identity and source_names(repository) == names, "HRD_BUILD_ID")
    require(
        artifacts["sdk-image.txt"]
        == custody.read(repository / "toolchains/devkitpro-image.txt", 4096),
        "HRD_SDK_IMAGE",
    )
    elf = artifacts[stem + ".elf"]
    require(elf[:6] == b"\x7fELF\x01\x01" and elf[18:20] == b"\x28\0", "HRD_ARM_ELF")
    require(
        identity.encode() in elf and identity.encode() in artifacts[stem + ".3dsx"],
        "HRD_EMBEDDED_ID",
    )
    return artifacts, identity


def prepare(scene, runtime, build, repository, custody):
    source, manifest = read_runtime(scene, runtime, custody)
    artifacts, identity = verified_build(build, repository, custody)
    guide = custody.read(repository / "docs/compatibility/heather-room.md", 65536)
    from tools.pipeline.prepare_heather_room_materials import TEXTURES

    original = "material-profile.json" in source
    files = {n: source[n] for n in RUNTIME_NAMES | (TEXTURES if original else set())}
    files.update({f"{STEM}.{ext}": artifacts[f"{STEM}.{ext}"] for ext in ("3dsx", "smdh")})
    files["LEEME.txt"] = f"SH3 Heather room / Build: {identity}\n\n".encode() + guide
    files["sd-card.zip"] = inspection_archive(files, STEM)
    report = dict(
        schema_version=1,
        task="HM-T4d",
        scope="private_room_sd_delivery",
        build_id=identity,
        source_runtime_manifest_sha256=sha(manifest),
        source_scene_manifest_sha256=sha(source["source-scene-manifest.json"]),
        build_files={n: sha(raw) for n, raw in sorted(artifacts.items())},
        label=(
            "MATERIALES ORIGINALES / LUZ FIJA"
            if original
            else "CAMARA FIJA PROPIA / 29 FORMAS: COLOR/LUZ DIAGNOSTICO"
        ),
        accounted_bytes=51726136 if original else 42288952,
        physical_validation=False,
        sd_installed=False,
    )
    return files, report


def publish(scene_a, scene_b, runtime_a, runtime_b, build, private_root, repository, prefix):
    custody = PinnedInputs()
    pairs = [(scene_a, runtime_a), (scene_b, runtime_b)]
    prepared = [prepare(*pair, build, repository, custody) for pair in pairs]
    require(prepared[0] == prepared[1], "HRD_AB")
    files, report = prepared[0]
    custody.verify()

    def validate_sources():
        custody.verify()
        require(
            [prepare(*pair, build, repository, custody) for pair in pairs] == prepared,
            "HRD_SOURCE_CHANGED",
        )

    manifests = []
    for copy in ("copy-a", "copy-b"):

        def verify(directory, _manifest):
            require(
                {n: read_at(directory, n, len(v))[0] for n, v in files.items()} == files,
                "HRD_OUTPUT_CHANGED",
            )
            validate_sources()

        manifests.append(
            _write_bundle(
                private_root,
                repository,
                prefix + "-" + copy,
                files,
                report,
                set(files),
                before_publish=verify,
                max_bytes=80 * 1024 * 1024,
            )
        )
    require(manifests[0] == manifests[1], "HRD_MANIFEST_AB")
    manifest_bytes = (json.dumps(manifests[0], sort_keys=True, indent=2) + "\n").encode()
    output = PinnedInputs()
    for copy in ("copy-a", "copy-b"):
        root = private_root / (prefix + "-" + copy)
        require(
            set(os.listdir(root)) == set(files) | {"manifest.json", ".manifest.pending.json"},
            "HRD_FINAL_SET",
        )
        require(
            {n: output.read(root / n, len(v)) for n, v in files.items()} == files,
            "HRD_FINAL_CONTENT",
        )
        for name in ("manifest.json", ".manifest.pending.json"):
            require(output.read(root / name, 65536) == manifest_bytes, "HRD_FINAL_MANIFEST")
    validate_sources()
    output.verify()
    return manifests[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scene-a", "scene-b", "runtime-a", "runtime-b", "build", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--run-prefix", required=True)
    a = parser.parse_args(argv)
    try:
        report = publish(
            a.scene_a,
            a.scene_b,
            a.runtime_a,
            a.runtime_b,
            a.build,
            a.private_root,
            Path(__file__).resolve().parents[2],
            a.run_prefix,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(dict(status="rejected", error_type=type(error).__name__)))
        return 1
    print(json.dumps(dict(status="prepared", copies=2, build_id=report["build_id"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
