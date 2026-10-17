"""RR01-RR07: repeated synthetic writer and return evidence, no original game data."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_camera_writer import (
    BASE,
    PC,
    archive,
    digest,
    instruction,
    repin_capture,
    save,
    state,
)
from test_camera_writer import (
    writer_case as writer_case,
)

from tools.inspectors import camera_return as cli
from tools.inspectors import camera_writer as writer
from tools.inspectors.return_compare import compare_writer_pairs
from tools.pipeline.profile import ProfileError


@pytest.fixture
def return_case(writer_case):
    c = writer_case
    registers = list(c.original.gpr_low64)
    registers[31] = PC + 128
    original = state(PC - 64, registers=registers)
    source_hash = save(c.root / "entry.p2s", archive(original))
    c.capture["source_state"]["sha256"] = source_hash
    c.capture["frames"][0]["state_sha256"] = save(c.root / "sstates/frame-1.p2s", archive(original))
    c.plan["restore_state_sha256"] = source_hash
    c.plan["stop_at_historical_event_sequence"] = 3
    c.origin["comparisons"][0].update({"state_sha256": source_hash, "event_sequence": 2})
    data = bytearray(c.after.data)
    data[98:100] = b"AB"
    registers[4] = BASE + 2048  # Return must preserve the entry base instead.
    returned = state(PC + 128, bytes(data), registers)
    historical = {
        "event_sequence": 3,
        "state_sha256": digest(archive(returned)),
        "against_resource": {"observed_sha256": digest(returned.data)},
    }
    c.origin["comparisons"].append(historical)
    c.origin_hash = save(c.origin_path, json.dumps(c.origin).encode())
    c.plan["origin_report_sha256"] = c.origin_hash
    c.plan_hash = save(c.plan_path, json.dumps(c.plan).encode())
    for flag, value in [("--plan-sha256", c.plan_hash), ("--origin-sha256", c.origin_hash)]:
        c.args[c.args.index(flag) + 1] = value
    repin_capture(c)
    assert writer.main(c.args) == 0
    previous_hash = digest(c.output.read_bytes())
    previous_capture_hash = digest((c.root / "capture.json").read_bytes())
    root = c.root.with_name("new-private")
    shutil.copytree(c.root, root)
    capture = json.loads((root / "capture.json").read_text())
    capture.update(
        {
            "kind": "sh3-return-writer-capture",
            "session_id": "1" * 32,
            "environment_sha256": "2" * 64,
            "return_sequence": 4,
            "return_reference": {
                "name": "historical-return.p2s",
                "sha256": historical["state_sha256"],
            },
        }
    )
    capture["closure"].update({"stop_reason": "return_observed", "return_captured": True})
    save(root / "historical-return.p2s", archive(returned))
    capture["frames"].append(
        {
            "sequence": 4,
            "session_id": capture["session_id"],
            "environment_sha256": capture["environment_sha256"],
            "state_name": "returned.p2s",
            "state_sha256": save(root / "sstates/returned.p2s", archive(returned)),
            "virtual_sha256": save(root / (digest(returned.data) + ".bin"), returned.data),
            "paused_before_after": True,
        }
    )
    for frame in capture["frames"]:
        frame.update(
            {
                "session_id": capture["session_id"],
                "environment_sha256": capture["environment_sha256"],
            }
        )
    capture_hash = save(root / "capture.json", json.dumps(capture).encode())
    output = c.output.with_name("return-report.json")
    args = [
        "--plan",
        str(c.plan_path),
        "--plan-sha256",
        c.plan_hash,
        "--origin",
        str(c.origin_path),
        "--origin-sha256",
        c.origin_hash,
        "--previous",
        str(c.output),
        "--previous-sha256",
        previous_hash,
        "--previous-capture-root",
        str(c.root),
        "--previous-capture-sha256",
        previous_capture_hash,
        "--capture-root",
        str(root),
        "--capture-sha256",
        capture_hash,
        "--output",
        str(output),
    ]
    return SimpleNamespace(**locals())


def repin(r):
    h = save(r.root / "capture.json", json.dumps(r.capture).encode())
    r.args[r.args.index("--capture-sha256") + 1] = h


def replace_return(r, value):
    frame = r.capture["frames"][-1]
    frame["state_sha256"] = save(r.root / "sstates" / frame["state_name"], archive(value))
    frame["virtual_sha256"] = save(r.root / (digest(value.data) + ".bin"), value.data)


def test_complete_cli_repeat_preserves_base_and_prior_report(return_case, capsys):
    r = return_case
    assert cli.main(r.args) == 0
    result = json.loads(r.output.read_text())
    assert result["previous_reproduced"] and result["repetition_equal"]
    assert result["return_equal_to_historical"] and result["current"]["return_captured"]
    returned = result["current"]["return"]
    assert returned["pc_matches_entry_link_and_historical"]
    assert returned["against_entry"]["different_bytes"] == 5
    assert not result["mapping_verified"] and result["origin_status"] == "pending"
    assert result["resource_links"] == result["capabilities"] == []
    assert all(
        v not in r.output.read_text() for v in (str(BASE), str(PC), str(r.root), "code_pc", "gpr")
    )
    repeat = r.output.with_name("return-repeat.json")
    args = r.args.copy()
    args[args.index("--output") + 1] = str(repeat)
    assert cli.main(args) == 0 and repeat.read_bytes() == r.output.read_bytes()
    assert cli.main(r.args) == 1 and "OUTPUT_EXISTS" in capsys.readouterr().out
    assert digest(r.c.output.read_bytes()) == r.previous_hash


@pytest.mark.parametrize("variant", ["return_difference", "pair_difference"])
def test_disagreement_is_reported_without_fabricated_equality(return_case, variant):
    r = return_case
    if variant == "return_difference":
        data = bytearray(r.returned.data)
        data[100] = 99
        replace_return(r, state(r.returned.cpu.pc, bytes(data), r.returned.gpr_low64))
    else:
        code = instruction(4, 1, 1, 3) + instruction()
        h = save(r.root / (digest(code) + ".bin"), code)
        r.capture["pairs"][0].update({"code_before_sha256": h, "code_after_sha256": h})
    repin(r)
    assert cli.main(r.args) == 0
    result = json.loads(r.output.read_text())
    if variant == "return_difference":
        assert not result["return_equal_to_historical"] and result["repetition_equal"]
        assert result["current"]["return"]["against_historical"]["different_bytes"] == 1
    else:
        assert not result["repetition_equal"] and result["return_equal_to_historical"]
        assert result["pair_comparisons"][0]["differing_fields"] == ["instruction_sha256"]


@pytest.mark.parametrize(
    "variant",
    [
        "same_session",
        "historical_session",
        "return_early",
        "return_late",
        "return_bool",
        "return_pc",
        "return_delay",
        "partial_kind",
        "partial_closure",
        "not_closed",
        "reference_hash",
        "reference_name",
        "reference_bytes",
        "return_hash",
        "old_capture_hash",
        "old_report_hash",
        "forged_previous",
        "new_capture_hash",
        "wrong_entry",
        "duplicate_frame",
        "pair_after_return",
        "no_changed_pair",
    ],
)
def test_identity_order_and_partial_capture_fail_without_publication(return_case, variant, capsys):
    r = return_case
    if variant in ("same_session", "historical_session"):
        session = (
            r.c.capture["session_id"] if variant == "same_session" else r.c.origin["session_id"]
        )
        r.capture["session_id"] = session
        for frame in r.capture["frames"]:
            frame["session_id"] = session
    elif variant in ("return_early", "return_late", "return_bool"):
        r.capture["return_sequence"] = {"return_early": 3, "return_late": 5, "return_bool": True}[
            variant
        ]
    elif variant in ("return_pc", "return_delay"):
        replace_return(
            r,
            state(
                r.returned.cpu.pc + (4 if variant == "return_pc" else 0),
                r.returned.data,
                r.returned.gpr_low64,
                variant == "return_delay",
            ),
        )
    elif variant == "partial_kind":
        r.capture["kind"] = "sh3-partial-writer-capture"
    elif variant == "partial_closure":
        r.capture["closure"].update(
            {"stop_reason": "partial_first_changed_store", "return_captured": False}
        )
    elif variant == "not_closed":
        r.capture["closure"]["emulator_closed"] = False
    elif variant == "reference_hash":
        r.capture["return_reference"]["sha256"] = "f" * 64
    elif variant == "reference_name":
        r.capture["return_reference"]["name"] = "../historical-return.p2s"
    elif variant == "reference_bytes":
        (r.root / "historical-return.p2s").write_bytes(b"private detail")
    elif variant == "return_hash":
        r.capture["frames"][-1]["state_sha256"] = "f" * 64
    elif variant in ("old_capture_hash", "old_report_hash"):
        flag = "--previous-capture-sha256" if variant == "old_capture_hash" else "--previous-sha256"
        r.args[r.args.index(flag) + 1] = "f" * 64
    elif variant == "forged_previous":
        h = save(r.c.output, b"{}")
        r.args[r.args.index("--previous-sha256") + 1] = h
    elif variant == "wrong_entry":
        frame = r.capture["frames"][0]
        frame["state_sha256"] = save(r.root / "sstates" / frame["state_name"], archive(state(PC)))
    elif variant == "duplicate_frame":
        r.capture["frames"][-1]["state_name"] = r.capture["frames"][0]["state_name"]
    elif variant == "pair_after_return":
        r.capture["pairs"].append(
            {**r.capture["pairs"][0], "before_sequence": 4, "after_sequence": 5}
        )
    elif variant == "no_changed_pair":
        # Retain a coherent same-value store, but it does not repeat the changed pair.
        before = r.c.after
        for n, pc in ((1, PC), (2, PC + 16)):
            frame = r.capture["frames"][n]
            frame["state_sha256"] = save(
                r.root / "sstates" / frame["state_name"],
                archive(state(pc, before.data, before.gpr_low64)),
            )
            frame["virtual_sha256"] = digest(before.data)
    repin(r)
    if variant == "new_capture_hash":
        r.args[r.args.index("--capture-sha256") + 1] = "f" * 64
    assert cli.main(r.args) == 1 and not r.output.exists()
    assert "private detail" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "variant",
    ["missing", "duplicate", "hash", "range", "wrong_pc", "delay", "early", "bool_target"],
)
def test_historical_reference_is_bound_to_plan_and_range(return_case, variant):
    r = return_case
    # Exercise the mode directly so a deliberately forged historical report is
    # isolated from SRC28 reproduction, which would also reject its new identity.
    origin, plan = json.loads(json.dumps(r.c.origin)), json.loads(json.dumps(r.c.plan))
    if variant == "missing":
        origin["comparisons"].pop()
    elif variant == "duplicate":
        origin["comparisons"].append(origin["comparisons"][-1])
    elif variant == "hash":
        origin["comparisons"][-1]["state_sha256"] = "f" * 64
    elif variant == "range":
        origin["comparisons"][-1]["against_resource"]["observed_sha256"] = "f" * 64
    elif variant in ("wrong_pc", "delay"):
        value = state(
            PC + (132 if variant == "wrong_pc" else 128),
            r.returned.data,
            r.returned.gpr_low64,
            variant == "delay",
        )
        h = save(r.root / "historical-return.p2s", archive(value))
        r.capture["return_reference"]["sha256"] = h
        origin["comparisons"][-1]["state_sha256"] = h
    else:
        plan["stop_at_historical_event_sequence"] = 2 if variant == "early" else True
    repin(r)
    with pytest.raises(ProfileError):
        writer.collect_writer_report(
            plan,
            r.c.plan_hash,
            origin,
            r.c.origin_hash,
            digest((r.root / "capture.json").read_bytes()),
            r.root,
            Path(__file__).resolve().parents[2],
            with_return=True,
        )


@pytest.mark.parametrize(
    "variant", ["reference_mutation", "state_mutation", "late_close", "write_failure"]
)
def test_late_failure_keeps_report_absent(return_case, monkeypatch, variant, capsys):
    r = return_case
    if variant in ("reference_mutation", "state_mutation"):
        original = writer.validate_return

        def mutate(*args):
            result = original(*args)
            path = r.root / (
                "historical-return.p2s"
                if variant == "reference_mutation"
                else "sstates/frame-1.p2s"
            )
            path.write_bytes(b"private detail")
            return result

        monkeypatch.setattr(writer, "validate_return", mutate)
    elif variant == "late_close":
        original = writer.PrivateCaptureReader.__exit__

        def fail(self, *args):
            original(self, *args)
            if self.root == r.root:
                raise OSError("private detail")

        monkeypatch.setattr(writer.PrivateCaptureReader, "__exit__", fail)
    else:

        def fail(*args):
            raise OSError("private detail")

        monkeypatch.setattr(cli, "publish_report", fail)
    assert cli.main(r.args) == 1 and not r.output.exists()
    assert "private detail" not in capsys.readouterr().out


def test_comparison_rejects_ambiguous_previous_changed_pair():
    with pytest.raises(ProfileError):
        compare_writer_pairs({"pairs": []}, {"pairs": []})
