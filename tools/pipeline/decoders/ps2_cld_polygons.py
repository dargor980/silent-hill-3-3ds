"""Pure, bounded reader for the CP01–CP15 indexed CLD polygon profile.

The view preserves words and references, without transforms or physics.
Callers retain the original bytes: opaque padding is not part of the view.
Dynamic overlay lists and active 48-byte shapes are outside this profile.
"""

import math
import struct

PROFILE = "ps2-cld-polygons-v1"
_STRIDES = (80, 80, 80, 80, 48)
_MIN_SIZE = 752
_MAX_SIZE = 65536
_INDEX_START = 0x174
_MAX_GROUP_POLYGONS = 512
_MAX_POLYGONS = 768
_MAX_LIST_REFERENCES = 512
_MAX_REFERENCES = 4096


class CollisionPolygonError(ValueError):
    """Stable rejection code, without input bytes or partial results."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _u32(raw: bytes, offset: int) -> int:
    return struct.unpack_from("<I", raw, offset)[0]


def _group_layout(raw: bytes) -> tuple[list[int], list[int], list[int]]:
    sizes = list(struct.unpack_from("<5I", raw, 0x08))
    offsets = list(struct.unpack_from("<5I", raw, 0x160))
    source_size = len(raw)
    for group, (offset, size, stride) in enumerate(zip(offsets, sizes, _STRIDES, strict=True)):
        if size < stride or size % stride:
            raise CollisionPolygonError("CP_GROUP_SIZE")
        if offset % 16:
            raise CollisionPolygonError("CP_GROUP_ALIGNMENT")
        if size > source_size or offset > source_size - size or (group == 0 and offset < 0x180):
            raise CollisionPolygonError("CP_GROUP_RANGE")
    for group in range(4):
        if offsets[group] + sizes[group] != offsets[group + 1]:
            raise CollisionPolygonError("CP_GROUP_LAYOUT")
    if offsets[4] + sizes[4] != source_size:
        raise CollisionPolygonError("CP_GROUP_LAYOUT")

    counts = [size // stride - 1 for size, stride in zip(sizes, _STRIDES, strict=True)]
    if any(count > _MAX_GROUP_POLYGONS for count in counts[:4]) or sum(counts[:4]) > _MAX_POLYGONS:
        raise CollisionPolygonError("CP_POLYGON_BUDGET")
    if sizes[4] != _STRIDES[4]:
        raise CollisionPolygonError("CP_NONPOLYGON_UNSUPPORTED")
    # Validate every terminator before reading any active record.
    for offset, size, stride in zip(offsets, sizes, _STRIDES, strict=True):
        if any(raw[offset + size - stride : offset + size]):
            raise CollisionPolygonError("CP_TERMINATOR")
    return offsets, sizes, counts


def _record(raw: bytes, index: int, offset: int) -> dict:
    present, variant, word_02, word_04, filter_word, word_0c = struct.unpack_from(
        "<BBHIII", raw, offset
    )
    if present != 1:
        raise CollisionPolygonError("CP_RECORD_PRESENT")
    if variant not in (0, 1):
        raise CollisionPolygonError("CP_VARIANT_UNSUPPORTED")
    vector_words, vectors_xyzw = [], []
    for vector in range(4):
        start = offset + 0x10 + vector * 16
        values = list(struct.unpack_from("<4f", raw, start))
        if any(not math.isfinite(value) for value in values):
            raise CollisionPolygonError("CP_COORDINATE")
        vector_words.append(list(struct.unpack_from("<4I", raw, start)))
        vectors_xyzw.append(values)
    return dict(
        index=index,
        offset=offset,
        present=present,
        variant=variant,
        point_count=3 + variant,
        word_02=word_02,
        word_04=word_04,
        filter_word=filter_word,
        word_0c=word_0c,
        vector_words=vector_words,
        vectors_xyzw=vectors_xyzw,
    )


def _cells(raw: bytes, data_start: int, counts: list[int]) -> list[list[dict]]:
    result = []
    total_references = 0
    for group, count in enumerate(counts):
        cells = []
        for cell in range(16):
            offset = _u32(raw, 0x20 + 0x40 * group + 4 * cell)
            if offset % 4 or not _INDEX_START <= offset <= data_start - 4:
                raise CollisionPolygonError("CP_LIST_OFFSET")
            position = offset
            indices = []
            while True:
                if position > data_start - 4:
                    raise CollisionPolygonError("CP_LIST_TERMINATOR")
                index = _u32(raw, position)
                if index == 0xFFFFFFFF:
                    break
                if index >= count:
                    raise CollisionPolygonError("CP_INDEX")
                if len(indices) >= _MAX_LIST_REFERENCES or total_references >= _MAX_REFERENCES:
                    raise CollisionPolygonError("CP_REFERENCE_BUDGET")
                # Each cell owns its list; aliases consume the budget again.
                indices.append(index)
                total_references += 1
                position += 4
            cells.append(
                dict(index=cell, offset=offset, terminator_offset=position, indices=indices)
            )
        result.append(cells)
    return result


def decode_polygons(raw: bytes) -> dict:
    """Decode one complete indexed resource or raise CollisionPolygonError.

    Validation follows the contract's stage order, including with Python -O.
    The result owns its mutable collections; no input or global state changes.
    """
    if type(raw) is not bytes:
        raise CollisionPolygonError("CP_INPUT")
    if not _MIN_SIZE <= len(raw) <= _MAX_SIZE:
        raise CollisionPolygonError("CP_SIZE")
    origin = list(struct.unpack_from("<2f", raw))
    if any(not math.isfinite(value) for value in origin):
        raise CollisionPolygonError("CP_ORIGIN")
    offsets, sizes, counts = _group_layout(raw)
    groups = []
    for group, (offset, size, stride, count) in enumerate(
        zip(offsets, sizes, _STRIDES, counts, strict=True)
    ):
        groups.append(
            dict(
                index=group,
                offset=offset,
                size=size,
                stride=stride,
                records=[_record(raw, index, offset + index * stride) for index in range(count)],
            )
        )
    # All active records must pass before any list is interpreted.
    for group, cells in zip(groups, _cells(raw, offsets[0], counts), strict=True):
        group["cells"] = cells
    return dict(
        profile=PROFILE,
        source_size=len(raw),
        origin_words=list(struct.unpack_from("<2I", raw)),
        origin_xz=origin,
        selection_word=_u32(raw, 0x1C),
        data_offsets=offsets,
        data_sizes=sizes,
        groups=groups,
    )
