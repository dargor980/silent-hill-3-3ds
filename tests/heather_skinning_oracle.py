"""HS-T2 mathematical contract oracle, with no runtime/producer imports.

The SHBIN evaluator uses host binary32, NOT PICA arithmetic or GPU execution.
Rational reference positions retain the source binary32 matrices exactly.
"""

import math
import struct
from fractions import Fraction as F

ORIGIN = (100000, 0, 140000)
CAPACITY = 30


def need(condition, field):
    if not condition:
        raise ValueError("HS_" + field)


def f32(value):
    try:
        result = struct.unpack("<f", struct.pack("<f", value))[0]
    except (OverflowError, struct.error):
        raise ValueError("HS_NUMBER") from None
    need(math.isfinite(result), "NUMBER")
    return result


def bits(values):
    return struct.pack("<" + "f" * len(values), *values).hex()


def affine(matrix, limit):
    need(len(matrix) == 16, "MATRIX")
    values = list(map(f32, matrix))
    need(all(abs(x) <= limit for x in values), "MATRIX")
    need([values[i] for i in (3, 7, 11, 15)] == [0, 0, 0, 1], "AFFINE")
    return values


def product(a, b):
    # Preserve the native helper composition's binary32 multiply/add ordering.
    out = []
    for c in range(4):
        for r in range(4):
            x = 0.0
            for k in range(4):
                x = f32(x + f32(a[4 * k + r] * b[4 * c + k]))
            out.append(x)
    return out


def prepare(case):
    """Validate a synthetic palette/vertex and return GPU rows and attributes."""
    slots = case["palette"]
    need(1 <= len(slots) <= CAPACITY, "CAPACITY")
    need(all(type(s) is int and 0 <= s <= 200 for s in slots), "SLOT")
    need(slots == sorted(set(slots)), "PALETTE_ORDER")
    used, weights = case["influences"], case["weights_q12"]
    need(1 <= len(used) <= 3 and len(weights) == 3, "INFLUENCES")
    need(all(s in slots for s in used), "SLOT")
    need(all(type(w) is int and 0 <= w <= 4096 for w in weights), "WEIGHTS")
    need(not any(weights[len(used) :]), "WEIGHTS")
    need(4097 - len(used) <= sum(weights) <= 4096, "WEIGHTS")
    xyz, uv = case["position_q4"], case["uv_q12"]
    need(len(xyz) == 3 and len(uv) == 2, "VERTEX")
    need(all(type(x) is int and -32768 <= x <= 32767 for x in xyz + uv), "VERTEX")
    instance = affine(case["instance"], 1000000)
    for a in range(3):
        for b in range(a, 3):
            need(
                abs(sum(instance[4 * a + r] * instance[4 * b + r] for r in range(3)) - (a == b))
                <= 0.0001,
                "INSTANCE",
            )
    determinant = (
        instance[0] * (instance[5] * instance[10] - instance[6] * instance[9])
        - instance[4] * (instance[1] * instance[10] - instance[2] * instance[9])
        + instance[8] * (instance[1] * instance[6] - instance[2] * instance[5])
    )
    need(determinant > 0.9999, "INSTANCE")
    bones = {int(s): affine(p, 1000000) for s, p in case["bones"].items()}
    need(all(0 <= s < 73 for s in bones), "SLOT")
    palette = dict(bones)
    for key, helper in case["helpers"].items():
        s = int(key)
        need(73 <= s <= 200 and helper["target"] in bones, "SLOT")
        palette[s] = product(bones[helper["target"]], affine(helper["matrix"], 100000))
    need(all(s in palette for s in slots), "SLOT")
    scale, rows = f32(0.002), []
    for slot in slots:
        p = palette[slot]
        for r in range(3):
            row = []
            for c in range(4):
                x = (instance[12 + r] - ORIGIN[r]) if c == 3 else 0.0
                for k in range(3):
                    x += instance[4 * k + r] * p[4 * c + k]
                row.append(f32(x * scale * (1 if r == 0 else -1)))
            rows.append(row)
    clip = list(map(f32, case["clip_from_room"]))
    need(len(clip) == 16 and all(abs(x) <= 1000000 for x in clip), "CLIP")
    attributes = [
        [*(x / 16 for x in xyz), 1.0],
        [*(w / 4096 for w in weights), sum(weights) / 4096],
        [*(3.0 * slots.index(s) for s in used), *([0.0] * (3 - len(used))), 0.0],
        [uv[0] / 4096, uv[1] / 4096, 0.0, 1.0],
    ]
    return dict(rows=rows, attributes=attributes, matrices=palette, instance=instance, clip=clip)


def reference(case, prepared):
    """Exact rational deformation first, then instance/basis, independently of packing."""
    p = [F(x, 16) for x in case["position_q4"]] + [F(1)]
    model = [F(0)] * 4
    for slot, weight in zip(case["influences"], case["weights_q12"], strict=False):
        m = list(map(F, prepared["matrices"][slot]))
        for r in range(4):
            model[r] += F(weight, 4096) * sum(m[4 * c + r] * p[c] for c in range(4))
    instance = list(map(F, prepared["instance"]))
    room = []
    for r in range(3):
        x = sum(instance[4 * c + r] * model[c] for c in range(4)) - ORIGIN[r] * model[3]
        room.append(x * F(f32(0.002)) * (1 if r == 0 else -1))
    return room + [model[3]]


