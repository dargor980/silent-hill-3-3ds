"""WR01-WR08: own instructions, registers, RAM and failure-injected private files."""

import hashlib
import json
import struct
import zipfile
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_pcsx2_state import CPU, CRC, own_archive, own_internals

from tools.inspectors import camera_writer as cli
from tools.inspectors import writer_state as decoder
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, VERSION, VERSION_MEMBER, EEState
from tools.inspectors.state_memory import RAM_MEMBER
from tools.inspectors.store_pair import validate_sw
from tools.pipeline.profile import ProfileError

BASE, SIZE, PC = 0x100000, 128, 0x400000
SESSION, ENV = "a" * 32, "b" * 64


def digest(data):
    return hashlib.sha256(data).hexdigest()


def instruction(op=43, rs=4, rt=5, immediate=84):
    return ((op << 26) | (rs << 21) | (rt << 16) | (immediate & 65535)).to_bytes(4, "little")


def state(pc=PC, data=bytes(SIZE), registers=None, delay=False):
    if registers is None:
        registers = [0] * 32
        registers[4], registers[5] = BASE, 0x33445500
    return decoder.WriterState(
        EEState(pc, delay, tuple(r & 0xFFFFFFFF for r in registers)), tuple(registers), data
    )


def pair(branch=False, equal=False):
    before = state()
    data = before.data if equal else before.data[:84] + b"\x00\x55\x44\x33" + before.data[88:]
    if equal:
        before = state(registers=[0] * 4 + [BASE, 0] + [0] * 26)
    code = instruction()
    if branch:
        code = instruction(4, 0, 0, 3) + code
    after = state(PC + (16 if branch else 4), data, before.gpr_low64)
    return before, after, code


@pytest.mark.parametrize("branch", [False, True])
@pytest.mark.parametrize("equal", [False, True])
def test_exact_effect_and_flow(branch, equal):
    before, after, code = pair(branch, equal)
    result = validate_sw(before, after, BASE, code, code)
    assert result["status"] == ("consistent_no_change" if equal else "consistent_changed_store")
    assert result["comparison"]["different_bytes"] == (0 if equal else 3)
    assert result["relative_offset"] == 84 and result["width"] == 4
    assert result["control_flow"] == ("beq_sw_delay_slot" if branch else "direct")
    assert not result["mapping_verified"] and result["execution_authentication"] == "not_provided"


def test_beq_uses_64_bits_not_only_low32():
    before, after, _ = pair(True)
    registers = list(before.gpr_low64)
    registers[1], registers[2] = 0x100000001, 0x200000001
    before = state(registers=registers)
    after = state(PC + 8, after.data, registers)
    code = instruction(4, 1, 2, 3) + instruction()
    assert validate_sw(before, after, BASE, code, code)["status"] == "consistent_changed_store"
    with pytest.raises(ProfileError, match="contract"):
        validate_sw(before, replace(after, cpu=replace(after.cpu, pc=PC + 16)), BASE, code, code)


def test_signed_displacement_backward_branch_and_zero_register():
    before, after, _ = pair(True)
    registers = list(before.gpr_low64)
    registers[4] = BASE + 100
    registers[0] = 999  # Architectural zero is still zero in instruction evaluation.
    before = state(registers=registers)
    after = state(PC - 8, after.data, registers)
    code = instruction(4, 0, 0, -3) + instruction(immediate=-16)
    assert validate_sw(before, after, BASE, code, code)["relative_offset"] == 84
    zero_code = instruction(rt=0, immediate=-16)
    zero_after = state(PC + 4, bytes(SIZE), registers)
    assert (
        validate_sw(before, zero_after, BASE, zero_code, zero_code)["status"]
        == "consistent_no_change"
    )


