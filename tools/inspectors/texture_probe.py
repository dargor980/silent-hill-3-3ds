"""Bounded structural subset of SH3 PS2 indexed textures; never decode pixels."""

import hashlib
import struct
from collections.abc import Callable

METHOD = "sh3-ps2-indexed-texture-structure-v1"
REFERENCE_REVISION = "f08ec73e32c0b0d5ddbb58f96eef51f0b8ee5b35"
MAX_TEXTURE_BYTES = 16 * 1024 * 1024
MAX_TEXTURES = 256
MAX_DIMENSION = 1024


class TextureProbeError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise TextureProbeError(code)


def probe_texture(size: int, read: Callable[[int, int], bytes]) -> dict:
    """Inspect only fixed-size headers via a caller-owned, verified range port."""
    _require(type(size) is int and size >= 0, "TEX_SIZE")
    _require(size <= MAX_TEXTURE_BYTES, "TEX_BUDGET")

    def header(offset: int, length: int) -> bytes:
        _require(0 <= offset <= size and length <= size - offset, "TEX_RANGE")
        data = read(offset, length)
        _require(type(data) is bytes and len(data) == length, "TEX_READ_CONTRACT")
        return data

    area = header(0, 32)
    words = struct.unpack("<8I", area)
    _require(words[0] == 0xFFFFFFFF and words[2] == 32, "TEX_AREA_VARIANT")
    _require(1 <= words[5] <= MAX_TEXTURES, "TEX_COUNT")
    blocks, offset = [], 32
    for ordinal in range(words[5]):
        start = offset
        raw = header(start, 48)
        width, height = struct.unpack_from("<HH", raw, 8)
        bpp, declared_padding = raw[12:14]
        _require(1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION, "TEX_DIMENSION")
        _require(
            raw[28] == width.bit_length() - 1 and raw[29] == height.bit_length() - 1,
            "TEX_EXPONENT",
        )
        _require(struct.unpack_from("<H", raw, 30)[0] == 0x9999, "TEX_MARKER")
        _require(bpp in (4, 8), "TEX_BPP")
        _require(raw[24] == 0 and raw[25] == {4: 0x14, 8: 0x13}[bpp], "TEX_PSM")
        data_size, all_size = struct.unpack_from("<II", raw, 16)
        bits = width * height * bpp
        _require(bits % 8 == 0 and data_size == bits // 8, "TEX_DATA_SIZE")
        _require(48 + data_size <= all_size <= size - start, "TEX_BLOCK_SIZE")
        padding = all_size - data_size - 48
        clut_start = start + all_size
        clut = header(clut_start, 48)
        clut_size, gs_offset, raw_offset = struct.unpack_from("<III", clut)
        clut_count = clut[12]
        _require(
            clut_count in (4, 8, 16)
            and clut_size == clut_count * 1024
            and clut[14:16] == bytes((64, 64)),
            "TEX_CLUT_VARIANT",
        )
        offset = clut_start + 48 + clut_size
        _require(offset <= size, "TEX_RANGE")
        blocks.append(
            {
                "ordinal": ordinal,
                "header_offset": start,
                "header_sha256": hashlib.sha256(raw).hexdigest(),
                "texture_id": struct.unpack_from("<i", raw)[0],
                "width": width,
                "height": height,
                "bpp": bpp,
                "send_psm": raw[24],
                "draw_psm": raw[25],
                "padding_declared": declared_padding,
                "padding_computed": padding,
                "all_size": all_size,
                "indices": {"offset": clut_start - data_size, "size": data_size},
                "opaque": {
                    "x": struct.unpack_from("<H", raw, 4)[0],
                    "y": struct.unpack_from("<H", raw, 6)[0],
                    "importance": struct.unpack_from("<H", raw, 14)[0],
                    "bit_shift": raw[26],
                    "tag_point": raw[27],
                },
                "clut": {
                    "header_offset": clut_start,
                    "header_sha256": hashlib.sha256(clut).hexdigest(),
                    "data_offset": clut_start + 48,
                    "size": clut_size,
                    "declared_count": clut_count,
                    "declared_width": clut[14],
                    "declared_height": clut[15],
                    "opaque_gs_offset": gs_offset,
                    "opaque_raw_offset": raw_offset,
                    "opaque_trans_cluts": clut[13],
                },
                "end_offset": offset,
            }
        )
    _require(offset == size, "TEX_TRAILING")
    _require(words[3] in (blocks[-1]["header_offset"], size), "TEX_LAST_OFFSET")
    return {
        "status": "structural_candidate",
        "area": {
            "header_sha256": hashlib.sha256(area).hexdigest(),
            "content_offset": words[2],
            "last_offset": words[3],
            "declared_count": words[5],
            "opaque_words": {str(i * 4): words[i] for i in (1, 4, 6, 7)},
        },
        "blocks": blocks,
        "consumed_bytes": offset,
    }
