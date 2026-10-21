"""MR01-MR07: synthetic root partitions, transform records and private CLI."""

import json
import struct

import pytest
import test_map_probe as mp

from tools.inspectors import map_render_probe as parser
from tools.inspectors import map_survey as survey
from tools.pipeline.profile import ProfileError


def own_map(gap=0):
    """Three own groups; slot 1 ends after one even though its link continues."""
    data = bytearray(1072 + gap)
    groups = [304 + gap, 560 + gap, 816 + gap]
    struct.pack_into("<I", data, 0, 0xFFFFFFFF)
    struct.pack_into("<I", data, 24, 80)
    struct.pack_into("<3I", data, 28, 0, groups[0], groups[1])
    struct.pack_into("<4H", data, 64, 3, 0, 2, 1)
    struct.pack_into("<3I", data, 80, 0, 32 + gap, 224 + gap)
    # Rotation around Z with a translation, independent of original game bytes.
    struct.pack_into("<16f", data, 112 + gap, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 8, 9, 10, 1)
    for index, group in enumerate(groups):
        following = groups[index + 1] if index < 2 else 0
        for offset, length in ((group, 256), (group + 48, 208), (group + 96, 160)):
            struct.pack_into(
                "<4I", data, offset, following if offset == group else 0, 48, length, 0
            )
        struct.pack_into("<H", data, group + 24, 1)
        struct.pack_into("<7I", data, group + 144, 0, 64, 112, 0, 3, index + 1, 18)
        data[group + 208 : group + 256] = b"OWN_VERTEX_DATA!" * 3
    return bytes(data)


def probe(data):
    return parser.probe_render_metadata(len(data), lambda o, n: data[o : o + n])


def test_counted_roots_exclude_shared_tail_without_losing_unique_groups():
    result = probe(own_map())
    assert result["counted_roots"] == [
        {
            "slot": 0,
            "offset": 0,
            "declared_count": 0,
            "group_offsets": [],
            "structural_tail_excluded": [],
        },
        {
            "slot": 1,
            "offset": 304,
            "declared_count": 1,
            "group_offsets": [304],
            "structural_tail_excluded": [560, 816],
        },
        {
            "slot": 2,
            "offset": 560,
            "declared_count": 2,
            "group_offsets": [560, 816],
            "structural_tail_excluded": [],
        },
    ]
    assert result["declared_group_count"] == 3
    assert result["shape_words"] == [
        {
            "shape_offset": g + 144,
            "group_offset": g,
            "mode_word_20": i + 1,
            "auxiliary_word_24": 18,
        }
        for i, g in enumerate((304, 560, 816))
    ]


def test_reads_only_metadata_and_classifies_without_exporting_matrix():
    data = own_map()
    allowed = {(0, 48), (48, 32), (80, 32), (112, 192)}
    for g in (304, 560, 816):
        allowed.update({(g, 48), (g + 48, 48), (g + 96, 48), (g + 144, 64), (g + 164, 8)})

    def read(o, n):
        assert (o, n) in allowed and n <= 192
        return data[o : o + n]

    result = parser.probe_render_metadata(len(data), read)
    matrix = result["base_transform"]
    assert matrix["matrix_offset"] == 112 and matrix["bounds_offset"] == 176
    assert matrix["matrix_sha256"] == mp.digest(data[112:176])
    assert matrix["bounds_sha256"] == mp.digest(data[176:304])
    assert matrix["affine_if_column_major"]
    assert not matrix["identity_basis_if_column_major"]
    assert not matrix["zero_translation_if_column_major"]
    assert matrix["application"] == "not_performed"
    assert result["material_binding"] == "unverified"
    assert result["runtime_comparison"] == "pending"
    assert "OWN_VERTEX" not in json.dumps(result)
    assert all(not isinstance(v, (list, float)) for v in matrix.values())


def test_identity_zero_translation_and_projective_classification():
    data = bytearray(own_map())
    identity = [float(row == col) for col in range(4) for row in range(4)]
    struct.pack_into("<16f", data, 112, *identity)
    result = probe(bytes(data))["base_transform"]
    assert result["identity_basis_if_column_major"]
    assert result["zero_translation_if_column_major"]
    struct.pack_into("<f", data, 124, 0.25)
    assert not probe(bytes(data))["base_transform"]["affine_if_column_major"]


def test_aligned_transform_payload_gap():
    result = probe(own_map(16))["base_transform"]
    assert result["record_size"] == 240
    assert result["matrix_offset"] == 128 and result["bounds_offset"] == 192


