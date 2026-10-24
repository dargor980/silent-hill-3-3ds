"""SRI1: bounded skeletal inspection, independent of the legacy horse formats."""

import math
import struct
import zlib

from tools.pipeline.animation_inspection import vector
from tools.pipeline.character_inspection import integers

MAGIC = b"S3RIv1\0\0"
MAX_BONES, MAX_SAMPLES, MAX_HELPERS = 73, 64, 128
MAX_VERTICES, MAX_INDICES, MAX_MATERIALS = 8192, 18000, 16


def encode_rig(
    parents,
    frames,
    targets,
    helpers,
    vertices,
    indices,
    materials,
    center,
    scale,
    clip_id,
    increment,
):
    nb, nf, nh, nv, ni, nm = map(len, (parents, frames, targets, vertices, indices, materials))
    if not (
        1 <= nb <= MAX_BONES
        and 2 <= nf <= MAX_SAMPLES
        and 0 <= nh <= MAX_HELPERS
        and 3 <= nv <= MAX_VERTICES
        and 3 <= ni <= MAX_INDICES
        and ni % 3 == 0
        and 1 <= nm <= MAX_MATERIALS
        and len(helpers) == nh
    ):
        raise ValueError("RI_COUNTS")
    parents = integers(parents, nb, -1, nb - 1)
    if any(p >= i for i, p in enumerate(parents)):
        raise ValueError("RI_PARENTS")
    center = vector(center, 3)
    scale = vector([scale], 1, 1)[0]
    if scale <= 0:
        raise ValueError("RI_SCALE")
    clip_id, increment = integers([clip_id, increment], 2, 1, 65535)
    if increment >= nf * 4096:
        raise ValueError("RI_INCREMENT")
    payload = bytearray(struct.pack(f"<4f{nb}i", *center, scale, *parents))
    for frame in frames:
        if len(frame) != nb:
            raise ValueError("RI_TRACKS")
        for translation, rotation in frame:
            t, q = vector(translation, 3), vector(rotation, 4, 1.001)
            if abs(sum(x * x for x in q) - 1) > 0.001:
                raise ValueError("RI_ROTATION")
            payload.extend(struct.pack("<7f", *t, *q))
    for target, matrix in zip(integers(targets, nh, 0, nb - 1), helpers, strict=True):
        h = vector(matrix, 16)
        if tuple(h[i] for i in (3, 7, 11, 15)) != (0, 0, 0, 1):
            raise ValueError("RI_HELPER")
        payload.extend(struct.pack("<I16f", target, *h))
    for v in vertices:
        count = len(v["weights_q12"])
        if not 1 <= count <= 3:
            raise ValueError("RI_INFLUENCES")
        weights = integers(v["weights_q12"], count, 0, 4096)
        if not 4097 - count <= sum(weights) <= 4096:
            raise ValueError("RI_WEIGHTS")
        primary = integers([v["primary_bone"]], 1, 0, nb - 1)[0]
        hs = integers(v["helper_indices"], count - 1, 0, nh - 1)
        payload.extend(
            struct.pack(
                "<8h3H4BH",
                *integers(v["position_q4"], 3, -32768, 32767),
                *integers(v["normal_q12"], 3, -32768, 32767),
                *integers(v["uv_q12"], 2, -32768, 32767),
                *(weights + (0,) * (3 - count)),
                primary,
                count,
                *(hs + (255,) * (3 - count)),
                0,
            )
        )
    payload.extend(struct.pack(f"<{ni}H", *integers(indices, ni, 0, nv - 1)))
    cursor, blended, total_pixels = 0, False, 0
    for i, material in enumerate(materials):
        first, count, texture, width, height, blend, crc = integers(material, 7, 0, 0xFFFFFFFF)
        if (
            first != cursor
            or count < 3
            or count % 3
            or first + count > ni
            or texture != i
            or width not in (128, 256, 512, 1024)
            or height not in (128, 256, 512, 1024)
            or blend not in (0, 1)
            or (blended and not blend)
        ):
            raise ValueError("RI_MATERIAL")
        blended |= bool(blend)
        total_pixels += width * height
        cursor += count
        payload.extend(struct.pack("<7I", *material))
    if cursor != ni or total_pixels > 8 * 1024 * 1024:
        raise ValueError("RI_MATERIAL_COVERAGE")
    return (
        struct.pack(
            "<8s14I",
            MAGIC,
            nb,
            nf,
            nh,
            nv,
            ni,
            nm,
            clip_id,
            increment,
            len(payload),
            zlib.crc32(payload),
            0,
            0,
            0,
            0,
        )
        + payload
    )


