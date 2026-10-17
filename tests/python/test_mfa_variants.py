"""MV01-MV08: explicit layouts, shared rejection policy and bounded private diagnostics."""

import hashlib
import json
import struct
from io import BytesIO

import pycdlib
import pytest
from test_mfa import MemoryDisc, Sectors, arguments, changed, own_files, profile_data, sector

from tools.inspectors import mfa, mfa_probe
from tools.inspectors.mfa_names import name_diagnostics
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile

LAYOUTS = [("b8", 184), ("d8", 216)]


@pytest.mark.parametrize("layout,toc", LAYOUTS)
def test_shared_parser_accepts_complete_multiblock_chain(layout, toc):
    reader = Sectors({0: sector(("own/first",), toc=toc), 4096: sector(("own/second",), toc=8)})
    result = mfa.inspect_layout(reader, 8192, layout)
    assert result["status"] == "structural_candidate"
    assert result["layout"] == f"mfa-{layout}-blocks-v1"
    assert result["entry_count"] == result["block_count"] == 2
    assert [b["toc_offset"] for b in result["blocks"]] == [toc, 4104]
    assert reader.calls == [(0, 2048), (4096, 2048)]


@pytest.mark.parametrize("layout,toc", LAYOUTS)
def test_requested_layout_does_not_fall_back_to_other_header(layout, toc):
    other = "d8" if layout == "b8" else "b8"
    reader = Sectors({0: sector(toc=toc)})
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_layout(reader, 4096, other)
    assert error.value.code == "MFA_TABLE"
    assert reader.calls == [(0, 2048)]


@pytest.mark.parametrize("layout", ["auto", "", "D8", 216, None, [], True])
def test_unregistered_layout_fails_before_reader_access(layout):
    reader = Sectors({})
    with pytest.raises(ProfileError) as error:
        mfa.inspect_layout(reader, 4096, layout)
    assert type(error.value) is ProfileError
    assert error.value.code == "MFA_LAYOUT"
    assert reader.calls == []


@pytest.mark.parametrize("layout,toc", LAYOUTS)
def test_ambiguous_initial_headers_reject_even_with_requested_layout(layout, toc):
    raw = bytearray(sector(toc=184))
    struct.pack_into("<II", raw, 216, 1, 2048)
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_layout(Sectors({0: bytes(raw)}), 4096, layout)
    assert error.value.code == "MFA_AMBIGUOUS_LAYOUT"


@pytest.mark.parametrize("layout,toc", LAYOUTS)
@pytest.mark.parametrize(
    "relative,value,code",
    [
        (0, 0, "MFA_TABLE"),
        (0, 0xFFFFFFFF, "MFA_TABLE"),
        (4, 0, "MFA_BLOCK_RANGE"),
        (4, 1, "MFA_BLOCK_RANGE"),
        (4, 4096, "MFA_BLOCK_RANGE"),
        (8, 0, "MFA_NAME"),
        (8, 2048, "MFA_NAME"),
        (12, 2049, "MFA_PAYLOAD_RANGE"),
        (20, 0xFFFFFFFF, "MFA_PAYLOAD_RANGE"),
    ],
)
def test_layouts_share_table_and_range_rejection(layout, toc, relative, value, code):
    reader = Sectors({0: changed(sector(toc=toc), toc + relative, value)})
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_layout(reader, 4096, layout)
    assert error.value.code == code


@pytest.mark.parametrize("layout,toc", LAYOUTS)
@pytest.mark.parametrize(
    "names,code",
    [
        (("../escape",), "MFA_PATH"),
        (("/absolute",), "MFA_PATH"),
        (("same", "SAME"), "MFA_DUPLICATE_PATH"),
        (("file", "file/child"), "MFA_DUPLICATE_PATH"),
    ],
)
def test_layouts_share_path_policy(layout, toc, names, code):
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_layout(Sectors({0: sector(names, toc=toc)}), 4096, layout)
    assert error.value.code == code
    assert error.value.details["block_index"] == 0
    assert error.value.details["entry_ordinal"] == len(names)
    assert names[0] not in str(error.value)


