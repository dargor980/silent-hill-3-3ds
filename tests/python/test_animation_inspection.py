"""Synthetic three-bone resources and verified-delivery failure controls."""

import copy
import hashlib
import io
import json
import struct
import zipfile
import zlib

import pytest

from tools.pipeline.animation_inspection import encode_clip, inspection_clip
from tools.pipeline.prepare_animation_probe import main, prepare_files


def sha(data):
    return hashlib.sha256(data).hexdigest()


def documents():
    matrices = [
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, *t, 1] for t in ((0, 0, 0), (0, 1, 0), (2, 4, 1))
    ]
    skeleton = {
        "schema_version": 1,
        "model_id": 0x209,
        "parents": [-1, -1, 1],
        "matrices_columns": matrices,
    }
    tracks = [
        {
            "bone_index": i,
            "translation": matrices[i][12:15] if i < 2 else None,
            "quaternion_xyzw": [0, 0, 0, 1],
        }
        for i in range(3)
    ]
    animation = {
        "schema_version": 1,
        "model_id": 0x209,
        "frame_bytes": 46,
        "frames": [{"tracks": copy.deepcopy(tracks)} for _ in range(76)],
    }
    return skeleton, animation


def test_clip_keeps_only_verified_samples_and_uses_rest_child_offset():
    s, a = documents()
    a["frames"][24]["tracks"][1]["quaternion_xyzw"] = [0, 0, 0, 0]
    data = inspection_clip(s, a)
    assert len(data) == 1248
    assert struct.unpack("<8s6I", data[:32]) == (
        b"S3ANv1\0\0",
        3,
        24,
        0x1449,
        3686,
        1216,
        zlib.crc32(data[32:]),
    )
    assert struct.unpack_from("<3f", data, 84) == (2, 3, 1)
    assert struct.unpack_from("<4f", data, 96) == (0, 0, 0, 1)
    assert data == inspection_clip(s, a)


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "model",
        "parents",
        "frames",
        "tracks",
        "order",
        "child_translation",
        "variable_translation",
        "projective",
        "nonrigid",
        "nan",
        "bool",
        "large",
        "zero_q",
        "short_q",
        "missing_bone",
        "zero_child",
        "tiny_child",
        "wrong_frame_bytes",
    ],
)
def test_rejects_unsupported_inputs(mutation):
    s, a = documents()
    if mutation == "version":
        s["schema_version"] = 2
    elif mutation == "model":
        a["model_id"] = 1
    elif mutation == "parents":
        s["parents"] = [-1, 0, 1]
    elif mutation == "frames":
        a["frames"].pop()
    elif mutation == "tracks":
        a["frames"][1]["tracks"].pop()
    elif mutation == "order":
        a["frames"][1]["tracks"].reverse()
    elif mutation == "child_translation":
        a["frames"][1]["tracks"][2]["translation"] = [0, 0, 0]
    elif mutation == "variable_translation":
        a["frames"][1]["tracks"][0]["translation"][0] = 1
    elif mutation == "projective":
        s["matrices_columns"][0][3] = 1
    elif mutation == "nonrigid":
        s["matrices_columns"][1][0] = 2
    elif mutation in ("nan", "bool", "large"):
        s["matrices_columns"][0][0] = {"nan": float("nan"), "bool": True, "large": 1e8}[mutation]
    elif mutation == "zero_q":
        a["frames"][0]["tracks"][1]["quaternion_xyzw"] = [0, 0, 0, 0]
    elif mutation == "short_q":
        a["frames"][0]["tracks"][1]["quaternion_xyzw"] = [0, 1]
    elif mutation == "missing_bone":
        s["matrices_columns"].pop()
    elif mutation == "zero_child":
        s["matrices_columns"][2] = s["matrices_columns"][1][:]
    elif mutation == "tiny_child":
        s["matrices_columns"][2][12:15] = [0.001, 1, 0]
        a["frames"][0]["tracks"][0]["translation"] = [100000, 0, 0]
        for f in a["frames"]:
            f["tracks"][0]["translation"] = [100000, 0, 0]
    else:
        a["frame_bytes"] = 47
    with pytest.raises(ValueError):
        inspection_clip(s, a)