def heather_rig(geometry, animation, textures):
    """Explicit original-outfit mask; preserve complete inputs in their own package."""
    mesh = geometry["mesh"]
    skeleton = mesh["skeleton"]
    if (
        geometry["schema_version"] != 1
        or skeleton["model_id"] != 0x100
        or len(skeleton["parents"]) != 73
        or animation["model_id"] != 0x100
        or animation["frame_bytes"] != 264
        or len(animation["frames"]) != 1763
    ):
        raise ValueError("HI_PROFILE")
    selected = [
        (i, s)
        for i, s in enumerate(mesh["submeshes"])
        if (0x3021 >> (s["header_words"][16] >> 16)) & 1
    ]
    if len(selected) != 79 or any(geometry["references"][i] for i, _ in selected):
        raise ValueError("HI_SELECTION")
    bones = sorted({b for _, s in selected for v in s["vertices"] for b in v["bones"]})
    hs = sorted({h for _, s in selected for g in s["groups"] for h in g["helper_indices"]})
    if len(bones) != 36 or len(hs) != 49:
        raise ValueError("HI_BINDINGS")
    bone_map, helper_map = {b: i for i, b in enumerate(bones)}, {h: i for i, h in enumerate(hs)}
    parents = [
        -1 if skeleton["parents"][b] == -1 else bone_map[skeleton["parents"][b]] for b in bones
    ]
    rest = [vector(m, 16) for m in skeleton["matrices_columns"]]
    frames = []
    for sample in animation["frames"][:10]:
        tracks = sample["tracks"]
        if [t["bone_index"] for t in tracks] != bones:
            raise ValueError("HI_TRACKS")
        frame = []
        for b, track in zip(bones, tracks, strict=True):
            t = track["translation"]
            if t is None:
                p = skeleton["parents"][b]
                if p < 0:
                    raise ValueError("HI_ROOT")
                a, child = rest[p], rest[b]
                t = tuple(
                    sum(a[4 * c + r] * (child[12 + r] - a[12 + r]) for r in range(3))
                    for c in range(3)
                )
            frame.append((t, track["quaternion_xyzw"]))
        frames.append(frame)
    targets = [bone_map[mesh["helpers"][h][1]] for h in hs]
    helpers = [
        struct.unpack("<16f", struct.pack("<16I", *mesh["helper_matrix_words"][h])) for h in hs
    ]
    vertices, indices, materials = [], [], []
    source_textures = sorted({s["texture_index"] for _, s in selected})
    if source_textures != [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14]:
        raise ValueError("HI_TEXTURE_SELECTION")
    # Framing uses a conservative sum of local offset lengths, including helpers.
    center = tuple((frames[0][0][0][k] + frames[0][1][0][k]) / 2 for k in range(3))
    radii = [0.0] * len(bones)
    for b, parent in enumerate(parents):
        radii[b] = max(
            math.dist(frame[b][0], center if parent < 0 else (0, 0, 0)) for frame in frames
        )
        if parent >= 0:
            radii[b] += radii[parent]
    radius, files = 0.0, {}
    for ti, texture in enumerate(source_textures):
        first = len(indices)
        for _, s in selected:
            if s["texture_index"] != texture:
                continue
            if bool(s["blend_partition"]) != (texture == 14):
                raise ValueError("HI_BLEND_BINDING")
            base, cursor = len(vertices), 0
            for group in s["groups"]:
                count = group["header_words"][0]
                for v in s["vertices"][cursor : cursor + count]:
                    expected = [v["primary_bone"]] + [
                        mesh["helpers"][h][1] for h in group["helper_indices"]
                    ]
                    if v["bones"] != expected or len(v["weights_q12"]) != len(expected):
                        raise ValueError("HI_INFLUENCE_BINDING")
                    vertex = dict(
                        v,
                        primary_bone=bone_map[v["primary_bone"]],
                        helper_indices=[helper_map[h] for h in group["helper_indices"]],
                    )
                    point = [x / 16 for x in v["position_q4"]]
                    radius = max(
                        radius, radii[vertex["primary_bone"]] + math.dist(point, (0, 0, 0))
                    )
                    for h in vertex["helper_indices"]:
                        hm = helpers[h]
                        p = [
                            hm[12 + r] + sum(hm[4 * k + r] * point[k] for k in range(3))
                            for r in range(3)
                        ]
                        radius = max(radius, radii[targets[h]] + math.dist(p, (0, 0, 0)))
                    vertices.append(vertex)
                cursor += count
            if cursor != len(s["vertices"]):
                raise ValueError("HI_VERTEX_GROUPS")
            for triangle in s["triangles"]:
                indices.extend(base + i for i in integers(triangle, 3, 0, cursor - 1))
        width, height, raw = textures[texture]
        if type(raw) is not bytes or len(raw) != width * height * 4:
            raise ValueError("HI_TEXTURE_BYTES")
        materials.append(
            (first, len(indices) - first, ti, width, height, int(texture == 14), zlib.crc32(raw))
        )
        files[f"texture-{ti:02}.rgba"] = raw
    if len(vertices) != 6943 or len(indices) != 16566 or not math.isfinite(radius) or radius <= 0:
        raise ValueError("HI_GEOMETRY_COUNTS")
    files["heather.sri"] = encode_rig(
        parents,
        frames,
        targets,
        helpers,
        vertices,
        indices,
        materials,
        center,
        min(1.0, 1.4 / radius),
        0x65,
        614,
    )
    return files, dict(
        bones=bones,
        helpers=hs,
        textures=source_textures,
        submeshes=[i for i, _ in selected],
        framing_radius=radius,
        pose="local_quaternion_nlerp_and_translation",
        clock="inspection_25Hz",
        native_timing_verified=False,
        morphs_applied=False,
        lighting="neutral",
        appearance="original_normal_game",
    )
