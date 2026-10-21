"""Synthetic MDL/ANM pairs and opaque MFA metadata; no original resources."""

import copy
import hashlib
import json
import math
import struct
from io import BytesIO

import pycdlib
import pytest
from test_mfa import Sectors, sector

from tools.inspectors.mfa import MfaError, parse_layout
from tools.pipeline import decode_skeleton_animation as coordinator
from tools.pipeline.decoders.ps2_animation import (
    MAX_FRAMES,
    MODEL_ID,
    AnimationDecodeError,
    decode_animation,
    encode_animation,
)
from tools.pipeline.decoders.ps2_skeleton import (
    SkeletonDecodeError,
    decode_skeleton,
    validate_parents,
)
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError

IDENTITY = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def mdl(parents=(-1, -1, 1)):
    data = bytearray(160 + len(parents) * 64 + len(parents) + 16)
    struct.pack_into("<8I", data, 0, 0, MODEL_ID, 0, 0, 0, 32, 0, 0)
    struct.pack_into("<5I", data, 32, 0xFFFF0003, 3, 128, len(parents), 128 + len(parents) * 64)
    for index in range(len(parents)):
        values = list(IDENTITY)
        values[1] = -0.0
        values[12:15] = [index * 10, index * -20, index * 30]
        struct.pack_into("<16f", data, 160 + index * 64, *values)
    struct.pack_into(f"<{len(parents)}b", data, 160 + len(parents) * 64, *parents)
    return bytes(data)


def frame(parents=(-1, -1, 1), flags=(10, 14, 9), phase=0):
    result = bytearray()
    for base in range(0, len(flags), 8):
        word = sum(flag << (index * 4) for index, flag in enumerate(flags[base : base + 8]))
        result.extend(struct.pack("<I", word))
        for index, flag in enumerate(flags[base : base + 8], base):
            if not flag & 7:
                continue
            if flag & 2:
                result.extend(
                    struct.pack("<3f" if parents[index] == -1 else "<3e", -0.0, 2 + phase, -3)
                )
            result.extend(struct.pack("<3h", 4096, -8192, 2048))
    assert len(result) == 46
    return bytes(result)


def anm(parents=(-1, -1, 1), flags=(10, 14, 9)):
    return struct.pack("<I", MODEL_ID) + frame(parents, flags) + frame(parents, flags, 1)


def mutate(data, offset, code, *values):
    result = bytearray(data)
    struct.pack_into(code, result, offset, *values)
    return bytes(result)


def test_skeleton_preserves_forest_column_matrices_and_bits():
    data = mdl()
    result = decode_skeleton(data)
    assert result.parents == (-1, -1, 1)
    assert result.model_id == MODEL_ID
    assert result.matrices_columns[2][12:15] == (20, -40, 60)
    assert result.matrix_words[0][1] == 0x80000000
    assert b"".join(struct.pack("<16I", *w) for w in result.matrix_words) == data[160:352]
    assert result.model_header_words[:5] == (0xFFFF0003, 3, 128, 3, 320)


@pytest.mark.parametrize(
    ("offset", "value", "code"),
    [
        (20, 0, "SA_MODEL_HEADER"),
        (20, 33, "SA_MODEL_HEADER"),
        (20, 0xFFFFFFF0, "SA_MODEL_HEADER"),
        (32, 0, "SA_MODEL_VERSION"),
        (36, 4, "SA_MODEL_VERSION"),
        (44, 0, "SA_BONE_COUNT"),
        (44, 129, "SA_BONE_COUNT"),
        (40, 0, "SA_SKELETON_RANGE"),
        (40, 129, "SA_SKELETON_RANGE"),
        (40, 0xFFFFFFF0, "SA_SKELETON_RANGE"),
        (48, 0, "SA_SKELETON_RANGE"),
        (48, 128, "SA_SKELETON_RANGE"),
        (48, 0xFFFFFFFF, "SA_SKELETON_RANGE"),
    ],
)
def test_invalid_mdl_ranges_and_versions(offset, value, code):
    with pytest.raises(SkeletonDecodeError, match=code):
        decode_skeleton(mutate(mdl(), offset, "<I", value))


@pytest.mark.parametrize("data", [b"", b"own", bytes(31), bytearray(mdl()), None])
def test_invalid_model_payload(data):
    with pytest.raises(SkeletonDecodeError, match="SA_MODEL_SIZE"):
        decode_skeleton(data)


@pytest.mark.parametrize("value", [float("inf"), -float("inf"), float("nan")])
def test_nonfinite_matrices(value):
    with pytest.raises(SkeletonDecodeError, match="SA_MATRIX_NONFINITE"):
        decode_skeleton(mutate(mdl(), 160, "<f", value))


