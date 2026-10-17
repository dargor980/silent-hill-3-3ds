"""CP01-CP08: own control-flow fixtures, no original instruction stream."""

import json
import struct
from copy import deepcopy
from dataclasses import replace

import pytest
from test_camera_consumer import OwnDisc, collect, digest, instruction, own_elf, parsed
from test_camera_consumer import evidence as evidence

from tools.inspectors import camera_pointer as pointer
from tools.inspectors import pointer_graph as graph
from tools.inspectors.elf32 import MAX_ELF_BYTES
from tools.inspectors.mips_camera import scan_loops
from tools.inspectors.mips_flow import Effect, decode
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile


def special(function, rs=0, rt=0, rd=0, shift=0):
    return (rs << 21) | (rt << 16) | (rd << 11) | (shift << 6) | function


def jump(target, *, call=False):
    return ((3 if call else 2) << 26) | ((target >> 2) & 0x3FFFFFF)


def words(*values):
    return struct.pack(f"<{len(values)}I", *values)


@pytest.mark.parametrize("op", [2, 3])
def test_jump_uses_region_of_pc_plus_four(op):
    item = decode(jump(0x10002000, call=op == 3), 0x0FFFFFFC)
    assert item.target == 0x10002000
    assert item.flow == ("call" if op == 3 else "jump")


@pytest.mark.parametrize(
    "op,rt,likely",
    [
        (4, 2, False),
        (5, 2, False),
        (6, 0, False),
        (7, 0, False),
        (20, 2, True),
        (21, 2, True),
        (22, 0, True),
        (23, 0, True),
        (1, 0, False),
        (1, 1, False),
        (1, 2, True),
        (1, 3, True),
    ],
)
def test_signed_conditional_targets(op, rt, likely):
    item = decode(instruction(op, 1, rt, -2), 0x1000)
    assert (item.flow, item.target, item.likely) == ("branch", 0xFFC, likely)


@pytest.mark.parametrize("rt", [0, 1, 2, 3])
def test_cop1_branch_delay_policy(rt):
    item = decode(instruction(17, 8, rt, 2), 0x1000)
    assert item.target == 0x100C and item.likely == (rt >= 2)


@pytest.mark.parametrize(
    "word,flow,destination",
    [
        (special(8, rs=31), "indirect", 0),
        (special(9, rs=4, rd=31), "indirect_call", 31),
        (special(9, rs=4), "indirect", 0),
    ],
)
def test_indirect_control_and_jalr_zero_link(word, flow, destination):
    item = decode(word, 0x1000)
    assert item.flow == flow and item.target is None
    assert item.effect.destination == destination


@pytest.mark.parametrize(
    "word",
    [
        special(8, rs=31, rt=1),
        special(9, rs=4, shift=1),
        instruction(6, 1, 2, -2),
        instruction(1, 1, 17, -2),
        instruction(15, 1, 3, 1),
        0xFFFFFFFF ^ 0x04000000,
        instruction(17, 7, 3, 1),
        special(33, 1, 2, 3, 1),
    ],
)
def test_unknown_or_reserved_instruction_invalidates_provenance(word):
    assert decode(word, 0x1000).effect.kind == "unknown"


@pytest.mark.parametrize("function", [33, 37, 45])
@pytest.mark.parametrize("reverse", [False, True])
def test_copy_uses_nonzero_source(function, reverse):
    word = special(function, rs=8 if reverse else 0, rt=0 if reverse else 8, rd=7)
    assert decode(word, 0x1000).effect == Effect("copy", 7, 8)
    assert decode(special(function, 1, 2, 7), 0x1000).effect == Effect("overwrite", 7)


def test_por_and_unknown_mmi():
    assert decode(0x700004A9 | (8 << 16) | (7 << 11), 0).effect == Effect("copy", 7, 8)
    assert decode(0x700004A9 | (8 << 21) | (9 << 16) | (7 << 11), 0).effect.kind == "overwrite"
    assert decode(0x70000000, 0).effect.kind == "unknown"


@pytest.mark.parametrize("function", [0, 1, 2, 3, 40, 41, 50, 52, 54])
def test_supported_scalar_float_effect_does_not_write_gpr(function):
    assert decode(0x46000000 | (2 << 16) | (3 << 11) | function, 0).effect == Effect()


@pytest.mark.parametrize("function", [5, 6, 7])
def test_unary_float_preserves_gprs_but_reserved_operand_is_unknown(function):
    assert decode(0x46000000 | (3 << 11) | (4 << 6) | function, 0).effect == Effect()
    assert decode(0x46010000 | function, 0).effect.kind == "unknown"


@pytest.mark.parametrize("word", [0x46000072, 0x46000074, 0x46000076, 0x46000024])
def test_unmodeled_scalar_float_forms_remain_unknown(word):
    assert decode(word, 0).effect.kind == "unknown"


