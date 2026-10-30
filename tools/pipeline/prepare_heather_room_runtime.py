"""Derive bounded SRR1 runtime inputs from the authenticated, immutable HRS A/B packages."""

import argparse
import json
import struct
import zlib
from pathlib import Path

from tools.pipeline.heather_room_contacts import require
from tools.pipeline.intermediate_assets import sha
from tools.pipeline.intermediate_json import encode_json
from tools.pipeline.prepare_heather_room_scene import read_bundle, verify_files
from tools.pipeline.private_texture_output import _write_bundle


def runtime_descriptor(files):
    verify_files(files)
    scene = json.loads(files["contacts.json"])["scene"]
    profile = json.loads(files["room-profile.json"])

    def box(values):
        return b"".join(struct.pack("<I", int(v[4:], 16)) for v in values)

    payload = struct.pack("<I4f", 32, *scene["origin"], scene["floor_y"])
    payload += box(scene["floor"])
    payload += struct.pack("<4f", *profile["spawn"]["world"], profile["spawn"]["yaw"])
    payload += b"".join(box(b) for b in scene["blockers"])
    require(len(payload) == 564, "HRR_LENGTH")
    return (
        struct.pack(
            "<8s6I",
            b"S3RRv1\0\0",
            len(payload),
            zlib.crc32(payload),
            zlib.crc32(files["map.srm"]),
            zlib.crc32(files["heather.sri"]),
            zlib.crc32(files["glass.rgba"]),
            1,
        )
        + payload
    )


def publish(a, b, private_root, repository, prefix):
    packages = [read_bundle(p) for p in (a, b)]
    require(packages[0] == packages[1], "HRR_AB")
    files, manifest = packages[0]
    data = {
        **files,
        "scene.srr": runtime_descriptor(files),
        "source-scene-manifest.json": encode_json(manifest),
    }
    report = dict(
        schema_version=1,
        task="HM-T4c.2",
        scope="private_room_runtime_data",
        source_manifest_sha256=sha(encode_json(manifest)),
        packaged_executable=False,
        physical_validation=False,
    )
    outputs = []
    for copy in ("copy-a", "copy-b"):

        def verify(directory, _manifest):
            # The writer itself rereads every output. Recheck authenticated input custody.
            require(read_bundle(a) == packages[0] and read_bundle(b) == packages[1], "HRR_CHANGED")

        outputs.append(
            _write_bundle(
                private_root,
                repository,
                prefix + "-" + copy,
                data,
                report,
                set(data),
                before_publish=verify,
            )
        )
    require(outputs[0] == outputs[1], "HRR_OUTPUT_AB")
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scene-a", "scene-b", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--run-prefix", required=True)
    args = parser.parse_args(argv)
    try:
        publish(
            args.scene_a,
            args.scene_b,
            args.private_root,
            Path(__file__).resolve().parents[2],
            args.run_prefix,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(dict(status="rejected", error_type=type(error).__name__)))
        return 1
    print(json.dumps(dict(status="prepared", copies=2, descriptor_bytes=596)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
