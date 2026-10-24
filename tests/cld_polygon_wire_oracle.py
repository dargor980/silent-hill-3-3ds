"""CP01–CP14 oracle, independent of production readers and fixture builders.

The layout and bounds are transcribed from ps2-cld-polygons-v1.md. Integer
reads use slices; IEEE-754 values are computed from sign/exponent/fraction,
without struct or a shared float decoder. Checks remain active under -O.
This is structural evidence only, not collision response or provenance.
"""

import math


class PolygonOracleError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def require(condition, code):
    if not condition:
        raise PolygonOracleError(code)


def identical(actual, expected):
    """Compare complete typed trees, retaining the sign of floating zero."""
    if type(actual) is not type(expected):
        raise AssertionError("view type")
    if type(expected) is dict:
        if actual.keys() != expected.keys():
            raise AssertionError("view keys")
        for key in expected:
            identical(actual[key], expected[key])
    elif type(expected) is list:
        if len(actual) != len(expected):
            raise AssertionError("view length")
        for index, value in enumerate(expected):
            identical(actual[index], value)
    elif type(expected) is float:
        if not math.isfinite(actual) or actual.hex() != expected.hex():
            raise AssertionError("view float")
    elif actual != expected:
        raise AssertionError("view value")


def _word(raw, offset, width=4):
    if offset < 0 or offset + width > len(raw):
        raise AssertionError("oracle read bounds")
    return int.from_bytes(raw[offset : offset + width], "little")


def _number(word, code):
    exponent = (word >> 23) & 255
    fraction = word & 0x7FFFFF
    require(exponent != 255, code)
    sign = -1.0 if word >> 31 else 1.0
    if exponent == 0:
        return sign * math.ldexp(float(fraction), -149)
    return sign * math.ldexp(float((1 << 23) + fraction), exponent - 150)


def observe(raw):
    """Derive a full view or an independently checked contract error code."""
    require(type(raw) is bytes, "CP_INPUT")
    length = len(raw)
    require(752 <= length <= 65536, "CP_SIZE")
    origin_words = [_word(raw, 0), _word(raw, 4)]
    origin = [_number(w, "CP_ORIGIN") for w in origin_words]

    regions = []
    for group in range(5):
        start, size = _word(raw, 352 + group * 4), _word(raw, 8 + group * 4)
        stride = 48 if group == 4 else 80
        require(size >= stride and size % stride == 0, "CP_GROUP_SIZE")
        require(start & 15 == 0, "CP_GROUP_ALIGNMENT")
        end = start + size  # Python integers do not wrap at 32 bits.
        require(end <= length and (group != 0 or start >= 384), "CP_GROUP_RANGE")
        regions.append((start, end, stride, size // stride - 1))
    ends = [r[1] for r in regions]
    starts = [r[0] for r in regions]
    require(ends == starts[1:] + [length], "CP_GROUP_LAYOUT")
    counts = [r[3] for r in regions]
    require(max(counts[:4]) <= 512 and sum(counts[:4]) <= 768, "CP_POLYGON_BUDGET")
    require(counts[4] == 0, "CP_NONPOLYGON_UNSUPPORTED")
    for _, end, stride, _ in regions:
        require(raw[end - stride : end] == bytes(stride), "CP_TERMINATOR")

    groups = []
    for group, (start, end, stride, count) in enumerate(regions):
        rows = []
        for index in range(count):
            base = start + index * 80
            present, variant = raw[base], raw[base + 1]
            require(present == 1, "CP_RECORD_PRESENT")
            require(variant < 2, "CP_VARIANT_UNSUPPORTED")
            words = [_word(raw, p) for p in range(base + 16, base + 80, 4)]
            values = [_number(word, "CP_COORDINATE") for word in words]
            rows.append(
                dict(
                    index=index,
                    offset=base,
                    present=present,
                    variant=variant,
                    point_count=(3, 4)[variant],
                    word_02=_word(raw, base + 2, 2),
                    word_04=_word(raw, base + 4),
                    filter_word=_word(raw, base + 8),
                    word_0c=_word(raw, base + 12),
                    vector_words=[words[i : i + 4] for i in range(0, 16, 4)],
                    vectors_xyzw=[values[i : i + 4] for i in range(0, 16, 4)],
                )
            )
        groups.append(
            dict(index=group, offset=start, size=end - start, stride=stride, records=rows, cells=[])
        )

    # Address all words once, but charge references for every cell, including aliases.
    index_words = [_word(raw, p) for p in range(372, starts[0], 4)]
    expanded = 0
    for group in range(5):
        for cell in range(16):
            pointer = _word(raw, 32 + group * 64 + cell * 4)
            require(pointer % 4 == 0 and 372 <= pointer < starts[0], "CP_LIST_OFFSET")
            indices = []
            for slot in range((pointer - 372) // 4, len(index_words)):
                item = index_words[slot]
                if item == 0xFFFFFFFF:
                    terminal = 372 + slot * 4
                    break
                require(item < counts[group], "CP_INDEX")
                require(len(indices) < 512 and expanded < 4096, "CP_REFERENCE_BUDGET")
                expanded += 1
                indices.append(item)
            else:
                raise PolygonOracleError("CP_LIST_TERMINATOR")
            groups[group]["cells"].append(
                dict(index=cell, offset=pointer, terminator_offset=terminal, indices=indices)
            )
    return dict(
        profile="ps2-cld-polygons-v1",
        source_size=length,
        origin_words=origin_words,
        origin_xz=origin,
        selection_word=_word(raw, 28),
        data_offsets=starts,
        data_sizes=[end - start for start, end, _, _ in regions],
        groups=groups,
    )


def check_view(raw, actual):
    """Reject wrong views and views claimed for out-of-profile buffers."""
    identical(actual, observe(raw))
