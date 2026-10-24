"""Own pixel/CLUT vectors; no private texture inputs."""

from dataclasses import replace

import pytest

from tools.pipeline.decoders.ps2_indexed import (
    clut_offset,
    decode_indexed,
    render_indexed,
    upload_nibble_offset,
)
from tools.pipeline.decoders.ps2_indexed8 import TextureDecodeError, decode_indexed8


def clut(count=8):
    # The color encodes the upload's X and Y, so selector/bit swaps cannot hide.
    return bytes(c for y in range(count * 4) for x in range(64) for c in (x, y, 97, 128))


@pytest.mark.parametrize("bpp", (4, 8))
def test_cbp_selector_is_not_horizontal_strip_number(bpp):
    image = decode_indexed(128, 128, bpp, bytes(128 * 128 * bpp // 8), clut())
    origins = [(0, 0), (16, 0), (0, 16), (16, 16), (32, 0), (48, 0), (32, 16), (48, 16)]
    for selector, (x, y) in enumerate(origins):
        assert image.palettes[selector][:4] == bytes((x, y, 97, 128))
        assert image.palettes[selector][8 * 4 : 9 * 4] == bytes((x, y + 1, 97, 128))
        assert render_indexed(image, selector, normalize_alpha=False)[:4] == bytes((x, y, 97, 128))
        assert render_indexed(image, selector, normalize_alpha=True)[:4] == bytes((x, y, 97, 255))


def test_selector_zero_preserves_the_previously_verified_indexed8_profile():
    data = bytes(range(256)) * 64
    old, new = decode_indexed8(128, 128, data, clut(4)), decode_indexed(128, 128, 8, data, clut(4))
    assert new.indices == old.indices and new.palettes[0] == old.palettes[0]
    assert new.selectors == (0, 1, 4, 5)
    assert new.palettes[2] == old.palettes[2]  # Same bytes, but actual CBP selector is 4.
    with pytest.raises(TextureDecodeError, match="PX_IMAGE_INPUT"):
        render_indexed(new, 2, normalize_alpha=False)


def test_four_bit_lanes_and_column_swaps_have_distinct_values():
    data = bytearray(8192)
    # PSMCT32 upload lanes for the first 32x16 PSMT4 block. These anchors
    # exercise both nibbles, the third row swap and the second column.
    anchors = [
        (0, 0, 0),
        (1, 0, 8),
        (8, 0, 2),
        (16, 0, 4),
        (0, 1, 512),
        (0, 2, 33),
        (4, 2, 1),
        (0, 4, 1056),
    ]
    for value, (_x, _y, source) in enumerate(anchors, 1):
        # Fill by a literal source-nibble vector, never via the decoder mapping.
        data[source // 2] |= value << ((source & 1) * 4)
    image = decode_indexed(128, 128, 4, bytes(data), clut())
    for value, (x, y, _) in enumerate(anchors, 1):
        assert image.indices[y * 128 + x] == value


@pytest.mark.parametrize(("width", "height"), [(128, 128), (256, 128), (128, 256), (512, 1024)])
def test_four_bit_map_has_no_unwritten_or_aliased_nibbles(width, height):
    offsets = {upload_nibble_offset(x, y, width) for y in range(height) for x in range(width)}
    assert (
        len(offsets) == width * height and min(offsets) == 0 and max(offsets) == width * height - 1
    )


@pytest.mark.parametrize("count", (4, 8, 16))
def test_clut_selectors_are_disjoint_and_exhaust_the_upload(count):
    selectors = (0, 1, 4, 5) if count == 4 else range(count)
    offsets = {clut_offset(i, p) for i in range(256) for p in selectors}
    assert offsets == set(range(0, count * 1024, 4))


@pytest.mark.parametrize(
    ("width", "height", "bpp", "data", "palette", "error"),
    [
        (127, 128, 4, bytes(8192), clut(), "PX_DIMENSIONS"),
        (128, 64, 4, bytes(4096), clut(), "PX_TRANSFER_VARIANT"),
        (128, 128, True, bytes(8192), clut(), "PX_TRANSFER_VARIANT"),
        (128, 128, 16, bytes(8192), clut(), "PX_TRANSFER_VARIANT"),
        (128, 128, 4, bytes(8191), clut(), "PX_INDEX_SIZE"),
        (128, 128, 4, bytearray(8192), clut(), "PX_INDEX_SIZE"),
        (128, 128, 4, bytes(8192), bytes(1024), "PX_CLUT_SIZE"),
        (128, 128, 4, bytes(8192), bytearray(8192), "PX_CLUT_SIZE"),
    ],
)
def test_rejects_incomplete_uploads(width, height, bpp, data, palette, error):
    with pytest.raises(TextureDecodeError, match=error):
        decode_indexed(width, height, bpp, data, palette)


@pytest.mark.parametrize("selector", (-1, 8, True, "0"))
def test_selector_validation(selector):
    image = decode_indexed(128, 128, 4, bytes(8192), clut())
    with pytest.raises(TextureDecodeError, match="PX_IMAGE_INPUT"):
        render_indexed(image, selector, normalize_alpha=False)


@pytest.mark.parametrize(
    "changes",
    [dict(bpp=16), dict(indices=bytes([16]) * 16384), dict(indices=b""), dict(palettes=(b"",) * 8)],
)
def test_forged_image_cannot_escape_renderer_bounds(changes):
    image = replace(decode_indexed(128, 128, 4, bytes(8192), clut()), **changes)
    with pytest.raises(TextureDecodeError, match="PX_IMAGE_INPUT"):
        render_indexed(image, 0, normalize_alpha=False)
