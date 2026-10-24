"""SRI1 encoder, independent native consumer, rejection and pose checks."""

import copy
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

from tools.pipeline.rig_inspection import encode_rig, heather_rig


def own_rig():
    vertex = dict(
        position_q4=[16, 0, 0],
        normal_q12=[0, 4096, 0],
        uv_q12=[0, 0],
        weights_q12=[2048, 2047],
        primary_bone=0,
        helper_indices=[0],
    )
    return dict(
        parents=[-1, 0],
        frames=[
            [[[0, 0, 0], [0, 0, 0, 1]], [[0, 1, 0], [0, 0, 0, 1]]],
            [[[2, 0, 0], [0, 0, 0, 1]], [[0, 1, 0], [0, 0, 0, -1]]],
        ],
        targets=[1],
        helpers=[[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1]],
        vertices=[copy.deepcopy(vertex) for _ in range(3)],
        indices=[0, 1, 2],
        materials=[[0, 3, 0, 128, 128, 1, 0]],
        center=[0, 0, 0],
        scale=0.1,
        clip_id=17,
        increment=1024,
    )


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    out = tmp_path_factory.mktemp("native-rig") / "reader"
    sources = [
        "tests/cpp/test_inspection_rig.cpp",
        "engine/domain/inspection_rig.cpp",
        "engine/domain/render_scene.cpp",
        "engine/domain/lifecycle.cpp",
        "engine/application/render_probe.cpp",
        "engine/application/rig_probe.cpp",
        "engine/platform/common/inspection_rig.cpp",
        "engine/platform/common/inspection_crc32.cpp",
        "engine/platform/common/stdio_files.cpp",
    ]
    includes = [
        "tests/cpp",
        "engine/domain/include",
        "engine/ports/include",
        "engine/application/include",
        "engine/platform/common/include",
    ]
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-O1",
            "-Wall",
            "-Wextra",
            "-Werror",
            *["-I" + str(root / i) for i in includes],
            *[str(root / s) for s in sources],
            "-o",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return out


def test_header_lossless_weights_native_pose_and_wrap(native, tmp_path):
    raw = encode_rig(**own_rig())
    assert struct.unpack_from("<8s14I", raw) == (
        b"S3RIv1\0\0",
        2,
        2,
        1,
        3,
        3,
        1,
        17,
        1024,
        len(raw) - 64,
        zlib.crc32(raw[64:]),
        0,
        0,
        0,
        0,
    )
    path = tmp_path / "own.sri"
    path.write_bytes(raw)
    runs = []
    for counter in (2048, 10240):
        output = subprocess.check_output([native, path, str(counter), "dump"], text=True)
        rows = [[float(x) for x in line.split()] for line in output.splitlines()]
        assert rows[0][12:15] == [1, 0, 0]
        assert rows[1][12:15] == [1, 1, 0]
        # Primary: (2,0,0); helper: (3,1,0); deficient Q12 sum is retained.
        assert rows[2] == pytest.approx(
            [1 + 3 * 2047 / 4096, 2047 / 4096, 0, 4095 / 4096], abs=1e-6
        )
        runs.append(output)
    assert runs[0] == runs[1]


@pytest.mark.parametrize(
    "fault",
    [
        "header",
        "version",
        "count",
        "length",
        "crc",
        "reserved",
        "truncated",
        "trailer",
        "parent",
        "nan",
        "weight",
        "range",
        "close-failure",
        "read-failure",
        "short-read",
    ],
)
def test_native_rejects_invalid_wire_without_publishing(native, tmp_path, fault):
    raw = bytearray(encode_rig(**own_rig()))
    extra = []
    if fault == "header":
        raw = raw[:31]
    elif fault == "version":
        raw[4] ^= 1
    elif fault == "count":
        struct.pack_into("<I", raw, 8, 74)
    elif fault == "length":
        struct.pack_into("<I", raw, 40, 0xFFFFFFFF)
    elif fault == "crc":
        raw[-1] ^= 1
    elif fault == "reserved":
        raw[48] = 1
    elif fault == "truncated":
        raw = raw[:-1]
    elif fault == "trailer":
        raw += b"x"
    elif fault in ("close-failure", "read-failure", "short-read"):
        extra = [fault]
    else:
        if fault == "parent":
            struct.pack_into("<i", raw, 80, 0)
        elif fault == "nan":
            struct.pack_into("<I", raw, 64, 0x7FC00000)
        elif fault == "weight":
            struct.pack_into("<H", raw, 64 + 16 + 8 + 112 + 68 + 16, 100)
        elif fault == "range":
            struct.pack_into("<I", raw, len(raw) - 28, 3)
        struct.pack_into("<I", raw, 44, zlib.crc32(raw[64:]))
    path = tmp_path / "bad.sri"
    path.write_bytes(raw)
    result = subprocess.run([native, path, *extra], capture_output=True)
    assert result.returncode == 2


