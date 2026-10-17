"""CB01-CB08, using only self-authored ELF/ISO and instruction fixtures."""

import json
from copy import deepcopy
from io import BytesIO

import pycdlib
import pytest
from test_camera_consumer import OwnDisc, digest, instruction, own_elf, parsed
from test_camera_consumer import evidence as evidence
from test_camera_pointer import collect_pointer, jump, kinds, special, words
from test_camera_pointer import pointer_evidence as pointer_evidence

from tools.inspectors import call_boundary as boundary
from tools.inspectors import callee_flow as flow
from tools.inspectors import camera_boundary as camera
from tools.inspectors.mips_flow import Effect
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile

RETURN = special(8, rs=31)


def summarize(code, register=16):
    return flow.summarize_callee(words(*code), 0x1000, register)


def stops(result):
    return {b["kind"] for b in result["boundaries"]}


@pytest.mark.parametrize(
    "data,start,register",
    [
        (None, 0, 1),
        (bytearray(4), 0, 1),
        (b"", 0, 1),
        (bytes(5), 0, 1),
        (bytes(4100), 0, 1),
        (bytes(4), -4, 1),
        (bytes(4), 1, 1),
        (bytes(4), True, 1),
        (bytes(8), 0xFFFFFFFC, 1),
        (bytes(4), 1 << 32, 1),
        (bytes(4), 0, -1),
        (bytes(4), 0, 32),
        (bytes(4), 0, True),
    ],
)
def test_invalid_window_or_register_rejected(data, start, register):
    with pytest.raises(ProfileError, match="Invalid callee"):
        flow.summarize_callee(data, start, register)


@pytest.mark.parametrize("register", [0, 4, 16, 31])
def test_leaf_return_preserves_untouched_register(register):
    result = summarize([RETURN, 0], register)
    assert result["effect"] == "preserved_in_model"
    assert result["returns"] == [{"pc": 0x1000, "identity_preserved": True}]
    assert result["identity_scope"] == "low_32_bits"


def test_copy_save_restore_in_register_is_proven_but_memory_is_not():
    def copy(src, dst):
        return special(45, rt=src, rd=dst)

    result = summarize([copy(16, 8), instruction(15, 0, 16, 1), copy(8, 16), RETURN, 0])
    assert result["effect"] == "preserved_in_model"
    result = summarize(
        [
            instruction(25, 29, 29, -16),
            instruction(31, 29, 16, 0),
            instruction(15, 0, 16, 1),
            instruction(30, 29, 16, 0),
            RETURN,
            instruction(25, 29, 29, 16),
        ]
    )
    assert result["effect"] == "unproven" and result["returns"]
    assert not result["returns"][0]["identity_preserved"]
    assert result["memory_identity"] == "not_modeled"


@pytest.mark.parametrize("likely", [False, True])
def test_divergent_exits_require_all_returns_preserved(likely):
    result = summarize(
        [
            instruction(20 if likely else 4, 1, 2, 3),
            0,
            RETURN,
            0,
            RETURN,
            instruction(15, 0, 16, 1),
        ]
    )
    assert result["effect"] == "unproven" and not result["boundaries"]
    assert {r["identity_preserved"] for r in result["returns"]} == {True, False}


def test_likely_annuls_slot_only_on_fallthrough():
    result = summarize([instruction(20, 1, 2, 3), instruction(15, 0, 16, 1), RETURN, 0, RETURN, 0])
    assert result["returns"] == [
        {"pc": 0x1008, "identity_preserved": True},
        {"pc": 0x1010, "identity_preserved": False},
    ]


def test_regular_branch_executes_slot_on_both_exits():
    result = summarize([instruction(4, 1, 2, 3), instruction(15, 0, 16, 1), RETURN, 0, RETURN, 0])
    assert len(result["returns"]) == 2
    assert not any(r["identity_preserved"] for r in result["returns"])


def test_return_target_read_before_delay_slot():
    result = summarize([RETURN, instruction(15, 0, 31, 1)], register=31)
    assert result["returns"] == [{"pc": 0x1000, "identity_preserved": False}]
    assert not result["boundaries"]
    assert stops(summarize([instruction(15, 0, 31, 1), RETURN, 0])) == {"unresolved_indirect"}


