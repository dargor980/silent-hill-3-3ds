"""HRM: immutable SRM2 materials from authenticated HRS A/B and consumed GS evidence."""

import argparse
import json
import os
import struct
import zlib
from pathlib import Path

from tools.inspectors.map_material_binding import apply_packet, initial_gs_state
from tools.inspectors.pcsx2_gs_dump import Dump
from tools.inspectors.texture_probe import probe_texture
from tools.pipeline.collision_polygon_inputs import PinnedInputs, read_at
from tools.pipeline.decoders.ps2_indexed import decode_indexed, render_indexed
from tools.pipeline.heather_room_contacts import require
from tools.pipeline.intermediate_assets import sha
from tools.pipeline.intermediate_json import decode_json, encode_json
from tools.pipeline.prepare_heather_room_runtime import runtime_descriptor
from tools.pipeline.prepare_heather_room_scene import read_bundle
from tools.pipeline.private_texture_output import _write_bundle

BINDING_SHA = "5ebe66786a34543c058451b7e9637b0e528ed50b3a07109c850cde1078ac5073"
GS_SHA = "4ce2e101e325e92ef68ac521bd6329fcd12cdf68ea09275aeab3d2e68ab2c801"
TEXTURES = {f"room-texture-{i:02}.rgba" for i in range(9)}
RUNTIME = (
    {"scene.srr", "map.srm", "glass.rgba", "heather.sri"}
    | {f"texture-{i:02}.rgba" for i in range(13)}
    | TEXTURES
)


def captured_colors(dump, binding, meshes):
    """Check each effective draw state and reconstruct overlapping source batches."""
    packets = {1: [], 3: []}
    state = initial_gs_state(dump.state)
    for packet in dump.packets():
        apply_packet(state, packet)
        f = packet.fields
        if (
            packet.frame in packets
            and f["flag"] == 0
            and f["nreg"] == 3
            and f["regs"] == 0x412
            and f["nloop"]
            and state.get(0) in (0x3C, 0x7C)
            and state.get(0x47) in (0x5800C, 0x5800D)
        ):
            packets[packet.frame].append((packet, dict(state)))
    frames = []
    for frame in (1, 3):
        expected = {
            row["shape_offset"]: row for row in binding["gs"]["draws"] if row["frame"] == frame
        }
        cursor, colors = 0, {}
        for mesh in meshes:
            for shape in mesh["shapes"]:
                if not shape["submitted"]:
                    continue
                offset = shape["shape_offset"]
                samples = [None] * shape["vertices"]
                for first, count in shape["source_ranges"]:
                    require(cursor < len(packets[frame]), "HRM_GS_MISSING")
                    packet, state = packets[frame][cursor]
                    cursor += 1
                    require(
                        packet.path == 3
                        and packet.fields["nloop"] == count
                        and all(
                            state.get(int(r, 16)) == int(v, 16)
                            for r, v in expected[offset]["registers"].items()
                        ),
                        "HRM_GS_STATE",
                    )
                    for j in range(count):
                        rgba = struct.unpack_from("<4I", packet.payload, j * 48 + 16)
                        fog = struct.unpack_from("<I", packet.payload, j * 48 + 44)[0] >> 4 & 255
                        require(
                            rgba[3] == (0 if mesh["mode"] == 0 else 127) and max(rgba[:3]) <= 129,
                            "HRM_GS_COLOR",
                        )
                        value = (*rgba, fog)
                        at = first + j
                        require(at < len(samples), "HRM_GS_RANGE")
                        require(samples[at] in (None, value), "HRM_GS_OVERLAP")
                        samples[at] = value
                require(all(v is not None for v in samples), "HRM_GS_COVERAGE")
                colors[offset] = samples
        require(cursor == len(packets[frame]) == 239, "HRM_GS_EXTRA")
        frames.append(colors)
    require(frames[0] == frames[1], "HRM_GS_FRAMES")
    return frames[0]


