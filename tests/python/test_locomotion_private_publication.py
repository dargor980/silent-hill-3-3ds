"""Synthetic source correspondence and exclusive publication; no original assets."""

import copy
import json
import struct
import zlib

import pytest
from test_locomotion_inspection import PAL, own_locomotion_shape

from tools.pipeline import publish_heather_locomotion as publisher
from tools.pipeline.locomotion_inspection import heather_locomotion_rig
from tools.pipeline.profile import ProfileError
from tools.qa.locomotion_source_audit import audit_selection


@pytest.fixture(scope="module")
def source():
    g, a, t = own_locomotion_shape()
    for frame in a["frames"]:
        for track in frame["tracks"]:
            track.update(rotation_words=[0, 0, 0], flag=1, quaternion_xyzw=[0, 0, 0, 1])
    files, report = heather_locomotion_rig(g, a, t, PAL)
    return g, a, t, files, report


def test_all_selected_fields_roundtrip(source):
    g, a, t, files, _ = source
    result = audit_selection(files, g, a, t, PAL)
    assert result == dict(
        samples=58,
        bones=36,
        raw_quaternion_max_error=0,
        vertices=6943,
        indices=16566,
        helpers=49,
        materials=13,
        all_selected_fields_exact=True,
    )


@pytest.mark.parametrize(
    "section",
    [
        "TR",
        "parents",
        "descriptors",
        "helpers",
        "vertices",
        "indices",
        "materials",
        "pixels",
        "framing",
        "groups",
        "blend",
        "bones",
    ],
)
def test_valid_package_cannot_hide_source_difference(source, section):
    g, a, t, files, _ = copy.deepcopy(source)
    sk = g["mesh"]["skeleton"]
    part = g["mesh"]["submeshes"][0]
    descriptors = PAL
    if section == "TR":
        a["frames"][199]["tracks"][0]["translation"][0] += 1
    elif section == "parents":
        sk["parents"][2] = 0
    elif section == "descriptors":
        descriptors = bytes(36)
    elif section == "helpers":
        g["mesh"]["helper_matrix_words"][0][12] = 0x3F800000
    elif section == "vertices":
        part["vertices"][0]["uv_q12"][0] += 1
    elif section == "indices":
        part["triangles"][0] = [1, 0, 2]
    elif section == "materials":
        t[0] = (256, 64, t[0][2])
    elif section == "pixels":
        t[0] = (*t[0][:2], b"x" + t[0][2][1:])
    elif section == "groups":
        part["groups"][0]["header_words"][0] += 1
    elif section == "blend":
        part["blend_partition"] = True
    elif section == "bones":
        part["vertices"][0]["bones"].append(72)
    else:
        raw = bytearray(files["heather.sri"])
        struct.pack_into("<f", raw, 96, 123)
        struct.pack_into("<I", raw, 60, zlib.crc32(raw[96:]))
        files["heather.sri"] = bytes(raw)
    with pytest.raises(ValueError, match=f"HL_SOURCE_RECONSTRUCTION:{section}"):
        audit_selection(files, g, a, t, descriptors)


def publication_seam(monkeypatch, source):
    files, report = source[-2:]
    monkeypatch.setattr(
        publisher,
        "produce_heather_locomotion",
        lambda *args, **kwargs: (dict(files), copy.deepcopy(report)),
    )


def test_exclusive_publication_and_reconstruction(tmp_path, monkeypatch, source):
    publication_seam(monkeypatch, source)
    root, repo = tmp_path / "private", tmp_path / "repo"
    root.mkdir()
    repo.mkdir()
    args = (root, repo, "own-a", b"model", b"animation", PAL)
    manifest = publisher.publish_heather_locomotion(*args)
    assert manifest["publication"] == "source_pinned_structural_readback"
    assert manifest["pose_reference_audit"] == "separate_required"
    assert json.loads((root / "own-a/manifest.json").read_text()) == manifest
    for name, data in source[-2].items():
        assert (root / "own-a" / name).read_bytes() == data
    with pytest.raises(FileExistsError):
        publisher.publish_heather_locomotion(*args)
    with pytest.raises(ProfileError, match="external"):
        publisher.publish_heather_locomotion(repo, repo, "inside", b"m", b"a", PAL)


@pytest.mark.parametrize("fault", ["readback", "reconstruction"])
def test_final_readback_failure_never_publishes(tmp_path, monkeypatch, source, fault):
    publication_seam(monkeypatch, source)
    original = publisher._write_bundle
    root, repo = tmp_path / "private", tmp_path / "repo"
    root.mkdir()
    repo.mkdir()

    def corrupt(*args, before_publish):
        def check(fd, raw):
            if fault == "readback":
                (root / "own-a/texture-00.rgba").write_bytes(b"corrupt")
            else:
                monkeypatch.setattr(publisher, "reconstruct_sri2_bundle", lambda _: {})
            before_publish(fd, raw)

        return original(*args, before_publish=check)

    monkeypatch.setattr(publisher, "_write_bundle", corrupt)
    with pytest.raises(ValueError, match="HL_PUBLICATION"):
        publisher.publish_heather_locomotion(root, repo, "own-a", b"m", b"a", PAL)
    assert not (root / "own-a/manifest.json").exists()
    assert (root / "own-a/.manifest.pending.json").exists()
