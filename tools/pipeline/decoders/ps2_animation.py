"""Lossless ANM samples for explicit PS2 recipes; no clip timing or interpolation."""

import math
import struct
from dataclasses import dataclass

from tools.pipeline.decoders.ps2_skeleton import validate_parents

RECIPE = "sh3-ps2-anm-0209-46-v1"
MODEL_ID = 0x209
FRAME_BYTES = 46
MAX_FRAMES = 4096
MAX_ANIMATION_BYTES = 512 * 1024
HEATHER_MODEL_ID = 0x100
HEATHER_FRAME_BYTES = 264
HEATHER_RECIPE = "sh3-ps2-anm-0100-264-v1"


class AnimationDecodeError(ValueError):
    pass


@dataclass(frozen=True)
class BoneSample:
    bone_index: int
    flag: int
    translation: tuple[float, ...] | None
    translation_words: tuple[int, ...] | None
    translation_format: str | None
    rotation_words: tuple[int, ...]
    quaternion_xyzw: tuple[float, ...]


@dataclass(frozen=True)
class AnimationFrame:
    flags: tuple[int, ...]
    tracks: tuple[BoneSample, ...]


@dataclass(frozen=True)
class Animation:
    model_id: int
    recipe: str
    frame_bytes: int
    frames: tuple[AnimationFrame, ...]


def encode_animation(animation: Animation) -> bytes:
    """Reconstruct only stored fields; derived floats never replace original words."""
    output = bytearray(struct.pack("<I", animation.model_id))
    for frame in animation.frames:
        tracks = {track.bone_index: track for track in frame.tracks}
        for group, flags in enumerate(frame.flags):
            output.extend(struct.pack("<I", flags))
            for bone in range(group * 8, group * 8 + 8):
                if bone not in tracks:
                    continue
                track = tracks[bone]
                if track.translation_words is not None:
                    code = "<3I" if track.translation_format == "float32" else "<3H"
                    output.extend(struct.pack(code, *track.translation_words))
                output.extend(struct.pack("<3h", *track.rotation_words))
    return bytes(output)


def decode_animation(data: bytes, model_id: int, parents: tuple[int, ...]) -> Animation:
    validate_parents(parents)
    if type(model_id) is not int or model_id not in (MODEL_ID, HEATHER_MODEL_ID):
        raise AnimationDecodeError("SA_ANIMATION_RECIPE")
    frame_bytes, recipe = FRAME_BYTES, RECIPE
    if model_id == HEATHER_MODEL_ID:
        if len(parents) != 73:
            raise AnimationDecodeError("SA_ANIMATION_SKELETON")
        frame_bytes, recipe = HEATHER_FRAME_BYTES, HEATHER_RECIPE
    if type(data) is not bytes or not 4 < len(data) <= MAX_ANIMATION_BYTES:
        raise AnimationDecodeError("SA_ANIMATION_SIZE")
    if struct.unpack_from("<I", data)[0] != model_id:
        raise AnimationDecodeError("SA_MODEL_ID_MISMATCH")
    count, remainder = divmod(len(data) - 4, frame_bytes)
    if remainder or not 1 <= count <= MAX_FRAMES:
        raise AnimationDecodeError("SA_FRAME_COUNT")
    frames = []
    for frame_index in range(count):
        cursor = 4 + frame_index * frame_bytes
        end = cursor + frame_bytes

        def take(code, limit=end):
            nonlocal cursor
            size = struct.calcsize(code)
            if cursor + size > limit:
                raise AnimationDecodeError("SA_FRAME_TRUNCATED")
            value = struct.unpack_from(code, data, cursor)
            cursor += size
            return value

        groups, tracks = [], []
        while cursor < end:
            base = len(groups) * 8
            if base >= len(parents):
                raise AnimationDecodeError("SA_FRAME_TRAILER")
            flags = take("<I")[0]
            groups.append(flags)
            for index in range(8):
                flag = (flags >> (index * 4)) & 15
                code = flag & 7
                bone = base + index
                if bone >= len(parents) and flag:
                    raise AnimationDecodeError("SA_BONE_REFERENCE")
                if code not in (0, 1, 2, 5, 6):
                    raise AnimationDecodeError("SA_ANIMATION_FLAG")
                if not code:
                    continue
                pos, pos_words, pos_format = None, None, None
                if code & 2:
                    root = parents[bone] == -1
                    pos_words = take("<3I" if root else "<3H")
                    pos = struct.unpack(
                        "<3f" if root else "<3e",
                        struct.pack("<3I" if root else "<3H", *pos_words),
                    )
                    pos_format = "float32" if root else "float16"
                    if any(not math.isfinite(x) for x in pos):
                        raise AnimationDecodeError("SA_TRANSLATION_NONFINITE")
                rotation = take("<3h")
                xyz = tuple(v / 32768 for v in rotation)
                squared = sum(v * v for v in xyz)
                if squared > 1 + 3 / 32768:
                    raise AnimationDecodeError("SA_QUATERNION_NORM")
                w = math.sqrt(max(0, 1 - squared))
                if code & 4:
                    w = -w
                tracks.append(
                    BoneSample(bone, flag, pos, pos_words, pos_format, rotation, (*xyz, w))
                )
        frames.append(AnimationFrame(tuple(groups), tuple(tracks)))
    result = Animation(model_id, recipe, frame_bytes, tuple(frames))
    if encode_animation(result) != data:
        raise AnimationDecodeError("SA_ANIMATION_ROUNDTRIP")
    return result