@pytest.mark.parametrize(
    "word,expected",
    [
        (0, Effect()),
        (instruction(9, 8, 7, 128), Effect("adjust", 7, 8)),
        (instruction(25, 8, 7, -1), Effect("adjust", 7, 8)),
        (instruction(15, 0, 7, 1), Effect("constant", 7)),
        (instruction(13, 0, 7, 1), Effect("constant", 7)),
        (instruction(13, 8, 7, 1), Effect("overwrite", 7)),
        (special(0, rt=8, rd=7, shift=2), Effect("overwrite", 7)),
        (special(10, rs=1, rt=2, rd=7), Effect("overwrite", 7)),
        (special(16, rd=7), Effect("overwrite", 7)),
        (special(18, rd=7), Effect("overwrite", 7)),
        (special(17, rs=7), Effect()),
        (special(19, rs=7), Effect()),
        (instruction(17, 0, 7, 0), Effect("overwrite", 7)),
        (instruction(17, 2, 7, 0), Effect("overwrite", 7)),
        (instruction(17, 4, 7, 0), Effect()),
        (instruction(17, 6, 7, 0), Effect()),
    ],
)
def test_effects_do_not_invent_values(word, expected):
    assert decode(word, 0x1000).effect == expected


@pytest.mark.parametrize("op", [26, 27, 30, 32, 33, 34, 35, 36, 37, 38, 39, 55])
def test_load_is_terminal_with_base_only(op):
    assert decode(instruction(op, 8, 7, 68), 0x1000).effect == Effect("load", 7, 8)


@pytest.mark.parametrize("op", [31, 40, 41, 42, 43, 44, 45, 46, 49, 57, 63])
def test_memory_store_or_float_memory_preserves_gprs(op):
    assert decode(instruction(op, 8, 7, 68), 0x1000).effect == Effect()


def trace(code, *, site=None, register=7, refs=None):
    data = words(*code)
    predecessors, summary = graph.local_graph(data, 0x1000, refs or [])
    result = graph.trace_origins(
        predecessors, 0x1000 + (len(code) - 1) * 4 if site is None else site, register
    )
    return result, predecessors, summary


def kinds(result):
    return {origin["kind"] for origin in result["origins"]}


def test_copy_adjustment_and_zero_are_followed_without_computing_values():
    result, _, _ = trace(
        [instruction(35, 4, 8, 16), special(45, rt=8, rd=7), instruction(9, 7, 7, 128), 0]
    )
    assert kinds(result) == {"load"}
    assert result["origins"][0]["source_register"] == 4
    assert result["origins"][0]["arithmetic_seen"]
    result, _, _ = trace([special(45, rd=7), 0])
    assert kinds(result) == {"zero_register"}


def test_constant_overwrite_and_unknown_are_distinct():
    for word, kind in [
        (instruction(15, 0, 7, 9), "constant"),
        (special(33, 8, 9, 7), "overwrite"),
        (0x70000000, "unknown"),
    ]:
        result, _, _ = trace([instruction(35, 4, 7, 16), word, 0])
        assert kinds(result) == {kind}
        assert result["origins"][0]["pc"] == 0x1004


@pytest.mark.parametrize("call", [jump(0x2000, call=True), special(9, rs=4, rd=31)])
def test_calls_invalidate_even_saved_registers_after_delay(call):
    result, predecessors, _ = trace(
        [instruction(15, 0, 16, 1), call, special(45, rd=16), 0], register=16
    )
    assert kinds(result) == {"call"}
    assert predecessors[(0x1008, 0x1004)][0].effects[0][1] == Effect("link", 31)


@pytest.mark.parametrize("transfer", [jump(0x3000), special(8, rs=31), special(9, rs=4)])
def test_jump_does_not_invent_return_or_normal_slot_fallthrough(transfer):
    result, predecessors, _ = trace([instruction(15, 0, 7, 1), transfer, 0, 0])
    assert kinds(result) == {"no_known_predecessor"}
    assert (0x1008, -1) not in predecessors


def test_diamond_convergence_keeps_both_definitions():
    result, _, _ = trace(
        [
            instruction(35, 4, 7, 16),
            instruction(4, 1, 2, 4),
            0,
            instruction(15, 0, 7, 1),
            jump(0x1020),
            0,
            instruction(9, 7, 7, 1),
            0,
            0,
        ]
    )
    assert kinds(result) == {"load", "constant"}
    assert {o["pc"] for o in result["origins"]} == {0x1000, 0x100C}


