"""SCM1 conversion: stored integer weights, helpers and homogeneous presentation."""

import math
import struct
import zlib

from tools.pipeline.animation_inspection import vector


def integers(values, count, low, high):
    if (
        not isinstance(values, (list, tuple))
        or len(values) != count
        or any(type(v) is not int or not low <= v <= high for v in values)
    ):
        raise ValueError("Invalid character integer vector")
    return tuple(values)


def encode_character(center, scale, targets, helpers, vertices, indices):
    center = vector(center, 3)
    scale = vector([scale], 1, 1)[0]
    targets = integers(targets, 3, 0, 2)
    if scale <= 0 or len(helpers) != 3 or not 3 <= len(vertices) <= 2048:
        raise ValueError("Unsupported character shape")
    if not 3 <= len(indices) <= 4608 or len(indices) % 3:
        raise ValueError("Invalid triangle count")
    matrices = [vector(m, 16) for m in helpers]
    if any(tuple(m[i] for i in (3, 7, 11, 15)) != (0, 0, 0, 1) for m in matrices):
        raise ValueError("Non-affine helper")
    payload = bytearray(
        struct.pack("<4f3I48f", *center, scale, *targets, *(x for m in matrices for x in m))
    )
    for v in vertices:
        count = len(v["weights_q12"])
        if not 1 <= count <= 3:
            raise ValueError("Unsupported influence count")
        weights = integers(v["weights_q12"], count, 0, 4096)
        if not 4097 - count <= sum(weights) <= 4096:
            raise ValueError("Invalid weight deficit")
        primary = integers([v["primary_bone"]], 1, 0, 2)[0]
        helper_ids = integers(v["helper_indices"], count - 1, 0, 2)
        position = integers(v["position_q4"], 3, -32768, 32767)
        normal = integers(v["normal_q12"], 3, -32768, 32767)
        uv = integers(v["uv_q12"], 2, -32768, 32767)
        payload += struct.pack(
            "<8h3H4BH",
            *position,
            *normal,
            *uv,
            *(weights + (0,) * (3 - count)),
            primary,
            count,
            *(helper_ids + (255,) * (3 - count)),
            0,
        )
    indices = integers(indices, len(indices), 0, len(vertices) - 1)
    payload += struct.pack(f"<{len(indices)}H", *indices)
    return (
        struct.pack(
            "<8s6I",
            b"S3CMv1\0\0",
            len(vertices),
            len(indices),
            3,
            28,
            len(payload),
            zlib.crc32(payload),
        )
        + payload
    )


def inspection_character(mesh, clip_bytes):
    if mesh["schema_version"] != 1 or len(mesh["helpers"]) != 3:
        raise ValueError("Unsupported mesh profile")
    if len(clip_bytes) != 1248 or clip_bytes[:8] != b"S3ANv1\0\0":
        raise ValueError("Unsupported animation profile")
    center = struct.unpack_from("<3f", clip_bytes, 44)
    translations = [struct.unpack_from("<3f", clip_bytes, 60 + 12 * i) for i in range(3)]
    targets = [integers(pair, 2, 0, 2)[1] for pair in mesh["helpers"]]
    matrices = [
        struct.unpack("<16f", struct.pack("<16I", *integers(m, 16, 0, 0xFFFFFFFF)))
        for m in mesh["helper_matrix_words"]
    ]
    if len(matrices) != 3:
        raise ValueError("Missing helper matrix")
    vertices, indices = [], []
    radius = 0.0
    for submesh in mesh["submeshes"]:
        if submesh["blend_partition"]:
            raise ValueError("Blend material is not verified")
        base, cursor = len(vertices), 0
        for group in submesh["groups"]:
            count = group["header_words"][0]
            if type(count) is not int or not 1 <= count <= 2048:
                raise ValueError("Invalid group count")
            for v in submesh["vertices"][cursor : cursor + count]:
                vertex = dict(v, helper_indices=group["helper_indices"])
                # Validate each influence's bone/helper association before conversion.
                primary = integers([v["primary_bone"]], 1, 0, 2)[0]
                helper_ids = integers(group["helper_indices"], len(group["helper_indices"]), 0, 2)
                expected = [primary] + [targets[h] for h in helper_ids]
                if v["bones"] != expected or len(v["weights_q12"]) != len(expected):
                    raise ValueError("Influence binding differs")
                point = vector([x / 16 for x in v["position_q4"]], 3)
                for i, bone in enumerate(expected):
                    p = point
                    if i:
                        h = matrices[group["helper_indices"][i - 1]]
                        p = tuple(
                            h[12 + r] + sum(h[4 * k + r] * point[k] for k in range(3))
                            for r in range(3)
                        )
                    root = 1 if bone == 2 else bone
                    bound = math.dist(translations[root], center) + math.dist(p, (0, 0, 0))
                    if bone == 2:
                        bound += math.dist(translations[2], (0, 0, 0))
                    radius = max(radius, bound)
                vertices.append(vertex)
            cursor += count
        if cursor != len(submesh["vertices"]):
            raise ValueError("Incomplete vertex groups")
        for triangle in submesh["triangles"]:
            indices.extend(base + i for i in integers(triangle, 3, 0, cursor - 1))
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("Invalid framing radius")
    return encode_character(center, min(1.0, 1.4 / radius), targets, matrices, vertices, indices)
