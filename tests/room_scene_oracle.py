"""Independent scalar MAP/skin/world/draw oracle and bounded native capture protocol."""

import json
import math
import struct
import subprocess

from tools.qa.locomotion_rig_oracle import reconstruct_sri2_bundle


def require(condition, code):
    if not condition:
        raise ValueError(code)


def f32(v):
    return struct.unpack("<f", struct.pack("<f", v))[0]


def source_map(raw, reference):
    seen, shapes = set(), []

    def chain(offset, level):
        while offset:
            if (level, offset) in seen:
                return
            seen.add((level, offset))
            following, delta, length = struct.unpack_from("<3I", raw, offset)
            require(length > delta and offset + length <= len(raw), "ORACLE_MAP_RANGE")
            if level < 3:
                chain(offset + delta, level + 1)
            else:
                n = struct.unpack_from("<I", raw, offset + 16)[0]
                words = list(
                    struct.iter_unpack("<8h", raw[offset + delta : offset + delta + n * 16])
                )
                faces = [
                    (i, i - 1, i - 2) if i % 2 else (i - 2, i - 1, i)
                    for i in range(2, n)
                    if not words[i][4] & 1
                ]
                shapes.append((offset, words, faces))
            offset = following

    for root in struct.unpack_from("<3I", raw, 28):
        chain(root, 0)
    shapes.sort()
    glass = {r["shape_offset"]: r for r in reference["shapes"]}
    vertices, ranges = [], []
    for offset, words, faces in shapes:
        first = len(vertices)
        for face in faces:
            for i in face:
                v = words[i]
                rgb = (
                    [c / 128 * 227 / 256 for c in glass[offset]["rgba"][i][:3]]
                    if offset in glass
                    else [0.55, 0.58, 0.62]
                )
                vertices.append(tuple(map(f32, (*v[:3], 1, *rgb, v[4] / 32768, v[5] / 32768))))
        ranges.append((offset, first, len(vertices) - first, int(offset in glass)))
    return vertices, ranges


def multiply(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def skin(model, sample):
    pose = []
    for bone, s in zip(model["bones"], model["samples"][sample], strict=True):
        norm = math.sqrt(sum(v * v for v in s[3:]))
        x, y, z, w = [v / norm for v in s[3:]]
        m = [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), s[0]],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), s[1]],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), s[2]],
            [0, 0, 0, 1],
        ]
        pose.append(m if bone["parent"] < 0 else multiply(pose[bone["parent"]], m))
    palette = pose + [
        multiply(pose[h[0]], [[h[1 + c * 4 + r] for c in range(4)] for r in range(4)])
        for h in model["helpers"]
    ]
    vertices = []
    for v in model["vertices"]:
        local = [*(x / 16 for x in v[:3]), 1]
        result = [0.0] * 4
        for j in range(v[12]):
            matrix = palette[v[11] if j == 0 else len(pose) + v[12 + j]]
            for r in range(4):
                result[r] += sum(matrix[r][c] * local[c] for c in range(4)) * v[8 + j] / 4096
        vertices.append(result)
    return vertices


def placed(points, world, yaw):
    x, y, z = [f32(v) for v in world]
    yaw = f32(yaw)
    c, s = f32(math.cos(yaw)), f32(math.sin(yaw))
    scale = f32(0.002)
    return [
        (
            f32((c * p[0] + s * p[2] + (x - 100000) * p[3]) * scale),
            f32(-(p[1] + y * p[3]) * scale),
            f32(-(-s * p[0] + c * p[2] + (z - 140000) * p[3]) * scale),
            f32(p[3]),
        )
        for p in points
    ]


def expected_frame(model, points, map_rows, map_ranges, camera):
    vs = [
        (*p, 1, 1, 1, model["vertices"][i][6] / 4096, model["vertices"][i][7] / 4096)
        for i, p in enumerate(points)
    ]
    rows = []
    ranges = [(0, r[1], r[2], 0) for r in map_ranges if not r[3]]
    indices = model["indices"]
    triangles = []
    forward = [f32(camera[i + 3] - camera[i]) for i in range(3)]

    def depth(vertices):
        return sum(sum(v[k] * forward[k] for k in range(3)) / v[3] for v in vertices)

    for _offset, first, count, glass in map_ranges:
        if glass:
            for i in range(first, first + count, 3):
                triangles.append(
                    (depth(map_rows[i : i + 3]), len(model["materials"]), i, map_rows[i : i + 3])
                )
    for material, m in enumerate(model["materials"]):
        first, count = m[:2]
        if m[5]:
            for i in range(first, first + count, 3):
                tri = [vs[j] for j in indices[i : i + 3]]
                triangles.append((depth(tri), material, i, tri))
        else:
            ranges.append((1, len(rows), count, material))
            rows.extend(vs[j] for j in indices[first : first + count])
    for _, material, _, vertices in sorted(triangles, key=lambda t: (-t[0], t[1], t[2])):
        kind = 2 if material == len(model["materials"]) else 3
        if ranges and (ranges[-1][0], ranges[-1][3]) == (kind, material):
            r = ranges[-1]
            ranges[-1] = (r[0], r[1], r[2] + 3, r[3])
        else:
            ranges.append((kind, len(rows), 3, material))
        rows.extend(vertices)
    return rows, ranges