@pytest.mark.parametrize("op,expected", [(4, {"load"}), (20, {"load", "constant"})])
def test_branch_likely_annuls_delay_on_untaken_path(op, expected):
    result, _, _ = trace(
        [
            instruction(15, 0, 7, 1),
            instruction(op, 1, 2, 3),
            instruction(35, 4, 7, 16),
            jump(0x1018),
            0,
            0,
            0,
        ]
    )
    assert kinds(result) == expected


def test_control_in_delay_slot_cuts_path_and_is_recorded():
    result, _, summary = trace([jump(0x100C), jump(0x100C), 0, 0])
    assert "no_known_predecessor" in kinds(result)
    assert summary["unsupported_delay_slots"] == 1


def test_direct_entry_to_delay_address_has_separate_normal_context():
    refs = [{"pc": 0x2000, "target": 0x1004}]
    result, predecessors, _ = trace([jump(0x3000), instruction(35, 8, 7, 0), 0], refs=refs)
    assert kinds(result) == {"load"}
    assert (0x1004, -1) in predecessors and (0x1004, 0x1000) in predecessors


def test_external_reference_and_cycle_stay_unproven():
    result, _, _ = trace(
        [0, instruction(4, 1, 2, -2), 0, 0], refs=[{"pc": 0x2000, "target": 0x1000}]
    )
    assert "external_reference" in kinds(result) and "revisited_state" in kinds(result)
    assert result["resource_link"] == "unproven" and result["analysis_completeness"] == "partial"


@pytest.mark.parametrize("limit", ["MAX_STATES", "MAX_DEPTH"])
def test_trace_limit_is_explicit_unknown(monkeypatch, limit):
    monkeypatch.setattr(graph, limit, 1)
    result, _, _ = trace([0] * 8)
    assert result["budget_exhausted"] and "budget" in kinds(result)


def test_edge_limit_aborts_graph(monkeypatch):
    monkeypatch.setattr(graph, "MAX_EDGES", 1)
    with pytest.raises(ProfileError, match="edge budget"):
        graph.local_graph(words(0, 0, 0), 0x1000, [])


@pytest.mark.parametrize(
    "data,start",
    [
        (b"", 0),
        (bytes(3), 0),
        (bytes(4100), 0),
        (bytearray(4), 0),
        (bytes(4), True),
        (bytes(4), -4),
        (bytes(4), 1),
        (bytes(8), 0xFFFFFFFC),
    ],
)
def test_window_limits(data, start):
    with pytest.raises(ProfileError) as error:
        graph.local_graph(data, start, [])
    assert error.value.code == "POINTER_WINDOW"


def test_reference_scan_is_bounded_and_counts_unbacked_and_indirect():
    data = own_elf(words(jump(0x100C, call=True), 0, jump(0x3000), special(8, rs=31), 0))
    reader, mapping = parsed(data)
    result = graph.references(reader, mapping, [(0x100C, 0x1014)])
    assert result["counts"] == {
        "direct_transfer_words": 2,
        "unbacked_direct_targets": 1,
        "indirect_transfer_words": 1,
    }
    assert len(result["references"]) == 1
    assert result["references"][0]["kind"] == "call"
    assert result["references"][0]["target_offset"] == 268


def test_reference_overlapping_windows_do_not_duplicate_and_no_match_works():
    reader, mapping = parsed(own_elf(words(jump(0x1000), 0)))
    assert len(graph.references(reader, mapping, [(0x1000, 0x1008)] * 2)["references"]) == 1
    assert graph.references(reader, mapping, [(0x2000, 0x3000)])["references"] == []


@pytest.mark.parametrize("mutation", ["bytes", "alignment", "references"])
def test_reference_limits(mutation, monkeypatch):
    reader, mapping = parsed(own_elf(words(jump(0x1000), 0)))
    if mutation == "bytes":
        mapping = replace(
            mapping, segments=(replace(mapping.segments[0], file_size=MAX_ELF_BYTES + 4),)
        )
    elif mutation == "alignment":
        mapping = replace(mapping, segments=(replace(mapping.segments[0], address=0x1001),))
    else:
        monkeypatch.setattr(graph, "MAX_REFERENCES", 0)
    with pytest.raises(ProfileError):
        graph.references(reader, mapping, [(0x1000, 0x2000)])


def test_integrated_inspector_uses_real_scan_sites_but_does_not_identify_resource():
    reader, mapping = parsed(own_elf())
    sites = scan_loops(reader, mapping)["candidates"]
    result = graph.inspect_pointers(reader, mapping, sites)
    assert result["site_count"] == 1 and result["confirmed_resource_links"] == 0
    assert result["sites"][0]["trace"]["resource_link"] == "unproven"
    assert len(result["sites"][0]["window"]["sha256"]) == 64