@pytest.mark.parametrize("transfer", [special(8, rs=4), special(9, rs=31)])
def test_other_indirects_never_count_as_returns(transfer):
    result = summarize([transfer, 0])
    assert stops(result) == {"unresolved_indirect"} and not result["returns"]


@pytest.mark.parametrize(
    "call", [jump(0x2000, call=True), jump(0x1000, call=True), special(9, rs=4, rd=31)]
)
def test_nested_and_recursive_calls_are_boundaries_even_before_restore(call):
    result = summarize([call, 0, instruction(30, 29, 16, 0), RETURN, 0])
    assert stops(result) == {"nested_call"} and result["effect"] == "unproven"
    assert not result["returns"]


@pytest.mark.parametrize(
    "code,expected",
    [
        ([0x70000000, RETURN, 0], "unknown_effect"),
        ([jump(0x2000), 0], "outside_window"),
        ([0], "outside_window"),
        ([RETURN], "missing_delay_slot"),
        ([RETURN, jump(0x1000)], "unsupported_delay_slot"),
        ([RETURN, 0x70000000], "unsupported_delay_slot"),
        ([jump(0x1000), 0], "revisited_state"),
    ],
)
def test_incomplete_flow_never_claims_preservation(code, expected):
    result = summarize(code)
    assert stops(result) == {expected} and result["effect"] == "unproven"


def test_likely_with_unknown_slot_retains_untaken_return():
    result = summarize([instruction(20, 1, 2, 3), 0x70000000, RETURN, 0, RETURN, 0])
    assert stops(result) == {"unsupported_delay_slot"}
    assert result["returns"] == [{"pc": 0x1008, "identity_preserved": True}]
    assert result["effect"] == "unproven"


@pytest.mark.parametrize("limit", ["MAX_STATES", "MAX_DEPTH"])
def test_budget_exhaustion_is_explicit(monkeypatch, limit):
    monkeypatch.setattr(flow, limit, 0)
    result = summarize([0, RETURN, 0])
    assert result["budget_exhausted"] and stops(result) == {"budget"}


def test_unknown_identity_invalidates_all_nonzero_registers():
    assert flow.apply_identity(tuple(range(32)), Effect("unknown")) == (0,) + (None,) * 31


def boundary_fixture(*, transfer=None, slot=None, target=0x1080):
    code = [0] * 64
    code[7] = instruction(35, 5, 6, 16)
    code[8] = instruction(15, 0, 4, 1)
    code[9] = jump(target, call=True) if transfer is None else transfer
    code[10] = special(45, rt=6, rd=4) if slot is None else slot
    code[32] = RETURN
    reader, mapping = parsed(own_elf(words(*code)))
    origin = {"kind": "external_reference", "pc": 0x1024, "register": 4, "arithmetic_seen": False}
    sites = [
        {
            "site_address": 0x1080,
            "trace": {"origins": [origin, {**origin, "arithmetic_seen": True}]},
        }
    ]
    return reader, mapping, sites


def test_argument_after_slot_is_distinct_from_prior_value_and_return():
    reader, mapping, sites = boundary_fixture()
    report = boundary.inspect_boundaries(reader, mapping, sites)
    assert len(report["boundaries"]) == 1
    result = report["boundaries"][0]
    assert kinds(result["before_call"]) == {"constant"}
    assert kinds(result["entry_after_slot"]) == {"load"}
    assert kinds(result["after_return_hypothesis"]) == {"call"}
    origin = result["entry_after_slot"]["origins"][0]
    assert origin["register"] == 6 and origin["source_register"] == 5
    assert result["callee"]["effect"] == "preserved_in_model"
    assert result["arithmetic_states"] == [False, True]
    assert result["capture_plan"]["expected_resource_sha256"] is None
    assert result["capture_plan"]["points"][0]["registers"] == [4, 5, 6, 31]
    assert max(size for _, size in reader.calls) <= 4096
    assert boundary.inspect_boundaries(reader, mapping, sites) == report


def test_nonempty_boundary_analysis_agrees_on_memory_and_iso(tmp_path):
    reader, mapping, sites = boundary_fixture()
    expected = boundary.inspect_boundaries(reader, mapping, sites)
    image_path = tmp_path / "own.iso"
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident="OWN")
    iso.add_fp(BytesIO(reader.data), len(reader.data), iso_path="/OWN.ELF;1")
    iso.write(str(image_path))
    iso.close()
    with IsoImage(image_path) as image:
        result = boundary.inspect_boundaries(
            lambda offset, length: image.read_range("OWN.ELF", offset, length), mapping, sites
        )
    assert result == expected