def shader_program(data):
    """Decode just the frozen straight-line HS probe, fail closed on other layouts."""
    need(len(data) == 408, "SHBIN")

    def region(at, size):
        need(0 <= at <= at + size <= len(data), "SHBIN")
        return data[at : at + size]

    def u32(at):
        return struct.unpack("<I", region(at, 4))[0]

    need(region(0, 8) == b"DVLB\x01\0\0\0", "SHBIN")
    p, v = 12, u32(8)
    need(region(p, 4) == b"DVLP" and region(v, 4) == b"DVLE", "SHBIN")
    need(u32(v + 4) >> 16 == 0, "SHBIN")
    need(u32(p + 12) == 28 and u32(p + 20) == 12, "SHBIN")
    need((u32(v + 8), u32(v + 12)) == (0, 28), "SHBIN")
    symbols = v + u32(v + 56)
    uniforms = {}
    need(u32(v + 52) == 2, "SHBIN")
    for i in range(2):
        name, start, end = struct.unpack("<IHH", region(v + u32(v + 48) + 8 * i, 8))
        name = region(symbols + name, u32(v + 60) - name).split(b"\0")[0]
        uniforms[name] = (start - 16, end - 16)
    need(uniforms == {b"palette": (0, 89), b"clip_from_room": (90, 93)}, "SHBIN")
    need(u32(v + 28) == 1, "SHBIN")
    constant = struct.unpack("<HH4I", region(v + u32(v + 24), 20))
    need(constant == (2, 95, 0, 0x3F0000, 0, 0), "SHBIN")
    need(u32(v + 44) == 3, "SHBIN")
    for i, semantic in enumerate((0, 2, 3)):
        need(
            struct.unpack("<HHI", region(v + u32(v + 40) + 8 * i, 8)) == (semantic, i, 15), "SHBIN"
        )
    instructions, written = [], [[0] * 4 for _ in range(3)]
    expected = [
        19,
        19,
        19,
        18,
        2,
        2,
        2,
        8,
        18,
        2,
        2,
        2,
        8,
        0,
        18,
        2,
        2,
        2,
        8,
        0,
        19,
        2,
        2,
        2,
        2,
        19,
        19,
        34,
    ]
    for pc, opcode in enumerate(expected):
        word = u32(p + u32(p + 8) + pc * 4)
        need(word >> 26 == opcode, "SHBIN")
        descriptor = word & 127
        need(descriptor < 12, "SHBIN")
        desc = u32(p + u32(p + 16) + descriptor * 8)
        dest, index, src1, src2 = (
            (word >> 21) & 31,
            (word >> 19) & 3,
            (word >> 12) & 127,
            (word >> 7) & 31,
        )
        need(index == (1 if pc in (4, 5, 6, 9, 10, 11, 15, 16, 17) else 0), "SHBIN")
        if opcode not in (18, 34) and dest < 16:
            need(dest < 3, "SHBIN")
            for j in range(4):
                written[dest][j] += bool(desc & (8 >> j))
        instructions.append((opcode, dest, index, src1, src2, desc))
    need(written == [[1] * 4] * 3, "SHBIN")
    return instructions


def execute_binary32(program, prepared):
    """Instruction/dataflow check only; no claim about PICA rounding or timing."""
    inputs = prepared["attributes"]
    uniform = prepared["rows"] + [[0.0] * 4] * (90 - len(prepared["rows"]))
    uniform += [prepared["clip"][i : i + 4] for i in range(0, 16, 4)]
    uniform += [[0.0] * 4, [0.0, 1.0, 0.0, 0.0]]
    scratch, output, address = [[0.0] * 4 for _ in range(16)], [[0.0] * 4 for _ in range(3)], 0

    def read(reg, swizzle, sign, offset=0):
        if reg < 16:
            need(reg < 4 and not offset, "SHADER_READ")
            value = inputs[reg]
        elif reg < 32:
            need(not offset, "SHADER_READ")
            value = scratch[reg - 16]
        else:
            need(0 <= reg - 32 + offset < 96, "SHADER_READ")
            value = uniform[reg - 32 + offset]
        return [(-1 if sign else 1) * value[(swizzle >> (6 - 2 * j)) & 3] for j in range(4)]

    for op, dest, index, s1, s2, desc in program:
        if op == 34:
            break
        a = read(s1, (desc >> 5) & 255, desc & 16, address if index else 0)
        if op == 18:
            need(desc & 15 == 8 and a[0] == int(a[0]) and 0 <= a[0] <= 87, "SHADER_ADDRESS")
            address = int(a[0])
            continue
        b = read(s2, (desc >> 14) & 255, desc & 8192) if op != 19 else a
        if op == 2:
            total = f32(a[0] * b[0])
            for i in range(1, 4):
                total = f32(total + f32(a[i] * b[i]))
            value = [total] * 4
        elif op == 8:
            value = [f32(x * y) for x, y in zip(a, b, strict=True)]
        elif op == 0:
            value = [f32(x + y) for x, y in zip(a, b, strict=True)]
        else:
            value = a
        target = output[dest] if dest < 16 else scratch[dest - 16]
        for j in range(4):
            if desc & (8 >> j):
                target[j] = value[j]
    return output, scratch[4]


def projection_delta(expected, actual):
    need(all(math.isfinite(x) for x in expected + actual), "NUMBER")
    need(expected[3] >= 0.02 and actual[3] >= 0.02, "PROJECTABILITY")
    return [
        abs(expected[i] / expected[3] - actual[i] / actual[3]) * size / 2
        for i, size in enumerate((240, 400))
    ]
