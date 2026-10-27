"""Compare reconstructed SRI2 with lossless decoded sources, without producer imports.

Source authentication is the caller's responsibility. Integer geometry is exact;
derived TR/helper/framing values compare their canonical f32 representation.
The separately implemented HL06 oracle supplies raw quaternion endpoints.
"""

import math
import struct
import zlib

from tools.qa.animation_precision import reconstruct_quaternion_f32
from tools.qa.locomotion_rig_oracle import reconstruct_sri2_bundle


def _same(actual, expected, field):
    if actual != expected:
        raise ValueError(f"HL_SOURCE_RECONSTRUCTION:{field}")


def _f32(values):
    return list(struct.unpack(f"<{len(values)}f", struct.pack(f"<{len(values)}f", *values)))


def audit_selection(files, geometry, animation, textures, descriptors):
    """Return aggregate evidence only after every selected field compares.

    The inputs are normalized lossless-decoder documents and original PS2 RGBA.
    No receipt from the producer is used to decide which data should be present.
    """
    result = reconstruct_sri2_bundle(files)
    mesh = geometry["mesh"]
    sk = mesh["skeleton"]
    parts = [s for s in mesh["submeshes"] if (1 << (s["header_words"][16] >> 16)) & 0x3021]
    bones = sorted({b for s in parts for v in s["vertices"] for b in v["bones"]})
    helpers = sorted({h for s in parts for g in s["groups"] for h in g["helper_indices"]})
    texture_ids = sorted({s["texture_index"] for s in parts})
    _same([b["source"] for b in result["bones"]], bones, "bones")
    parents = [-1 if sk["parents"][b] < 0 else bones.index(sk["parents"][b]) for b in bones]
    _same([b["parent"] for b in result["bones"]], parents, "parents")
    _same(
        b"".join(struct.pack("<HHhHHBB", *c[:7]) for c in result["clips"]),
        descriptors,
        "descriptors",
    )
    samples, quaternion_error = [], 0.0
    for packed, source in enumerate(result["sample_sources"]):
        tracks = {t["bone_index"]: t for t in animation["frames"][source]["tracks"]}
        values = []
        for compact, bone in enumerate(bones):
            track = tracks[bone]
            translation = track["translation"]
            if translation is None:
                parent = sk["matrices_columns"][sk["parents"][bone]]
                child = sk["matrices_columns"][bone]
                delta = [child[12 + i] - parent[12 + i] for i in range(3)]
                translation = [
                    sum(x * y for x, y in zip(parent[c : c + 3], delta, strict=True))
                    for c in (0, 4, 8)
                ]
            q = reconstruct_quaternion_f32(
                track["rotation_words"], negative_w=bool(track["flag"] & 4)
            )
            expected = _f32([*translation, *q])
            actual = result["samples"][packed][compact]
            _same(actual, expected, "TR")
            quaternion_error = max(
                quaternion_error, *(abs(x - y) for x, y in zip(actual[3:], q, strict=True))
            )
            values.append([*translation, *q])
        samples.append(values)
    helper_values = []
    for h in helpers:
        matrix = struct.unpack("<16f", struct.pack("<16I", *mesh["helper_matrix_words"][h]))
        helper_values.append([bones.index(mesh["helpers"][h][1]), *matrix])
    _same(result["helpers"], helper_values, "helpers")
    vertices, indices, materials = [], [], []
    for ti, texture in enumerate(texture_ids):
        first = len(indices)
        for part in (s for s in parts if s["texture_index"] == texture):
            base, cursor = len(vertices), 0
            for group in part["groups"]:
                end = cursor + group["header_words"][0]
                hs = [helpers.index(h) for h in group["helper_indices"]]
                for v in part["vertices"][cursor:end]:
                    weights = v["weights_q12"]
                    vertices.append(
                        [
                            *v["position_q4"],
                            *v["normal_q12"],
                            *v["uv_q12"],
                            *weights,
                            *([0] * (3 - len(weights))),
                            bones.index(v["primary_bone"]),
                            len(weights),
                            *hs,
                            *([255] * (2 - len(hs))),
                            0,
                        ]
                    )
                cursor = end
            _same(cursor, len(part["vertices"]), "groups")
            indices.extend(base + i for triangle in part["triangles"] for i in triangle)
        w, h, rgba = textures[texture]
        _same(files[f"texture-{ti:02}.rgba"], rgba, "pixels")
        blends = {int(bool(s["blend_partition"])) for s in parts if s["texture_index"] == texture}
        _same(len(blends), 1, "blend")
        materials.append([first, len(indices) - first, ti, w, h, blends.pop(), zlib.crc32(rgba)])
    _same(result["vertices"], vertices, "vertices")
    _same(result["indices"], indices, "indices")
    _same(result["materials"], materials, "materials")
    # Independent expression of the conservative framing bound: sum maximum
    # offsets along each ancestry path, then test primary and helper positions.
    center = [(samples[0][0][c] + samples[0][1][c]) / 2 for c in range(3)]
    lengths = [
        max(math.dist(f[b][:3], center if p < 0 else [0, 0, 0]) for f in samples)
        for b, p in enumerate(parents)
    ]
    distances = []
    for b in range(len(bones)):
        path = []
        while b >= 0:
            path.append(b)
            b = parents[b]
        distances.append(sum(lengths[i] for i in reversed(path)))
    radius = 0
    for v in vertices:
        point = [x / 16 for x in v[:3]]
        radius = max(radius, distances[v[11]] + math.dist(point, [0, 0, 0]))
        for hi in v[13 : 13 + v[12] - 1]:
            target, *matrix = helper_values[hi]
            position = [
                sum(matrix[c * 4 + r] * point[c] for c in range(3)) + matrix[12 + r]
                for r in range(3)
            ]
            radius = max(radius, distances[target] + math.dist(position, [0, 0, 0]))
    _same(result["framing"], _f32([*center, min(1.0, 1.4 / radius)]), "framing")
    return dict(
        samples=len(samples),
        bones=len(bones),
        raw_quaternion_max_error=quaternion_error,
        vertices=len(vertices),
        indices=len(indices),
        helpers=len(helpers),
        materials=len(materials),
        all_selected_fields_exact=True,
    )
