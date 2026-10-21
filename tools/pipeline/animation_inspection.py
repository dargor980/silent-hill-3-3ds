"""Bounded SAN1 encoder for the verified three-bone 0x1449 inspection profile."""

import math
import struct
import zlib


def vector(values, count, bound=100000):
    if not isinstance(values, (list, tuple)) or len(values) != count:
        raise ValueError("Invalid animation vector")
    if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > bound for v in values):
        raise ValueError("Invalid animation number")
    return tuple(float(v) for v in values)


def encode_clip(parents, translations, rotations):
    if parents != [-1, -1, 1] or len(translations) != 3 or len(rotations) != 24:
        raise ValueError("Unsupported clip shape")
    translations = [vector(t, 3) for t in translations]
    child_length = math.dist(translations[2], (0, 0, 0))
    if child_length < 0.001:
        raise ValueError("Empty child offset")
    center = tuple((translations[0][i] + translations[1][i]) / 2 for i in range(3))
    radius = max(
        math.dist(t, center) + (child_length if i == 1 else 0)
        for i, t in enumerate(translations[:2])
    )
    scale = min(1.0, 1.4 / radius)
    if child_length * scale < 0.001:
        raise ValueError("Unrepresentable child offset")
    quaternions = []
    for frame in rotations:
        if len(frame) != 3:
            raise ValueError("Missing animation track")
        for q in frame:
            q = vector(q, 4, 1.001)
            if abs(sum(v * v for v in q) - 1) > 0.001:
                raise ValueError("Non-unit quaternion")
            quaternions.extend(q)
    payload = struct.pack(
        "<3i4f9f288f", *parents, *center, scale, *(v for t in translations for v in t), *quaternions
    )
    return (
        struct.pack("<8s6I", b"S3ANv1\0\0", 3, 24, 0x1449, 3686, len(payload), zlib.crc32(payload))
        + payload
    )


def inspection_clip(skeleton, animation):
    if (
        skeleton["schema_version"] != 1
        or animation["schema_version"] != 1
        or skeleton["model_id"] != 0x209
        or animation["model_id"] != 0x209
        or skeleton["parents"] != [-1, -1, 1]
        or animation["frame_bytes"] != 46
        or len(animation["frames"]) != 76
        or len(skeleton["matrices_columns"]) != 3
    ):
        raise ValueError("Unsupported decoded resource")
    matrices = [vector(m, 16) for m in skeleton["matrices_columns"]]
    parent, child = matrices[1:]
    for m in matrices:
        if tuple(m[i] for i in (3, 7, 11, 15)) != (0, 0, 0, 1):
            raise ValueError("Non-affine rest matrix")
        for a in range(3):
            for b in range(3):
                if abs(sum(m[a * 4 + i] * m[b * 4 + i] for i in range(3)) - (a == b)) > 1e-5:
                    raise ValueError("Non-rigid rest matrix")
    # Inverse rigid parent applied to child origin, independently of the QA oracle.
    offset = tuple(
        sum(parent[c * 4 + i] * (child[12 + i] - parent[12 + i]) for i in range(3))
        for c in range(3)
    )
    translations = None
    rotations = []
    for frame in animation["frames"][:24]:
        tracks = frame["tracks"]
        if len(tracks) != 3 or [t["bone_index"] for t in tracks] != [0, 1, 2]:
            raise ValueError("Invalid track order")
        if tracks[2]["translation"] is not None:
            raise ValueError("Unexpected child translation")
        current = [vector(tracks[i]["translation"], 3) for i in range(2)] + [offset]
        if translations is not None and current != translations:
            raise ValueError("Variable translation is not verified")
        translations = current
        rotations.append([t["quaternion_xyzw"] for t in tracks])
    return encode_clip(skeleton["parents"], translations, rotations)
