"""Independent SRI2 reconstruction; imports neither the producer nor runtime code.

Only the selected local TR, topology, descriptors and shared geometry/materials
are reconstructed. CRC and identity metadata do not authenticate private sources.
"""

import math
import struct
import zlib


def _require(condition, field):
    if not condition:
        raise ValueError(f"SRI2:{field}")


def _numbers(values, limit=100000):
    return all(math.isfinite(v) and abs(v) <= limit for v in values)


def reconstruct_sri2(data):
    _require(type(data) is bytes and len(data) >= 96, "header")
    magic, *h = struct.unpack_from("<8s22I", data)
    _require(magic == b"S3RIv2\0\0", "magic")
    b, f, helpers, vertices, indices, materials = h[:6]
    _require(
        b == 36
        and f <= 80
        and helpers <= 128
        and 3 <= vertices <= 8192
        and 3 <= indices <= 18000
        and indices % 3 == 0
        and 1 <= materials <= 16,
        "counts",
    )
    _require((h[9], h[6], f) in ((1, 3, 58), (2, 5, 78)), "profile")
    _require(h[7:9] == [2, 25] and h[10:12] == [522, 525], "profile")
    size = (
        16
        + 8 * b
        + 20 * h[6]
        + 28 * b * f
        + 68 * helpers
        + 28 * vertices
        + 2 * indices
        + 28 * materials
    )
    _require(h[12] == size and len(data) == 96 + size, "length")
    _require(h[14:] == [0] * 8, "reserved")
    _require(zlib.crc32(data[96:]) == h[13], "crc32")
    cursor = 96

    def take(fmt):
        nonlocal cursor
        result = struct.unpack_from("<" + fmt, data, cursor)
        cursor += struct.calcsize("<" + fmt)
        return result

    framing = list(take("4f"))
    _require(_numbers(framing[:3]) and math.isfinite(framing[3]) and 0 < framing[3] <= 1, "framing")
    parents = take(f"{b}i")
    _require(all(-1 <= p < i for i, p in enumerate(parents)), "parents")
    source_bones = (
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        21,
        24,
        25,
        26,
        27,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
    )
    channel2 = {1, 3, 5, 7, 8, 10, 12, 13, 14, 16, 17, 21, 27, 33, 35}
    bones = []
    for i, expected in enumerate(source_bones):
        source, channel, reserved = take("HBB")
        _require(
            (source, channel, reserved) == (expected, 2 if expected in channel2 else 1, 0),
            "bindings",
        )
        bones.append(dict(source=source, parent=parents[i], channel=channel))
    expected_clips = (
        (101, 10, 307, 0, 9, 1, 0, 0, 0),
        (109, 24, 1996, 80, 103, 1, 0, 10, 0),
        (113, 24, 2227, 176, 199, 1, 0, 34, 0),
    )
    if h[9] == 2:
        expected_clips += (
            (107, 10, 1152, 60, 69, 1, 0, 58, 0),
            (108, 10, 1152, 70, 79, 1, 0, 68, 0),
        )
    clips = []
    for expected in expected_clips:
        record = take("HHhHHBBII")
        _require(record == expected, "descriptors")
        clips.append(list(record))
    samples = []
    for _ in range(f):
        frame = []
        for _ in range(b):
            tr = list(take("7f"))
            _require(
                _numbers(tr[:3])
                and _numbers(tr[3:], 1.001)
                and abs(sum(x * x for x in tr[3:]) - 1) <= 0.001,
                "samples",
            )
            frame.append(tr)
        samples.append(frame)
    hs = []
    for _ in range(helpers):
        target, *matrix = take("I16f")
        _require(
            target < b and _numbers(matrix) and [matrix[i] for i in (3, 7, 11, 15)] == [0, 0, 0, 1],
            "helpers",
        )
        hs.append([target, *matrix])
    vs = []
    for _ in range(vertices):
        v = list(take("8h3H4BH"))
        weights, primary, count, refs, reserved = v[8:11], v[11], v[12], v[13:15], v[15]
        _require(primary < b and 1 <= count <= 3 and reserved == 0, "vertices")
        _require(
            all(w <= 4096 for w in weights)
            and all(w == 0 for w in weights[count:])
            and 4097 - count <= sum(weights) <= 4096,
            "weights",
        )
        _require(
            all(h < helpers for h in refs[: count - 1])
            and all(h == 255 for h in refs[count - 1 :]),
            "vertex_helpers",
        )
        vs.append(v)
    ix = list(take(f"{indices}H"))
    _require(all(i < vertices for i in ix), "indices")
    ms, first, pixels, blended = [], 0, 0, False
    for i in range(materials):
        m = list(take("7I"))
        start, count, texture, width, height, blend, _ = m
        _require(
            start == first
            and count >= 3
            and count % 3 == 0
            and start + count <= indices
            and texture == i
            and width in (128, 256, 512, 1024)
            and height in (128, 256, 512, 1024)
            and blend in (0, 1)
            and not (blended and not blend),
            "materials",
        )
        first += count
        pixels += width * height
        blended = bool(blend)
        ms.append(m)
    _require(first == indices and pixels <= 8 * 1024 * 1024, "material_coverage")
    _require(cursor == len(data), "trailer")
    return dict(
        profile=h[9],
        model_resource=h[10],
        animation_resource=h[11],
        ticks=h[7],
        inspection_hz=h[8],
        framing=framing,
        bones=bones,
        clips=clips,
        sample_sources=[i for c in expected_clips for i in range(c[3], c[4] + 1)],
        samples=samples,
        helpers=hs,
        vertices=vs,
        indices=ix,
        materials=ms,
    )


def reconstruct_sri2_bundle(files):
    """Require exactly SRI + its numbered textures; return only after every check."""
    _require(type(files) is dict and "heather.sri" in files, "files")
    model = reconstruct_sri2(files["heather.sri"])
    names = {"heather.sri"} | {f"texture-{i:02}.rgba" for i in range(len(model["materials"]))}
    _require(set(files) == names, "files")
    for i, m in enumerate(model["materials"]):
        raw = files[f"texture-{i:02}.rgba"]
        _require(type(raw) is bytes and len(raw) == m[3] * m[4] * 4, "texture_length")
        _require(zlib.crc32(raw) == m[6], "texture_crc32")
    return model
