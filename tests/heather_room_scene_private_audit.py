"""Explicit local A/B scene audit; stdout/report contain metadata only."""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.room_scene_oracle import check  # noqa: E402
from tools.pipeline.collision_polygon_inputs import PinnedInputs  # noqa: E402
from tools.pipeline.intermediate_assets import sha  # noqa: E402
from tools.pipeline.prepare_heather_room_scene import prepare, read_bundle  # noqa: E402


def requests_for(profile):
    spawn = profile["spawn"]["world"]
    origin = profile["coordinates"]["origin"]
    requests = [(i, spawn, 0) for i in range(58)]
    # All route endpoints, all clips, four quadrants; every original keyframe at spawn.
    for x, z in profile["inspection_route"]["local_xz"]:
        for sample in (0, 22, 46):
            for yaw in (0, math.pi / 2, -math.pi, -math.pi / 2):
                requests.append((sample, [origin[0] + x, 0, origin[2] + z], yaw))
    return requests


def audit(args):
    custody = PinnedInputs()
    code_names = [
        "engine/domain/room_scene.cpp",
        "engine/domain/include/sh3/domain/room_scene.hpp",
        "engine/platform/common/room_scene.cpp",
        "engine/platform/3ds/render/room_material_state.cpp",
        "tools/pipeline/heather_room_scene.py",
        "tools/pipeline/prepare_heather_room_scene.py",
        "tests/room_scene_oracle.py",
        "tests/room_scene_visual_audit.py",
        "tests/heather_room_scene_private_audit.py",
        "tests/cpp/test_room_scene.cpp",
    ]
    code_hashes = {name: sha(custody.read(ROOT / name, 1024 * 1024)) for name in code_names}
    files, preparation = prepare(
        {k: getattr(args, k) for k in ("profile", "catalog", "receipt", "copies")},
        args.heather_a,
        args.heather_b,
        args.reference,
        custody,
    )
    if args.bundle_a or args.bundle_b:
        if not (args.bundle_a and args.bundle_b):
            raise ValueError("AUDIT_BOTH_BUNDLES_REQUIRED")
        for copy, path in (("copy-a", args.bundle_a), ("copy-b", args.bundle_b)):
            actual, _ = read_bundle(path)
            if actual != files[copy]:
                raise ValueError("AUDIT_BUNDLE_RECONSTRUCTION")
    profile = json.loads(files["copy-a"]["room-profile.json"])
    requests = requests_for(profile)
    results = []
    for executable in args.executable:
        binary = custody.read(executable, 64 * 1024 * 1024)
        for copy, rig in (
            ("copy-a", args.bundle_a or args.heather_a),
            ("copy-b", args.bundle_b or args.heather_b),
        ):
            result, _, _ = check(executable, files[copy], rig, requests)
            results.append(dict(copy=copy, executable_sha256=sha(binary), **result))
    if args.bundle_a and args.bundle_b:
        for copy, path in (("copy-a", args.bundle_a), ("copy-b", args.bundle_b)):
            if read_bundle(path)[0] != files[copy]:
                raise ValueError("AUDIT_FINAL_BUNDLE_READBACK")
    custody.verify()
    report = dict(
        schema_version=1,
        task="HM-T4c.1",
        preparation=preparation,
        identical_ab=True,
        files_per_copy=len(files["copy-a"]),
        bytes_per_copy=sum(map(len, files["copy-a"].values())),
        code_sha256=code_hashes,
        prepared_files={
            k: dict(size=len(v), sha256=sha(v)) for k, v in sorted(files["copy-a"].items())
        },
        native_results=results,
        validated_published_bundles=bool(args.bundle_a and args.bundle_b),
        physical_validation=False,
    )
    if args.preview_root:
        report["visual"] = visual(files["copy-a"], args.bundle_a or args.heather_a, args)
    return report


def visual(files, rig, args):
    # NumPy/Pillow are local audit dependencies, not production or CI dependencies.
    import numpy as np
    from PIL import Image, ImageDraw

    from tests.room_scene_visual_audit import (
        framing,
        opaque_visibility,
        placed,
        pose_vertices,
        preview,
    )
    from tools.pipeline.private_texture_output import _write_bundle
    from tools.qa.locomotion_rig_oracle import reconstruct_sri2_bundle

    model = reconstruct_sri2_bundle(
        {k: v for k, v in files.items() if k == "heather.sri" or k.startswith("texture-")}
    )
    profile = json.loads(files["room-profile.json"])
    camera = json.loads(files["render-profile.json"])["camera"]
    old_camera = dict(camera, target_local=[275, -550, 100], vertical_fov_degrees=70)
    previous, final = framing(model, profile, old_camera), framing(model, profile, camera)
    if final["failing_vertex_halfspaces"]:
        raise ValueError("AUDIT_FRAMING")
    requests = [
        (0, [100275, 0, 140000], 0),
        (22, [100230, 0, 139850], 0),
        (46, [100320, 0, 140400], math.pi / 2),
        (57, [100230, 0, 139850], -math.pi),
    ]
    _, frames, (map_rows, shapes) = check(args.executable[0], files, rig, requests, range(4))
    textures = []
    for i, m in enumerate(model["materials"]):
        tex = (
            np.frombuffer(files[f"texture-{i:02}.rgba"], dtype=np.uint8)
            .reshape(m[4], m[3], 4)
            .copy()
        )
        tex[:, :, 3] = np.minimum(tex[:, :, 3].astype(np.uint16) * 2, 255)
        textures.append(tex[::-1].astype(float))
    textures.append(
        np.frombuffer(files["glass.rgba"], dtype=np.uint8).reshape(256, 256, 4).astype(float)
    )
    sheet = Image.new("RGB", (800, 560), "#101820")
    labels = [
        "Idle / spawn",
        "Walk / near endpoint",
        "Run / far endpoint / turn",
        "Run / near endpoint / reverse",
    ]
    results = []
    draw = ImageDraw.Draw(sheet)
    for i, (sample, world, yaw) in enumerate(requests):
        local = [world[0] - 100000, world[1], world[2] - 140000]
        points = placed(pose_vertices(model, sample), local, yaw)
        visible = opaque_visibility(np.array(map_rows), shapes, points, camera)
        rendered, pixels = preview(map_rows, frames[i], textures, camera)
        if not pixels or visible["visible"] < visible["tested"] * 0.7:
            raise ValueError("AUDIT_OCCLUDED")
        x, y = (i % 2) * 400, (i // 2) * 280
        sheet.paste(rendered, (x, y + 20))
        draw.text((x + 8, y + 3), labels[i], fill="white")
        draw.text((x + 8, y + 262), "CPU diagnostic - 29 neutral shapes - not PICA", fill="#aabaca")
        results.append(dict(sample=sample, **visible, actor_pixels=pixels))
    import io

    out = io.BytesIO()
    sheet.save(out, format="PNG")
    report = dict(
        original_camera=previous, refined_camera=final, previews=results, physical_validation=False
    )
    _write_bundle(
        args.preview_root,
        ROOT,
        args.preview_name,
        {"contact-sheet.png": out.getvalue()},
        report,
        {"contact-sheet.png"},
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("profile", "catalog", "receipt", "copies", "heather-a", "heather-b", "reference"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--executable", action="append", type=Path, required=True)
    parser.add_argument("--bundle-a", type=Path)
    parser.add_argument("--bundle-b", type=Path)
    parser.add_argument("--preview-root", type=Path)
    parser.add_argument("--preview-name", default="heather-room-scene-visual-v1")
    args = parser.parse_args()
    print(json.dumps(audit(args), sort_keys=True))


if __name__ == "__main__":
    main()
