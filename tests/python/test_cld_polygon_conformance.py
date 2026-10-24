"""CF-T5b acceptance families for CP01–CP14; exclusively synthetic inputs."""

import ast
import copy
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from tests import cld_polygon_fixtures as fixtures
from tests import cld_polygon_wire_oracle as oracle
from tools.pipeline.decoders import ps2_cld_polygons as decoder

_MULTIGROUP = fixtures.multigroup()
_EMPTY = fixtures.resource((0, 0, 0, 0))
_FINITE = [0, 0x80000000, 1, 0x80000001, 0x007FFFFF, 0x00800000, 0x7F7FFFFF, 0xFF7FFFFF]
_NONFINITE = [0x7FC12345, 0x7F800000, 0xFF800000]
_COMPONENTS = [(g, r, c) for g in range(4) for r in range(2) for c in range(16)]


def word(raw, offset):
    return struct.unpack_from("<I", raw, offset)[0]


def changed(raw, offset, value, fmt="<I"):
    result = bytearray(raw)
    struct.pack_into(fmt, result, offset, value)
    return bytes(result)


def start(raw, group):
    return word(raw, 352 + group * 4)


def reject(raw, code):
    for read, error in (
        (decoder.decode_polygons, decoder.CollisionPolygonError),
        (oracle.observe, oracle.PolygonOracleError),
    ):
        with pytest.raises(error) as caught:
            read(raw)
        assert caught.value.code == str(caught.value) == code
        assert caught.value.args == (code,)


def accept(raw):
    value = decoder.decode_polygons(raw)
    oracle.check_view(raw, value)
    return value


