"""Private A/B SRM2 conformance: native geometry, ordered ranges, fixed light and budgets."""

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.room_scene_oracle import capture  # noqa: E402
from tools.pipeline.collision_polygon_inputs import PinnedInputs  # noqa: E402
from tools.pipeline.heather_room_contacts import require  # noqa: E402
from tools.pipeline.intermediate_assets import sha  # noqa: E402
from tools.pipeline.prepare_heather_room_materials import read_runtime  # noqa: E402
from tools.pipeline.prepare_heather_room_scene import read_bundle  # noqa: E402


def audit(a):
    custody = PinnedInputs()
    requests = [
        (0, [100275, 0, 140000], 0),
        (22, [100230, 0, 139850], 0),
        (46, [100320, 0, 140400], 1.5707963),
        (57, [100230, 0, 139850], -3.1415927),
    ]
    results, first = [], None
    for scene, runtime in ((a.scene_a, a.runtime_a), (a.scene_b, a.runtime_b)):
        data, manifest = read_runtime(scene, runtime, custody)
        source, _ = read_bundle(scene)
        require(first is None or first == data, "MATERIAL_AUDIT_AB")
        first = data
        raw = data["map.srm"]
        shapes = list(struct.iter_unpack("<6I", raw[32 : 32 + 31 * 24]))
        materials = list(struct.iter_unpack("<4I", raw[32 + 31 * 24 : 32 + 31 * 24 + 9 * 16]))
        expected = [
            (materials[m][3], start, n, 14 + m)
            for _, start, n, glass, m, visible in shapes
            if not glass and visible
        ]
        require(len(expected) == 26, "MATERIAL_AUDIT_VISIBLE")
        wire_vertices = list(struct.iter_unpack("<9f", raw[32 + 31 * 24 + 9 * 16 :]))
        for executable in a.executable:
            identity = sha(custody.read(executable, 64 * 1024 * 1024))
            old = capture(executable, source["map.srm"], scene, requests)
            new = capture(executable, raw, runtime, requests)
            colored = capture(executable, raw, runtime, requests, diagnostic=True)
            require(new == colored, "MATERIAL_AUDIT_NO_RECOLOR")
            ledger, camera, vertices, desc, frames = new
            require(camera == old[1] and desc == old[3], "MATERIAL_AUDIT_CAMERA_SHAPES")
            require(
                all(
                    v[:4] == p[:4] and v[7:] == p[7:] and v[4:7] == w[4:7]
                    for v, p, w in zip(vertices, old[2], wire_vertices, strict=True)
                ),
                "MATERIAL_AUDIT_GEOMETRY_UV_LIGHT",
            )
            require(
                ledger[0] == 27787264 and ledger[-1] + 2097152 == 51726136, "MATERIAL_AUDIT_BUDGET"
            )
            for (verts, ranges), (old_verts, old_ranges) in zip(frames, old[4], strict=True):
                require(ranges[:26] == expected, "MATERIAL_AUDIT_ORDER")
                require(
                    ranges[26:] == old_ranges[29:] and verts == old_verts,
                    "MATERIAL_AUDIT_ACTOR_GLASS",
                )
            results.append(
                dict(
                    copy=runtime.name,
                    executable_sha256=identity,
                    runtime_manifest_sha256=sha(manifest),
                    frames=len(frames),
                    vertices=len(vertices),
                    submitted_internal=26,
                    texture_bytes=ledger[0],
                    accounted_bytes=ledger[-1] + 2097152,
                )
            )
    custody.verify()
    return dict(
        task="HM-T4c.3.3",
        copies_identical=True,
        results=results,
        hardware_validation=False,
        pixel_fidelity=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scene-a", "scene-b", "runtime-a", "runtime-b"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--executable", required=True, action="append", type=Path)
    print(json.dumps(audit(parser.parse_args()), sort_keys=True))


if __name__ == "__main__":
    main()