@pytest.mark.parametrize("layout,toc", LAYOUTS)
def test_overlap_is_not_hidden_by_layout_selection(layout, toc):
    raw = sector(("a", "b"), toc=toc, ranges=[(0, 17), (16, 16)])
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_layout(Sectors({0: raw}), 4096, layout)
    assert error.value.code == "MFA_OVERLAP"


@pytest.mark.parametrize("layout,toc", LAYOUTS)
@pytest.mark.parametrize("limit", ["MAX_BLOCKS", "MAX_ENTRIES"])
def test_same_budgets_for_both_layouts(monkeypatch, layout, toc, limit):
    monkeypatch.setattr(mfa, limit, 1)
    reader = Sectors({0: sector(toc=toc), 4096: sector(("other",), toc=8)})
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_layout(reader, 8192, layout)
    assert error.value.code == "MFA_LIMIT"


@pytest.mark.parametrize("layout,toc", LAYOUTS)
def test_short_read_is_not_format_unknown(layout, toc):
    with pytest.raises(ProfileError) as error:
        mfa.inspect_layout(Sectors({0: b"short"}), 4096, layout)
    assert type(error.value) is ProfileError
    assert error.value.code == "SHORT_READ"


@pytest.mark.parametrize("layout,toc", LAYOUTS)
def test_following_blocks_do_not_reuse_initial_header(layout, toc):
    reader = Sectors({0: sector(toc=toc), 4096: sector(("other",), toc=toc)})
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_layout(reader, 8192, layout)
    assert error.value.code == "MFA_TABLE"


@pytest.mark.parametrize("layout,toc", LAYOUTS)
def test_late_encoding_failure_has_safe_location_and_no_partial_success(layout, toc):
    raw = bytearray(sector(("private/AA.bin",), toc=8))
    name_offset = struct.unpack_from("<I", raw, 16)[0]
    raw[name_offset + 8 : name_offset + 10] = (
        b"\x82\xa0"  # Own Shift-JIS fixture, not original data.
    )
    reader = Sectors({0: sector(toc=toc), 4096: bytes(raw)})
    with pytest.raises(mfa.MfaError) as error:
        mfa.inspect_layout(reader, 8192, layout)
    assert error.value.code == "MFA_NAME"
    details = error.value.details
    assert {
        k: details[k]
        for k in ("block_index", "entry_index", "entry_ordinal", "block_offset", "name_offset")
    } == {
        "block_index": 1,
        "entry_index": 0,
        "entry_ordinal": 2,
        "block_offset": 4096,
        "name_offset": 32,
    }
    assert details["encoding"] == "unresolved"
    assert details["name_bytes"] == len("private/AA.bin")
    assert details["non_ascii_bytes"] == 2
    assert details["codec_candidates"]["shift_jis"] == {"decodes": True, "round_trip": True}
    assert details["codec_candidates"]["cp932"] == {"decodes": True, "round_trip": True}
    assert "private" not in json.dumps(details)
    assert "payload_bytes" not in details


@pytest.mark.parametrize("raw", ["text", None, b"a" * 1025, bytearray(b"a")])
def test_name_diagnostics_are_bounded_and_typed(raw):
    with pytest.raises(ProfileError) as error:
        name_diagnostics(raw)
    assert error.value.code == "NAME_DIAGNOSTIC_LIMIT"


def test_strict_codec_success_does_not_choose_encoding():
    result = name_diagnostics("own/あ.bin".encode())
    assert result["codec_candidates"]["utf-8"] == {"decodes": True, "round_trip": True}
    assert result["encoding"] == "unresolved"
    assert result["non_ascii_bytes"] == 3
    assert "own/" not in json.dumps(result)


