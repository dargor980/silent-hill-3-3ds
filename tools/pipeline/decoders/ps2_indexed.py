"""PSMCT32 uploads sampled as PSMT8/PSMT4 with explicit CSM1 CBP selectors.

The selector advances CBP by four GS blocks (1024 bytes); it is not a
horizontal strip number in the uploaded CLUT. Alpha bytes remain unmodified.
"""

from dataclasses import dataclass

from tools.pipeline.decoders.ps2_indexed8 import (
    TextureDecodeError,
    upload_offset,
    validate_dimensions,
)

RECIPE = "sh3-ps2-indexed-csm1-selectors-v1"


def _source32(address, width):
    page, local = divmod(address, 8192)
    block, column = divmod(local, 256)
    word, lane = divmod(column, 4)
    x = (page % (width // 64)) * 64
    y = (page // (width // 64)) * 32
    x += (block & 1) * 8 + (block & 4) * 4 + (block & 16) * 2
    y += (block & 2) * 4 + (block & 8) * 2
    x += (word & 1) + ((word & 4) >> 1) + ((word & 8) >> 1)
    y += ((word & 2) >> 1) + ((word & 16) >> 3) + ((word & 32) >> 3)
    return (y * width + x) * 4 + lane


def _address32(x, y):
    """One 64x32 PSMCT32 page, byte address."""
    block = ((x >> 3) & 1) | ((y >> 2) & 2) | ((x >> 2) & 4)
    block |= ((y >> 1) & 8) | ((x >> 1) & 16)
    word = (x & 1) | ((y & 1) << 1) | ((x & 6) << 1) | ((y & 6) << 3)
    return block * 256 + word * 4


def upload_nibble_offset(x, y, width):
    """Source nibble offset for a full-page PSMT4 coordinate."""
    page = (y // 128) * (width // 128) + x // 128
    block = ((y >> 4) & 1) | ((x >> 4) & 2) | ((y >> 3) & 4)
    block |= ((x >> 3) & 8) | ((y >> 2) & 16)
    column = ((y >> 1) & 1) | ((x >> 2) & 6) | ((x & 1) << 3)
    column |= ((y & 1) << 4) | ((x & 2) << 4)
    column |= (((x >> 2) ^ (y >> 1) ^ (y >> 2)) & 1) << 6
    column |= (y & 12) << 5
    nibble = page * 16384 + block * 512 + column
    return _source32(nibble // 2, width // 2) * 2 + (nibble & 1)


def clut_offset(index, selector):
    x = (index & 7) | ((index & 16) >> 1)
    y = ((index & 8) >> 3) | ((index & 224) >> 4)
    return _source32(selector * 1024 + _address32(x, y), 64)


@dataclass(frozen=True)
class IndexedImage:
    width: int
    height: int
    bpp: int
    indices: bytes
    selectors: tuple[int, ...]
    palettes: tuple[bytes, ...]


def decode_indexed(width, height, bpp, data, clut):
    validate_dimensions(width, height)
    if type(bpp) is not int or bpp not in (4, 8) or (bpp == 4 and height < 128):
        raise TextureDecodeError("PX_TRANSFER_VARIANT")
    if type(data) is not bytes or len(data) != width * height * bpp // 8:
        raise TextureDecodeError("PX_INDEX_SIZE")
    if type(clut) is not bytes or len(clut) not in (4096, 8192, 16384):
        raise TextureDecodeError("PX_CLUT_SIZE")
    if bpp == 8:
        indices = bytes(
            data[upload_offset(x, y, width)] for y in range(height) for x in range(width)
        )
    else:
        offsets = (upload_nibble_offset(x, y, width) for y in range(height) for x in range(width))
        indices = bytes((data[i // 2] >> (4 * (i & 1))) & 15 for i in offsets)
    selectors = (0, 1, 4, 5) if len(clut) == 4096 else tuple(range(len(clut) // 1024))
    palettes = tuple(
        b"".join(clut[(at := clut_offset(i, p)) : at + 4] for i in range(1 << bpp))
        for p in selectors
    )
    return IndexedImage(width, height, bpp, indices, selectors, palettes)


def render_indexed(image, selector, *, normalize_alpha):
    if (
        type(image) is not IndexedImage
        or type(selector) is not int
        or selector not in image.selectors
        or type(normalize_alpha) is not bool
    ):
        raise TextureDecodeError("PX_IMAGE_INPUT")
    validate_dimensions(image.width, image.height)
    if (
        type(image.bpp) is not int
        or image.bpp not in (4, 8)
        or type(image.indices) is not bytes
        or len(image.indices) != image.width * image.height
        or len(image.palettes) not in (4, 8, 16)
        or image.selectors
        != ((0, 1, 4, 5) if len(image.palettes) == 4 else tuple(range(len(image.palettes))))
        or any(type(p) is not bytes or len(p) != (4 << image.bpp) for p in image.palettes)
        or max(image.indices) >= 1 << image.bpp
    ):
        raise TextureDecodeError("PX_IMAGE_INPUT")
    colors = image.palettes[image.selectors.index(selector)]
    rgba = bytearray(len(image.indices) * 4)
    for pixel, index in enumerate(image.indices):
        rgba[pixel * 4 : pixel * 4 + 4] = colors[index * 4 : index * 4 + 4]
        if normalize_alpha:
            rgba[pixel * 4 + 3] = min(255, rgba[pixel * 4 + 3] * 2)
    return bytes(rgba)
