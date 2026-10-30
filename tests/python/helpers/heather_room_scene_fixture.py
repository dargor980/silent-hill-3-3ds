"""Invented 31-shape room and original-format SRI2 test bytes; no private assets."""

import json
import struct
import zlib

from tests.locomotion_rig_fixtures import own_sri2
from tests.python.helpers.heather_room_preparation_fixture import configured, pin, wire


def map_and_reference():
    counts = [18, 18] + [3] * 29
    offsets, cursor = [], 304
    for count in counts:
        offsets.append(cursor)
        cursor += 208 + 16 * count
    raw = bytearray(cursor)
    struct.pack_into("<I", raw, 0, 0xFFFFFFFF)
    struct.pack_into("<I", raw, 24, 80)
    struct.pack_into("<3I", raw, 28, 304, 0, 0)
    struct.pack_into("<4H", raw, 64, 31, 31, 0, 0)
    struct.pack_into("<3I", raw, 80, 0, 32, 224)
    matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 100000, 0, 140000, 1]
    struct.pack_into("<16f", raw, 112, *matrix)
    references = []
    for index, (offset, count) in enumerate(zip(offsets, counts, strict=True)):
        length = 208 + 16 * count
        for at, size in ((offset, length), (offset + 48, length - 48), (offset + 96, length - 96)):
            following = offsets[index + 1] if index < 30 and at == offset else 0
            struct.pack_into("<4I", raw, at, following, 48, size, 0)
        struct.pack_into("<H", raw, offset + 24, 1)
        shape = offset + 144
        struct.pack_into("<7I", raw, shape, 0, 64, length - 144, 0, count, 1 + index % 2, 0)
        vertices = []
        for i in range(count):
            vertices.append(
                struct.pack(
                    "<8h",
                    (i % 2) * 10,
                    -(i // 2) * 10,
                    50 * index,
                    -32768,
                    1 if i < 2 else 0,
                    16384,
                    127,
                    32767,
                )
            )
        data = b"".join(vertices)
        raw[shape + 64 : shape + 64 + len(data)] = data
        if index < 2:
            references.append(
                dict(
                    shape_offset=shape,
                    source_sha256=pin(data)["sha256"],
                    rgba=[[64, 96, 128, 127]] * count,
                )
            )
    reference = dict(
        schema_version=1,
        scope="mr_t4d_material_reference",
        model_columns=matrix,
        profile=dict(
            prim=0x7B,
            alpha=0x8000000044,
            test=0x53000,
            vertex_alpha=127,
            fog=227,
            fog_color=[0, 0, 0],
            depth_write=False,
            filter="linear",
            wrap="clamp",
        ),
        shapes=references,
        draw_order=[r["shape_offset"] for r in reversed(references)],
        texture_rgba_sha256=pin(bytes([120, 100, 80, 64]) * 256 * 256)["sha256"],
    )
    return bytes(raw), reference


def texture():
    header = bytearray(48)
    struct.pack_into("<iHHHH", header, 0, 17, 3, 5, 256, 256)
    header[12:14] = bytes([8, 32])
    struct.pack_into("<HII", header, 14, 23, 65536, 48 + 32 + 65536)
    header[25] = 0x13
    struct.pack_into("<H", header, 30, 0x9999)
    header[28:30] = bytes([8, 8])
    clut = bytearray(48)
    struct.pack_into("<III", clut, 0, 4096, 11, 13)
    clut[12:16] = bytes([4, 19, 64, 64])
    block = (
        bytes(header) + bytes(32) + bytes(65536) + bytes(clut) + bytes([120, 100, 80, 64]) * 1024
    )
    return struct.pack("<8I", 0xFFFFFFFF, 101, 32, 32 + len(block), 103, 1, 107, 109) + block


def rig():
    base = own_sri2()["heather.sri"]
    header = list(struct.unpack_from("<8s22I", base))
    payload = bytearray(base[96:-68])
    payload.extend(struct.pack("<39H", *([0, 1, 2] * 13)))
    files = {}
    for i in range(13):
        pixels = bytes([17 + i, 31 + i, 67 + i, 128]) * 128 * 128
        files[f"texture-{i:02}.rgba"] = pixels
        payload.extend(struct.pack("<7I", i * 3, 3, i, 128, 128, int(i == 12), zlib.crc32(pixels)))
    header[5] = 39
    header[6] = 13
    header[13] = len(payload)
    header[14] = zlib.crc32(payload)
    files["heather.sri"] = struct.pack("<8s22I", *header) + payload
    return files


def scene_inputs(folder):
    folder = folder.resolve()
    paths, profile, _ = configured(folder)
    raw_map, reference = map_and_reference()
    changes = {"map": raw_map, "external_texture": texture()}
    catalog = json.loads(paths["catalog"].read_bytes())
    receipt = json.loads(paths["receipt"].read_bytes())
    for role, raw in changes.items():
        identity = profile["resources"][role]["id"]
        new_pin = pin(raw)
        profile["resources"][role].update(new_pin)
        for rows in (
            catalog["entries"],
            receipt["resources"],
            receipt["copies"]["copy-a"],
            receipt["copies"]["copy-b"],
        ):
            next(r for r in rows if r["id"] == identity).update(new_pin)
        for copy in ("copy-a", "copy-b"):
            (paths["copies"] / copy / (identity[6:] + ".bin")).write_bytes(raw)
    paths["catalog"].write_bytes(wire(catalog))
    receipt["catalog_sha256"] = pin(wire(catalog))["sha256"]
    paths["receipt"].write_bytes(wire(receipt))
    profile["catalog_sha256"] = pin(wire(catalog))["sha256"]
    profile["extraction_receipt_sha256"] = pin(wire(receipt))["sha256"]
    profile["render"].update(
        expected_shapes=31,
        expected_vertices=123,
        expected_triangles=61,
        verified_glass_shape_offsets=[r["shape_offset"] for r in reference["shapes"]],
    )
    files = rig()
    manifest = dict(
        appearance="original_normal_game",
        model_resource=522,
        animation_resource=525,
        clips=[dict(clip_id=i) for i in (101, 109, 113)],
        files=[dict(file=k, **pin(v)) for k, v in sorted(files.items())],
    )
    profile["heather"].update(
        package_manifest_sha256=pin(wire(manifest))["sha256"],
        sri_sha256=pin(files["heather.sri"])["sha256"],
    )
    paths["profile"].write_bytes(wire(profile))
    roots = []
    for name in ("heather-a", "heather-b"):
        root = folder / name
        root.mkdir()
        roots.append(root)
        for key, raw in files.items():
            (root / key).write_bytes(raw)
        (root / "manifest.json").write_bytes(wire(manifest))
    ref = folder / "reference.json"
    ref.write_bytes(wire(reference))
    return paths, profile, *roots, ref
