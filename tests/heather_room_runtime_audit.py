"""Explicit private integration audit. Emits only identity/status metadata, no source payload."""

import argparse
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.pipeline.collision_polygon_inputs import PinnedInputs  # noqa: E402
from tools.pipeline.heather_room_contacts import require  # noqa: E402
from tools.pipeline.intermediate_assets import sha  # noqa: E402
from tools.pipeline.intermediate_json import encode_json  # noqa: E402
from tools.pipeline.prepare_heather_room_scene import read_bundle  # noqa: E402


def runtime_copy(source, path, custody):
    files, manifest = read_bundle(source)
    expected = set(files) | {
        "scene.srr",
        "source-scene-manifest.json",
        "manifest.json",
        ".manifest.pending.json",
    }
    require(set(os.listdir(path)) == expected, "HRR_AUDIT_INVENTORY")
    actual = {name: custody.read(path / name, 8 * 1024 * 1024) for name in expected}
    require(all(actual[n] == v for n, v in files.items()), "HRR_AUDIT_SOURCE")
    require(actual["source-scene-manifest.json"] == encode_json(manifest), "HRR_AUDIT_PARENT")
    raw = actual["scene.srr"]
    require(len(raw) == 596, "HRR_AUDIT_LENGTH")
    header = struct.unpack_from("<8s6I", raw)
    require(
        header
        == (
            b"S3RRv1\0\0",
            564,
            zlib.crc32(raw[32:]),
            zlib.crc32(files["map.srm"]),
            zlib.crc32(files["heather.sri"]),
            zlib.crc32(files["glass.rgba"]),
            1,
        ),
        "HRR_AUDIT_HEADER",
    )
    contact = json.loads(files["contacts.json"])["scene"]
    profile = json.loads(files["room-profile.json"])
    require(
        struct.unpack_from("<I4f", raw, 32) == (32, *contact["origin"], contact["floor_y"]),
        "HRR_AUDIT_ORIGIN",
    )
    require(
        struct.unpack_from("<4I", raw, 52) == tuple(int(v[4:], 16) for v in contact["floor"]),
        "HRR_AUDIT_FLOOR",
    )
    require(
        struct.unpack_from("<4f", raw, 68) == (*profile["spawn"]["world"], profile["spawn"]["yaw"]),
        "HRR_AUDIT_SPAWN",
    )
    require(
        struct.unpack_from("<128I", raw, 84)
        == tuple(int(v[4:], 16) for b in contact["blockers"] for v in b),
        "HRR_AUDIT_BOXES",
    )
    require(actual["manifest.json"] == actual[".manifest.pending.json"], "HRR_AUDIT_MANIFEST")
    entries = json.loads(actual["manifest.json"])["files"]
    data_names = expected - {"manifest.json", ".manifest.pending.json"}
    require(
        entries
        == [dict(file=n, size=len(actual[n]), sha256=sha(actual[n])) for n in sorted(data_names)],
        "HRR_AUDIT_HASHES",
    )
    return actual


def audit(args):
    custody = PinnedInputs()
    inputs = [
        runtime_copy(a, b, custody)
        for a, b in ((args.scene_a, args.runtime_a), (args.scene_b, args.runtime_b))
    ]
    require(inputs[0] == inputs[1], "HRR_AUDIT_AB")
    code = [
        "engine/application/room_loop.cpp",
        "engine/application/movement_controller.cpp",
        "engine/platform/common/room_runtime.cpp",
        "engine/platform/3ds/movement_controls.cpp",
        "engine/platform/3ds/render/room_renderer.cpp",
        "engine/platform/3ds/render/room_main.cpp",
        "tools/pipeline/prepare_heather_room_runtime.py",
        "tests/heather_room_runtime_audit.py",
        "tests/cpp/test_room_runtime.cpp",
        "tests/cpp/room_sdk.cpp",
    ]
    pins = {n: sha(custody.read(ROOT / n, 1024 * 1024)) for n in code}
    runs = []
    for executable in args.executable:
        binary = custody.read(executable, 64 * 1024 * 1024)
        for copy, path in (("copy-a", args.runtime_a), ("copy-b", args.runtime_b)):
            run = subprocess.run(
                [str(executable), str(path), "--private"], capture_output=True, timeout=180
            )
            require(
                run.returncode == 0
                and b"Room runtime: read/render/HID/clock/contacts/APT/retry/cleanup PASS"
                in run.stdout,
                "HRR_AUDIT_NATIVE",
            )
            runs.append(
                dict(
                    copy=copy,
                    executable_sha256=sha(binary),
                    output_sha256=sha(run.stdout),
                    cadences_hz=[25, 60, 143],
                    fixed_steps_per_replay=100,
                    status="passed",
                )
            )
    for i, pair in enumerate(((args.scene_a, args.runtime_a), (args.scene_b, args.runtime_b))):
        require(runtime_copy(*pair, custody) == inputs[i], "HRR_AUDIT_FINAL_READBACK")
    custody.verify()
    return dict(
        schema_version=1,
        task="HM-T4c.2",
        copies_identical=True,
        native_runs=runs,
        descriptor_sha256=sha(inputs[0]["scene.srr"]),
        descriptor_bytes=596,
        code_sha256=pins,
        sdk_calls="host_doubles",
        physical_validation=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scene-a", "scene-b", "runtime-a", "runtime-b"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--executable", type=Path, action="append", required=True)
    print(json.dumps(audit(parser.parse_args()), sort_keys=True))


if __name__ == "__main__":
    main()
