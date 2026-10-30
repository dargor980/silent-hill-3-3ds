"""Optional local NumPy/Pillow oracle for shared-room framing and software previews.

Never imports the production geometry/pose/placement implementation. Private
payloads stay in memory or an explicitly supplied external output directory.
This is a geometric diagnostic, not a PICA pixel or hardware-performance claim.
"""

import math
import struct

import numpy as np


def pose_vertices(model, sample, fraction=0):
    clip = next(c for c in model["clips"] if c[7] <= sample < c[7] + c[1])
    following = clip[7] + (sample - clip[7] + 1) % clip[1]
    pose = []
    for bone, a, b in zip(
        model["bones"], model["samples"][sample], model["samples"][following], strict=True
    ):
        translation = (1 - fraction) * np.array(a[:3]) + fraction * np.array(b[:3])
        qa, qb = np.array(a[3:]), np.array(b[3:])
        q = (1 - fraction) * qa + fraction * (qb if np.dot(qa, qb) >= 0 else -qb)
        x, y, z, w = q / np.linalg.norm(q)
        mat = np.eye(4)
        mat[:3, :3] = [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
        mat[:3, 3] = translation
        pose.append(mat if bone["parent"] < 0 else pose[bone["parent"]] @ mat)
    palette = np.array(
        pose + [pose[h[0]] @ np.array(h[1:]).reshape((4, 4), order="F") for h in model["helpers"]]
    )
    vs = np.array(model["vertices"])
    points = np.column_stack((vs[:, :3] / 16, np.ones(len(vs))))
    refs = np.column_stack((vs[:, 11], len(pose) + vs[:, 13], len(pose) + vs[:, 14]))
    refs[vs[:, 8:11] == 0] = 0
    return np.einsum("vjik,vk,vj->vi", palette[refs], points, vs[:, 8:11] / 4096)


def map_source(raw, reference):
    """Traverse source links and reconstruct strip parity directly from packed words."""
    shapes, visited = [], set()

    def chain(offset, level):
        while offset:
            if (level, offset) in visited:
                return
            visited.add((level, offset))
            following, delta, length = struct.unpack_from("<3I", raw, offset)
            if length <= delta or offset + length > len(raw):
                raise ValueError("ORACLE_MAP_RANGE")
            if level < 3:
                chain(offset + delta, level + 1)
            else:
                n = struct.unpack_from("<I", raw, offset + 16)[0]
                words = np.array(
                    list(struct.iter_unpack("<8h", raw[offset + delta : offset + delta + n * 16]))
                )
                triangles = [
                    (i, i - 1, i - 2) if i % 2 else (i - 2, i - 1, i)
                    for i in range(2, n)
                    if not words[i, 4] & 1
                ]
                shapes.append((offset, words, np.array(triangles)))
            offset = following

    for root in struct.unpack_from("<3I", raw, 28):
        chain(root, 0)
    shapes.sort(key=lambda s: s[0])
    glass = {r["shape_offset"]: r for r in reference["shapes"]}
    vertices, ranges = [], []
    for offset, words, triangles in shapes:
        rgb = (
            np.array(glass[offset]["rgba"])[:, :3] / 128 * 227 / 256
            if offset in glass
            else np.tile([0.55, 0.58, 0.62], (len(words), 1))
        )
        rows = np.column_stack((words[:, :3], np.ones(len(words)), rgb, words[:, 4:6] / 32768))[
            triangles.reshape(-1)
        ]
        ranges.append([offset, sum(len(v) for v in vertices), len(rows), int(offset in glass)])
        vertices.append(rows)
    return np.concatenate(vertices).astype(np.float32), np.array(ranges, dtype=np.uint32)


def placed(points, local, yaw=0):
    # Match input binary32 quantization; matrix/skin derivation remains independent.
    yaw = np.float32(yaw).item()
    c, s = np.float32(math.cos(yaw)).item(), np.float32(math.sin(yaw)).item()
    rotation = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    result = points.copy()
    result[:, :3] = (
        (points[:, :3] @ rotation.T + points[:, 3, None] * local)
        * np.array([1, -1, -1])
        * np.float32(0.002).item()
    )
    return result


def view_basis(camera):
    eye = np.array(camera["eye_local"]) * [1, -1, -1] * np.float32(0.002).item()
    target = np.array(camera["target_local"]) * [1, -1, -1] * np.float32(0.002).item()
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    return eye, forward, right, up


def framing(model, profile, camera):
    eye, forward, right, up = view_basis(camera)
    tangent = math.tan(math.radians(camera["vertical_fov_degrees"]) / 2)
    # Linear view halfspaces, before perspective division. Min over yaw is
    # analytic, and min over each translation segment occurs at an endpoint.
    planes = [
        (forward, camera["near_render_units"]),
        (-forward, -camera["far_render_units"]),
        (forward * tangent * 400 / 240 + right, 0),
        (forward * tangent * 400 / 240 - right, 0),
        (forward * tangent + up, 0),
        (forward * tangent - up, 0),
    ]
    points = [[275, 0, 0]] + [[x, 0, z] for x, z in profile["inspection_route"]["local_xz"]]
    minimum, failures = 1e9, 0
    for sample in range(len(model["samples"])):
        for fraction in (0, 0.25, 0.5, 0.75):
            v = pose_vertices(model, sample, fraction)
            # W is retained by rendering; divide only for this projective audit.
            v = v[:, :3] / v[:, 3, None]
            radius = np.hypot(v[:, 0], v[:, 2]) * np.float32(0.002).item()
            for point in points:
                center = np.array(point) * [1, -1, -1] * np.float32(0.002).item() - eye
                for normal, boundary in planes:
                    margin = (
                        center @ normal
                        - v[:, 1] * np.float32(0.002).item() * normal[1]
                        - boundary
                        - radius * math.hypot(normal[0], normal[2])
                    )
                    m = float(margin.min())
                    minimum = min(minimum, m)
                    failures += int(np.count_nonzero(margin < -2e-5))
    return dict(
        sampled_poses=len(model["samples"]) * 4,
        route_endpoints=len(points),
        all_yaws_analytic=True,
        continuous_translation_segments=True,
        minimum_plane_margin=minimum,
        failing_vertex_halfspaces=failures,
    )


def opaque_visibility(raw_map_vertices, ranges, actor_points, camera):
    """Ray tests from the eye to actor vertices; no backface omission of neutral geometry."""
    eye, *_ = view_basis(camera)
    triangles = np.concatenate(
        [raw_map_vertices[r[1] : r[1] + r[2], :4].reshape(-1, 3, 4) for r in ranges if r[3] == 0]
    )
    triangles = triangles[:, :, :3] / triangles[:, :, 3, None]
    a = triangles[:, 0]
    ab = triangles[:, 1] - a
    ac = triangles[:, 2] - a
    origin = eye - a
    q = np.cross(origin, ab)
    distance = np.einsum("ij,ij->i", ac, q)
    visible = 0
    # Evenly spaced original vertices, including body/feet/hair; no material substitution.
    for point in actor_points[:: max(1, len(actor_points) // 128)]:
        direction = point[:3] / point[3] - eye
        p = np.cross(np.broadcast_to(direction, ac.shape), ac)
        determinant = np.einsum("ij,ij->i", ab, p)
        mask = np.abs(determinant) > 1e-10
        inv = np.zeros_like(determinant)
        inv[mask] = 1 / determinant[mask]
        u = np.einsum("ij,ij->i", origin, p) * inv
        v = (q @ direction) * inv
        t = distance * inv
        blocked = mask & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6) & (t < 1 - 1e-6)
        visible += not np.any(blocked)
    return dict(tested=len(actor_points[:: max(1, len(actor_points) // 128)]), visible=int(visible))


def preview(map_rows, frame, textures, camera):
    """400x240 software diagnostic: six-plane clipping, perspective UV, depth and alpha.

    Consumes the actual native draw plan. It is not a PICA rasterizer: edge
    ownership, quantization and filtering precision are intentionally approximate.
    Textures supplied in upload orientation, RGBA8 with alpha already normalized.
    """
    from PIL import Image

    eye, forward, right, up = view_basis(camera)
    tangent = math.tan(math.radians(camera["vertical_fov_degrees"]) / 2)
    near, far = camera["near_render_units"], camera["far_render_units"]
    planes = np.array(
        [
            [0, 0, 1, -near],
            [0, 0, -1, far],
            [1, 0, tangent * 400 / 240, 0],
            [-1, 0, tangent * 400 / 240, 0],
            [0, 1, tangent, 0],
            [0, -1, tangent, 0],
        ]
    )
    color = np.full((240, 400, 3), 0.07)
    depth = np.zeros((240, 400))  # reciprocal Euclidean camera depth, larger is nearer
    actor_mask = np.zeros((240, 400), dtype=bool)
    rows, ranges = frame
    rows, map_rows = np.array(rows), np.array(map_rows)

    def sample(texture, uv):
        h, w = texture.shape[:2]
        xy = np.clip(uv, 0, 1) * [w, h] - 0.5
        base = np.floor(xy).astype(int)
        frac = xy - base
        x0, y0 = np.clip(base[:, 0], 0, w - 1), np.clip(base[:, 1], 0, h - 1)
        x1, y1 = np.clip(base[:, 0] + 1, 0, w - 1), np.clip(base[:, 1] + 1, 0, h - 1)
        a = texture[y0, x0] * (1 - frac[:, 0, None]) + texture[y0, x1] * frac[:, 0, None]
        b = texture[y1, x0] * (1 - frac[:, 0, None]) + texture[y1, x1] * frac[:, 0, None]
        return (a * (1 - frac[:, 1, None]) + b * frac[:, 1, None]) / 255

    def draw(triangle, kind, slot):
        z = triangle[:, 2]
        xy = triangle[:, :2] / z[:, None] / [tangent * 400 / 240, tangent]
        xy = (xy * [1, -1] + 1) * [200, 120]
        a, b, c = xy
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        # Screen Y points down; front CCW in view becomes negative signed area.
        if abs(area) < 1e-10 or (kind == 2 and area >= 0):
            return
        lo = np.maximum(np.floor(xy.min(axis=0)).astype(int), [0, 0])
        hi = np.minimum(np.ceil(xy.max(axis=0)).astype(int), [399, 239])
        if np.any(lo > hi):
            return
        yy, xx = np.mgrid[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1]
        px, py = xx.ravel() + 0.5, yy.ravel() + 0.5
        v = ((px - a[0]) * (c[1] - a[1]) - (py - a[1]) * (c[0] - a[0])) / area
        w = ((b[0] - a[0]) * (py - a[1]) - (b[1] - a[1]) * (px - a[0])) / area
        weights = np.column_stack((1 - v - w, v, w))
        inv = weights @ (triangle[:, 3] / z)
        keep = np.all(weights >= -1e-9, axis=1) & (inv >= depth[yy.ravel(), xx.ravel()])
        if not np.any(keep):
            return
        xx, yy, weights, inv = xx.ravel()[keep], yy.ravel()[keep], weights[keep], inv[keep]
        attr = (weights @ (triangle[:, 4:] / z[:, None])) / (weights @ (1 / z))[:, None]
        rgb, alpha = attr[:, :3], np.ones(len(xx))
        if kind:
            tex = sample(textures[slot], attr[:, 3:5])
            rgb, alpha = rgb * tex[:, :3], tex[:, 3]
            if kind == 2:
                alpha *= 253 / 255
            threshold = 100 / 255 if kind == 3 else 0
            visible = np.ones(len(alpha), dtype=bool) if kind == 2 else alpha > threshold
            xx, yy, inv, rgb, alpha = (
                xx[visible],
                yy[visible],
                inv[visible],
                rgb[visible],
                alpha[visible],
            )
        if kind in (2, 3):
            color[yy, xx] = rgb * alpha[:, None] + color[yy, xx] * (1 - alpha[:, None])
        else:
            color[yy, xx] = rgb
            depth[yy, xx] = inv
            actor_mask[yy, xx] = kind == 1
        if kind == 3:
            actor_mask[yy, xx] = True

    for kind, first, count, slot in ranges:
        vertices = (map_rows if kind == 0 else rows)[first : first + count].copy()
        delta = vertices[:, :3] - vertices[:, 3, None] * eye
        vertices[:, :3] = delta @ np.array([right, up, forward]).T
        for triangle in vertices.reshape(-1, 3, 9):
            polygon = list(triangle)
            for plane in planes:
                clipped = []
                for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
                    da, db = a[:4] @ plane, b[:4] @ plane
                    if da >= 0:
                        clipped.append(a)
                    if (da >= 0) != (db >= 0):
                        clipped.append(a + (b - a) * da / (da - db))
                polygon = clipped
                if not polygon:
                    break
            for i in range(1, len(polygon) - 1):
                draw(np.array([polygon[0], polygon[i], polygon[i + 1]]), kind, slot)
    return Image.fromarray(np.uint8(np.clip(color, 0, 1) * 255)), int(actor_mask.sum())
