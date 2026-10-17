"""Small, conservative GPR/control subset for static hypotheses, not disassembly."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Effect:
    kind: str = "preserve"
    destination: int = 0
    source: int = 0


@dataclass(frozen=True)
class Instruction:
    effect: Effect = Effect()
    flow: str = "next"
    target: int | None = None
    likely: bool = False


UNKNOWN = Instruction(Effect("unknown"))


def decode(word: int, pc: int) -> Instruction:
    """Interpret supported effects only; unknown invalidates every tracked GPR."""
    op, rs, rt, rd = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
    immediate = word & 0xFFFF
    signed = immediate if immediate < 0x8000 else immediate - 0x10000
    if word == 0:
        return Instruction()
    if op in (2, 3):
        target = ((pc + 4) & 0xF0000000) | ((word & 0x3FFFFFF) << 2)
        return Instruction(
            Effect("link", 31) if op == 3 else Effect(), "call" if op == 3 else "jump", target
        )
    if op in (4, 5, 20, 21) or (op in (6, 7, 22, 23) and rt == 0):
        return Instruction(flow="branch", target=pc + 4 + signed * 4, likely=op >= 20)
    if op == 1:
        if rt in (0, 1, 2, 3):
            return Instruction(flow="branch", target=pc + 4 + signed * 4, likely=rt >= 2)
        # REGIMM link/trap variants are outside this dataflow contract.
        return UNKNOWN
    if op == 0:
        function, shift = word & 63, (word >> 6) & 31
        if function == 8 and word & 0x1FFFFF == 8:
            return Instruction(flow="indirect")
        if function == 9 and rt == 0 and shift == 0:
            return Instruction(Effect("link", rd), "indirect_call" if rd else "indirect")
        if function in (33, 37, 45) and shift == 0:
            if rs == 0 or rt == 0:
                return Instruction(Effect("copy", rd, rt if rs == 0 else rs))
            return Instruction(Effect("overwrite", rd))
        if function in (0, 2, 3, 56, 58, 59, 60, 62, 63) and rs == 0:
            return Instruction(Effect("overwrite", rd))
        if function in (4, 6, 7, 10, 11, 32, 34, 35, 36, 38, 39, 42, 43, 44, 46, 47) and shift == 0:
            return Instruction(Effect("overwrite", rd))
        if function in (16, 18) and rs == rt == shift == 0:
            return Instruction(Effect("overwrite", rd))
        if function in (17, 19) and rt == rd == shift == 0:
            return Instruction()
        return UNKNOWN
    if word & 0xFC0007FF == 0x700004A9:  # R5900 POR, copying only with a zero operand.
        if rs == 0 or rt == 0:
            return Instruction(Effect("copy", rd, rt if rs == 0 else rs))
        return Instruction(Effect("overwrite", rd))
    if op in (9, 25):
        return Instruction(Effect("adjust", rt, rs))
    if op == 15 and rs == 0:
        return Instruction(Effect("constant", rt))
    if op in (8, 10, 11, 12, 13, 14, 24):
        return Instruction(Effect("constant" if rs == 0 else "overwrite", rt))
    if op in (26, 27, 30, 32, 33, 34, 35, 36, 37, 38, 39, 55):
        return Instruction(Effect("load", rt, rs))
    if op in (31, 40, 41, 42, 43, 44, 45, 46, 49, 57, 63):
        return Instruction()  # Stores and COP1 memory operations do not write GPRs.
    if op == 17:
        if rs == 8 and rt in (0, 1, 2, 3):
            return Instruction(flow="branch", target=pc + 4 + signed * 4, likely=rt >= 2)
        if rs in (0, 2) and word & 0x7FF == 0:
            return Instruction(Effect("overwrite", rt))
        if rs in (4, 6) and word & 0x7FF == 0:
            return Instruction()
        if rs == 16:
            function = word & 63
            if function in (0, 1, 2, 3, 40, 41):
                return Instruction()  # FP arithmetic writes FPRs, not GPRs.
            if function in (5, 6, 7) and rt == 0:
                return Instruction()
            if function in (50, 52, 54) and word & 0x7C0 == 0:
                return Instruction()  # R5900 scalar comparisons write the FP condition.
        # No general COP1/COP2 or MMI decoding: invalidate rather than invent effects.
    return UNKNOWN