def capture(executable, map_raw, rig_root, requests, *, diagnostic=False):
    data = struct.pack("<I", len(map_raw)) + map_raw + struct.pack("<I", len(requests))
    data += b"".join(struct.pack("<I4f", sample, *world, yaw) for sample, world, yaw in requests)
    run = subprocess.run(
        [str(executable), "capture-diagnostic" if diagnostic else "capture", str(rig_root)],
        input=data,
        capture_output=True,
        timeout=90,
    )
    require(run.returncode == 0, "ORACLE_NATIVE_EXECUTION")
    raw = memoryview(run.stdout)
    cursor = 0

    def take(fmt, count=1):
        nonlocal cursor
        size = struct.calcsize("<" + fmt) * count
        require(cursor + size <= len(raw), "ORACLE_NATIVE_LENGTH")
        result = list(struct.iter_unpack("<" + fmt, raw[cursor : cursor + size]))
        cursor += size
        return result

    ledger = take("8Q")[0]
    camera = take("9f")[0]
    ns, nv = take("2I")[0]
    require(0 < ns <= 31 and 0 < nv <= 27900, "ORACLE_NATIVE_COUNTS")
    shapes = take("4I", ns)
    map_rows = take("9f", nv)
    frames = []
    for _ in requests:
        count, nranges = take("2I")[0]
        require(count <= 18096 and nranges <= 6079, "ORACLE_NATIVE_COUNTS")
        ranges = take("4I", nranges)
        rows = take("9f", count)
        frames.append((rows, ranges))
    require(cursor == len(raw), "ORACLE_NATIVE_TRAILER")
    return ledger, camera, map_rows, shapes, frames


def check(executable, files, rig_root, requests, keep=()):
    model = reconstruct_sri2_bundle(
        {k: v for k, v in files.items() if k == "heather.sri" or k.startswith("texture-")}
    )
    raw_rows, shapes = source_map(files["source.map"], json.loads(files["glass-reference.json"]))
    map_expected = [
        (f32(v[0] * f32(0.002)), f32(-v[1] * f32(0.002)), f32(-v[2] * f32(0.002)), *v[3:])
        for v in raw_rows
    ]
    render = json.loads(files["render-profile.json"])
    c = render["camera"]
    camera_expected = [
        f32(x * f32(0.002) * sign)
        for p in (c["eye_local"], c["target_local"])
        for x, sign in zip(p, (1, -1, -1), strict=True)
    ] + [c["vertical_fov_degrees"], f32(c["near_render_units"]), c["far_render_units"]]
    cache = {}
    saved = {}
    maximum = 0
    previous_ledger = None
    for begin in range(0, len(requests), 16):
        batch = requests[begin : begin + 16]
        ledger, camera, map_rows, native_shapes, frames = capture(
            executable, files["map.srm"], rig_root, batch
        )
        require(
            struct.pack("<9f", *camera) == struct.pack("<9f", *camera_expected), "ORACLE_CAMERA"
        )
        require(native_shapes == shapes and map_rows == map_expected, "ORACLE_MAP_TRANSFORM")
        require(
            ledger[0] == sum(m[3] * m[4] * 4 for m in model["materials"]) + 256 * 256 * 4
            and ledger[1] <= 2 * 1024 * 1024
            and ledger[2] <= 2 * 1024 * 1024
            and sum(ledger[:7]) == ledger[7] < 64 * 1024 * 1024,
            "ORACLE_MEMORY",
        )
        require(previous_ledger is None or previous_ledger == ledger, "ORACLE_LEDGER_CHANGED")
        previous_ledger = ledger
        for i, ((sample, world, yaw), (rows, ranges)) in enumerate(zip(batch, frames, strict=True)):
            if sample not in cache:
                cache[sample] = skin(model, sample)
            expected, expected_ranges = expected_frame(
                model, placed(cache[sample], world, yaw), map_expected, shapes, camera
            )
            require(
                ranges == expected_ranges and len(rows) == len(expected),
                f"ORACLE_DRAW_ORDER_{begin + i}",
            )
            for actual, want in zip(rows, expected, strict=True):
                require(actual[3] == want[3] and actual[4:] == want[4:], "ORACLE_ATTRIBUTES_W")
                error = max(abs(a - b) for a, b in zip(actual[:3], want[:3], strict=True))
                maximum = max(maximum, error)
                require(error <= 2e-5, f"ORACLE_PLACEMENT_{begin + i}")
            if begin + i in keep:
                saved[begin + i] = (rows, ranges)
    return (
        dict(frames=len(requests), maximum_position_error=maximum, ledger=list(previous_ledger)),
        saved,
        (map_expected, shapes),
    )