@pytest.mark.parametrize("variant", ["none", "many", "large", "reversed"])
def test_inspection_limits(variant):
    reader, mapping = parsed(own_elf())
    sites = scan_loops(reader, mapping)["candidates"]
    if variant == "none":
        sites = []
    elif variant == "many":
        sites *= 17
    elif variant == "large":
        sites[0]["virtual_address"] += 4096
    else:
        sites[0]["branch_target_address"] += 1024
    with pytest.raises(ProfileError):
        graph.inspect_pointers(reader, mapping, sites)


def test_reference_io_failure_is_not_swallowed():
    reader, mapping = parsed(own_elf(bytes(8192)))

    def broken(offset, size):
        if offset > 4096:
            raise ProfileError("OWN_IO_ERROR", "read failed")
        return reader(offset, size)

    with pytest.raises(ProfileError, match="read failed"):
        graph.references(broken, mapping, [(0x1000, 0x2000)])


@pytest.fixture
def pointer_evidence(evidence, tmp_path):
    prior = collect(evidence)
    path = tmp_path / "consumer.json"
    path.write_text(json.dumps(prior))
    args = evidence[-1] + ["--consumer", str(path), "--consumer-sha256", digest(path.read_bytes())]
    return evidence, prior, args


def collect_pointer(pointer_evidence, *, prior=None, reader=None):
    evidence, original, args = pointer_evidence
    files, _, profile, probe, oldargs = evidence
    return pointer.survey_pointers(
        reader or OwnDisc(files),
        parse_profile(profile),
        probe,
        original if prior is None else prior,
        probe["source"]["size"],
        oldargs[7],
        oldargs[9],
        oldargs[11],
        args[-1],
    )


def test_memory_iso_and_cli_repeat_agree(pointer_evidence, tmp_path):
    evidence, _, args = pointer_evidence
    expected = collect_pointer(pointer_evidence)
    with IsoImage(evidence[1]) as iso:
        assert collect_pointer(pointer_evidence, reader=iso) == expected
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    assert pointer.main(args + ["--output", str(a)]) == 0
    assert pointer.main(args + ["--output", str(b)]) == 0
    assert a.read_bytes() == b.read_bytes() and json.loads(a.read_bytes()) == expected
    assert expected["f02_07_status"] == "pending" and expected["capabilities"] == []
    assert pointer.main(args + ["--output", str(a)]) == 1


@pytest.mark.parametrize(
    "mutation", ["site", "version", "evidence", "executable", "summary", "empty"]
)
def test_prior_must_match_regenerated_evidence_completely(pointer_evidence, mutation):
    prior = deepcopy(pointer_evidence[1])
    if mutation == "site":
        prior["scan"]["candidates"][0]["virtual_address"] += 4
    elif mutation == "version":
        prior["schema_version"] = True
    elif mutation == "evidence":
        prior["evidence"]["profile_sha256"] = "f" * 64
    elif mutation == "executable":
        prior["executable"]["sha256"] = "f" * 64
    elif mutation == "summary":
        prior["confirmed_camera_consumers"] = 1
    else:
        prior = {}
    with pytest.raises(ProfileError) as error:
        collect_pointer(pointer_evidence, prior=prior)
    assert error.value.code == "POINTER_EVIDENCE"


@pytest.mark.parametrize(
    "arg", ["--image-sha256", "--consumer-sha256", "--camera-probe-sha256", "--profile-sha256"]
)
def test_cli_hash_mismatch_never_publishes(pointer_evidence, tmp_path, arg, capsys):
    args = list(pointer_evidence[-1])
    args[args.index(arg) + 1] = "f" * 64
    path = tmp_path / "fail.json"
    assert pointer.main(args + ["--output", str(path)]) == 1
    assert not path.exists() and json.loads(capsys.readouterr().out)["status"] == "rejected"


def test_late_input_change_prevents_publication(pointer_evidence, tmp_path, monkeypatch, capsys):
    class Changed(IsoImage):
        def __exit__(self, *args):
            super().__exit__(*args)
            raise ProfileError("INPUT_CHANGED", "private detail")

    monkeypatch.setattr(pointer, "IsoImage", Changed)
    path = tmp_path / "fail.json"
    assert pointer.main(pointer_evidence[-1] + ["--output", str(path)]) == 1
    assert not path.exists()
    assert json.loads(capsys.readouterr().out)["code"] == "INPUT_CHANGED"


def test_publication_oserror_sanitized(pointer_evidence, tmp_path, monkeypatch, capsys):
    def broken(*_):
        raise OSError("private detail")

    monkeypatch.setattr(pointer, "publish_report", broken)
    assert pointer.main(pointer_evidence[-1] + ["--output", str(tmp_path / "fail.json")]) == 1
    assert json.loads(capsys.readouterr().out) == {"status": "rejected", "code": "POINTER_IO_ERROR"}