def test_projective_matrix_is_not_accepted_as_skeleton_transform():
    with pytest.raises(SkeletonDecodeError, match="SA_MATRIX_AFFINE"):
        decode_skeleton(mutate(mdl(), 160 + 12, "<f", 1))


@pytest.mark.parametrize("parents", [(), (-2,), (1,), (True,), [-1], tuple([-1] * 129)])
def test_invalid_parents(parents):
    with pytest.raises(SkeletonDecodeError, match="SA_PARENTS"):
        validate_parents(parents)


@pytest.mark.parametrize("parents", [(0,), (1, 0), (-1, 2, 1)])
def test_cycles_rejected(parents):
    with pytest.raises(SkeletonDecodeError, match="SA_PARENT_CYCLE"):
        decode_skeleton(mdl(parents))


def test_forward_parent_and_multiple_roots_are_supported():
    assert decode_skeleton(mdl((2, -1, 1))).parents == (2, -1, 1)
    assert len(decode_skeleton(mdl(tuple([-1] * 128))).parents) == 128


def test_animation_keeps_signed_w_root_translations_flags_and_sample_order():
    raw = anm()
    animation = decode_animation(raw, MODEL_ID, (-1, -1, 1))
    assert encode_animation(animation) == raw
    assert len(animation.frames) == 2
    first = animation.frames[0].tracks
    assert [track.flag for track in first] == [10, 14, 9]
    assert [track.bone_index for track in first] == [0, 1, 2]
    assert first[0].translation_words[0] == 0x80000000
    assert first[0].translation == (-0.0, 2, -3)
    assert first[1].translation_format == "float32"
    assert first[2].translation is None
    assert first[2].translation_words is None
    assert first[2].translation_format is None
    assert first[0].rotation_words == (4096, -8192, 2048)
    xyz = (1 / 8, -1 / 4, 1 / 16)
    expected_w = math.sqrt(235) / 16
    assert first[0].quaternion_xyzw == pytest.approx((*xyz, expected_w))
    assert first[1].quaternion_xyzw == pytest.approx((*xyz, -expected_w))
    assert animation.frames[1].tracks[0].translation[1] == 3


def test_child_half_float_and_sparse_track_preservation():
    parents, flags = (-1, 0, 0, 0), (2, 6, 1, 5)
    data = anm(parents, flags)
    result = decode_animation(data, MODEL_ID, parents)
    assert encode_animation(result) == data
    child = result.frames[0].tracks[1]
    assert child.translation_format == "float16"
    assert child.translation == (-0.0, 2, -3)
    assert child.translation_words == (0x8000, 0x4000, 0xC200)
    assert child.quaternion_xyzw[3] < 0
    parents, flags = (-1, -1, -1, 2), (8, 2, 2, 1)
    data = anm(parents, flags)
    result = decode_animation(data, MODEL_ID, parents)
    assert [t.bone_index for t in result.frames[0].tracks] == [1, 2, 3]
    assert result.frames[0].flags[0] & 15 == 8
    assert encode_animation(result) == data


def test_multiple_flag_groups_and_absent_tail():
    parents = (-1,) + (0,) * 25
    flags = [0] * 25
    flags[0], flags[8], flags[24] = 2, 1, 5
    data = anm(parents, flags)
    result = decode_animation(data, MODEL_ID, parents)
    assert len(result.frames[0].flags) == 4
    assert [t.bone_index for t in result.frames[0].tracks] == [0, 8, 24]
    assert encode_animation(result) == data  # Bone 25 remains explicitly absent.


@pytest.mark.parametrize("data", [b"", bytes(4), None, bytearray(anm()), anm()[:-1], anm() + b"x"])
def test_animation_sizes(data):
    with pytest.raises(AnimationDecodeError):
        decode_animation(data, MODEL_ID, (-1, -1, 1))


@pytest.mark.parametrize("model_id", [0, True, "521"])
def test_animation_recipe_is_explicit(model_id):
    with pytest.raises(AnimationDecodeError, match="SA_ANIMATION_RECIPE"):
        decode_animation(anm(), model_id, (-1, -1, 1))