@pytest.mark.parametrize(
    "variant",
    [
        "changed_code",
        "short_code",
        "long_code",
        "bytearray_code",
        "unsupported_store",
        "unsupported_branch",
        "unsupported_slot",
        "before_delay",
        "after_delay",
        "wrong_pc",
        "unaligned_pc",
        "pc_overflow",
        "branch_overflow",
        "branch_underflow",
        "branch_self",
        "branch_slot",
        "changed_gpr",
        "before_range",
        "after_range",
        "unaligned_target",
        "bad_effect",
        "extra_change",
        "short_data",
        "long_data",
        "unequal_data",
        "bool_base",
        "high_base",
        "range_overflow",
        "zero_base_register",
    ],
)
def test_pair_rejects_unsupported_or_inconsistent_evidence(variant):
    before, after, code = pair()
    other, base = code, BASE
    if variant == "changed_code":
        other = bytes(4)
    elif variant in ("short_code", "long_code", "bytearray_code"):
        code = (
            code[:3]
            if variant == "short_code"
            else code * 3
            if variant == "long_code"
            else bytearray(code)
        )
        other = code
    elif variant == "unsupported_store":
        code = other = instruction(op=40)
    elif variant in ("unsupported_branch", "unsupported_slot"):
        code = other = instruction(
            5 if variant == "unsupported_branch" else 4, 0, 0, 3
        ) + instruction(op=40 if variant == "unsupported_slot" else 43)
        after = replace(after, cpu=replace(after.cpu, pc=PC + 16))
    elif variant in ("before_delay", "after_delay"):
        if variant == "before_delay":
            before = replace(before, cpu=replace(before.cpu, delay_slot=True))
        else:
            after = replace(after, cpu=replace(after.cpu, delay_slot=True))
    elif variant in ("wrong_pc", "unaligned_pc", "pc_overflow"):
        if variant == "wrong_pc":
            after = replace(after, cpu=replace(after.cpu, pc=PC + 8))
        else:
            before = replace(
                before,
                cpu=replace(before.cpu, pc=PC + 1 if variant == "unaligned_pc" else 0xFFFFFFFC),
            )
    elif variant.startswith("branch_"):
        immediate = {
            "branch_overflow": 32767,
            "branch_underflow": -32768,
            "branch_self": -1,
            "branch_slot": 0,
        }[variant]
        pc = (
            0xFFFFFF00
            if variant == "branch_overflow"
            else 0
            if variant == "branch_underflow"
            else PC
        )
        before = replace(before, cpu=replace(before.cpu, pc=pc))
        code = other = instruction(4, 0, 0, immediate) + instruction()
    elif variant == "changed_gpr":
        registers = list(after.gpr_low64)
        registers[31] += 1
        after = state(after.cpu.pc, after.data, registers)
    elif variant in ("before_range", "after_range", "unaligned_target"):
        code = other = instruction(
            immediate={"before_range": -4, "after_range": SIZE, "unaligned_target": 85}[variant]
        )
    elif variant in ("bad_effect", "extra_change"):
        data = bytearray(after.data)
        data[85 if variant == "bad_effect" else 2] ^= 1
        after = replace(after, data=bytes(data))
    elif variant in ("short_data", "long_data", "unequal_data"):
        before = replace(
            before,
            data=bytes(3 if variant == "short_data" else 4097 if variant == "long_data" else 127),
        )
    elif variant in ("bool_base", "high_base", "range_overflow"):
        base = {"bool_base": True, "high_base": 0x2000000, "range_overflow": 0x2000000 - 4}[variant]
    else:
        code = other = instruction(rs=0)
    with pytest.raises(ProfileError):
        validate_sw(before, after, base, code, other)


def archive(value):
    internal = bytearray(own_internals(value.cpu.pc, int(value.cpu.delay_slot)))
    for r, register in enumerate(value.gpr_low64):
        struct.pack_into("<Q", internal, CPU + 16 * r, register)
    return own_archive(
        [
            (VERSION_MEMBER, VERSION),
            (INTERNALS_MEMBER, bytes(internal)),
            (RAM_MEMBER, bytes(BASE) + value.data),
        ],
        compression=zipfile.ZIP_DEFLATED,
    )


def test_reader_preserves_stride_high64_and_hides_originals(monkeypatch):
    monkeypatch.setattr(decoder, "RAM_SIZE", BASE + SIZE)
    registers = list(state().gpr_low64)
    registers[7] = 0xABCDEF0112345678
    original = state(registers=registers)
    decoded = decoder.read_writer_state(archive(original), CRC, None, SIZE)
    assert decoded.gpr_low64 == original.gpr_low64 and decoded.data == original.data
    assert str(registers[7]) not in repr(decoded)
    for base, size in ((True, SIZE), (BASE, 0), (BASE, 4097), (BASE + 4, SIZE)):
        with pytest.raises(ProfileError):
            decoder.read_writer_state(archive(original), CRC, base, size)
    monkeypatch.setattr(decoder, "RAM_SIZE", BASE + SIZE + 1)
    with pytest.raises(ProfileError):
        decoder.read_writer_state(archive(original), CRC, BASE, SIZE)


def save(path, data):
    path.write_bytes(data)
    path.chmod(0o600)
    return digest(data)


