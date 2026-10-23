"""Check complete, single output writes in the inspection shaders' compiled SHBIN.

This deliberately supports only one vertex DVLE, full position/color/UV outputs,
and straight-line MOV/DP4/NOP/END. It is not a general shader verifier. Unknown
programs fail closed. DVLE masks are XYZW low-to-high; instruction masks reverse
that order. See docs/execution/f03-02-character-material-gpu-fix.md for sources.
"""

import argparse
import struct
from pathlib import Path


def validate_shader(data: bytes) -> dict[str, int]:
    """Raise ValueError on unsupported layout, missing or repeated output writes."""

    def region(offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError("truncated SHBIN region")
        return data[offset : offset + size]

    def u32(offset: int) -> int:
        return struct.unpack("<I", region(offset, 4))[0]

    if region(0, 4) != b"DVLB" or u32(4) != 1:
        raise ValueError("expected one DVLE")
    dvlp = 12
    dvle = u32(8)
    if region(dvlp, 4) != b"DVLP" or region(dvle, 4) != b"DVLE":
        raise ValueError("invalid shader section signature")
    region(dvlp, 28)
    region(dvle, 64)
    if u32(dvle + 4) >> 16:
        raise ValueError("only a vertex shader without merged outmaps is supported")
    code_count, desc_count = u32(dvlp + 12), u32(dvlp + 20)
    if not 1 <= code_count <= 512 or not 1 <= desc_count <= 128:
        raise ValueError("invalid code or descriptor count")
    code = dvlp + u32(dvlp + 8)
    desc = dvlp + u32(dvlp + 16)
    region(code, code_count * 4)
    region(desc, desc_count * 8)
    start, stop = u32(dvle + 8), u32(dvle + 12)
    if not 0 <= start < stop <= code_count:
        raise ValueError("invalid entrypoint range")
    output_count = u32(dvle + 44)
    if output_count != 3:
        raise ValueError("expected position, color and UV outputs")
    outputs = dvle + u32(dvle + 40)
    declared = {}
    semantics = set()
    for index in range(output_count):
        semantic, register, mask = struct.unpack("<HHI", region(outputs + index * 8, 8))
        if semantic not in {0, 2, 3} or semantic in semantics:
            raise ValueError("unsupported or duplicate output semantic")
        if register >= 3 or register in declared or mask != 15:
            raise ValueError("expected three distinct, full output registers")
        semantics.add(semantic)
        declared[register] = [0, 0, 0, 0]
    ended = False
    for pc in range(start, stop):
        word = u32(code + pc * 4)
        opcode = word >> 26
        if opcode == 0x21:  # NOP, including assembler padding after END.
            continue
        if ended:
            raise ValueError("non-padding instruction after END")
        if opcode == 0x22:
            ended = True
            continue
        if opcode not in {0x02, 0x13}:  # DP4 and MOV use the same DST/DESC fields.
            raise ValueError(f"unsupported instruction at {pc}: {opcode:#x}")
        descriptor = word & 0x7F
        if descriptor >= desc_count:
            raise ValueError("operand descriptor outside table")
        register = (word >> 21) & 0x1F
        if register >= 16:  # Scratch writes do not emit output components.
            continue
        if register not in declared:
            raise ValueError(f"write to undeclared output o{register}")
        mask = u32(desc + descriptor * 8) & 15
        for component in range(4):
            declared[register][component] += bool(mask & (8 >> component))
    if not ended:
        raise ValueError("missing END")
    for register, counts in declared.items():
        for component, count in zip("xyzw", counts, strict=True):
            if count != 1:
                raise ValueError(f"o{register}.{component}: expected one write, found {count}")
    return {"instructions": stop - start, "output_registers": len(declared), "components": 12}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shader", type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate_shader(args.shader.read_bytes())
    except (OSError, ValueError) as error:
        print(f"PICA output check: FAIL: {error}")
        return 1
    print(f"PICA output check: PASS: {args.shader.name}: {result['components']} components once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