@pytest.mark.parametrize(
    ("offset", "fmt", "value", "code"),
    [
        (0, "<I", 0x100, "SA_MODEL_ID_MISMATCH"),
        (4, "<I", 3, "SA_ANIMATION_FLAG"),
        (4, "<I", 4, "SA_ANIMATION_FLAG"),
        (4, "<I", 7, "SA_ANIMATION_FLAG"),
        (4, "<I", 0x1000, "SA_BONE_REFERENCE"),
        (4, "<I", 0x8000, "SA_BONE_REFERENCE"),
        (4, "<I", 0, "SA_FRAME_TRAILER"),
        (4, "<I", 0x2AA, "SA_FRAME_TRUNCATED"),
        (8, "<f", float("nan"), "SA_TRANSLATION_NONFINITE"),
    ],
)
def test_malformed_animation(offset, fmt, value, code):
    with pytest.raises(AnimationDecodeError, match=code):
        decode_animation(mutate(anm(), offset, fmt, value), MODEL_ID, (-1, -1, 1))


def test_rejects_nonfinite_child_translation_and_invalid_quaternion():
    parents = (-1, 0, 0, 0)
    data = anm(parents, (2, 2, 1, 1))
    with pytest.raises(AnimationDecodeError, match="SA_TRANSLATION_NONFINITE"):
        decode_animation(mutate(data, 26, "<H", 0x7C00), MODEL_ID, parents)
    with pytest.raises(AnimationDecodeError, match="SA_QUATERNION_NORM"):
        decode_animation(mutate(anm(), 20, "<3h", 32767, 32767, 32767), MODEL_ID, (-1, -1, 1))
    # At the unit sphere boundary W is exactly zero; no normalization of XYZ.
    data = mutate(anm(), 20, "<3h", -32768, 0, 0)
    assert decode_animation(data, MODEL_ID, (-1, -1, 1)).frames[0].tracks[0].quaternion_xyzw == (
        -1,
        0,
        0,
        0,
    )


def test_sample_budget_and_model_budget(monkeypatch):
    from tools.pipeline.decoders import ps2_skeleton

    data = struct.pack("<I", MODEL_ID) + frame() * (MAX_FRAMES + 1)
    with pytest.raises(AnimationDecodeError, match="SA_FRAME_COUNT"):
        decode_animation(data, MODEL_ID, (-1, -1, 1))
    monkeypatch.setattr(ps2_skeleton, "MAX_MODEL_BYTES", 32)
    with pytest.raises(SkeletonDecodeError, match="SA_MODEL_SIZE"):
        decode_skeleton(mdl())


def test_opaque_names_preserve_bytes_without_changing_ascii_default():
    raw = bytearray(sector())
    raw[240] = 255
    reader = Sectors({0: bytes(raw)})
    with pytest.raises(MfaError, match="Unsupported name bytes"):
        parse_layout(reader, 4096, "d8")
    result = parse_layout(reader, 4096, "d8", name_policy="opaque_bytes")
    assert result.entries[0].name == bytes(raw[240:251])
    assert result.summary["name_policy"] == "opaque_bytes"
    assert reader.calls == [(0, 2048), (0, 2048)]


def test_opaque_names_are_not_paths_and_duplicates_remain_separate_ordinals():
    reader = Sectors({0: sector(("../own", "../own"))})
    result = parse_layout(reader, 4096, "d8", name_policy="opaque_bytes")
    assert [e.name for e in result.entries] == [b"../own", b"../own"]
    assert [e.entry_ordinal for e in result.entries] == [1, 2]
    with pytest.raises(MfaError):
        parse_layout(reader, 4096, "d8")
    with pytest.raises(MfaError, match="Unknown name policy"):
        parse_layout(reader, 4096, "d8", name_policy="guessed_encoding")


@pytest.mark.parametrize("change", ["terminator", "empty", "overlap", "late_block"])
def test_opaque_names_do_not_skip_structural_validation(change):
    raw = bytearray(sector(("own", "two"), ranges=[(0, 16), (32, 16)]))
    if change == "terminator":
        raw[256:] = b"x" * (2048 - 256)
    elif change == "empty":
        raw[256] = 0
    elif change == "overlap":
        struct.pack_into("<I", raw, 244, 8)
    sectors = {0: bytes(raw)}
    if change == "late_block":
        sectors[4096] = bytes(2048)
    with pytest.raises(MfaError):
        parse_layout(
            Sectors(sectors),
            8192 if change == "late_block" else 4096,
            "d8",
            name_policy="opaque_bytes",
        )