@pytest.mark.parametrize(
    "parents,translations,rotations",
    [
        ([-1, -1, 0], [(0, 0, 0)] * 3, [[[0, 0, 0, 1]] * 3] * 24),
        ([-1, -1, 1], [(0, 0, 0)] * 3, [[[0, 0, 0, 1]] * 3] * 24),
        ([-1, -1, 1], [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [[[0, 0, 0, 1]] * 2] * 24),
    ],
)
def test_encoder_rejects_incomplete_shape(parents, translations, rotations):
    with pytest.raises(ValueError):
        encode_clip(parents, translations, rotations)


@pytest.fixture
def bundle(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    s, a = documents()
    entries = []
    for name, doc in (("skeleton.json", s), ("animation.json", a)):
        data = json.dumps(doc).encode()
        (source / name).write_bytes(data)
        entries.append({"file": name, "size": len(data), "sha256": sha(data)})
    manifest = {
        "scope": "ps2_skeleton_animation_candidate",
        "recipe": "sh3-ps2-anm-0209-46-v1",
        "model_id": 0x209,
        "resources": {"model": {"sha256": "a" * 64}, "animation": {"sha256": "b" * 64}},
        "files": entries,
    }
    raw = json.dumps(manifest).encode()
    (source / "manifest.json").write_bytes(raw)
    ref = {
        "schema": "sh3-animation-continuity-observation-v1",
        "continuous_loop_verified": True,
        "natural_initial_selection_verified": True,
        "identity": {
            "start": 0,
            "end": 23,
            "loop": True,
            "actor": {"kind": 0x209},
            "model_sha256": "a" * 64,
            "animation_sha256": "b" * 64,
        },
        "selections": [{"clip": 0x1449}],
        "samples": [{"sample": {"increment": 3686}}] * 28,
        "provenance": {"state_restores": 0},
    }
    rp = tmp_path / "reference.json"
    rp.write_text(json.dumps(ref))
    build = tmp_path / "build"
    build.mkdir()
    artifacts = {
        "sh3_animation_probe.elf": b"ELF",
        "sh3_animation_probe.3dsx": b"3DSXfixture",
        "sh3_animation_probe.smdh": b"SMDHfixture",
        "build-id.txt": b"123456789abc\n",
        "sdk-image.txt": b"fixture\n",
        "toolchain-packages.txt": b"fixture\n",
    }
    for name, data in artifacts.items():
        (build / name).write_bytes(data)
    (build / "SHA256SUMS").write_text("".join(f"{sha(v)}  {k}\n" for k, v in artifacts.items()))
    return source, sha(raw), rp, sha(rp.read_bytes()), build


def test_prepare_and_private_delivery(bundle, tmp_path):
    files, report = prepare_files(*bundle)
    assert (files, report) == prepare_files(*bundle)
    assert report["damage_0x144a"] == report["death_0x144b"] == "pending"
    with zipfile.ZipFile(io.BytesIO(files["sd-card.zip"])) as z:
        assert z.read("3ds/sh3_animation_probe/animation.san") == files["animation.san"]
        assert all("texture" not in p for p in z.namelist())
    private = tmp_path / "private"
    private.mkdir()
    source, digest, reference, ref_sha, build = bundle
    args = [
        "--source",
        str(source),
        "--source-sha256",
        digest,
        "--reference",
        str(reference),
        "--reference-sha256",
        ref_sha,
        "--build",
        str(build),
        "--private-root",
        str(private),
        "--run-id",
        "fixture",
    ]
    assert main(args) == 0
    result = json.loads((private / "fixture/manifest.json").read_text())
    for entry in result["files"]:
        assert sha((private / "fixture" / entry["file"]).read_bytes()) == entry["sha256"]
    with pytest.raises(FileExistsError):
        main(args)


@pytest.mark.parametrize(
    "mutation",
    [
        "source_hash",
        "reference_hash",
        "identity",
        "restored",
        "clip",
        "counter",
        "missing",
        "duplicate",
        "size",
        "tamper",
        "build",
    ],
)
def test_prepare_fails_closed(bundle, mutation):
    source, digest, reference, ref_sha, build = bundle
    if mutation == "source_hash":
        digest = "0" * 64
    elif mutation == "reference_hash":
        ref_sha = "0" * 64
    elif mutation in ("identity", "restored", "clip", "counter"):
        r = json.loads(reference.read_text())
        if mutation == "identity":
            r["identity"]["model_sha256"] = "c" * 64
        elif mutation == "restored":
            r["provenance"]["state_restores"] = 1
        elif mutation == "clip":
            r["selections"][0]["clip"] = 0x144A
        else:
            r["samples"][0]["sample"]["increment"] = 4914
        reference.write_text(json.dumps(r))
        ref_sha = sha(reference.read_bytes())
    elif mutation in ("missing", "duplicate", "size"):
        p = source / "manifest.json"
        m = json.loads(p.read_text())
        if mutation == "missing":
            m["files"].pop()
        elif mutation == "duplicate":
            m["files"].append(m["files"][0])
        else:
            m["files"][0]["size"] += 1
        p.write_text(json.dumps(m))
        digest = sha(p.read_bytes())
    elif mutation == "tamper":
        (source / "animation.json").write_text("{}")
    else:
        (build / "sh3_animation_probe.3dsx").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        prepare_files(source, digest, reference, ref_sha, build)