def test_external_reference_to_caller_remains_an_unknown_root():
    reader, mapping, sites = boundary_fixture()
    data = bytearray(reader.data)
    import struct

    struct.pack_into("<I", data, 256 + 52 * 4, jump(0x1024))
    reader, mapping = parsed(bytes(data))
    result = boundary.inspect_boundaries(reader, mapping, sites)["boundaries"][0]
    assert kinds(result["entry_after_slot"]) == {"load", "external_reference"}


def test_register_write_in_callee_return_slot_is_not_preserved():
    reader, mapping, sites = boundary_fixture()
    data = bytearray(reader.data)
    import struct

    struct.pack_into("<I", data, 256 + 33 * 4, instruction(15, 0, 4, 1))
    reader, mapping = parsed(bytes(data))
    result = boundary.inspect_boundaries(reader, mapping, sites)["boundaries"][0]
    assert result["callee"]["effect"] == "unproven"


def test_slot_reads_new_link_register_not_previous_link():
    reader, mapping, sites = boundary_fixture(slot=special(45, rt=31, rd=4))
    result = boundary.inspect_boundaries(reader, mapping, sites)["boundaries"][0]
    assert kinds(result["entry_after_slot"]) == {"link"}


@pytest.mark.parametrize("slot,expected", [(jump(0x1000), None), (0x70000000, "unknown")])
def test_unhandled_slot_cannot_prove_argument(slot, expected):
    reader, mapping, sites = boundary_fixture(slot=slot)
    result = boundary.inspect_boundaries(reader, mapping, sites)["boundaries"][0]
    if expected is None:
        assert result["entry_after_slot"] is None and result["status"] == "unsupported_delay_slot"
    else:
        assert kinds(result["entry_after_slot"]) == {expected}


def test_external_noncall_is_left_unsupported():
    reader, mapping, sites = boundary_fixture(transfer=jump(0x1080))
    result = boundary.inspect_boundaries(reader, mapping, sites)["boundaries"][0]
    assert result["status"] == "unsupported_transfer" and "callee" not in result


def test_unbacked_call_target_aborts():
    reader, mapping, sites = boundary_fixture(target=0x3000)
    with pytest.raises(ProfileError):
        boundary.inspect_boundaries(reader, mapping, sites)


def test_boundary_budget_aborts(monkeypatch):
    reader, mapping, sites = boundary_fixture()
    monkeypatch.setattr(boundary, "MAX_BOUNDARIES", 0)
    with pytest.raises(ProfileError, match="Too many"):
        boundary.inspect_boundaries(reader, mapping, sites)


def test_empty_selection_and_unselected_origins():
    reader, mapping, sites = boundary_fixture()
    for origin in sites[0]["trace"]["origins"]:
        origin["kind"] = "load"
    assert boundary.inspect_boundaries(reader, mapping, sites)["boundaries"] == []


def test_late_read_error_propagates():
    reader, mapping, sites = boundary_fixture()

    def broken(offset, size):
        if offset == 384:
            raise OSError("private detail")
        return reader(offset, size)

    with pytest.raises(OSError):
        boundary.inspect_boundaries(broken, mapping, sites)


@pytest.fixture
def boundary_evidence(pointer_evidence, tmp_path):
    pointer = collect_pointer(pointer_evidence)
    path = tmp_path / "pointer.json"
    path.write_text(json.dumps(pointer))
    args = pointer_evidence[-1] + [
        "--pointer",
        str(path),
        "--pointer-repeat",
        str(path),
        "--pointer-sha256",
        digest(path.read_bytes()),
        "--pointer-repeat-sha256",
        digest(path.read_bytes()),
    ]
    return pointer_evidence, pointer, args