def convert(files, binding, dump):
    meshes = binding["captures"][-1]["meshes"]
    require(len(meshes) == 9, "HRM_MATERIAL_COUNT")
    colors = captured_colors(dump, binding, meshes)
    embedded = files["source.map"][258048:]
    blocks = probe_texture(len(embedded), lambda o, n: embedded[o : o + n])["blocks"]
    require(len(blocks) == 7, "HRM_BANKS")
    textures, materials, shape_material = {}, [], {}
    for i, mesh in enumerate(meshes):
        b = blocks[mesh["group_index"]]
        require((b["width"], b["height"], b["bpp"]) == (512, 512, 8), "HRM_IMAGE_SIZE")
        indices, clut = b["indices"], b["clut"]
        image = decode_indexed(
            512,
            512,
            8,
            embedded[indices["offset"] : indices["offset"] + indices["size"]],
            embedded[clut["data_offset"] : clut["data_offset"] + clut["size"]],
        )
        rgba = render_indexed(image, mesh["selector"], normalize_alpha=False)
        palette = image.palettes[image.selectors.index(mesh["selector"])]
        require(
            sha(rgba) == mesh["rgba_sha256"]
            and sha(palette) == mesh["palette_sha256"]
            and max(rgba[3::4]) <= 128,
            "HRM_IMAGE_PIN",
        )
        normalized = bytearray(rgba)
        normalized[3::4] = bytes((a * 255 + 64) // 128 for a in rgba[3::4])
        pixels = bytes(normalized)
        textures[f"room-texture-{i:02}.rgba"] = pixels
        materials.append((512, 512, zlib.crc32(pixels), {0: 4, 3: 5, 1: 6}[mesh["mode"]]))
        for shape in mesh["shapes"]:
            require(shape["shape_offset"] not in shape_material, "HRM_DUPLICATE")
            shape_material[shape["shape_offset"]] = (i, int(shape["submitted"]))
    old = files["map.srm"]
    magic, ns, nv, size, crc, glass_crc, version = struct.unpack_from("<8s6I", old)
    require(magic == b"S3RMv1\0\0" and ns == 31 and nv == 27900 and version == 1, "HRM_SOURCE_MAP")
    require(size == len(old) - 32 and crc == zlib.crc32(old[32:]), "HRM_SOURCE_CRC")
    view = decode_json(files["map-view.json"])
    vertices = bytearray(old[32 + ns * 16 :])
    shapes, visible_order, hidden = [], [], []
    for index, (offset, first, count, glass) in enumerate(
        struct.iter_unpack("<4I", old[32 : 32 + ns * 16])
    ):
        item = view["shapes"][index]
        require(item["header"]["offset"] == offset, "HRM_SHAPE_ORDER")
        material, visible = (0, 1) if glass else shape_material[offset]
        shapes.append((offset, first, count, glass, material, visible))
        if glass:
            continue
        if not visible:
            hidden.append(offset)
            continue
        visible_order.append(offset)
        samples = colors[offset]
        require(len(samples) == len(item["geometry"]["vertices"]), "HRM_LIGHT_COUNT")
        order = [v for tri in item["geometry"]["triangles"] for v in tri]
        require(len(order) == count, "HRM_TRIANGLES")
        for j, v in enumerate(order):
            r, g, b, _, fog = samples[v]
            rgb = tuple(c / 128 * fog / 256 for c in (r, g, b))
            require(all(0 <= c <= 1 for c in rgb), "HRM_LIGHT_RANGE")
            struct.pack_into("<3f", vertices, (first + j) * 36 + 16, *rgb)
    require(hidden == [149504, 222736, 245648], "HRM_VISIBILITY")
    require(visible_order == binding["gs"]["order"]["1"], "HRM_ORDER")
    payload = b"".join(struct.pack("<6I", *s) for s in shapes)
    payload += b"".join(struct.pack("<4I", *m) for m in materials) + vertices
    binary = (
        struct.pack("<8s6I", b"S3RMv2\0\0", ns, nv, len(payload), zlib.crc32(payload), glass_crc, 2)
        + payload
    )
    descriptor = bytearray(runtime_descriptor(files))
    struct.pack_into("<I", descriptor, 16, zlib.crc32(binary))
    out = {n: files[n] for n in RUNTIME - TEXTURES - {"scene.srr"}}
    out.update(textures)
    out.update({"map.srm": binary, "scene.srr": bytes(descriptor)})
    profile = dict(
        schema_version=2,
        task="HM-T4c.3.3",
        binding_sha256=BINDING_SHA,
        gs_sha256=GS_SHA,
        internal_materials=9,
        internal_submitted=26,
        omitted_shapes=hidden,
        internal_order=visible_order,
        lighting="captured_rgb_times_black_fog_fixed",
        pixel_fidelity=False,
        physical_validation=False,
        texture_bytes=sum(len(v) for n, v in out.items() if n.endswith(".rgba")),
        files=[dict(file=n, size=len(v), sha256=sha(v)) for n, v in sorted(out.items())],
    )
    require(profile["texture_bytes"] == 27787264, "HRM_TEXTURE_BUDGET")
    return out, profile


def prepare(scene, reference, custody):
    files, parent = read_bundle(scene)
    raw = custody.read(reference, 256 * 1024)
    require(sha(raw) == BINDING_SHA, "HRM_BINDING_PIN")
    binding = decode_json(raw)
    gs = [p for p in binding["inputs"] if p["sha256"] == GS_SHA]
    require(len(gs) == 1, "HRM_GS_PIN")
    gs_raw = custody.read(Path(gs[0]["path"]), gs[0]["size"])
    require(sha(gs_raw) == GS_SHA, "HRM_GS_PIN")
    data, profile = convert(files, binding, Dump(gs_raw))
    data.update(
        {
            "material-profile.json": encode_json(profile),
            "binding-reference.json": raw,
            "source-scene-manifest.json": encode_json(parent),
        }
    )
    report = dict(
        schema_version=2,
        task="HM-T4c.3.3",
        scope="private_room_material_runtime",
        source_manifest_sha256=sha(encode_json(parent)),
        binding_sha256=BINDING_SHA,
        packaged_executable=False,
        physical_validation=False,
    )
    return data, report


def read_runtime(scene, runtime, custody):
    expected, report = prepare(scene, runtime / "binding-reference.json", custody)
    names = set(os.listdir(runtime))
    require(
        names
        in (
            set(expected) | {"manifest.json"},
            set(expected) | {"manifest.json", ".manifest.pending.json"},
        ),
        "HRM_FILES",
    )
    actual = {
        n: custody.read(runtime / n, 256 * 1024 if n == "binding-reference.json" else len(v))
        for n, v in expected.items()
    }
    require(actual == expected, "HRM_CONTENT")
    raw = custody.read(runtime / "manifest.json", 65536)
    report["files"] = [dict(file=n, size=len(v), sha256=sha(v)) for n, v in sorted(actual.items())]
    require(decode_json(raw) == report, "HRM_MANIFEST")
    if ".manifest.pending.json" in names:
        require(custody.read(runtime / ".manifest.pending.json", 65536) == raw, "HRM_PENDING")
    return actual, raw


def publish(a, b, reference, private_root, repository, prefix):
    custody = PinnedInputs()
    prepared = [prepare(p, reference, custody) for p in (a, b)]
    require(prepared[0] == prepared[1], "HRM_AB")
    data, report = prepared[0]
    custody.verify()

    def verify(directory, _manifest):
        require(
            {n: read_at(directory, n, len(v))[0] for n, v in data.items()} == data, "HRM_READBACK"
        )
        require([prepare(p, reference, custody) for p in (a, b)] == prepared, "HRM_CHANGED")
        custody.verify()

    manifests = [
        _write_bundle(
            private_root,
            repository,
            prefix + "-copy-" + copy,
            data,
            report,
            set(data),
            before_publish=verify,
        )
        for copy in ("a", "b")
    ]
    require(manifests[0] == manifests[1], "HRM_OUTPUT_AB")
    for copy in ("a", "b"):
        require(
            read_runtime(a, private_root / (prefix + "-copy-" + copy), custody)[0] == data,
            "HRM_FINAL_READBACK",
        )
    custody.verify()
    return manifests[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scene-a", "scene-b", "binding", "private-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--run-prefix", required=True)
    a = parser.parse_args(argv)
    result = publish(
        a.scene_a,
        a.scene_b,
        a.binding,
        a.private_root,
        Path(__file__).resolve().parents[2],
        a.run_prefix,
    )
    print(json.dumps(dict(status="prepared", copies=2, files=len(result["files"]))))


if __name__ == "__main__":
    main()
