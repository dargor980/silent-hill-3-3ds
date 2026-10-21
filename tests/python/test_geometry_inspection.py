"""GI contracts use only constructed triangles, never game files."""

import copy
import hashlib
import io
import json
import struct
import zipfile
import zlib
from dataclasses import asdict

import pytest

from tools.pipeline.decoders.ps2_map_geometry import RECIPE, decode_shape
from tools.pipeline.geometry_inspection import COLORS, encode_sgm, normalize_shapes
from tools.pipeline.inspection_archive import inspection_archive
from tools.pipeline.prepare_geometry_probe import main, prepare_files, verified_shapes
from tools.pipeline.private_texture_output import write_geometry_inspection_bundle
from tools.pipeline.profile import ProfileError

TRIANGLE = [(-1, -1, -2, 0, 0, 1, 0, 0), (1, -1, -2, 1, 0, 0, 1, 0), (0, 1, -2, 0, 1, 0, 0, 1)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def own_documents():
    raw = b"".join(
        struct.pack("<8h", *p, 23, u, v, -12, 7)
        for p, u, v in [((0, 0, 0), 1, 0), ((10, 0, 0), 16385, 32767), ((0, 20, 0), 0, -32768)]
    )
    geometry = decode_shape(raw, 3)
    shape = {
        "shape_offset": 192,
        "source_sha256": sha(raw),
        "vertex_count": 3,
        "triangle_count": 1,
        "skipped_count": 2,
        "degenerate_count": 0,
        "data_bytes": 48,
    }
    report = {
        "schema_version": 1,
        "scope": "ps2_map_group_geometry",
        "recipe": RECIPE,
        "status": "decoded_candidate",
        "positions": "local_i16_no_transform",
        "uv_reference": "U/32768,1-V/32768_control_bit_retained",
        "packed_attributes": "preserved_not_interpreted",
        "material_binding": "unverified",
        "ps2_visual_comparison": "pending",
        "geometry_3ds": "pending",
        "capabilities": [],
        "summary": {"shapes": 1, "vertices": 3, "triangles": 1, "degenerate_triangles": 0},
        "resource": {"id": "synthetic"},
        "shapes": [shape],
    }
    document = {**copy.deepcopy(report), "shapes": [{**shape, **asdict(geometry)}]}
    return json.loads(json.dumps(document)), report, geometry


@pytest.fixture
def bundle(tmp_path):
    decoded, build, private = (tmp_path / p for p in ("decoded", "build", "private"))
    for p in (decoded, build, private):
        p.mkdir()
    document, report, _ = own_documents()
    raw = json.dumps(document).encode()
    (decoded / "geometry.json").write_bytes(raw)
    report["files"] = [{"file": "geometry.json", "size": len(raw), "sha256": sha(raw)}]
    manifest = json.dumps(report).encode()
    (decoded / "manifest.json").write_bytes(manifest)
    artifacts = {
        "sh3_geometry_probe.elf": b"synthetic",
        "sh3_geometry_probe.3dsx": b"3DSXsynthetic",
        "sh3_geometry_probe.smdh": b"SMDHsynthetic",
        "build-id.txt": b"123456789abc\n",
        "toolchain-packages.txt": b"synthetic",
        "sdk-image.txt": b"synthetic",
    }
    for name, data in artifacts.items():
        (build / name).write_bytes(data)
    (build / "SHA256SUMS").write_text(
        "".join(f"{sha(data)}  {name}\n" for name, data in artifacts.items())
    )
    return decoded, build, private, sha(manifest)


def test_independent_wire_layout_and_maximum_budget():
    encoded = encode_sgm(TRIANGLE)
    magic, count, stride, length, crc = struct.unpack("<8sIIII", encoded[:24])
    assert (magic, count, stride, length) == (b"S3GMv1\0\0", 3, 32, 96)
    assert crc == zlib.crc32(encoded[24:])
    assert list(struct.iter_unpack("<8f", encoded[24:])) == TRIANGLE
    assert len(encode_sgm(TRIANGLE * 1024)) == 98328


@pytest.mark.parametrize("count", [0, 1, 2, 4, 3073])
def test_wire_count_limits(count):
    with pytest.raises(ValueError):
        encode_sgm([TRIANGLE[0]] * count)


@pytest.mark.parametrize("component", range(8))
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -5, 5, True, "0"])
def test_wire_numeric_limits(component, bad):
    vertices = list(map(list, TRIANGLE))
    vertices[0][component] = bad
    with pytest.raises(ValueError):
        encode_sgm(vertices)


def test_wire_rounding_degeneracy_and_color():
    with pytest.raises(ValueError, match="degenerate"):
        encode_sgm([TRIANGLE[0]] * 3)
    vertices = list(map(list, TRIANGLE))
    vertices[1][:3] = [-1 + 1e-10, -1, -2]
    with pytest.raises(ValueError, match="degenerate"):
        encode_sgm(vertices)
    vertices = list(map(list, TRIANGLE))
    vertices[0][5] = -0.5
    with pytest.raises(ValueError):
        encode_sgm(vertices)
    with pytest.raises(ValueError):
        encode_sgm([TRIANGLE[0][:-1], *TRIANGLE[1:]])


