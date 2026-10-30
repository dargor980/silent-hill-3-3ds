"""Explicit private A/B audit of native diagnostic colors; stdout is metadata only.

NumPy/Pillow are optional local dependencies. Geometry and rendered pixels stay
in memory or in the explicitly selected private preview directory.
"""

import argparse
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.room_scene_oracle import capture  # noqa: E402
from tests.room_scene_visual_audit import preview  # noqa: E402
from tools.pipeline.collision_polygon_inputs import PinnedInputs  # noqa: E402
from tools.pipeline.heather_room_contacts import require  # noqa: E402
from tools.pipeline.intermediate_assets import sha  # noqa: E402
from tools.pipeline.prepare_heather_room_scene import read_bundle  # noqa: E402
from tools.pipeline.private_texture_output import _write_bundle  # noqa: E402
from tools.qa.locomotion_rig_oracle import reconstruct_sri2_bundle  # noqa: E402


def expected_colors(rows, shapes):
    """Independent vectorized normal/light calculation on the original native positions."""
    result = rows.copy()
    palette = np.array(
        [
            [0.68, 0.78, 0.88],
            [0.80, 0.61, 0.38],
            [0.42, 0.74, 0.66],
            [0.76, 0.47, 0.48],
            [0.61, 0.54, 0.79],
            [0.70, 0.73, 0.44],
        ],
        dtype=np.float32,
    ).astype(float)
    for shape, (_offset, first, count, glass) in enumerate(shapes):
        if glass:
            continue
        triangles = rows[first : first + count, :3].reshape(-1, 3, 3)
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        light = np.full(len(lengths), 0.65)
        nonzero = lengths > 1e-12
        unit = normals[nonzero] / lengths[nonzero, None]
        light[nonzero] = 0.32 + 0.68 * np.minimum(1, np.abs(unit @ [-0.48, 0.8, 0.36]))
        result[first : first + count, 4:7] = np.repeat(
            palette[shape % len(palette)][None, :] * light[:, None], 3, axis=0
        )
    return result


def audit(args):
    custody = PinnedInputs()
    requests = [
        (0, [100275, 0, 140000], 0),
        (22, [100230, 0, 139850], 0),
        (46, [100320, 0, 140400], math.pi / 2),
        (57, [100230, 0, 139850], -math.pi),
    ]
    results, first_files, saved = [], None, None
    for bundle in (args.bundle_a, args.bundle_b):
        files, _manifest = read_bundle(bundle)
        for name, raw in files.items():
            require(custody.read(bundle / name, 8 * 1024 * 1024) == raw, "DIAGNOSTIC_SOURCE")
        if first_files is None:
            first_files = files
        require(files == first_files, "DIAGNOSTIC_AB")
        for executable in args.executable:
            binary = custody.read(executable, 64 * 1024 * 1024)
            original = capture(executable, files["map.srm"], bundle, requests)
            colored = capture(executable, files["map.srm"], bundle, requests, diagnostic=True)
            ledger, camera, rows, shapes, frames = original
            require(colored[:2] == original[:2], "DIAGNOSTIC_CAMERA_MEMORY")
            require(colored[3:] == original[3:], "DIAGNOSTIC_ACTOR_GLASS_ORDER")
            before, after = np.array(rows), np.array(colored[2])
            require(np.array_equal(before[:, :4], after[:, :4]), "DIAGNOSTIC_GEOMETRY_W")
            require(np.array_equal(before[:, 7:], after[:, 7:]), "DIAGNOSTIC_UV")
            require(np.isfinite(after).all(), "DIAGNOSTIC_FINITE")
            expected = expected_colors(before, shapes)
            maximum = float(np.max(np.abs(expected[:, 4:7] - after[:, 4:7])))
            require(maximum < 1e-6, "DIAGNOSTIC_LIGHT_ORACLE")
            neutral_count = 0
            for _offset, start, count, glass in shapes:
                if glass:
                    require(
                        np.array_equal(before[start : start + count], after[start : start + count]),
                        "DIAGNOSTIC_GLASS",
                    )
                else:
                    neutral_count += count
            changed = int(np.count_nonzero(np.any(before[:, 4:7] != after[:, 4:7], axis=1)))
            require(changed == neutral_count and len(shapes) == 31, "DIAGNOSTIC_CHANGED_COLORS")
            results.append(
                dict(
                    bundle=bundle.name,
                    executable_sha256=sha(binary),
                    frames=len(requests),
                    shapes=len(shapes),
                    neutral_vertices=changed,
                    maximum_color_error=maximum,
                    ledger=list(ledger),
                )
            )
            if saved is None:
                saved = (before, after, frames)
    custody.verify()
    report = dict(
        task="HM-T5-diagnostic-appearance",
        copies_identical=True,
        native_results=results,
        physical_validation=False,
    )
    if args.preview_root:
        report["visual"] = render_preview(first_files, saved, args)
    custody.verify()
    return report


