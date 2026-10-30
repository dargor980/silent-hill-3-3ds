"""Invented GIF colors, selected palettes and transactional material packages."""

import struct
import zlib
from types import SimpleNamespace

import pytest

from tests.python.test_texture_probe import own_block, own_file
from tools.inspectors.pcsx2_gs_dump import Packet
from tools.pipeline import prepare_heather_room_materials as m
from tools.pipeline.collision_polygon_inputs import PinnedInputs
from tools.pipeline.intermediate_assets import sha
from tools.pipeline.intermediate_json import encode_json


def gs_fixture():
    state = bytearray(4194813)
    struct.pack_into("<I", state, 0, 9)
    struct.pack_into("<Q", state, 124 + 8 * 8, 0x5800C)
    tag = struct.pack("<QQ", 3 | (1 << 46) | (0x3C << 47) | (3 << 60), 0x412)
    payload = bytearray(3 * 48)
    for i in range(3):
        struct.pack_into("<4I", payload, i * 48 + 16, 64, 32, 16, 0)
        struct.pack_into("<I", payload, i * 48 + 44, 192 << 4)
    packets = [Packet(3, f, i, tag, bytes(payload)) for f in (1, 3) for i in range(239)]
    meshes = [
        dict(
            mode=0,
            shapes=[
                dict(shape_offset=100, submitted=True, vertices=3, source_ranges=[[0, 3]] * 239),
                dict(shape_offset=200, submitted=False),
            ],
        )
    ]
    binding = {
        "gs": {
            "draws": [
                dict(frame=f, shape_offset=100, registers={"00": "3c", "47": "5800c"})
                for f in (1, 3)
            ]
        }
    }
    dump = SimpleNamespace(state=bytes(state), packets=lambda: iter(packets))
    return dump, binding, meshes, packets


def test_gs_coverage_two_frames_and_overlaps():
    dump, binding, meshes, _ = gs_fixture()
    assert m.captured_colors(dump, binding, meshes) == {100: [(64, 32, 16, 0, 192)] * 3}


@pytest.mark.parametrize(
    "change,code",
    [
        ("missing", "MISSING"),
        ("extra", "EXTRA"),
        ("state", "STATE"),
        ("path", "STATE"),
        ("color", "COLOR"),
        ("overlap", "OVERLAP"),
        ("range", "RANGE"),
        ("coverage", "COVERAGE"),
        ("frames", "FRAMES"),
    ],
)
def test_gs_rejects_unverified_changes(change, code):
    dump, binding, meshes, packets = gs_fixture()
    if change == "missing":
        packets.pop(0)
    elif change == "extra":
        packets.append(packets[-1])
    elif change == "state":
        binding["gs"]["draws"][0]["registers"]["06"] = "123"
    elif change == "path":
        packets[0] = Packet(2, 1, 0, packets[0].tag, packets[0].payload)
    elif change in ("color", "overlap", "frames"):
        indices = range(239, 478) if change == "frames" else [1]
        for i in indices:
            p = packets[i]
            raw = bytearray(p.payload)
            struct.pack_into("<I", raw, 16, 255 if change == "color" else 63)
            packets[i] = Packet(p.path, p.frame, p.offset, p.tag, bytes(raw))
    elif change == "range":
        meshes[0]["shapes"][0]["vertices"] = 2
    else:
        meshes[0]["shapes"][0]["vertices"] = 4
    with pytest.raises(ValueError, match="HRM_GS_" + code):
        m.captured_colors(dump, binding, meshes)