def test_decode_success_and_round_trip_are_distinct():
    result = name_diagnostics(b"own/\x87\x90.bin")
    assert result["codec_candidates"]["cp932"] == {"decodes": True, "round_trip": False}
    assert result["codec_candidates"]["utf-8"] == {"decodes": False, "round_trip": False}
    assert result["encoding"] == "unresolved"


def test_controls_are_reported_separately_from_nonascii():
    result = name_diagnostics(b"own/\x1f\x7f\xff")
    assert result["control_bytes"] == 2
    assert result["non_ascii_bytes"] == 1


@pytest.fixture
def variant_source(tmp_path):
    files = own_files()
    # Same generated disc contains both hypotheses and unknown bytes.
    image = pycdlib.PyCdlib()
    image.new(interchange_level=3, vol_ident="OWNVARIANT")
    for path, data in files.items():
        image.add_fp(BytesIO(data), len(data), iso_path=f"/{path};1")
    iso = tmp_path / "own.iso"
    image.write(str(iso))
    image.close()
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps(profile_data(files)))
    return iso, profile


@pytest.mark.parametrize("layout,accepted", [("b8", "ALT.MFA"), ("d8", "B0.MFA")])
def test_cli_and_memory_iso_contract_repeatable_with_selected_layout(
    variant_source, tmp_path, capsys, layout, accepted
):
    iso, profile = variant_source
    original = iso.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    parsed = parse_profile(json.loads(profile.read_text()))
    with IsoImage(iso) as image:
        offsets = {path: image.file_offset(path) for path in image.paths()}
        report = mfa_probe.collect_probe(image, parsed, len(original), digest, layout)
    expected = mfa_probe.collect_probe(
        MemoryDisc(own_files(), offsets), parsed, len(original), digest, layout
    )
    assert report == expected
    assert report["schema_version"] == report["tool"]["version"] == 2
    assert report["selection"] == {"mode": "fixed_layout", "layout": layout}
    assert [
        e["path"] for e in report["entries"] if e["result"]["status"] == "structural_candidate"
    ] == [accepted]
    args = [*arguments(variant_source, tmp_path), "--layout", layout]
    assert mfa_probe.main(args) == 0
    assert json.loads(capsys.readouterr().out)["structural_entry_count"] == 1
    saved = (tmp_path / "out.json").read_bytes()
    assert b"own/one.bin" not in saved and b"own payload" not in saved
    args[7] = str(tmp_path / "repeat.json")
    assert mfa_probe.main(args) == 0
    assert (tmp_path / "repeat.json").read_bytes() == saved
    assert mfa_probe.main(args) == 1
    assert (tmp_path / "repeat.json").read_bytes() == saved
    assert iso.read_bytes() == original


def test_invalid_selection_fails_before_inventory():
    with pytest.raises(ProfileError) as error:
        mfa_probe.collect_probe(None, None, 0, "", "auto")
    assert error.value.code == "MFA_LAYOUT"


def test_b8_identity_failure_aborts_before_any_range(variant_source, tmp_path, monkeypatch, capsys):
    def unexpected(*args):
        pytest.fail("Read range before identity verification")

    monkeypatch.setattr(IsoImage, "read_range", unexpected)
    args = [*arguments(variant_source, tmp_path), "--layout", "b8"]
    args[5] = "0" * 64
    assert mfa_probe.main(args) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "IMAGE_MISMATCH"
    assert not (tmp_path / "out.json").exists()


def test_b8_read_failure_never_becomes_unknown(variant_source, tmp_path, monkeypatch, capsys):
    def failed(*args):
        raise ProfileError("ISO_READ_ERROR", "Own failure injection")

    monkeypatch.setattr(IsoImage, "read_range", failed)
    assert mfa_probe.main([*arguments(variant_source, tmp_path), "--layout", "b8"]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "ISO_READ_ERROR"
    assert not (tmp_path / "out.json").exists()