def render_preview(files, saved, args):
    model = reconstruct_sri2_bundle(
        {k: v for k, v in files.items() if k == "heather.sri" or k.startswith("texture-")}
    )
    textures = []
    for i, material in enumerate(model["materials"]):
        texture = (
            np.frombuffer(files[f"texture-{i:02}.rgba"], dtype=np.uint8)
            .reshape(material[4], material[3], 4)
            .copy()
        )
        texture[:, :, 3] = np.minimum(texture[:, :, 3].astype(np.uint16) * 2, 255)
        textures.append(texture[::-1].astype(float))
    textures.append(
        np.frombuffer(files["glass.rgba"], dtype=np.uint8).reshape(256, 256, 4).astype(float)
    )
    camera = json.loads(files["render-profile.json"])["camera"]
    before, after, frames = saved
    sheet = Image.new("RGB", (800, 560), "#101820")
    draw = ImageDraw.Draw(sheet)
    labels = ["Idle / spawn", "Walk / near", "Run / far / turn", "Run / near / reverse"]
    results = []
    for i, frame in enumerate(frames):
        old, old_actor = preview(before, frame, textures, camera)
        new, new_actor = preview(after, frame, textures, camera)
        require(old_actor == new_actor and new_actor > 1000, "DIAGNOSTIC_ACTOR_VISIBILITY")
        # Evaluate pixels that were the old neutral field, excluding textured actor/glass.
        old_pixels, new_pixels = np.array(old), np.array(new)
        neutral = np.all(old_pixels == [140, 147, 158], axis=2)
        count = int(neutral.sum())
        changed = int(np.count_nonzero(np.any(new_pixels[neutral] != old_pixels[neutral], axis=1)))
        colors = len(np.unique(new_pixels[neutral], axis=0))
        require(
            count > 60000 and changed > count * 0.95 and colors >= 12, "DIAGNOSTIC_VISIBLE_CONTRAST"
        )
        x, y = i % 2 * 400, i // 2 * 280
        sheet.paste(new, (x, y + 20))
        draw.text((x + 8, y + 3), labels[i], fill="white")
        draw.text((x + 8, y + 262), "Native colors - software preview, not PICA", fill="#aabaca")
        results.append(
            dict(
                actor_pixels=new_actor,
                old_neutral_pixels=count,
                changed_neutral_pixels=changed,
                visible_neutral_colors=colors,
            )
        )
    raw = io.BytesIO()
    sheet.save(raw, format="PNG")
    _write_bundle(
        args.preview_root,
        ROOT,
        args.preview_name,
        {"contact-sheet.png": raw.getvalue()},
        dict(previews=results, physical_validation=False),
        {"contact-sheet.png"},
    )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-a", type=Path, required=True)
    parser.add_argument("--bundle-b", type=Path, required=True)
    parser.add_argument("--executable", type=Path, action="append", required=True)
    parser.add_argument("--preview-root", type=Path)
    parser.add_argument("--preview-name", default="heather-room-diagnostic-visual-v1")
    print(json.dumps(audit(parser.parse_args()), sort_keys=True))


if __name__ == "__main__":
    main()
