"""Synthetic mesh and provenance controls; no original game data."""

import copy
import hashlib
import io
import json
import struct
import zipfile
import zlib

import pytest
import test_animation_inspection as animation_tests

from tools.pipeline.animation_inspection import inspection_clip
from tools.pipeline.character_inspection import encode_character, inspection_character
from tools.pipeline.prepare_character_probe import main, prepare_files


def fixture():
    skeleton, animation = animation_tests.documents()
    clip = inspection_clip(skeleton, animation)
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    words = list(struct.unpack("<16I", struct.pack("<16f", *identity)))
    vertices = [
        dict(
            position_q4=p,
            normal_q12=[0, 4096, 0],
            uv_q12=[0, 0],
            weights_q12=[2048, 1023, 1023],
            primary_bone=0,
            bones=[0, 1, 2],
        )
        for p in ([0, 0, 0], [16, 0, 0], [0, 16, 0])
    ]
    mesh = dict(
        schema_version=1,
        helpers=[[0, 1], [0, 2], [1, 2]],
        helper_matrix_words=[words] * 3,
        submeshes=[
            dict(
                blend_partition=False,
                vertices=vertices,
                groups=[dict(header_words=[3, 0, 0, 0], helper_indices=[0, 1])],
                triangles=[[0, 1, 2]],
            )
        ],
    )
    return mesh, clip


def test_preserves_integer_data_and_conservative_framing():
    mesh, clip = fixture()
    raw = inspection_character(mesh, clip)
    assert raw == inspection_character(mesh, clip)
    assert struct.unpack_from("<6I", raw, 8) == (3, 3, 3, 28, 310, zlib.crc32(raw[32:]))
    values = struct.unpack_from("<8h3H4BH", raw, 252)
    assert values[8:11] == (2048, 1023, 1023)
    assert values[11:] == (0, 3, 0, 1, 0)
    assert struct.unpack_from("<3H", raw, len(raw) - 6) == (0, 1, 2)
    assert 0 < struct.unpack_from("<f", raw, 44)[0] < 1


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "blend",
        "binding",
        "group",
        "indices",
        "weights",
        "position",
        "normal",
        "uv",
        "primary",
        "helper",
        "matrix",
        "nan",
        "count",
        "short_clip",
    ],
)
def test_invalid_conversion(mutation):
    mesh, clip = fixture()
    s = mesh["submeshes"][0]
    v = s["vertices"][0]
    if mutation == "version":
        mesh["schema_version"] = 2
    elif mutation == "blend":
        s["blend_partition"] = True
    elif mutation == "binding":
        v["bones"] = [0, 2, 2]
    elif mutation == "group":
        s["groups"][0]["header_words"][0] = 4
    elif mutation == "indices":
        s["triangles"] = [[0, 1, 3]]
    elif mutation == "weights":
        v["weights_q12"] = [2047, 1023, 1023]
    elif mutation in ("position", "normal", "uv"):
        v[mutation + "_q" + ("4" if mutation == "position" else "12")][0] = 32768
    elif mutation == "primary":
        v["primary_bone"] = 3
    elif mutation == "helper":
        s["groups"][0]["helper_indices"] = [3, 1]
    elif mutation == "matrix":
        mesh["helper_matrix_words"][0][3] = 0x3F800000
    elif mutation == "nan":
        mesh["helper_matrix_words"][0][0] = 0x7FC00000
    elif mutation == "count":
        s["groups"][0]["header_words"][0] = 0
    else:
        clip = clip[:-1]
    with pytest.raises(ValueError):
        inspection_character(mesh, clip)


@pytest.mark.parametrize(
    "change",
    ["scale", "center", "targets", "affine", "vertices", "indices", "zero_weights", "many_weights"],
)
def test_encoder_limits(change):
    mesh, clip = fixture()
    v = dict(mesh["submeshes"][0]["vertices"][0], helper_indices=[0, 1])
    args = [
        [0, 0, 0],
        0.1,
        [1, 2, 2],
        [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1] for _ in range(3)],
        [copy.deepcopy(v) for _ in range(3)],
        [0, 1, 2],
    ]
    if change == "scale":
        args[1] = 0
    elif change == "center":
        args[0] = [True, 0, 0]
    elif change == "targets":
        args[2][0] = 3
    elif change == "affine":
        args[3][0][15] = 0
    elif change == "vertices":
        args[4] = []
    elif change == "indices":
        args[5] = [0, 1]
    elif change == "zero_weights":
        args[4][0]["weights_q12"] = []
    else:
        args[4][0]["weights_q12"] = [1024] * 4
    with pytest.raises(ValueError):
        encode_character(*args)