@pytest.fixture
def writer_case(tmp_path, monkeypatch):
    monkeypatch.setattr(decoder, "RAM_SIZE", BASE + SIZE)
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    (root / "sstates").mkdir(mode=0o700)
    original = state(PC - 64)
    before, after, code = pair(True)
    source_hash = save(root / "entry.p2s", archive(original))
    resource = {"id": "asset:" + "c" * 64, "size": SIZE, "sha256": digest(original.data)}
    origin = {
        "session_id": "d" * 32,
        "evidence": {"capture_sha256": "e" * 64},
        "source_event_sequence": 2,
        "comparisons": [{"state_sha256": source_hash}],
        "resource": resource,
        "status": "compared_full_candidate",
    }
    origin_path = tmp_path / "origin.json"
    origin_hash = save(origin_path, json.dumps(origin).encode())
    plan = {
        "kind": "sh3-origin-writer-observation-plan",
        "schema_version": 1,
        "new_session_required": True,
        "origin_report_sha256": origin_hash,
        "parent_session_id": origin["session_id"],
        "parent_capture_sha256": "e" * 64,
        "base_source": {"register": 4},
        "restore_event_sequence": 2,
        "restore_state_sha256": source_hash,
        "resource": resource,
    }
    plan_path = tmp_path / "plan.json"
    plan_hash = save(plan_path, json.dumps(plan).encode())
    frames = []
    for sequence, value in enumerate((original, before, after), 1):
        name = f"frame-{sequence}.p2s"
        h = save(root / "sstates" / name, archive(value))
        blob_hash = save(root / (digest(value.data) + ".bin"), value.data)
        frames.append(
            {
                "sequence": sequence,
                "session_id": SESSION,
                "environment_sha256": ENV,
                "state_name": name,
                "state_sha256": h,
                "virtual_sha256": blob_hash,
                "paused_before_after": True,
            }
        )
    h = save(root / (digest(code) + ".bin"), code)
    capture = {
        "schema_version": 1,
        "kind": "sh3-partial-writer-capture",
        "session_id": SESSION,
        "environment_sha256": ENV,
        "expected_crc": CRC,
        "source_state": {"name": "entry.p2s", "sha256": source_hash},
        "frames": frames,
        "pairs": [
            {
                "before_sequence": 2,
                "after_sequence": 3,
                "operation": "step_into",
                "code_pc": PC,
                "code_size": 8,
                "code_before_sha256": h,
                "code_after_sha256": h,
            }
        ],
        "closure": {
            "emulator_closed": True,
            "socket_removed": True,
            "ipc_disabled": True,
            "baseline_unchanged": True,
            "stop_reason": "partial_first_changed_store",
            "return_captured": False,
        },
    }
    capture_hash = save(root / "capture.json", json.dumps(capture).encode())
    output = tmp_path / "report.json"
    args = [
        "--plan",
        str(plan_path),
        "--plan-sha256",
        plan_hash,
        "--origin",
        str(origin_path),
        "--origin-sha256",
        origin_hash,
        "--capture-root",
        str(root),
        "--capture-sha256",
        capture_hash,
        "--output",
        str(output),
    ]
    return SimpleNamespace(**locals())


def repin_capture(c):
    h = save(c.root / "capture.json", json.dumps(c.capture).encode())
    c.args[c.args.index("--capture-sha256") + 1] = h


def test_repeated_cli_metadata_only_and_no_overwrite(writer_case, capsys):
    c = writer_case
    assert cli.main(c.args) == 0
    report = json.loads(c.output.read_text())
    assert report["pairs"][0]["comparison"]["difference_ranges"] == [{"start": 85, "end": 88}]
    assert report["entry_matches_restored_cpu_and_full_resource"]
    assert report["coverage"] == "partial_pairs_only" and not report["return_captured"]
    assert not report["mapping_verified"] and report["origin_status"] == "pending"
    assert report["resource_links"] == report["capabilities"] == []
    assert all(
        s not in c.output.read_text() for s in (str(BASE), str(PC), str(c.root), "gpr", "code_pc")
    )
    repeated = c.output.with_name("repeat.json")
    args = c.args.copy()
    args[args.index("--output") + 1] = str(repeated)
    assert cli.main(args) == 0 and repeated.read_bytes() == c.output.read_bytes()
    assert cli.main(c.args) == 1 and "OUTPUT_EXISTS" in capsys.readouterr().out