@pytest.mark.parametrize(
    "fault",
    [
        "counts",
        "parents",
        "scale",
        "increment",
        "tracks",
        "rotation",
        "helper",
        "influences",
        "weights",
        "primary",
        "indices",
        "material",
        "coverage",
        "texture_budget",
        "nan",
    ],
)
def test_encoder_rejects_invalid_contract(fault):
    d = own_rig()
    if fault == "counts":
        d["vertices"] = []
    elif fault == "parents":
        d["parents"] = [-1, 1]
    elif fault == "scale":
        d["scale"] = 0
    elif fault == "increment":
        d["increment"] = 8192
    elif fault == "tracks":
        d["frames"][0] = []
    elif fault == "rotation":
        d["frames"][0][0][1] = [0, 0, 0, 0]
    elif fault == "helper":
        d["helpers"][0][3] = 1
    elif fault == "influences":
        d["vertices"][0]["weights_q12"] = []
    elif fault == "weights":
        d["vertices"][0]["weights_q12"] = [2047, 2047]
    elif fault == "primary":
        d["vertices"][0]["primary_bone"] = 2
    elif fault == "indices":
        d["indices"][0] = 3
    elif fault == "material":
        d["materials"][0][3] = 127
    elif fault == "coverage":
        d["indices"] *= 2
    elif fault == "nan":
        d["center"][0] = float("nan")
    elif fault == "texture_budget":
        d["indices"] *= 9
        d["materials"] = [[i * 3, 3, i, 1024, 1024, 0, 0] for i in range(9)]
    with pytest.raises(ValueError):
        encode_rig(**d)


def own_heather_shape():
    # Invented numbers with the profile's counts, never copied from proprietary geometry.
    identity = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    words = list(struct.unpack("<16I", struct.pack("<16f", *identity)))
    textures = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14]
    sk = dict(model_id=0x100, parents=[-1, -1] + [1] * 71, matrices_columns=[identity] * 73)
    subs = []
    for i in range(79):
        n = 88 if i < 70 else 87
        h, bone, texture = i % 49, i % 36, textures[i % 13]
        v = dict(
            position_q4=[16, 0, 0],
            normal_q12=[0, 4096, 0],
            uv_q12=[0, 0],
            weights_q12=[2048, 2048],
            primary_bone=bone,
            bones=[bone, h % 36],
        )
        subs.append(
            dict(
                header_words=[0] * 17,
                texture_index=texture,
                blend_partition=texture == 14,
                vertices=[copy.deepcopy(v) for _ in range(n)],
                groups=[dict(header_words=[n], helper_indices=[h])],
                triangles=[[0, 1, 2]] * (70 if i < 71 else 69),
            )
        )
    g = dict(
        schema_version=1,
        references=[[] for _ in subs],
        mesh=dict(
            skeleton=sk,
            submeshes=subs,
            helpers=[[0, h % 36] for h in range(49)],
            helper_matrix_words=[words] * 49,
        ),
    )
    tracks = [
        dict(bone_index=b, translation=[0, 0, 0] if b < 2 else None, quaternion_xyzw=[0, 0, 0, 1])
        for b in range(36)
    ]
    a = dict(model_id=0x100, frame_bytes=264, frames=[dict(tracks=tracks)] * 1763)
    t = {i: (128, 128, bytes((17, 31, 67, 128)) * 128 * 128) for i in textures}
    return g, a, t