@pytest.mark.parametrize(
    "offset,fmt,value,code",
    [
        (64, "H", 4, "MR_ROOT_COUNTS"),
        (68, "H", 1, "MR_ROOT_COUNTS"),
        (70, "H", 0, "MR_ROOT_COUNTS"),
        (66, "H", 65535, "MR_ROOT_COUNTS"),
        (24, "I", 0, "MR_TRANSFORM_OFFSET"),
        (24, "I", 48, "MR_TRANSFORM_OFFSET"),
        (24, "I", 81, "MR_TRANSFORM_OFFSET"),
        (24, "I", 304, "MR_RANGE"),
        (24, "I", 0xFFFFFFF0, "MR_RANGE"),
        (80, "I", 80, "MR_TRANSFORM_CHAIN_UNSUPPORTED"),
        (84, "I", 16, "MR_TRANSFORM_RANGE"),
        (84, "I", 33, "MR_TRANSFORM_RANGE"),
        (84, "I", 0xFFFFFFF0, "MR_TRANSFORM_RANGE"),
        (88, "I", 208, "MR_TRANSFORM_RANGE"),
        (88, "I", 240, "MR_TRANSFORM_RANGE"),
    ],
)
def test_malformed_metadata(offset, fmt, value, code):
    data = bytearray(own_map())
    struct.pack_into("<" + fmt, data, offset, value)
    with pytest.raises(parser.MapProbeError, match=code):
        probe(bytes(data))


@pytest.mark.parametrize("offset", [112, 176, 300])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_all_transform_and_bounds_floats_must_be_finite(offset, value):
    data = bytearray(own_map())
    struct.pack_into("<f", data, offset, value)
    with pytest.raises(parser.MapProbeError, match="MR_NONFINITE"):
        probe(bytes(data))


def test_counts_cannot_assign_one_group_to_two_roots():
    data = bytearray(own_map())
    struct.pack_into("<3I", data, 28, 304, 304, 816)
    struct.pack_into("<4H", data, 64, 3, 1, 1, 1)
    with pytest.raises(parser.MapProbeError, match="MR_ROOT_OVERLAP"):
        probe(bytes(data))


@pytest.mark.parametrize("kind", ["zero_with_root", "count_without_root", "short_chain"])
def test_counts_and_root_lengths_must_agree(kind):
    data = bytearray(own_map())
    if kind == "zero_with_root":
        struct.pack_into("<I", data, 28, 304)
    elif kind == "count_without_root":
        struct.pack_into("<4H", data, 64, 3, 1, 1, 1)
    else:
        struct.pack_into("<I", data, 36, 816)
        struct.pack_into("<4H", data, 64, 3, 0, 2, 1)
    with pytest.raises(parser.MapProbeError, match="MR_ROOT_COUNTS"):
        probe(bytes(data))


def test_older_structural_variant_without_prefix_is_not_promoted():
    with pytest.raises(parser.MapProbeError, match="MR_PREFIX"):
        probe(mp.own_map())


@pytest.mark.parametrize("target", [(48, 32), (80, 32), (112, 192), (468, 8)])
@pytest.mark.parametrize("response", [b"", None, bytearray(32)])
def test_additional_reads_require_exact_bytes(target, response):
    data = own_map()

    def read(o, n):
        return response if (o, n) == target else data[o : o + n]

    with pytest.raises(parser.MapProbeError, match="MR_READ_CONTRACT"):
        parser.probe_render_metadata(len(data), read)


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "own_map", own_map)
    return mp.evidence.__wrapped__(tmp_path)


def test_cli_two_copies_and_legacy_report_are_separate(evidence):
    legacy = mp.run(evidence)
    assert "render_metadata" not in legacy
    evidence["render_metadata"] = True
    a = mp.run(evidence)
    assert a == mp.run(evidence, "copy-b")
    assert {k: v for k, v in a.items() if k != "render_metadata"} == legacy
    output = evidence["root"] / "render.json"
    assert survey.main([*mp.cli_args(evidence, output), "--render-metadata"]) == 0
    assert json.loads(output.read_bytes()) == a
    assert a["capabilities"] == [] and a["material_binding"] == "unverified"
    for forbidden in ("own-room", "OWN_VERTEX", str(evidence["root"])):
        assert forbidden not in json.dumps(a)
    before = output.read_bytes()
    assert survey.main([*mp.cli_args(evidence, output), "--render-metadata"]) == 1
    assert output.read_bytes() == before


@pytest.mark.parametrize("fault", ["nonfinite", "short", "final_set", "publish"])
def test_cli_metadata_failure_closes_without_publishing(evidence, monkeypatch, capsys, fault):
    events = []
    original = survey.VerifiedPrivateReader

    class Reader(original):
        checks = 0

        def verify_set(self, resources):
            self.checks += 1
            if fault == "final_set" and self.checks == 2:
                raise ProfileError("PRIVATE_SET_MISMATCH", "changed")
            super().verify_set(resources)

        def read_verified(self, resource, o, n):
            raw = super().read_verified(resource, o, n)
            if (o, n) == (112, 192):
                if fault == "nonfinite":
                    return struct.pack("<f", float("nan")) + raw[4:]
                if fault == "short":
                    return b""
            return raw

        def __exit__(self, *args):
            result = super().__exit__(*args)
            events.append("closed")
            return result

    monkeypatch.setattr(survey, "VerifiedPrivateReader", Reader)
    if fault == "publish":

        def publish(*args):
            assert events == ["closed"]
            raise OSError("disk")

        monkeypatch.setattr(survey, "publish_report", publish)
    output = evidence["root"] / "failure.json"
    assert survey.main([*mp.cli_args(evidence, output), "--render-metadata"]) == 1
    assert not output.exists() and events == ["closed"]
    assert '"status": "rejected"' in capsys.readouterr().out
