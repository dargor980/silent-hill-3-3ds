"""Synthetic material contracts: no game resources or private paths."""

import copy
import io
import json
import struct
import zipfile
import zlib

import pytest
from test_geometry_inspection import bundle as geometry_bundle  # noqa: F401
from test_geometry_inspection import own_documents, sha

from tools.pipeline.material_inspection import PROFILE, material_geometry, material_texture
from tools.pipeline.prepare_material_probe import main, prepare_files


def reference(geometry_sha="a" * 64, texture_sha="b" * 64, rgba_sha="c" * 64):
    _, report, _ = own_documents()
    return {
        "schema_version": 1,
        "scope": "mr_t4d_material_reference",
        "geometry_manifest_sha256": geometry_sha,
        "texture_manifest_sha256": texture_sha,
        "texture_rgba_sha256": rgba_sha,
        "model_columns": [2, 0, 0, 0, 0, -3, 0, 0, 0, 0, -1, 0, 100, -40, 30, 1],
        "profile": copy.deepcopy(PROFILE),
        "draw_order": [192],
        "shapes": [
            {
                "shape_offset": 192,
                "source_sha256": report["shapes"][0]["source_sha256"],
                "rgba": [[128, 64, 32, 127], [16, 32, 64, 127], [8, 16, 32, 127]],
            }
        ],
    }


def test_model_then_basis_normalization_uv_colors_and_wire():
    _, _, geometry = own_documents()
    mesh, report = material_geometry([(192, geometry)], reference())
    magic, count, stride, size, crc = struct.unpack("<8sIIII", mesh[:24])
    assert (magic, count, stride, size) == (b"S3GMv1\0\0", 3, 32, 96)
    assert crc == zlib.crc32(mesh[24:])
    rows = list(struct.iter_unpack("<8f", mesh[24:]))
    for row, expected in zip(
        rows, [(-2 / 3, -1.25, -2), (2 / 3, -1.25, -2), (-2 / 3, 2.75, -2)], strict=True
    ):
        assert row[:3] == pytest.approx(expected)
    assert report["world_center_after_basis"] == [110, 70, -30]
    assert report["uniform_scale"] == pytest.approx(1 / 15)
    assert rows[2][3:5] == (0, -1)  # Raw negative V, never preview's 1-V.
    assert rows[1][3] == 16385 / 32768  # Retains control bit in U.
    assert rows[0][5:] == (227 / 256, 227 / 512, 227 / 1024)


def test_draw_order_does_not_follow_input_inventory():
    _, _, geometry = own_documents()
    ref = reference()
    ref["shapes"].append({**copy.deepcopy(ref["shapes"][0]), "shape_offset": 384})
    ref["shapes"][1]["rgba"] = [[0, 0, 0, 127]] * 3
    ref["draw_order"] = [384, 192]
    mesh, report = material_geometry([(192, geometry), (384, geometry)], ref)
    assert [r["shape_offset"] for r in report["ranges"]] == [384, 192]
    assert struct.unpack_from("<3f", mesh, 24 + 20) == (0, 0, 0)


@pytest.mark.parametrize(
    "mutation",
    [
        "profile",
        "nan",
        "infinity",
        "bool",
        "large",
        "projective",
        "singular",
        "reflection",
        "unknown_shape",
        "missing_shape",
        "repeated_order",
        "missing_order",
        "missing_color",
        "alpha",
        "overbright",
        "float_color",
        "backface",
        "nonplanar",
    ],
)
def test_rejects_unsupported_or_inconsistent_material(mutation):
    _, _, geometry = own_documents()
    ref = reference()
    model = ref["model_columns"]
    if mutation == "profile":
        ref["profile"]["depth_write"] = True
    elif mutation in ("nan", "infinity", "bool", "large"):
        model[0] = {"nan": float("nan"), "infinity": float("inf"), "bool": True, "large": 1e7}[
            mutation
        ]
    elif mutation == "projective":
        model[3] = 1
    elif mutation == "singular":
        model[0] = 0
    elif mutation == "reflection":
        model[0] = -2
    elif mutation == "unknown_shape":
        ref["shapes"][0]["shape_offset"] = 384
    elif mutation == "missing_shape":
        ref["shapes"] = []
    elif mutation == "repeated_order":
        ref["draw_order"] = [192, 192]
    elif mutation == "missing_order":
        ref["draw_order"] = []
    elif mutation == "missing_color":
        ref["shapes"][0]["rgba"].pop()
    elif mutation in ("alpha", "overbright", "float_color"):
        ref["shapes"][0]["rgba"][0][3 if mutation == "alpha" else 0] = {
            "alpha": 128,
            "overbright": 129,
            "float_color": 1.0,
        }[mutation]
    elif mutation == "backface":
        model[5], model[10] = 3, 1
    else:
        model[2] = 1
    with pytest.raises(ValueError):
        material_geometry([(192, geometry)], ref)