def test_transform_preserves_aspect_axes_uv_order_and_shape_colors():
    _, _, geometry = own_documents()
    sgm, report = normalize_shapes([(192, geometry), (384, geometry)])
    rows = list(struct.iter_unpack("<8f", sgm[24:]))
    assert report["center"] == [5, 10, 0] and report["uniform_scale"] == 0.2
    assert [r[:3] for r in rows[:3]] == [(-1, -1.25, -2), (1, -1.25, -2), (-1, 2.75, -2)]
    assert [r[3:5] for r in rows[:3]] == [v.uv_reference for v in geometry.vertices]
    assert rows[0][5:] == pytest.approx(COLORS[0])
    assert rows[3][5:] == pytest.approx(COLORS[1])
    assert report["ranges"] == [
        {"shape_offset": 192, "first": 0, "count": 3},
        {"shape_offset": 384, "first": 3, "count": 3},
    ]
    with pytest.raises(ValueError, match="budget"):
        normalize_shapes([])
    with pytest.raises(ValueError, match="budget"):
        normalize_shapes([(192, geometry)] * 1025)
    zero = decode_shape(
        b"".join(struct.pack("<8h", 0, 0, 0, 0, int(i < 2), 0, 0, 0) for i in range(3)), 3
    )
    with pytest.raises(ValueError, match="extent"):
        normalize_shapes([(192, zero)])


def test_documents_roundtrip_and_known_topology():
    document, report, geometry = own_documents()
    assert verified_shapes(document, report) == [(192, geometry)]


@pytest.mark.parametrize(
    "mutation",
    [
        "scope",
        "metadata",
        "inventory",
        "duplicate",
        "identity",
        "words",
        "fields",
        "hash",
        "topology",
        "counts",
        "summary",
        "source_budget",
    ],
)
def test_rejects_false_geometry_evidence(mutation):
    doc, manifest, _ = own_documents()
    shape = doc["shapes"][0]
    if mutation == "scope":
        manifest["scope"] = "other"
    elif mutation == "metadata":
        doc["positions"] = "world"
    elif mutation == "inventory":
        manifest["shapes"] = []
    elif mutation == "duplicate":
        doc["shapes"] *= 2
        manifest["shapes"] *= 2
    elif mutation == "identity":
        shape["shape_offset"] = manifest["shapes"][0]["shape_offset"] = True
    elif mutation == "words":
        shape["vertices"][0]["position"][0] = True
    elif mutation == "fields":
        shape["vertices"][0]["unknown"] = []
    elif mutation == "hash":
        shape["vertices"][0]["position"][0] = 1
    elif mutation == "topology":
        shape["triangles"][0] = [2, 1, 0]
    elif mutation == "counts":
        shape["triangle_count"] = manifest["shapes"][0]["triangle_count"] = 2
    elif mutation == "summary":
        doc["summary"]["vertices"] = manifest["summary"]["vertices"] = 4
    else:
        shape["vertices"] *= 22000
    with pytest.raises(ValueError):
        verified_shapes(doc, manifest)


def test_delivery_deterministic_private_exclusive_and_cli(bundle, tmp_path, capsys):
    decoded, build, private, digest = bundle
    files, report = prepare_files(decoded, digest, build)
    assert (files, report) == prepare_files(decoded, digest, build)
    assert report["physical_2ds_xl"] == report["ps2_visual_comparison"] == "pending"
    assert report["capabilities"] == []
    with zipfile.ZipFile(io.BytesIO(files["sd-card.zip"])) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 5
        for line in archive.read("SHA256SUMS").decode().splitlines():
            digest_in_zip, name = line.split("  ")
            assert name.startswith("3ds/sh3_geometry_probe/")
            assert sha(archive.read(name)) == digest_in_zip
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
    checkout = tmp_path / "repo"
    checkout.mkdir()
    write_geometry_inspection_bundle(private, checkout, "run-a", files, report)
    for name, data in files.items():
        assert (private / "run-a" / name).read_bytes() == data
        assert (private / "run-a" / name).stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        write_geometry_inspection_bundle(private, checkout, "run-a", files, report)
    with pytest.raises(ProfileError):
        write_geometry_inspection_bundle(checkout, checkout, "run", files, report)
    with pytest.raises(ProfileError):
        write_geometry_inspection_bundle(private, checkout, "run-b", {}, report)
    assert (
        main(
            [
                "--decoded",
                str(decoded),
                "--build",
                str(build),
                "--private-root",
                str(private),
                "--manifest-sha256",
                digest,
                "--run-id",
                "cli",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "prepared"


@pytest.mark.parametrize(
    "mutation", ["digest", "geometry", "build", "missing", "duplicate", "size"]
)
def test_rejects_delivery_inputs(bundle, mutation):
    decoded, build, _, digest = bundle
    if mutation == "digest":
        digest = "0" * 64
    elif mutation == "geometry":
        (decoded / "geometry.json").write_bytes(b"{}")
    elif mutation == "build":
        (build / "sh3_geometry_probe.3dsx").write_bytes(b"changed")
    else:
        path = decoded / "manifest.json"
        manifest = json.loads(path.read_bytes())
        if mutation == "missing":
            manifest["files"] = []
        elif mutation == "duplicate":
            manifest["files"] *= 2
        else:
            manifest["files"][0]["size"] += 1
        raw = json.dumps(manifest).encode()
        path.write_bytes(raw)
        digest = sha(raw)
    with pytest.raises(ValueError):
        prepare_files(decoded, digest, build)


def test_archive_rejects_unknown_paths_and_viewer():
    for files, stem in [
        ({"../escape": b"x"}, "sh3_geometry_probe"),
        ({}, "../bad"),
        ({}, "sh3_geometry_probe"),
    ]:
        with pytest.raises(ValueError):
            inspection_archive(files, stem)
