"""Invented multi-clip inputs; literal wire assertions independent of producer tables."""

import copy
import hashlib
import json
import math
import shlex
import struct
import zlib
from pathlib import Path

import pytest
import yaml
from test_rig_inspection import own_heather_shape, own_rig

from tools.pipeline.locomotion_inspection import encode_locomotion_rig, heather_locomotion_rig
from tools.pipeline.rig_inspection import encode_rig, heather_rig, prepare_heather_rig

# Literal expected values, deliberately not imported from production.
BONES = (
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
CHANNEL2 = {1, 3, 5, 7, 8, 10, 12, 13, 14, 16, 17, 21, 27, 33, 35}
CHANNELS = tuple(2 if b in CHANNEL2 else 1 for b in BONES)
SAMPLES = (*range(10), *range(80, 104), *range(176, 200))
PAL = bytes.fromhex("65000a0033010000090001006d001800cc0750006700010071001800b308b000c7000100")


def own_locomotion_shape():
    geometry, animation, textures = own_heather_shape()
    mesh = geometry["mesh"]
    for part in mesh["submeshes"]:
        for v in part["vertices"]:
            v["bones"] = [BONES[b] for b in v["bones"]]
            v["primary_bone"] = BONES[v["primary_bone"]]
    for helper in mesh["helpers"]:
        helper[1] = BONES[helper[1]]
    matrices = []
    for b in range(73):
        matrix = list(mesh["skeleton"]["matrices_columns"][b])
        matrix[12:15] = [b / 16, b / 32, -b / 64]
        matrices.append(matrix)
    mesh["skeleton"]["matrices_columns"] = matrices
    # Unselected tracks are poisoned to detect accidental contiguous 0..57 selection.
    animation["frames"] = [dict(tracks=[])] * 1763
    for f in SAMPLES:
        animation["frames"][f] = dict(
            tracks=[
                dict(
                    bone_index=b,
                    translation=[f / 8 + b, 2 * b, -f / 16] if b < 2 else None,
                    quaternion_xyzw=[0, 0, math.sin((f + b) / 1000), math.cos((f + b) / 1000)],
                )
                for b in BONES
            ]
        )
    return geometry, animation, textures


def own_wire():
    rig = own_rig()
    del rig["clip_id"], rig["increment"]
    rig["parents"] = [-1, -1] + [1] * 34
    rig["frames"] = [[[[0, 0, 0], [0, 0, 0, 1]] for _ in range(36)] for _ in range(58)]
    return dict(**rig, source_bones=BONES, channels=CHANNELS, descriptors=PAL)


def test_sri1_bytes_are_unchanged_by_shared_preparation():
    assert hashlib.sha256(encode_rig(**own_rig())).hexdigest() == (
        "1d14965d162764cb29dcf4189b360fe19926324d4a204c0307229a5fefb5c9fd"
    )
    files, _ = heather_rig(*own_heather_shape())
    assert hashlib.sha256(files["heather.sri"]).hexdigest() == (
        "43f1f8544668c8fc956e44ea871b2ea703417faab8dc0ddaf8ccf7a2abc6d68a"
    )


@pytest.mark.parametrize("maximum", [False, True])
def test_structural_geometry_boundaries_are_encodable(maximum):
    d = own_wire()
    v = d["vertices"][0]
    if maximum:
        v.update(primary_bone=35, weights_q12=[1366, 1365, 1365], helper_indices=[0, 127])
        d["helpers"] *= 128
        d["targets"] = [35] * 128
        d["vertices"] = [v] * 8192
        d["indices"] = [i % 8192 for i in range(18000)]
        d["materials"] = [[i * 1125, 1125, i, 512, 1024, int(i > 7), 0xFFFFFFFF] for i in range(16)]
    else:
        v.update(primary_bone=35, weights_q12=[4096], helper_indices=[])
        d["vertices"] = [v] * 3
        d["helpers"], d["targets"] = [], []
    d["center"], d["scale"] = [-100000, 0, 100000], 1
    raw = encode_locomotion_rig(**d)
    nb, nf, nh, nv, ni, nm = struct.unpack_from("<6I", raw, 8)
    assert len(raw) == 96 + 16 + 8 * nb + 60 + 28 * nb * nf + 68 * nh + 28 * nv + 2 * ni + 28 * nm
    vertex_at = 460 + 28 * 36 * 58 + 68 * nh
    vertex = struct.unpack_from("<8h3H4BH", raw, vertex_at)
    assert vertex[8:] == (
        (1366, 1365, 1365, 35, 3, 0, 127, 0) if maximum else (4096, 0, 0, 35, 1, 255, 255, 0)
    )


def test_full_layout_preserves_every_selected_sample_and_source_binding():
    g, a, t = own_locomotion_shape()
    before = copy.deepcopy((g, a, t))
    files, report = heather_locomotion_rig(g, a, t, PAL)
    assert (g, a, t) == before
    assert (files, report) == heather_locomotion_rig(g, a, dict(reversed(list(t.items()))), PAL)
    assert len(files) == 14
    raw = files["heather.sri"]
    assert type(raw) is bytes and len(raw) == 290156
    assert struct.unpack_from("<8s22I", raw) == (
        b"S3RIv2\0\0",
        36,
        58,
        49,
        6943,
        16566,
        13,
        3,
        2,
        25,
        1,
        522,
        525,
        290060,
        zlib.crc32(raw[96:]),
        *([0] * 8),
    )
    center_scale = struct.unpack_from("<4f", raw, 96)
    assert center_scale[:3] == (0.5, 1, 0)
    assert center_scale[3] == pytest.approx(report["framing"]["scale"], abs=1e-8)
    assert struct.unpack_from("<36i", raw, 112) == (-1, -1, *([1] * 34))
    at = 256
    for i, b in enumerate(BONES):
        assert struct.unpack_from("<HBB", raw, at) == (b, CHANNELS[i], 0)
        assert report["bones"][i] == dict(
            source=b,
            compact=i,
            channel=CHANNELS[i],
            source_parent=-1 if b < 2 else 1,
            compact_parent=-1 if b < 2 else 1,
        )
        at += 4
    for i, (clip, count, speed, start, end, first) in enumerate(
        (
            (101, 10, 307, 0, 9, 0),
            (109, 24, 1996, 80, 103, 10),
            (113, 24, 2227, 176, 199, 34),
        )
    ):
        assert struct.unpack_from("<HHhHHBBII", raw, at) == (
            clip,
            count,
            speed,
            start,
            end,
            1,
            0,
            first,
            0,
        )
        c = report["clips"][i]
        assert c["descriptor_hex"] == PAL[i * 12 : (i + 1) * 12].hex()
        assert c["source_samples"] == list(range(start, end + 1))
        assert c["packed_samples"] == list(range(first, first + count))
        at += 20
    assert at == 460
    for source in SAMPLES:
        for i, b in enumerate(BONES):
            track = a["frames"][source]["tracks"][i]
            pos = track["translation"]
            if b >= 2:
                # Invented rigid parents have identity rotation and known origins.
                pos = [(b - 1) / 16, (b - 1) / 32, -(b - 1) / 64]
            expected = (*pos, *track["quaternion_xyzw"])
            assert struct.unpack_from("<7f", raw, at) == pytest.approx(expected, abs=1e-7, rel=0)
            at += 28
    # Shared geometry follows once. Inspect bindings, original integers and full range coverage.
    for h in range(49):
        target, *matrix = struct.unpack_from("<I16f", raw, at)
        assert target == h % 36
        assert matrix == [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        assert report["helpers"][h] == dict(
            source=h, compact=h, compact_target=target, source_target=BONES[target]
        )
        at += 68
    vertices_at = at
    indices_at = at + 6943 * 28
    total_vertices = total_indices = 0
    for mapping in report["submeshes"]:
        part = g["mesh"]["submeshes"][mapping["source"]]
        assert mapping["first_vertex"] == total_vertices
        assert mapping["first_index"] == total_indices
        assert mapping["vertex_count"] == len(part["vertices"])
        assert mapping["index_count"] == 3 * len(part["triangles"])
        for v in part["vertices"]:
            words = struct.unpack_from("<8h3H4BH", raw, vertices_at + total_vertices * 28)
            assert words == (
                *v["position_q4"],
                *v["normal_q12"],
                *v["uv_q12"],
                2048,
                2048,
                0,
                BONES.index(v["primary_bone"]),
                2,
                part["groups"][0]["helper_indices"][0],
                255,
                0,
            )
            total_vertices += 1
        for triangle in part["triangles"]:
            assert struct.unpack_from("<3H", raw, indices_at + total_indices * 2) == tuple(
                mapping["first_vertex"] + i for i in triangle
            )
            total_indices += 3
    assert (total_vertices, total_indices) == (6943, 16566)
    at = indices_at + 16566 * 2
    for i, source in enumerate((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14)):
        first, count, texture, width, height, blend, crc = struct.unpack_from("<7I", raw, at)
        assert (texture, width, height, blend) == (i, 128, 128, int(source == 14))
        assert files[f"texture-{i:02}.rgba"] == t[source][2]
        assert crc == zlib.crc32(t[source][2])
        assert report["materials"][i] == dict(
            source_texture=source,
            texture=i,
            file=f"texture-{i:02}.rgba",
            first_index=first,
            index_count=count,
            width=width,
            height=height,
            blend=blend,
            crc32=crc,
        )
        at += 28
    assert at == len(raw)
    assert report["source_verified"] is False and "sources" not in report
    assert report["outfit_mask"] == 0x3021 and not report["morphs_applied"]
    for name, data in files.items():
        assert report["files"][name] == dict(
            bytes=len(data), sha256=hashlib.sha256(data).hexdigest()
        )
    assert report["descriptors_sha256"] == hashlib.sha256(PAL).hexdigest()
    json.dumps(report, allow_nan=False)


def test_shared_frame_zero_center_and_bound_cover_all_three_clips():
    g, a, t = own_locomotion_shape()
    single, single_receipt = heather_rig(g, a, t)
    files, receipt = heather_locomotion_rig(g, a, t, PAL)
    assert receipt["framing"]["radius"] > single_receipt["framing_radius"]
    assert struct.unpack_from("<3f", files["heather.sri"], 96) == struct.unpack_from(
        "<3f", single["heather.sri"], 64
    )
    assert (
        struct.unpack_from("<f", files["heather.sri"], 108)[0]
        < struct.unpack_from("<f", single["heather.sri"], 76)[0]
    )
    # Deliberately huge unselected sample must not change framing or outputs.
    a["frames"][10] = dict(tracks=[dict(translation=[1e30, 0, 0])])
    assert (files, receipt) == heather_locomotion_rig(g, a, t, PAL)
    # Original outfit hides this group; no geometry, references or material from it may leak.
    g["mesh"]["submeshes"].append(dict(header_words=[0] * 16 + [2 << 16]))
    g["references"].append(["inactive morph"])
    assert (files, receipt) == heather_locomotion_rig(g, a, t, PAL)


@pytest.mark.parametrize("offset", range(36))
def test_every_original_descriptor_byte_is_checked(offset):
    d = own_wire()
    bad = bytearray(PAL)
    bad[offset] ^= 1
    d["descriptors"] = bytes(bad)
    with pytest.raises(ValueError, match="HL_DESCRIPTORS"):
        encode_locomotion_rig(**d)


@pytest.mark.parametrize(
    "descriptors", [None, bytearray(PAL), PAL[:-1], PAL + b"\0", PAL[12:24] + PAL[:12] + PAL[24:]]
)
def test_descriptor_type_length_order(descriptors):
    with pytest.raises(ValueError, match="HL_DESCRIPTORS"):
        heather_locomotion_rig({}, {}, {}, descriptors)


@pytest.mark.parametrize(
    "fault",
    [
        "bone_order",
        "bone_duplicate",
        "bone_bool",
        "channel",
        "channel_bool",
        "channel_count",
        "parents",
        "frame_count",
        "parent_forward",
        "track",
        "nan",
        "inf",
        "translation_bound",
        "quaternion_zero",
        "quaternion_bound",
        "scale",
        "helpers",
        "vertices",
        "indices",
        "material",
        "weight",
        "helper_affine",
    ],
)
def test_wire_rejects_bad_metadata_and_shared_payload(fault):
    d = own_wire()
    if fault == "bone_order":
        d["source_bones"] = tuple(reversed(BONES))
    elif fault == "bone_duplicate":
        d["source_bones"] = (1, *BONES[1:])
    elif fault == "bone_bool":
        d["source_bones"] = (False, *BONES[1:])
    elif fault == "channel":
        d["channels"] = (2, *CHANNELS[1:])
    elif fault == "channel_bool":
        d["channels"] = (True, *CHANNELS[1:])
    elif fault == "channel_count":
        d["channels"] = CHANNELS[:-1]
    elif fault == "parents":
        d["parents"].pop()
    elif fault == "frame_count":
        d["frames"].pop()
    elif fault == "parent_forward":
        d["parents"][3] = 4
    elif fault == "track":
        d["frames"][34].pop()
    elif fault in ("nan", "inf", "translation_bound"):
        d["frames"][57][35][0][0] = {"nan": math.nan, "inf": math.inf, "translation_bound": 100001}[
            fault
        ]
    elif fault == "quaternion_zero":
        d["frames"][10][1][1] = [0, 0, 0, 0]
    elif fault == "quaternion_bound":
        d["frames"][10][1][1] = [0, 0, 0, 1.002]
    elif fault == "scale":
        d["scale"] = 0
    elif fault == "helpers":
        d["helpers"] *= 129
        d["targets"] *= 129
    elif fault == "vertices":
        d["vertices"] = d["vertices"][:1] * 8193
    elif fault == "indices":
        d["indices"][0] = 3
    elif fault == "material":
        d["materials"][0][0] = 3
    elif fault == "weight":
        d["vertices"][0]["weights_q12"] = [0, 0]
    elif fault == "helper_affine":
        d["helpers"][0][15] = 0
    with pytest.raises(ValueError):
        encode_locomotion_rig(**d)


@pytest.mark.parametrize("source", [0, 9, 80, 103, 176, 199])
def test_all_clip_endpoints_require_complete_ordered_tracks(source):
    g, a, t = own_locomotion_shape()
    a["frames"][source]["tracks"].reverse()
    with pytest.raises(ValueError, match="HI_TRACKS"):
        heather_locomotion_rig(g, a, t, PAL)


@pytest.mark.parametrize(
    "fault",
    [
        "map",
        "parent_absent",
        "frame_bytes",
        "model",
        "schema",
        "source_count",
        "texture_missing",
        "texture_short",
        "texture_mutable",
        "missing_key",
        "invalid_shape",
        "helper_range",
        "helper_word",
        "rest_nan",
    ],
)
def test_reducer_rejects_incompatible_inputs_without_mutation(fault):
    g, a, t = own_locomotion_shape()
    mesh = g["mesh"]
    if fault == "map":
        # Replace active bone 42 by a different, still valid source index everywhere.
        for part in mesh["submeshes"]:
            for v in part["vertices"]:
                v["bones"] = [43 if b == 42 else b for b in v["bones"]]
                if v["primary_bone"] == 42:
                    v["primary_bone"] = 43
        for h in mesh["helpers"]:
            if h[1] == 42:
                h[1] = 43
        for f in SAMPLES:
            a["frames"][f]["tracks"][-1]["bone_index"] = 43
    elif fault == "parent_absent":
        mesh["skeleton"]["parents"][42] = 22
    elif fault == "frame_bytes":
        a["frame_bytes"] = 46
    elif fault == "model":
        a["model_id"] = 0x209
    elif fault == "schema":
        g["schema_version"] = 2
    elif fault == "source_count":
        a["frames"].pop()
    elif fault == "texture_missing":
        del t[14]
    elif fault == "texture_short":
        t[14] = (128, 128, b"short")
    elif fault == "texture_mutable":
        t[14] = (128, 128, bytearray(t[14][2]))
    elif fault == "missing_key":
        del g["references"]
    elif fault == "invalid_shape":
        mesh["submeshes"] = None
    elif fault == "helper_range":
        mesh["submeshes"][0]["groups"][0]["helper_indices"] = [999]
    elif fault == "helper_word":
        mesh["helper_matrix_words"][0] = [-1] * 16
    elif fault == "rest_nan":
        mesh["skeleton"]["matrices_columns"][1][0] = math.nan
    before = repr((g, a, t))
    with pytest.raises(ValueError):
        heather_locomotion_rig(g, a, t, PAL)
    assert repr((g, a, t)) == before


@pytest.mark.parametrize("selected", [[], [0], list(range(65)), [-1, 0], [0, 1763], [False, 1]])
def test_shared_preparer_sample_bounds(selected):
    with pytest.raises(ValueError):
        prepare_heather_rig({}, {}, {}, selected)


def test_individual_producer_coverage_gates():
    workflow = yaml.load(Path(".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    commands = [
        shlex.split(line)
        for s in workflow["jobs"]["quality"]["steps"]
        for line in s.get("run", "").splitlines()
    ]
    for name in ("locomotion_inspection", "produce_heather_locomotion"):
        assert any(
            "tools.qa.coverage_gate" in c and "--files" in c and f"tools/pipeline/{name}.py" in c
            for c in commands
        )
