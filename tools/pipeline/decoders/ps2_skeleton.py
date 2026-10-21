"""Bounded PS2 MDL skeleton records, without mesh or pose-space inference."""

import math
import struct
from dataclasses import dataclass

MAX_MODEL_BYTES = 16 * 1024 * 1024
MAX_BONES = 128


class SkeletonDecodeError(ValueError):
    pass


@dataclass(frozen=True)
class Skeleton:
    model_id: int
    model_offset: int
    matrices_offset: int
    parents_offset: int
    parents: tuple[int, ...]
    matrices_columns: tuple[tuple[float, ...], ...]
    matrix_words: tuple[tuple[int, ...], ...]
    file_header_words: tuple[int, ...]
    model_header_words: tuple[int, ...]


def validate_parents(parents: tuple[int, ...]) -> None:
    if (
        type(parents) is not tuple
        or not 1 <= len(parents) <= MAX_BONES
        or any(type(p) is not int or not -1 <= p < len(parents) for p in parents)
    ):
        raise SkeletonDecodeError("SA_PARENTS")
    for index in range(len(parents)):
        seen = set()
        while index != -1:
            if index in seen:
                raise SkeletonDecodeError("SA_PARENT_CYCLE")
            seen.add(index)
            index = parents[index]


def decode_skeleton(data: bytes) -> Skeleton:
    if type(data) is not bytes or not 32 <= len(data) <= MAX_MODEL_BYTES:
        raise SkeletonDecodeError("SA_MODEL_SIZE")
    file_header = struct.unpack_from("<8I", data)
    model = file_header[5]
    if model < 32 or model % 16 or model + 128 > len(data):
        raise SkeletonDecodeError("SA_MODEL_HEADER")
    header = struct.unpack_from("<32I", data, model)
    if header[:2] != (0xFFFF0003, 3):
        raise SkeletonDecodeError("SA_MODEL_VERSION")
    count = header[3]
    if not 1 <= count <= MAX_BONES:
        raise SkeletonDecodeError("SA_BONE_COUNT")
    matrices_at, parents_at = model + header[2], model + header[4]
    ranges = sorted(((matrices_at, matrices_at + count * 64), (parents_at, parents_at + count)))
    if (
        any(start < model + 128 or end > len(data) for start, end in ranges)
        or matrices_at % 16
        or ranges[0][1] > ranges[1][0]
    ):
        raise SkeletonDecodeError("SA_SKELETON_RANGE")
    parents = struct.unpack_from(f"<{count}b", data, parents_at)
    validate_parents(parents)
    matrices, words = [], []
    for index in range(count):
        offset = matrices_at + index * 64
        values = struct.unpack_from("<16f", data, offset)
        if any(not math.isfinite(x) for x in values):
            raise SkeletonDecodeError("SA_MATRIX_NONFINITE")
        if tuple(values[i] for i in (3, 7, 11, 15)) != (0, 0, 0, 1):
            raise SkeletonDecodeError("SA_MATRIX_AFFINE")
        matrices.append(values)
        words.append(struct.unpack_from("<16I", data, offset))
    if (
        b"".join(struct.pack("<16f", *m) for m in matrices)
        != data[matrices_at : matrices_at + count * 64]
        or struct.pack(f"<{count}b", *parents) != data[parents_at : parents_at + count]
    ):
        raise SkeletonDecodeError("SA_SKELETON_ROUNDTRIP")
    return Skeleton(
        file_header[1],
        model,
        matrices_at,
        parents_at,
        parents,
        tuple(matrices),
        tuple(words),
        file_header,
        header,
    )