@pytest.mark.parametrize(
    "module,allowed", [(oracle, {"math"}), (fixtures, {"struct"}), (decoder, {"math", "struct"})]
)
def test_readers_and_writer_have_separate_stdlib_dependencies(module, allowed):
    tree = ast.parse(Path(module.__file__).read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imports.add(node.module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "__import__", "open"}
    assert imports <= allowed


def test_writer_literal_anchors_and_cross_group_reference_semantics():
    raw = _MULTIGROUP
    assert raw[:8] == bytes.fromhex("0000008000002040")
    assert raw[372:392] == bytes.fromhex("ffffffff010000000000000001000000ffffffff")
    assert raw[416:432] == bytes.fromhex("010034120000c0ab21000080efbeadde")
    value = accept(raw)
    assert value["data_offsets"] == [416, 656, 896, 1136, 1376]
    assert value["data_sizes"] == [240, 240, 240, 240, 48]
    assert [r["point_count"] for r in value["groups"][3]["records"]] == [3, 4]
    cells = value["groups"][0]["cells"]
    assert [c["indices"] for c in cells[:3]] == [[1, 0, 1], [1, 0, 1], [1]]
    other = value["groups"][1]["cells"][15]
    assert other["offset"] == cells[0]["offset"] == 376
    assert other["terminator_offset"] == cells[0]["terminator_offset"] == 388
    assert other["indices"] == [1, 0, 1]
    assert value["groups"][0]["records"][0]["vectors_xyzw"][0][0] == -8.0
    assert value["groups"][1]["records"][0]["vectors_xyzw"][0][0] == 92.0


@pytest.mark.parametrize("component", _COMPONENTS)
@pytest.mark.parametrize("bits", _NONFINITE)
def test_every_triangle_and_quad_component_rejects_nonfinite(component, bits):
    group, record, axis = component
    raw = changed(_MULTIGROUP, start(_MULTIGROUP, group) + record * 80 + 16 + axis * 4, bits)
    reject(raw, "CP_COORDINATE")


@pytest.mark.parametrize("component", _COMPONENTS)
@pytest.mark.parametrize("bits", _FINITE)
def test_every_triangle_and_quad_component_preserves_finite_words(component, bits):
    group, record, axis = component
    raw = changed(_MULTIGROUP, start(_MULTIGROUP, group) + record * 80 + 16 + axis * 4, bits)
    row = accept(raw)["groups"][group]["records"][record]
    assert row["vector_words"][axis // 4][axis % 4] == bits
    numeric = row["vectors_xyzw"][axis // 4][axis % 4]
    assert struct.pack("<f", numeric) == struct.pack("<I", bits)


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("bits", _NONFINITE + [0xFFC12345, 0x7F800001])
def test_both_origins_reject_nan_and_infinities(axis, bits):
    reject(changed(_MULTIGROUP, axis * 4, bits), "CP_ORIGIN")


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("bits", _FINITE)
def test_both_origins_preserve_words_without_applying_translation(axis, bits):
    value = accept(changed(_MULTIGROUP, axis * 4, bits))
    assert value["origin_words"][axis] == bits
    oracle.identical(value["groups"], oracle.observe(_MULTIGROUP)["groups"])


@pytest.mark.parametrize(
    "group,byte", [(g, b) for g in range(5) for b in range(48 if g == 4 else 80)]
)
def test_each_byte_of_each_terminal_record_must_be_zero(group, byte):
    reject(changed(_EMPTY, start(_EMPTY, group) + byte, 1, "<B"), "CP_TERMINATOR")


@pytest.mark.parametrize("group", range(4))
@pytest.mark.parametrize("record", [0, 1])
@pytest.mark.parametrize("present", [0, 2, 255])
def test_active_presence_is_not_a_shortcut_terminator(group, record, present):
    reject(
        changed(_MULTIGROUP, start(_MULTIGROUP, group) + record * 80, present, "<B"),
        "CP_RECORD_PRESENT",
    )


@pytest.mark.parametrize("group", range(4))
@pytest.mark.parametrize("record", [0, 1])
@pytest.mark.parametrize("variant", [2, 3, 255])
def test_unknown_polygon_variants_reject_the_entire_resource(group, record, variant):
    reject(
        changed(_MULTIGROUP, start(_MULTIGROUP, group) + record * 80 + 1, variant, "<B"),
        "CP_VARIANT_UNSUPPORTED",
    )


@pytest.mark.parametrize("record", [0, 1, 2])
def test_zero_record_before_declared_terminal_cannot_hide_following_records(record):
    raw = bytearray(fixtures.resource((3, 0, 0, 0)))
    base = start(raw, 0) + record * 80
    raw[base : base + 80] = bytes(80)
    reject(bytes(raw), "CP_RECORD_PRESENT")


@pytest.mark.parametrize("group", range(4))
@pytest.mark.parametrize(
    "offset,fmt,key,value",
    [
        (2, "<H", "word_02", 0),
        (2, "<H", "word_02", 65535),
        (4, "<I", "word_04", 0),
        (4, "<I", "word_04", 0xFFFFFFFF),
        (8, "<I", "filter_word", 0),
        (8, "<I", "filter_word", 0xFFFFFFFF),
        (12, "<I", "word_0c", 0),
        (12, "<I", "word_0c", 0xFFFFFFFF),
    ],
)
def test_opaque_words_are_preserved_in_every_group(group, offset, fmt, key, value):
    raw = changed(_MULTIGROUP, start(_MULTIGROUP, group) + offset, value, fmt)
    assert accept(raw)["groups"][group]["records"][0][key] == value


@pytest.mark.parametrize("selection", [0, 1, 0xFFFFFFFF])
def test_selection_word_does_not_filter_shapes(selection):
    value = accept(changed(_MULTIGROUP, 28, selection))
    assert value["selection_word"] == selection
    oracle.identical(value["groups"], oracle.observe(_MULTIGROUP)["groups"])


@pytest.mark.parametrize("variant", [0, 1])
def test_degenerate_unreferenced_geometry_is_retained(variant):
    raw = bytearray(fixtures.resource((1, 0, 0, 0)))
    base = start(raw, 0)
    raw[base + 1] = variant
    raw[base + 16 : base + 80] = bytes(64)
    row = accept(bytes(raw))["groups"][0]["records"][0]
    assert row["point_count"] == variant + 3
    assert row["vectors_xyzw"] == [[0.0] * 4 for _ in range(4)]


@pytest.mark.parametrize("length", [0, 1, 8, 31, 32, 351, 352, 371, 372, 383, 384, 751])
def test_short_buffers_reject_before_header_reads(length):
    reject(_EMPTY[:length], "CP_SIZE")


def test_minimum_and_maximum_valid_resources_and_one_byte_over_budget():
    assert accept(_EMPTY)["source_size"] == 752
    largest = fixtures.resource((0, 0, 0, 0), data_start=65168)
    assert len(largest) == accept(largest)["source_size"] == 65536
    reject(largest + b"\0", "CP_SIZE")


@pytest.mark.parametrize("group", range(5))
@pytest.mark.parametrize("relative", [-1, 0, 1])
def test_truncating_each_group_boundary_never_leaks_unpack_errors(group, relative):
    end = start(_MULTIGROUP, group) + word(_MULTIGROUP, 8 + group * 4)
    length = min(len(_MULTIGROUP) - 1, end + relative)
    reject(_MULTIGROUP[:length], "CP_SIZE" if length < 752 else "CP_GROUP_RANGE")


@pytest.mark.parametrize("group", range(5))
@pytest.mark.parametrize("kind", ["zero", "short", "stride", "huge"])
def test_group_sizes_all_positions(group, kind):
    stride = 48 if group == 4 else 80
    size = {
        "zero": 0,
        "short": stride - 1,
        "stride": stride + 1,
        "huge": (0xFFFFFFFF // stride) * stride,
    }[kind]
    reject(
        changed(_MULTIGROUP, 8 + group * 4, size),
        "CP_GROUP_RANGE" if kind == "huge" else "CP_GROUP_SIZE",
    )


@pytest.mark.parametrize("group", range(5))
@pytest.mark.parametrize(
    "pointer,code",
    [
        (0, "CP_GROUP_RANGE"),
        (368, "CP_GROUP_RANGE"),
        (1, "CP_GROUP_ALIGNMENT"),
        (0xFFFFFFF0, "CP_GROUP_RANGE"),
        (0xFFFFFFFF, "CP_GROUP_ALIGNMENT"),
    ],
)
def test_group_offsets_bounds_alignment_and_overflow(group, pointer, code):
    if group > 0 and pointer in (0, 368):
        code = "CP_GROUP_LAYOUT"
    reject(changed(_MULTIGROUP, 352 + group * 4, pointer), code)


@pytest.mark.parametrize("group", [1, 2, 3])
@pytest.mark.parametrize("delta", [-16, 16])
def test_gaps_and_overlaps_are_not_accepted(group, delta):
    reject(
        changed(_MULTIGROUP, 352 + group * 4, start(_MULTIGROUP, group) + delta), "CP_GROUP_LAYOUT"
    )


def test_reordered_groups_and_trailing_bytes_are_outside_the_profile():
    raw = changed(_MULTIGROUP, 356, start(_MULTIGROUP, 2))
    raw = changed(raw, 360, start(_MULTIGROUP, 1))
    reject(raw, "CP_GROUP_LAYOUT")
    reject(_MULTIGROUP + bytes(16), "CP_GROUP_LAYOUT")


@pytest.mark.parametrize("group", range(4))
@pytest.mark.parametrize("count", [512, 513])
def test_polygon_capacity_in_each_group(group, count):
    counts = [0] * 4
    counts[group] = count
    raw = fixtures.resource(counts)
    if count == 512:
        assert len(accept(raw)["groups"][group]["records"]) == 512
    else:
        reject(raw, "CP_POLYGON_BUDGET")


@pytest.mark.parametrize(
    "counts",
    [
        (512, 256, 0, 0),
        (192, 192, 192, 192),
        (0, 0, 256, 512),
        (512, 257, 0, 0),
        (192, 192, 192, 193),
        (0, 0, 257, 512),
    ],
)
def test_total_polygon_capacity_with_different_group_distributions(counts):
    raw = fixtures.resource(counts)
    if sum(counts) == 768:
        assert sum(len(g["records"]) for g in accept(raw)["groups"]) == 768
    else:
        reject(raw, "CP_POLYGON_BUDGET")


@pytest.mark.parametrize("payload", [0, 1, 255])
def test_active_group4_is_unsupported_without_reading_its_payload(payload):
    raw = bytearray(fixtures.resource(group4_count=1))
    raw[start(raw, 4) :] = bytes([payload]) * 96
    reject(bytes(raw), "CP_NONPOLYGON_UNSUPPORTED")


_CELLS = [(g, c) for g in range(5) for c in range(16)]


@pytest.mark.parametrize("cell", _CELLS)
@pytest.mark.parametrize("pointer", [0, 368, 373, 415, 416, 1424, 0xFFFFFFFC, 0xFFFFFFFF])
def test_each_cell_pointer_must_be_aligned_and_inside_the_index_region(cell, pointer):
    group, cell_index = cell
    reject(changed(_MULTIGROUP, 32 + group * 64 + cell_index * 4, pointer), "CP_LIST_OFFSET")


@pytest.mark.parametrize("cell", _CELLS)
def test_last_index_word_is_a_valid_empty_list_in_every_cell(cell):
    group, index = cell
    raw = changed(_MULTIGROUP, 32 + group * 64 + index * 4, 412)
    assert accept(raw)["groups"][group]["cells"][index]["indices"] == []


@pytest.mark.parametrize("cell", _CELLS)
@pytest.mark.parametrize("index", [2, 0x80000000, 0xFFFFFFFE])
def test_index_out_of_group_never_resolves_to_a_terminal_or_negative_index(cell, index):
    reject(fixtures.resource(lists={cell: [index]}), "CP_INDEX")


@pytest.mark.parametrize("cell", range(16))
def test_empty_group4_rejects_even_index_zero(cell):
    reject(fixtures.resource(lists={(4, cell): [0]}), "CP_INDEX")


@pytest.mark.parametrize("cell", [(g, c) for g in range(4) for c in range(16)])
def test_missing_list_sentinel_cannot_be_found_inside_a_shape(cell):
    group, index = cell
    raw = changed(fixtures.resource(data_start=416), 412, 0)
    raw = changed(raw, 32 + group * 64 + index * 4, 412)
    # This is an opaque word in a valid shape, not a list terminator.
    raw = changed(raw, 420, 0xFFFFFFFF)
    reject(raw, "CP_LIST_TERMINATOR")


@pytest.mark.parametrize("group", range(4))
@pytest.mark.parametrize("cell", [0, 15])
@pytest.mark.parametrize("count", [512, 513])
def test_reference_capacity_per_list_in_each_polygon_group(group, cell, count):
    raw = fixtures.resource(lists={(group, cell): [1] * count})
    if count == 512:
        assert accept(raw)["groups"][group]["cells"][cell]["indices"] == [1] * 512
    else:
        reject(raw, "CP_REFERENCE_BUDGET")


def reference_limit(*, shared, extra):
    slots = [(0, 0), (0, 15), (1, 0), (1, 15), (2, 0), (2, 15), (3, 0), (3, 14)]
    lists = {slots[0]: [0] * 512}
    aliases = {}
    for slot in slots[1:]:
        if shared:
            aliases[slot] = (slots[0], 0)
        else:
            lists[slot] = [0] * 512
    if extra:
        lists[(3, 15)] = [0]
    return fixtures.resource((1, 1, 1, 1), lists=lists, aliases=aliases)


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("extra", [False, True])
def test_reference_total_counts_each_cell_across_all_groups(shared, extra):
    raw = reference_limit(shared=shared, extra=extra)
    if extra:
        reject(raw, "CP_REFERENCE_BUDGET")
    else:
        assert sum(len(c["indices"]) for g in accept(raw)["groups"] for c in g["cells"]) == 4096


def precedence_cases():
    raw = _MULTIGROUP
    shape = start(raw, 0)
    yield "origin-before-groups", changed(changed(raw, 0, 0x7F800000), 8, 0), "CP_ORIGIN"
    yield (
        "alignment-before-later-size",
        changed(changed(raw, 352, 417), 12, 0),
        "CP_GROUP_ALIGNMENT",
    )
    yield "range-before-later-size", changed(changed(raw, 352, 0xFFFFFFF0), 12, 0), "CP_GROUP_RANGE"
    yield "later-range-before-layout", changed(changed(raw, 356, 672), 16, 0), "CP_GROUP_SIZE"
    over = fixtures.resource((513, 0, 0, 0))
    yield "layout-before-budget", changed(over, 356, start(over, 1) - 16), "CP_GROUP_LAYOUT"
    yield (
        "budget-before-unsupported",
        fixtures.resource((513, 0, 0, 0), group4_count=1),
        "CP_POLYGON_BUDGET",
    )
    unsupported = fixtures.resource(group4_count=1)
    yield (
        "unsupported-before-term",
        changed(unsupported, len(unsupported) - 1, 1, "<B"),
        "CP_NONPOLYGON_UNSUPPORTED",
    )
    yield (
        "late-term-before-early-record",
        changed(changed(raw, len(raw) - 1, 1, "<B"), shape, 0, "<B"),
        "CP_TERMINATOR",
    )
    yield (
        "presence-before-variant",
        changed(changed(raw, shape, 0, "<B"), shape + 1, 255, "<B"),
        "CP_RECORD_PRESENT",
    )
    yield (
        "variant-before-coordinate",
        changed(changed(raw, shape + 1, 255, "<B"), shape + 16, 0x7F800000),
        "CP_VARIANT_UNSUPPORTED",
    )
    yield (
        "coordinate-before-next-record",
        changed(changed(raw, shape + 16, 0x7F800000), shape + 80, 0, "<B"),
        "CP_COORDINATE",
    )
    yield (
        "late-record-before-early-list",
        changed(changed(raw, start(raw, 3) + 96, 0x7F800000), 32, 0),
        "CP_COORDINATE",
    )
    yield "index-before-next-pointer", changed(changed(raw, 376, 2), 36, 0), "CP_INDEX"
    no_end = changed(changed(changed(raw, 32, 412), 412, 0), 36, 0)
    yield "termination-before-next-pointer", no_end, "CP_LIST_TERMINATOR"
    long_list = fixtures.resource(lists={(0, 0): [0] * 512 + [2]})
    yield "index-before-list-budget", long_list, "CP_INDEX"
    total = reference_limit(shared=True, extra=True)
    pointer = word(total, 32 + 3 * 64 + 15 * 4)
    yield "index-before-total-budget", changed(total, pointer, 1), "CP_INDEX"
    long_list = fixtures.resource(lists={(0, 0): [0] * 513})
    yield "budget-before-next-pointer", changed(long_list, 36, 0), "CP_REFERENCE_BUDGET"
    yield "size-before-origin", changed(_EMPTY, 0, 0x7F800000)[:-1], "CP_SIZE"


@pytest.mark.parametrize(
    "name,raw,code", list(precedence_cases()), ids=[c[0] for c in precedence_cases()]
)
def test_multiple_faults_preserve_contract_order(name, raw, code):
    reject(raw, code)


def containers(value):
    if type(value) in (dict, list):
        yield value
        for child in value.values() if type(value) is dict else value:
            yield from containers(child)


def test_every_mutable_container_is_owned_within_and_between_calls():
    raw = _MULTIGROUP
    before = bytes(bytearray(raw))
    expected = oracle.observe(raw)
    first, second = accept(raw), accept(raw)
    left = [id(c) for c in containers(first)]
    right = [id(c) for c in containers(second)]
    assert len(left) == len(set(left))
    assert len(right) == len(set(right))
    assert set(left).isdisjoint(right)
    # Retain handles before parents are cleared, then mutate every nested collection.
    for collection in list(containers(first)):
        collection.clear()
    oracle.identical(second, expected)
    for _, bad, code in precedence_cases():
        reject(bad, code)
    oracle.identical(accept(raw), expected)
    assert raw == before


@pytest.mark.parametrize("delta", [16, 256, 4096])
def test_relocating_data_preserves_shapes_and_lists_with_adjusted_offsets(delta):
    raw = _MULTIGROUP
    boundary = start(raw, 0)
    shifted = raw[:boundary] + b"\x69" * delta + raw[boundary:]
    for group in range(5):
        shifted = changed(shifted, 352 + group * 4, start(raw, group) + delta)
    expected = oracle.observe(raw)
    expected["source_size"] += delta
    expected["data_offsets"] = [o + delta for o in expected["data_offsets"]]
    for group in expected["groups"]:
        group["offset"] += delta
        for row in group["records"]:
            row["offset"] += delta
    oracle.identical(accept(shifted), expected)


def test_padding_mutations_preserve_the_entire_view():
    raw = fixtures.resource((1, 0, 0, 0), data_start=512)
    modified = raw[:376] + bytes(range(136)) + raw[512:]
    assert raw != modified
    oracle.identical(accept(modified), accept(raw))


@pytest.mark.parametrize("shared", [False, True])
def test_reordering_a_list_changes_only_its_references_and_explicit_aliases(shared):
    raw = fixtures.resource(
        lists={(0, 0): [1, 0, 1], (0, 3): [1, 0, 1]},
        aliases={(1, 15): ((0, 0), 0)} if shared else {},
    )
    offset = word(raw, 32)
    modified = changed(changed(raw, offset, 0), offset + 4, 1)
    expected = oracle.observe(raw)
    expected["groups"][0]["cells"][0]["indices"] = [0, 1, 1]
    if shared:
        expected["groups"][1]["cells"][15]["indices"] = [0, 1, 1]
    oracle.identical(accept(modified), expected)


@pytest.mark.parametrize(
    "fault",
    [
        "deduplicate",
        "word04_count",
        "drop_fourth",
        "apply_origin",
        "drop_unreferenced",
        "signed_zero",
        "type",
        "extra_key",
        "missing_key",
        "coordinate_bit",
    ],
)
def test_oracle_detects_controlled_faults_in_decoder_output(fault):
    raw = _MULTIGROUP
    value = decoder.decode_polygons(raw)
    row = value["groups"][0]["records"][0]
    if fault == "deduplicate":
        value["groups"][0]["cells"][0]["indices"] = [1, 0]
    elif fault == "word04_count":
        row["point_count"] = row["word_04"]
    elif fault == "drop_fourth":
        row["vector_words"].pop()
        row["vectors_xyzw"].pop()
    elif fault == "apply_origin":
        row["vectors_xyzw"][0][2] += value["origin_xz"][1]
        row["vector_words"][0][2] = word(struct.pack("<f", row["vectors_xyzw"][0][2]), 0)
    elif fault == "drop_unreferenced":
        # Group 1 references both; make a separate resource with no references.
        raw = fixtures.resource()
        value = decoder.decode_polygons(raw)
        value["groups"][0]["records"].pop()
    elif fault == "signed_zero":
        value["origin_xz"][0] = 0.0
    elif fault == "type":
        row["present"] = True
    elif fault == "extra_key":
        value["capabilities"] = []
    elif fault == "missing_key":
        del row["word_02"]
    else:
        row["vector_words"][0][0] ^= 1
    with pytest.raises(AssertionError, match="view"):
        oracle.check_view(raw, value)


def test_oracle_rejects_acceptance_caused_by_counting_aliases_only_once(monkeypatch):
    raw = reference_limit(shared=True, extra=True)
    reject(raw, "CP_REFERENCE_BUDGET")
    # Controlled faulty reader: disable expanded counting, then enforce a unique-offset budget.
    with monkeypatch.context() as patch:
        patch.setattr(decoder, "_MAX_REFERENCES", 65536)
        wrong = decoder.decode_polygons(raw)
        unique = {c["offset"]: len(c["indices"]) for g in wrong["groups"] for c in g["cells"]}
        assert sum(unique.values()) == 513  # A cache-key budget would accept this.
    with pytest.raises(oracle.PolygonOracleError, match="CP_REFERENCE_BUDGET"):
        oracle.check_view(raw, wrong)
    reject(raw, "CP_REFERENCE_BUDGET")


def test_oracle_alias_detection_does_not_replace_ownership_checks():
    value = decoder.decode_polygons(_MULTIGROUP)
    wrong = copy.deepcopy(value)
    wrong["groups"][0]["cells"][1]["indices"] = wrong["groups"][0]["cells"][0]["indices"]
    oracle.check_view(_MULTIGROUP, wrong)  # Same values alone cannot detect mutable aliases.
    identities = [id(c) for c in containers(wrong)]
    assert len(identities) != len(set(identities))


def optimization_cases():
    """Public test corpus for normal/-O subprocesses, with independent error labels."""
    yield "empty", _EMPTY, None
    yield "multigroup", _MULTIGROUP, None
    largest = fixtures.resource((0, 0, 0, 0), data_start=65168)
    yield "maximum", largest, None
    yield "maximum-plus-one", largest + b"\0", "CP_SIZE"
    for axis in range(2):
        for bits in _FINITE + _NONFINITE:
            yield (
                "origin",
                changed(_MULTIGROUP, axis * 4, bits),
                ("CP_ORIGIN" if bits in _NONFINITE else None),
            )
    for group, record, component in _COMPONENTS:
        for bits in _FINITE + _NONFINITE:
            offset = start(_MULTIGROUP, group) + record * 80 + 16 + component * 4
            yield (
                "component",
                changed(_MULTIGROUP, offset, bits),
                ("CP_COORDINATE" if bits in _NONFINITE else None),
            )
    for group in range(5):
        for byte in range(48 if group == 4 else 80):
            yield "terminal", changed(_EMPTY, start(_EMPTY, group) + byte, 1, "<B"), "CP_TERMINATOR"
        for value in (0, 1, 0xFFFFFFFF):
            yield "size", changed(_MULTIGROUP, 8 + group * 4, value), "CP_GROUP_SIZE"
        yield "group-pointer", changed(_MULTIGROUP, 352 + group * 4, 0xFFFFFFF0), "CP_GROUP_RANGE"
    for group, cell in _CELLS:
        for pointer in (0, 368, 373, 415, 416, 1424, 0xFFFFFFFC, 0xFFFFFFFF):
            yield (
                "cell-pointer",
                changed(_MULTIGROUP, 32 + group * 64 + cell * 4, pointer),
                "CP_LIST_OFFSET",
            )
        for index in (2, 0x80000000, 0xFFFFFFFE):
            yield "index", fixtures.resource(lists={(group, cell): [index]}), "CP_INDEX"
    for group in range(4):
        for count in (512, 513):
            counts = [0] * 4
            counts[group] = count
            yield (
                "polygon-budget",
                fixtures.resource(counts),
                "CP_POLYGON_BUDGET" if count == 513 else None,
            )
        for count in (512, 513):
            yield (
                "list-budget",
                fixtures.resource(lists={(group, 15): [0] * count}),
                ("CP_REFERENCE_BUDGET" if count == 513 else None),
            )
    for count in (768, 769):
        yield (
            "polygon-total",
            fixtures.resource((192, 192, 192, count - 576)),
            ("CP_POLYGON_BUDGET" if count == 769 else None),
        )
    for shared in (False, True):
        for extra in (False, True):
            yield (
                "reference-total",
                reference_limit(shared=shared, extra=extra),
                ("CP_REFERENCE_BUDGET" if extra else None),
            )
    yield from precedence_cases()


def view_digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


@pytest.mark.parametrize("optimized", [False, True], ids=["normal", "optimized"])
def test_extended_corpus_and_both_readers_in_subprocesses(optimized):
    cases = list(optimization_cases())
    expected = []
    for _, raw, code in cases:
        if code:
            with pytest.raises(oracle.PolygonOracleError) as caught:
                oracle.observe(raw)
            assert caught.value.code == code
            expected.append({"code": code, "message": code})
        else:
            expected.append({"sha256": view_digest(oracle.observe(raw))})
    script = """
import hashlib, json, sys
from tests import cld_polygon_wire_oracle as oracle
from tools.pipeline.decoders.ps2_cld_polygons import CollisionPolygonError, decode_polygons
buffers = [bytes.fromhex(h) for h in json.load(sys.stdin)]
class ByteSubclass(bytes):
    pass
class Trap:
    def __len__(self):
        raise RuntimeError('coercion occurred')
    def __bytes__(self):
        raise RuntimeError('coercion occurred')
bad_types = [None, True, 752, 'bytes', [], bytearray(752), memoryview(bytes(752)),
             ByteSubclass(bytes(752)), Trap()]
result = []
readers = [(decode_polygons, CollisionPolygonError), (oracle.observe, oracle.PolygonOracleError)]
for read, error in readers:
    values = []
    for raw in buffers + bad_types:
        try:
            value = read(raw)
        except error as caught:
            values.append({'code': caught.code, 'message': str(caught)})
        else:
            encoded = json.dumps(
                value, sort_keys=True, separators=(',', ':'), allow_nan=False
            ).encode()
            values.append({'sha256': hashlib.sha256(encoded).hexdigest()})
    result.append(values)
# Also ensure the oracle's exact comparison is not disabled by -O.
try:
    oracle.identical(-0.0, 0.0)
except AssertionError:
    pass
else:
    raise RuntimeError('comparison disabled')
print(json.dumps(result))
"""
    result = subprocess.run(
        [sys.executable, *(["-O"] if optimized else []), "-c", script],
        input=json.dumps([raw.hex() for _, raw, _ in cases]),
        capture_output=True,
        text=True,
        timeout=30,
        cwd=Path(__file__).resolve().parents[2],
        check=False,
    )
    assert result.returncode == 0, result.stderr
    expected.extend([{"code": "CP_INPUT", "message": "CP_INPUT"} for _ in range(9)])
    assert json.loads(result.stdout) == [expected, expected]