def test_full_synthetic_profile_selects_and_remaps_without_morphs(native, tmp_path):
    g, a, t = own_heather_shape()
    files, report = heather_rig(g, a, t)
    assert len(files) == 14 and report["appearance"] == "original_normal_game"
    assert not report["native_timing_verified"] and not report["morphs_applied"]
    assert files == heather_rig(g, a, t)[0]
    path = tmp_path / "own.sri"
    path.write_bytes(files["heather.sri"])
    subprocess.run([native, path, "2048"], check=True)


@pytest.mark.parametrize(
    "fault",
    [
        "profile",
        "selection",
        "morphs",
        "bones",
        "helpers",
        "tracks",
        "root",
        "textures",
        "blend",
        "binding",
        "groups",
        "rgba",
        "counts",
    ],
)
def test_original_profile_rejects_incompatible_inputs(fault):
    g, a, t = own_heather_shape()
    s = g["mesh"]["submeshes"][0]
    if fault == "profile":
        a["frame_bytes"] = 46
    elif fault == "selection":
        s["header_words"][16] = 2 << 16
    elif fault == "morphs":
        g["references"][0] = [1]
    elif fault == "bones":
        s["vertices"][0]["bones"] = [72, 1]
    elif fault == "helpers":
        s["groups"][0]["helper_indices"] = [50]
    elif fault == "tracks":
        a["frames"][0]["tracks"] = []
    elif fault == "root":
        a["frames"][0]["tracks"][0]["translation"] = None
    elif fault == "textures":
        s["texture_index"] = 11
    elif fault == "blend":
        s["blend_partition"] = True
    elif fault == "binding":
        s["vertices"][0]["bones"] = [0, 1]
    elif fault == "groups":
        s["groups"][0]["header_words"][0] -= 1
    elif fault == "rgba":
        t[0] = (128, 128, b"x")
    elif fault == "counts":
        s["triangles"] = [[0, 1, 2]]
    with pytest.raises(ValueError):
        heather_rig(g, a, t)


def test_heather_ci_individual_gate():
    import shlex

    import yaml

    workflow = yaml.load(Path(".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    commands = [
        shlex.split(line)
        for s in workflow["jobs"]["quality"]["steps"]
        for line in s.get("run", "").splitlines()
    ]
    gates = [
        c
        for c in commands
        if "tools.qa.coverage_gate" in c
        and "--files" in c
        and "tools/pipeline/rig_inspection.py" in c
    ]
    assert len(gates) == 1
    assert {
        "tools/pipeline/decoders/ps2_character_morphs.py",
        "tools/pipeline/decoders/ps2_indexed.py",
        "tools/pipeline/decode_morph_character.py",
    } <= set(gates[0])


def test_heather_archive_exact_set_determinism_and_hashes():
    import hashlib
    import io
    import zipfile

    from tools.pipeline.inspection_archive import inspection_archive

    names = {"heather.sri", "sh3_heather_probe.3dsx", "sh3_heather_probe.smdh", "LEEME.txt"}
    names |= {f"texture-{i:02}.rgba" for i in range(13)}
    files = {name: name.encode() for name in sorted(names)}
    archive = inspection_archive(files, "sh3_heather_probe")
    assert archive == inspection_archive(dict(reversed(list(files.items()))), "sh3_heather_probe")
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert set(z.namelist()) == {"SHA256SUMS"} | {
            f"3ds/sh3_heather_probe/{name}" for name in names
        }
        for line in z.read("SHA256SUMS").decode().splitlines():
            digest, path = line.split("  ")
            assert hashlib.sha256(z.read(path)).hexdigest() == digest
            assert z.read(path) == files[path.rsplit("/", 1)[1]]
    for missing in names:
        with pytest.raises(ValueError, match="Unexpected inspection archive files"):
            inspection_archive(
                {n: b for n, b in files.items() if n != missing}, "sh3_heather_probe"
            )
    for unexpected in ("texture-13.rgba", "../escape", "/absolute", "character.scm"):
        with pytest.raises(ValueError, match="Unexpected inspection archive files"):
            inspection_archive({**files, unexpected: b"x"}, "sh3_heather_probe")
