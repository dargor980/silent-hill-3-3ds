"""Analytical 73-bone vectors for the explicitly selected Heather recipe."""

import struct

import pytest

from tools.pipeline.decoders.ps2_animation import (
    HEATHER_RECIPE,
    AnimationDecodeError,
    decode_animation,
    encode_animation,
)

PARENTS = (-1, -1, *range(1, 72))


def animation(samples=2):
    data = bytearray(struct.pack("<I", 0x100))
    present = set(range(35)) | {40}
    for sample in range(samples):
        frame = bytearray()
        for base in range(0, 48, 8):
            flags = [
                0 if b not in present else (10 if b < 2 else 13) for b in range(base, base + 8)
            ]
            frame.extend(struct.pack("<I", sum(f << (i * 4) for i, f in enumerate(flags))))
            for index, flag in enumerate(flags, base):
                if not flag:
                    continue
                if index < 2:
                    frame.extend(struct.pack("<3f", -0.0, sample + index, -3.5))
                frame.extend(struct.pack("<3h", 0, 0, sample * 1024))
        assert len(frame) == 264
        data.extend(frame)
    return bytes(data)


def test_heather_sparse_tracks_roundtrip_and_root_bits():
    raw = animation()
    decoded = decode_animation(raw, 0x100, PARENTS)
    assert decoded.recipe == HEATHER_RECIPE and decoded.frame_bytes == 264
    assert len(decoded.frames) == 2
    assert len(decoded.frames[0].tracks) == 36
    assert decoded.frames[0].tracks[-1].bone_index == 40
    assert decoded.frames[0].tracks[0].translation_words[0] == 0x80000000
    assert decoded.frames[0].tracks[2].quaternion_xyzw[3] == -1
    assert encode_animation(decoded) == raw


@pytest.mark.parametrize("parents", [(-1, -1, 1), PARENTS[:-1], (*PARENTS, 72)])
def test_heather_requires_its_skeleton_size(parents):
    with pytest.raises(AnimationDecodeError, match="SKELETON"):
        decode_animation(animation(), 0x100, parents)


@pytest.mark.parametrize("delta", [-264, -1, 1, 4, 46, 263])
def test_heather_rejects_partial_or_empty_samples(delta):
    raw = animation(1)
    raw = raw[:delta] if delta < 0 else raw + bytes(delta)
    with pytest.raises(AnimationDecodeError):
        decode_animation(raw, 0x100, PARENTS)


@pytest.mark.parametrize("offset,value", [(0, 0x209), (4, 0xBBBBBBBB), (4 + 264, 0xFFFFFFFF)])
def test_heather_rejects_wrong_id_and_flags(offset, value):
    raw = bytearray(animation())
    struct.pack_into("<I", raw, offset, value)
    with pytest.raises(AnimationDecodeError):
        decode_animation(bytes(raw), 0x100, PARENTS)


@pytest.mark.parametrize("offset", [8, 12, 16, 272, 276, 280])
def test_nonfinite_translations_rejected(offset):
    raw = bytearray(animation())
    struct.pack_into("<I", raw, offset, 0x7F800000)
    with pytest.raises(AnimationDecodeError, match="NONFINITE"):
        decode_animation(bytes(raw), 0x100, PARENTS)


def test_heather_never_uses_horse_stride():
    with pytest.raises(AnimationDecodeError, match="MODEL_ID_MISMATCH"):
        decode_animation(animation(), 0x209, (-1, -1, 1))


def test_bounded_resource_size():
    with pytest.raises(AnimationDecodeError, match="SIZE"):
        decode_animation(struct.pack("<I", 0x100) + bytes(512 * 1024), 0x100, PARENTS)