@pytest.fixture
def conversion(monkeypatch):
    offsets = [1000 + i for i in range(26)] + [149504, 222736, 245648]
    colors = {o: [(64, 32, 16, 0, 192)] * 3 for o in offsets[:26]}
    monkeypatch.setattr(m, "captured_colors", lambda *args: colors)
    block = bytearray(own_block(width=512, height=512, count=16))
    block[-16384:] = bytes((64, 32, 16, 64)) * 4096
    source = b"\0" * 258048 + own_file(*([bytes(block)] * 7))
    rgba, palette = bytes((64, 32, 16, 64)) * (512 * 512), bytes((64, 32, 16, 64)) * 256
    meshes = [
        dict(
            group_index=min(i, 6),
            selector=0,
            mode=(0, 1, 3)[i % 3],
            rgba_sha256=sha(rgba),
            palette_sha256=sha(palette),
            shapes=[dict(shape_offset=o, submitted=o < 2000) for o in offsets[i::9]],
        )
        for i in range(9)
    ]
    # Source order may differ from mesh grouping in this invented fixture.
    binding = dict(captures=[dict(meshes=meshes)], gs=dict(order={"1": offsets[:26]}))
    shapes, view, vertices = [], [], bytearray()
    for i, o in enumerate([10, 11] + offsets):
        count = 27810 if i == 30 else 3
        shapes.append((o, len(vertices) // 36, count, int(i < 2)))
        vertices.extend(struct.pack("<9f", 1, 2, 3, 1, 0.5, 0.5, 0.5, 0.25, 0.75) * count)
        view.append(
            dict(
                header=dict(offset=o),
                geometry=dict(vertices=[{}] * 3, triangles=[[0, 1, 2]] * (count // 3)),
            )
        )
    payload = b"".join(struct.pack("<4I", *s) for s in shapes) + vertices
    raw = (
        struct.pack("<8s6I", b"S3RMv1\0\0", 31, 27900, len(payload), zlib.crc32(payload), 0, 1)
        + payload
    )
    files = {
        "source.map": source,
        "map.srm": raw,
        "map-view.json": encode_json(dict(shapes=view)),
        "heather.sri": b"sri",
        "glass.rgba": b"g" * 262144,
    }
    files.update({f"texture-{i:02}.rgba": b"t" * (18087744 if i == 0 else 16) for i in range(13)})
    monkeypatch.setattr(m, "runtime_descriptor", lambda _: b"\0" * 596)
    return files, binding


def test_convert_preserves_geometry_uv_visibility_and_original_order(conversion):
    files, binding = conversion
    out, profile = m.convert(files, binding, None)
    assert set(out) == m.RUNTIME and profile["internal_submitted"] == 26
    assert profile["texture_bytes"] == 27787264
    raw = out["map.srm"]
    assert raw[:8] == b"S3RMv2\0\0" and len(raw) == 32 + 31 * 24 + 9 * 16 + 27900 * 36
    assert zlib.crc32(raw[32:]) == struct.unpack_from("<I", raw, 20)[0]
    assert zlib.crc32(raw) == struct.unpack_from("<I", out["scene.srr"], 16)[0]
    before = list(struct.iter_unpack("<9f", files["map.srm"][32 + 31 * 16 :]))
    after = list(struct.iter_unpack("<9f", raw[32 + 31 * 24 + 9 * 16 :]))
    assert all(a[:4] == b[:4] and a[7:] == b[7:] for a, b in zip(before, after, strict=True))
    assert after[6][4:7] == (0.375, 0.1875, 0.09375)
    assert before[:6] == after[:6] and before[-27816:] == after[-27816:]
    shapes = list(struct.iter_unpack("<6I", raw[32 : 32 + 31 * 24]))
    assert [s[0] for s in shapes if not s[5]] == [149504, 222736, 245648]
    assert all(out[n][3::4] == bytes([128]) * (512 * 512) for n in m.TEXTURES)
    assert all(out[n] == files[n] for n in files if n.startswith("texture-") or n == "heather.sri")


@pytest.mark.parametrize(
    "change,code",
    [
        ("count", "MATERIAL_COUNT"),
        ("image", "IMAGE_PIN"),
        ("header", "SOURCE_MAP"),
        ("crc", "SOURCE_CRC"),
        ("order", "ORDER"),
    ],
)
def test_converter_rejects_changed_evidence(conversion, change, code):
    files, binding = conversion
    if change == "count":
        binding["captures"][0]["meshes"].pop()
    elif change == "image":
        binding["captures"][0]["meshes"][0]["rgba_sha256"] = "bad"
    elif change in ("header", "crc"):
        raw = bytearray(files["map.srm"])
        raw[0 if change == "header" else -1] ^= 1
        files["map.srm"] = bytes(raw)
    else:
        binding["gs"]["order"]["1"].reverse()
    with pytest.raises(ValueError, match="HRM_" + code):
        m.convert(files, binding, None)


@pytest.fixture
def package(tmp_path, monkeypatch):
    root, repo = tmp_path / "private", tmp_path / "repo"
    root.mkdir()
    repo.mkdir()
    gs = root / "source.gs"
    gs.write_bytes(b"gs")
    reference = root / "binding.json"
    reference.write_bytes(encode_json(dict(inputs=[dict(path=str(gs), size=2, sha256=sha(b"gs"))])))
    monkeypatch.setattr(m, "BINDING_SHA", sha(reference.read_bytes()))
    monkeypatch.setattr(m, "GS_SHA", sha(b"gs"))
    monkeypatch.setattr(m, "read_bundle", lambda _: ({}, dict(parent="original")))
    monkeypatch.setattr(m, "Dump", lambda raw: raw)
    monkeypatch.setattr(
        m, "convert", lambda *args: ({"map.srm": b"map", "scene.srr": b"scene"}, {})
    )
    return root, repo, reference


def test_publication_and_readback_use_consistent_pins(package):
    root, repo, ref = package
    report = m.publish(root, root, ref, root, repo, "materials")
    assert report["task"] == "HM-T4c.3.3"
    custody = PinnedInputs()
    a = m.read_runtime(root, root / "materials-copy-a", custody)
    b = m.read_runtime(root, root / "materials-copy-b", custody)
    assert a == b
    custody.verify()
    with pytest.raises(FileExistsError):
        m.publish(root, root, ref, root, repo, "materials")


@pytest.mark.parametrize("change", ["binding", "gs", "files", "content", "manifest", "pending"])
def test_package_rejects_tampering(package, change):
    root, repo, ref = package
    if change in ("binding", "gs"):
        (ref if change == "binding" else root / "source.gs").write_bytes(b"xx")
        with pytest.raises(ValueError):
            m.prepare(root, ref, PinnedInputs())
        return
    m.publish(root, root, ref, root, repo, "materials")
    out = root / "materials-copy-a"
    path = {
        "files": "extra",
        "content": "map.srm",
        "manifest": "manifest.json",
        "pending": ".manifest.pending.json",
    }[change]
    (out / path).unlink(missing_ok=True)  # Break pending/manifest hardlink before mutation.
    (out / path).write_bytes(b"{}")
    with pytest.raises(ValueError):
        m.read_runtime(root, out, PinnedInputs())