@pytest.fixture
def pair(tmp_path):
    model, animation = mdl(), anm()
    metadata = bytearray(
        sector(("own/model", "own/animation"), ranges=[(0, len(model)), (512, len(animation))])
    )
    # Include an unresolved name; it must not become a path or prevent structural reading.
    metadata[256] = 255
    payload = bytearray(2048)
    payload[: len(model)] = model
    payload[512 : 512 + len(animation)] = animation
    archive = bytes(metadata + payload)
    disc = pycdlib.PyCdlib()
    disc.new(interchange_level=3, vol_ident="OWNPAIR")
    disc.add_fp(BytesIO(archive), len(archive), iso_path="/OWN.MFA;1")
    path = tmp_path / "own.iso"
    disc.write(str(path))
    disc.close()
    image = path.read_bytes()
    selection = {
        "schema_version": 1,
        "image_size": len(image),
        "image_sha256": sha(image),
        "container": {
            "path": "OWN.MFA",
            "size": len(archive),
            "sha256": sha(archive),
            "layout": "d8",
        },
        "model": {"ordinal": 1, "size": len(model), "sha256": sha(model)},
        "animation": {"ordinal": 2, "size": len(animation), "sha256": sha(animation)},
    }
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps(selection))
    private = tmp_path / "private"
    private.mkdir()
    return path, selection, selection_path, private


def arguments(pair):
    iso, _, selection, private = pair
    return [
        "--iso",
        str(iso),
        "--selection",
        str(selection),
        "--selection-sha256",
        sha(selection.read_bytes()),
        "--private-root",
        str(private),
        "--run-id",
        "pair-a",
    ]


def test_pair_repeated_iso_and_private_output(pair):
    iso, selection, _, private = pair
    with IsoImage(iso) as reader:
        files, report = coordinator.decode_pair(reader, selection)
    with IsoImage(iso) as reader:
        assert coordinator.decode_pair(reader, selection) == (files, report)
    assert report["summary"] == {"bones": 3, "roots": 2, "samples": 2, "tracks": 6}
    assert report["runtime_binding"] == "unverified" and report["capabilities"] == []
    assert report["resources"]["model"]["name_bytes_hex"].startswith("ff")
    assert coordinator.main(arguments(pair)) == 0
    for name, data in files.items():
        assert (private / "pair-a" / name).read_bytes() == data
    args = arguments(pair)
    args[-1] = "pair-b"
    assert coordinator.main(args) == 0
    assert (private / "pair-a/manifest.json").read_bytes() == (
        private / "pair-b/manifest.json"
    ).read_bytes()
    assert coordinator.main(args) == 1  # Never overwrite a previous delivery.


@pytest.mark.parametrize(
    "mutation", ["schema", "extra", "hash", "size", "ordinal", "same", "layout", "path"]
)
def test_bad_selection_before_reading(pair, mutation):
    selection = copy.deepcopy(pair[1])
    if mutation == "schema":
        selection["schema_version"] = True
    elif mutation == "extra":
        selection["guess"] = True
    elif mutation == "hash":
        selection["model"]["sha256"] = "wrong"
    elif mutation == "size":
        selection["animation"]["size"] = 1 << 30
    elif mutation == "ordinal":
        selection["model"]["ordinal"] = True
    elif mutation == "same":
        selection["animation"]["ordinal"] = 1
    elif mutation == "layout":
        selection["container"]["layout"] = "b8"
    else:
        selection["container"]["path"] = "../escape"
    with pytest.raises(ProfileError):
        coordinator.decode_pair(None, selection)


@pytest.mark.parametrize(
    ("target", "field", "value", "code"),
    [
        (None, "image_sha256", "0" * 64, "IMAGE_MISMATCH"),
        ("container", "sha256", "0" * 64, "SA_CONTAINER_IDENTITY"),
        ("model", "ordinal", 3, "SA_RESOURCE_MISSING"),
        ("model", "size", 1, "SA_RESOURCE_SIZE"),
        ("model", "sha256", "0" * 64, "SA_RESOURCE_HASH"),
    ],
)
def test_changed_identity_or_selection_rejected(pair, target, field, value, code):
    selection = copy.deepcopy(pair[1])
    (selection if target is None else selection[target])[field] = value
    with IsoImage(pair[0]) as reader, pytest.raises(ProfileError) as caught:
        coordinator.decode_pair(reader, selection)
    assert caught.value.code == code


def test_short_payload_and_close_mutation_prevent_publication(pair, monkeypatch):
    read = IsoImage.read_range

    def short(self, path, offset, length):
        return b"" if offset >= 2048 else read(self, path, offset, length)

    with monkeypatch.context() as patch:
        patch.setattr(IsoImage, "read_range", short)
        assert coordinator.main(arguments(pair)) == 1
    assert not (pair[3] / "pair-a").exists()
    decode = coordinator.decode_pair

    def changed(reader, selection):
        result = decode(reader, selection)
        with pair[0].open("ab") as stream:
            stream.write(b"own change")
        return result

    monkeypatch.setattr(coordinator, "decode_pair", changed)
    assert coordinator.main(arguments(pair)) == 1
    assert not (pair[3] / "pair-a").exists()
