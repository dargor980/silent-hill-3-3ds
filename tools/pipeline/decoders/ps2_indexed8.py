"""PSMCT32-uploaded PSMT8 indices and the four-unit SH3 CLUT subset."""

from dataclasses import dataclass

RECIPE = "sh3-ps2-indexed8-four-cluts-v1"


class TextureDecodeError(ValueError):
    pass


def validate_dimensions(width: int, height: int) -> None:
    if (
        type(width) is not int
        or type(height) is not int
        or width not in (128, 256, 512, 1024)
        or height not in (64, 128, 256, 512, 1024)
    ):
        raise TextureDecodeError("PX_DIMENSIONS")


def upload_offset(x: int, y: int, width: int) -> int:
    """Source byte for one raster coordinate; caller validates dimensions."""
    stripe = (y & ~15) * width + (x & ~15) * 2
    row = (((y & ~3) >> 1) + (y & 1)) & 7
    swap = (((y + 2) >> 2) & 1) * 4
    column = row * width * 2 + ((x + swap) & 7) * 4
    lane = ((y >> 1) & 1) + ((x >> 2) & 2)
    return stripe + column + lane


@dataclass(frozen=True)
class IndexedTexture:
    width: int
    height: int
    indices: bytes
    palettes: tuple[bytes, ...]


def decode_indexed8(width: int, height: int, data: bytes, clut: bytes) -> IndexedTexture:
    validate_dimensions(width, height)
    if type(data) is not bytes or len(data) != width * height:
        raise TextureDecodeError("PX_INDEX_SIZE")
    if type(clut) is not bytes or len(clut) != 4096:
        raise TextureDecodeError("PX_CLUT_SIZE")
    indices = bytes(data[upload_offset(x, y, width)] for y in range(height) for x in range(width))
    palettes = []
    for palette in range(4):
        colors = bytearray()
        for index in range(256):
            shifted = (index & ~24) | ((index & 8) << 1) | ((index & 16) >> 1)
            offset = (shifted // 16) * 256 + palette * 64 + (shifted % 16) * 4
            colors.extend(clut[offset : offset + 4])
        palettes.append(bytes(colors))
    return IndexedTexture(width, height, indices, tuple(palettes))


def render_palette(texture: IndexedTexture, palette: int, *, normalize_alpha: bool) -> bytes:
    validate_dimensions(texture.width, texture.height)
    if (
        type(palette) is not int
        or not 0 <= palette < 4
        or type(normalize_alpha) is not bool
        or type(texture.indices) is not bytes
        or len(texture.indices) != texture.width * texture.height
        or len(texture.palettes) != 4
        or any(type(p) is not bytes or len(p) != 1024 for p in texture.palettes)
    ):
        raise TextureDecodeError("PX_IMAGE_INPUT")
    colors = texture.palettes[palette]
    rgba = bytearray(len(texture.indices) * 4)
    for pixel, index in enumerate(texture.indices):
        start = pixel * 4
        rgba[start : start + 4] = colors[index * 4 : index * 4 + 4]
        if normalize_alpha:
            rgba[start + 3] = min(255, 2 * rgba[start + 3])
    return bytes(rgba)
