"""WR04-WR06: narrow SW pair consistency; no execution or mapping authentication."""

import hashlib

from tools.inspectors.observation_capture import require
from tools.inspectors.origin_compare import compare_ranges
from tools.inspectors.writer_state import WriterState


def signed_immediate(word: int) -> int:
    value = word & 65535
    return value if value < 32768 else value - 65536


def next_pc(state: WriterState, code: bytes) -> tuple[int, str]:
    pc = state.cpu.pc
    require(0 <= pc <= 0xFFFFFFFF - len(code) and pc % 4 == 0, "WRITER_STEP")
    word = int.from_bytes(code[:4], "little")
    if len(code) == 4:
        require(word >> 26 == 43, "WRITER_UNSUPPORTED")
        return pc + 4, "direct"
    require(word >> 26 == 4, "WRITER_UNSUPPORTED")
    rs, rt = (word >> 21) & 31, (word >> 16) & 31
    left, right = (state.gpr_low64[r] if r else 0 for r in (rs, rt))
    target = pc + 4 + signed_immediate(word) * 4 if left == right else pc + 8
    require(0 <= target <= 0xFFFFFFFF and target not in (pc, pc + 4), "WRITER_STEP")
    return target, "beq_sw_delay_slot"


def validate_sw(
    before: WriterState,
    after: WriterState,
    base: int,
    code_before: bytes,
    code_after: bytes,
) -> dict:
    require(
        isinstance(code_before, bytes)
        and len(code_before) in (4, 8)
        and isinstance(code_after, bytes)
        and code_before == code_after,
        "WRITER_CODE",
    )
    target, control_flow = next_pc(before, code_before)
    require(
        not before.cpu.delay_slot
        and not after.cpu.delay_slot
        and after.cpu.pc == target
        and before.gpr_low64 == after.gpr_low64,
        "WRITER_STEP",
    )
    data_before, data_after = before.data, after.data
    require(
        type(base) is int
        and 0x100000 <= base < 0x2000000
        and isinstance(data_before, bytes)
        and isinstance(data_after, bytes)
        and 4 <= len(data_before) == len(data_after) <= 4096
        and base + len(data_before) <= 0x2000000,
        "WRITER_RANGE",
    )
    word = int.from_bytes(code_before[-4:], "little")
    require(word >> 26 == 43, "WRITER_UNSUPPORTED")
    rs, rt = (word >> 21) & 31, (word >> 16) & 31
    address = ((before.cpu.gpr_low32[rs] if rs else 0) + signed_immediate(word)) & 0xFFFFFFFF
    require(address % 4 == 0 and base <= address <= base + len(data_before) - 4, "WRITER_TARGET")
    offset = address - base
    value = (before.cpu.gpr_low32[rt] if rt else 0).to_bytes(4, "little")
    expected = data_before[:offset] + value + data_before[offset + 4 :]
    require(expected == data_after, "WRITER_EFFECT")
    comparison = compare_ranges(data_before, data_after)
    return {
        "status": "consistent_no_change" if comparison["equal"] else "consistent_changed_store",
        "instruction_class": "SW",
        "control_flow": control_flow,
        "instruction_sha256": hashlib.sha256(code_before).hexdigest(),
        "relative_offset": offset,
        "width": 4,
        "comparison": comparison,
        "mapping_verified": False,
        "execution_authentication": "not_provided",
    }