def test_alpha_scaling_preserves_rgb_and_half_opacity():
    pixels = bytes(channel for i in range(65536) for channel in (17, 59, 203, (i % 3) * 64))
    stx = material_texture(pixels)
    assert stx[:8] == b"S3TXv1\0\0"
    assert zlib.crc32(stx[24:]) == struct.unpack_from("<I", stx, 20)[0]
    assert stx[24:36] == bytes([17, 59, 203, 0, 17, 59, 203, 128, 17, 59, 203, 255])
    # Analytic UNORM conversion error, not a claim about rasterizer precision.
    for a in range(129):
        ps2 = a * 127 / 128 / 128
        pica = ((a * 255 + 64) // 128) / 255 * 253 / 255
        assert abs(ps2 - pica) <= 1 / 255
    for bad in (b"", bytes([0, 0, 0, 129]) * 65536, bytearray(pixels)):
        with pytest.raises(ValueError):
            material_texture(bad)


@pytest.fixture
def bundle(request, tmp_path):
    geometry, build, private, geometry_sha = request.getfixturevalue("geometry_bundle")
    for path in list(build.iterdir()):
        if path.name.startswith("sh3_geometry"):
            path.rename(path.with_name(path.name.replace("geometry", "material")))
    (build / "SHA256SUMS").write_text(
        "".join(
            f"{sha(p.read_bytes())}  {p.name}\n"
            for p in sorted(build.iterdir())
            if p.name != "SHA256SUMS"
        )
    )
    texture = tmp_path / "texture"
    texture.mkdir()
    rgba = bytes([32, 64, 96, 64]) * 65536
    (texture / "palette-0.rgba").write_bytes(rgba)
    tm = {
        "scope": "ps2_indexed_texture_decode",
        "recipe": "sh3-ps2-indexed8-four-cluts-v1",
        "orientation": "row_major_no_flip",
        "alpha": {"rgba": "original_ps2"},
        "block": {"width": 256, "height": 256},
        "files": [{"file": "palette-0.rgba", "size": len(rgba), "sha256": sha(rgba)}],
    }
    raw = json.dumps(tm).encode()
    (texture / "manifest.json").write_bytes(raw)
    ref = reference(geometry_sha, sha(raw), sha(rgba))
    raw_ref = json.dumps(ref).encode()
    rp = tmp_path / "reference.json"
    rp.write_bytes(raw_ref)
    return (geometry, geometry_sha, texture, sha(raw), rp, sha(raw_ref), build), private


def test_repeatable_delivery_cli_and_archive(bundle):
    args, private = bundle
    files, report = prepare_files(*args)
    assert (files, report) == prepare_files(*args)
    assert report["physical_2ds_xl"] == "pending"
    with zipfile.ZipFile(io.BytesIO(files["sd-card.zip"])) as archive:
        assert len(archive.namelist()) == 6 and archive.testzip() is None
        for line in archive.read("SHA256SUMS").decode().splitlines():
            digest, name = line.split("  ")
            assert name.startswith("3ds/sh3_material_probe/")
            assert sha(archive.read(name)) == digest
    options = []
    for name, value in zip(
        (
            "geometry",
            "geometry-sha256",
            "texture",
            "texture-sha256",
            "reference",
            "reference-sha256",
            "build",
        ),
        args,
        strict=True,
    ):
        options += ["--" + name, str(value)]
    assert main(options + ["--private-root", str(private), "--run-id", "material"]) == 0
    assert (private / "material/geometry.sgm").read_bytes() == files["geometry.sgm"]
    with pytest.raises(FileExistsError):
        main(options + ["--private-root", str(private), "--run-id", "material"])


@pytest.mark.parametrize(
    "mutation", ["scope", "source", "pixels", "shape", "rgba", "manifest", "file_size", "duplicate"]
)
def test_rejects_material_provenance_mismatch(bundle, mutation):
    args, _ = bundle
    args = list(args)
    ref = json.loads(args[4].read_bytes())
    if mutation == "scope":
        ref["scope"] = "guessed"
    elif mutation == "source":
        ref["geometry_manifest_sha256"] = "0" * 64
    elif mutation == "pixels":
        ref["texture_rgba_sha256"] = "0" * 64
    elif mutation == "shape":
        ref["shapes"][0]["source_sha256"] = "0" * 64
    elif mutation == "rgba":
        (args[2] / "palette-0.rgba").write_bytes(b"changed")
    elif mutation == "manifest":
        args[3] = "0" * 64
    else:
        path = args[2] / "manifest.json"
        tm = json.loads(path.read_bytes())
        if mutation == "file_size":
            tm["files"][0]["size"] += 1
        else:
            tm["files"] *= 2
        raw = json.dumps(tm).encode()
        path.write_bytes(raw)
        args[3] = ref["texture_manifest_sha256"] = sha(raw)
    raw = json.dumps(ref).encode()
    args[4].write_bytes(raw)
    args[5] = sha(raw)
    with pytest.raises(ValueError):
        prepare_files(*args)