@pytest.mark.parametrize(
    "variant",
    [
        "session",
        "old_session",
        "env",
        "paused",
        "order",
        "bool_order",
        "duplicate_state",
        "pair_order",
        "bool_pair",
        "operation",
        "code_pc",
        "code_size",
        "code_hash",
        "closure",
        "source_hash",
        "source_path",
        "crc",
        "entry_pc",
        "entry_ram",
        "state_hash",
        "virtual_hash",
        "code_changed",
        "unknown_field",
        "empty_pairs",
        "many_frames",
        "many_pairs",
    ],
)
def test_capture_errors_publish_nothing(writer_case, variant, capsys):
    c = writer_case
    f, p = c.capture["frames"][1], c.capture["pairs"][0]
    if variant in (
        "session",
        "env",
        "paused",
        "order",
        "bool_order",
        "duplicate_state",
        "state_hash",
        "virtual_hash",
    ):
        key, value = {
            "session": ("session_id", "f" * 32),
            "env": ("environment_sha256", "f" * 64),
            "paused": ("paused_before_after", 1),
            "order": ("sequence", 3),
            "bool_order": ("sequence", True),
            "duplicate_state": ("state_name", "frame-1.p2s"),
            "state_hash": ("state_sha256", "f" * 64),
            "virtual_hash": ("virtual_sha256", "f" * 64),
        }[variant]
        f[key] = value
    elif variant == "old_session":
        c.capture["session_id"] = c.origin["session_id"]
    elif variant in ("pair_order", "bool_pair", "operation", "code_pc", "code_size", "code_hash"):
        key, value = {
            "pair_order": ("before_sequence", 1),
            "bool_pair": ("after_sequence", True),
            "operation": ("operation", "continue"),
            "code_pc": ("code_pc", PC + 4),
            "code_size": ("code_size", True),
            "code_hash": ("code_after_sha256", "f" * 64),
        }[variant]
        p[key] = value
    elif variant == "closure":
        c.capture["closure"]["ipc_disabled"] = False
    elif variant.startswith("source_"):
        c.capture["source_state"]["sha256" if variant == "source_hash" else "name"] = (
            "f" * 64 if variant == "source_hash" else "../entry.p2s"
        )
    elif variant == "crc":
        c.capture["expected_crc"] += 1
    elif variant in ("entry_pc", "entry_ram"):
        value = state(PC - 60) if variant == "entry_pc" else state(PC - 64, b"X" * SIZE)
        frame = c.capture["frames"][0]
        frame["state_sha256"] = save(c.root / "sstates" / frame["state_name"], archive(value))
        frame["virtual_sha256"] = save(c.root / (digest(value.data) + ".bin"), value.data)
    elif variant == "code_changed":
        data = bytes(8)
        p["code_after_sha256"] = save(c.root / (digest(data) + ".bin"), data)
    elif variant == "unknown_field":
        c.capture["private detail"] = "unwanted"
    elif variant == "empty_pairs":
        c.capture["pairs"] = []
    elif variant == "many_pairs":
        c.capture["pairs"] *= 257
    else:
        c.capture["frames"] *= 172
    repin_capture(c)
    assert cli.main(c.args) == 1 and not c.output.exists()
    assert "private detail" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "variant",
    [
        "plan",
        "resource",
        "origin_hash",
        "source_mutation",
        "frame_mutation",
        "virtual_mismatch",
        "late_close",
        "write_failure",
    ],
)
def test_dependency_or_late_failure_blocks_publication(writer_case, monkeypatch, variant, capsys):
    c = writer_case
    if variant in ("plan", "resource"):
        if variant == "plan":
            c.plan["base_source"]["register"] = 5
        else:
            c.plan["resource"]["sha256"] = "f" * 64
        h = save(c.plan_path, json.dumps(c.plan).encode())
        c.args[c.args.index("--plan-sha256") + 1] = h
    elif variant == "origin_hash":
        c.args[c.args.index("--origin-sha256") + 1] = "f" * 64
    elif variant == "virtual_mismatch":
        f = c.capture["frames"][1]
        data = b"Z" * SIZE
        f["virtual_sha256"] = save(c.root / (digest(data) + ".bin"), data)
        repin_capture(c)
    elif variant in ("source_mutation", "frame_mutation"):
        original = cli.validate_sw

        def mutate(*args):
            result = original(*args)
            path = (
                c.root / "entry.p2s"
                if variant == "source_mutation"
                else c.root / "sstates/frame-1.p2s"
            )
            path.write_bytes(b"private detail")
            return result

        monkeypatch.setattr(cli, "validate_sw", mutate)
    elif variant == "late_close":
        original = cli.PrivateCaptureReader.__exit__

        def fail(self, *args):
            original(self, *args)
            raise OSError("private detail")

        monkeypatch.setattr(cli.PrivateCaptureReader, "__exit__", fail)
    else:

        def fail(*args):
            raise OSError("private detail")

        monkeypatch.setattr(cli, "publish_report", fail)
    assert cli.main(c.args) == 1 and not c.output.exists()
    assert "private detail" not in capsys.readouterr().out