def collect_boundary(boundary_evidence, *, reader=None, pointer=None, repeat=None, hashes=None):
    prior, original, args = boundary_evidence
    evidence, consumer, _ = prior
    files, _, profile, probe, _ = evidence
    if hashes is None:
        hashes = {
            name: args[args.index("--" + flag + "-sha256") + 1]
            for name, flag in {
                "image": "image",
                "profile": "profile",
                "probe": "camera-probe",
                "consumer": "consumer",
                "pointer": "pointer",
                "repeat": "pointer-repeat",
            }.items()
        }
    return camera.survey_boundaries(
        reader or OwnDisc(files),
        parse_profile(profile),
        probe,
        consumer,
        original if pointer is None else pointer,
        original if repeat is None else repeat,
        probe["source"]["size"],
        hashes,
    )


def test_memory_iso_cli_repeat_and_exclusive_output(boundary_evidence, tmp_path):
    expected = collect_boundary(boundary_evidence)
    with IsoImage(boundary_evidence[0][0][1]) as image:
        assert collect_boundary(boundary_evidence, reader=image) == expected
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    args = boundary_evidence[-1]
    assert camera.main(args + ["--output", str(a)]) == 0
    assert camera.main(args + ["--output", str(b)]) == 0
    assert a.read_bytes() == b.read_bytes() and json.loads(a.read_bytes()) == expected
    assert expected["capabilities"] == [] and expected["f02_07_status"] == "pending"
    assert camera.main(args + ["--output", str(a)]) == 1


@pytest.mark.parametrize("mutation", ["version", "site", "summary", "evidence", "empty"])
def test_recomputed_pointer_must_match_all_fields(boundary_evidence, mutation):
    altered = deepcopy(boundary_evidence[1])
    if mutation == "version":
        altered["schema_version"] = True
    elif mutation == "site":
        altered["analysis"]["sites"][0]["site_address"] += 4
    elif mutation == "summary":
        altered["summary"]["confirmed_resource_links"] = 1
    elif mutation == "evidence":
        altered["evidence"]["consumer_sha256"] = "a" * 64
    else:
        altered = {}
    with pytest.raises(ProfileError, match="differs from source"):
        collect_boundary(boundary_evidence, pointer=altered, repeat=altered)


def test_repeated_evidence_must_match(boundary_evidence):
    with pytest.raises(ProfileError, match="repetitions differ"):
        collect_boundary(boundary_evidence, repeat={})


@pytest.mark.parametrize(
    "flag", ["image", "profile", "camera-probe", "consumer", "pointer", "pointer-repeat"]
)
def test_hash_mismatch_never_publishes(boundary_evidence, tmp_path, flag, capsys):
    args = list(boundary_evidence[-1])
    args[args.index("--" + flag + "-sha256") + 1] = "f" * 64
    out = tmp_path / "fail.json"
    assert camera.main(args + ["--output", str(out)]) == 1
    assert not out.exists() and json.loads(capsys.readouterr().out)["status"] == "rejected"


def test_repeat_different_bytes_even_same_json_is_rejected(boundary_evidence, tmp_path):
    args = list(boundary_evidence[-1])
    path = tmp_path / "repeat.json"
    path.write_text(json.dumps(boundary_evidence[1], indent=2))
    args[args.index("--pointer-repeat") + 1] = str(path)
    args[args.index("--pointer-repeat-sha256") + 1] = digest(path.read_bytes())
    out = tmp_path / "fail.json"
    assert camera.main(args + ["--output", str(out)]) == 1 and not out.exists()


def test_stable_close_before_publish(boundary_evidence, tmp_path, monkeypatch, capsys):
    class Changed(IsoImage):
        def __exit__(self, *args):
            super().__exit__(*args)
            raise ProfileError("INPUT_CHANGED", "private detail")

    monkeypatch.setattr(camera, "IsoImage", Changed)
    out = tmp_path / "fail.json"
    assert camera.main(boundary_evidence[-1] + ["--output", str(out)]) == 1
    assert not out.exists() and json.loads(capsys.readouterr().out)["code"] == "INPUT_CHANGED"


def test_oserror_sanitized(boundary_evidence, tmp_path, monkeypatch, capsys):
    def broken(*_):
        raise OSError("private detail")

    monkeypatch.setattr(camera, "publish_report", broken)
    assert camera.main(boundary_evidence[-1] + ["--output", str(tmp_path / "fail.json")]) == 1
    assert json.loads(capsys.readouterr().out) == {
        "status": "rejected",
        "code": "BOUNDARY_IO_ERROR",
    }