@pytest.fixture
def bundle(tmp_path):
    source, digest, reference, ref_sha, build = animation_tests.bundle.__wrapped__(tmp_path)
    # Reuse the signed synthetic animation identity, with a different viewer build.
    for p in list(build.iterdir()):
        if p.name.startswith("sh3_animation"):
            p.rename(build / p.name.replace("animation", "character"))
    (build / "SHA256SUMS").write_text(
        "".join(
            f"{animation_tests.sha(p.read_bytes())}  {p.name}\n"
            for p in sorted(build.iterdir())
            if p.name != "SHA256SUMS"
        )
    )
    mesh, _ = fixture()
    raw = json.dumps(mesh).encode()
    mesh_sha = animation_tests.sha(raw)
    ms = tmp_path / "mesh"
    ms.mkdir()
    (ms / "mesh.json").write_bytes(raw)
    manifest = dict(
        scope="ps2_character_mesh_candidate",
        model_id=0x209,
        recipe="mdl_v3_unmasked_skip_vif_integer_mesh_v1",
        resources={"model": {"sha256": "a" * 64}, "animation": {"sha256": "b" * 64}},
        files=[dict(file="mesh.json", sha256=mesh_sha, size=len(raw))],
    )
    mr = json.dumps(manifest).encode()
    (ms / "manifest.json").write_bytes(mr)
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        json.dumps(
            dict(
                schema_version=1,
                scope="cm_t4_bounded_character_skinning",
                status="pass",
                vertex_samples=500,
                distinct_vertices=125,
                poses=[{}] * 4,
                provenance=dict(
                    guest_writes=False,
                    mdl_sha256="a" * 64,
                    anm_sha256="b" * 64,
                    mesh_sha256=mesh_sha,
                ),
                gs=dict(resident_tail_packet_exact=True),
            )
        )
    )
    return (
        source,
        digest,
        reference,
        ref_sha,
        ms,
        animation_tests.sha(mr),
        runtime,
        animation_tests.sha(runtime.read_bytes()),
        build,
    )


def test_delivery_reproducible_and_exclusive(bundle, tmp_path):
    files, report = prepare_files(*bundle)
    assert (files, report) == prepare_files(*bundle)
    assert report["physical_2ds_xl"] == report["damage_0x144a"] == "pending"
    with zipfile.ZipFile(io.BytesIO(files["sd-card.zip"])) as z:
        assert z.read("3ds/sh3_character_probe/character.scm") == files["character.scm"]
    private = tmp_path / "private"
    private.mkdir()
    names = (
        "source",
        "source-sha256",
        "reference",
        "reference-sha256",
        "mesh-source",
        "mesh-sha256",
        "runtime",
        "runtime-sha256",
        "build",
    )
    args = [item for n, v in zip(names, bundle, strict=True) for item in ("--" + n, str(v))]
    args += ["--private-root", str(private), "--run-id", "fixture"]
    assert main(args) == 0
    with pytest.raises(FileExistsError):
        main(args)


@pytest.mark.parametrize(
    "mutation",
    [
        "hash",
        "status",
        "writes",
        "model",
        "mesh_identity",
        "gs",
        "count",
        "size",
        "tamper",
        "duplicate",
    ],
)
def test_prepare_rejects_bad_provenance(bundle, mutation):
    args = list(bundle)
    ms = args[4]
    rt = args[6]
    m = json.loads((ms / "manifest.json").read_text())
    r = json.loads(rt.read_text())
    if mutation == "hash":
        args[7] = "0" * 64
    elif mutation == "status":
        r["status"] = "fail"
    elif mutation == "writes":
        r["provenance"]["guest_writes"] = True
    elif mutation == "model":
        r["provenance"]["mdl_sha256"] = "c" * 64
    elif mutation == "mesh_identity":
        r["provenance"]["mesh_sha256"] = "d" * 64
    elif mutation == "gs":
        r["gs"]["resident_tail_packet_exact"] = False
    elif mutation == "count":
        r["vertex_samples"] = 1
    elif mutation == "size":
        m["files"][0]["size"] += 1
    elif mutation == "duplicate":
        m["files"].append(m["files"][0])
    else:
        (ms / "mesh.json").write_bytes(b"{}")
    if mutation != "hash":
        rt.write_text(json.dumps(r))
        args[7] = hashlib.sha256(rt.read_bytes()).hexdigest()
    (ms / "manifest.json").write_text(json.dumps(m))
    args[5] = animation_tests.sha((ms / "manifest.json").read_bytes())
    with pytest.raises(ValueError):
        prepare_files(*args)
