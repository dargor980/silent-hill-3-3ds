"""Bounded low-32 GPR identity at modeled returns; never assumes an ABI or memory."""

import struct

from tools.inspectors.mips_flow import decode
from tools.pipeline.profile import ProfileError

MAX_STATES = 1024
MAX_DEPTH = 256


def apply_identity(identities: tuple, effect) -> tuple:
    """Only supported copies establish equality; an unknown value may still be equal."""
    values = list(identities)
    if effect.kind == "unknown":
        return (0,) + (None,) * 31
    if effect.destination:
        values[effect.destination] = values[effect.source] if effect.kind == "copy" else None
    return tuple(values)


def summarize_callee(data: bytes, start: int, register: int) -> dict:
    if (
        not isinstance(data, bytes)
        or not 4 <= len(data) <= 4096
        or len(data) % 4
        or type(start) is not int
        or not 0 <= start < (1 << 32)
        or start % 4
        or start + len(data) > (1 << 32)
        or type(register) is not int
        or not 0 <= register < 32
    ):
        raise ProfileError("BOUNDARY_WINDOW", "Invalid callee inspection window")
    words = dict(
        zip(
            range(start, start + len(data), 4),
            struct.unpack(f"<{len(data) // 4}I", data),
            strict=True,
        )
    )
    pending = [(start, tuple(range(32)), 0)]
    visited, boundaries, returns = set(), set(), set()

    def stop(kind, pc):
        boundaries.add((kind, pc))

    while pending:
        pc, values, depth = pending.pop()
        if len(visited) >= MAX_STATES or depth > MAX_DEPTH:
            stop("budget", pc)
            continue
        state = (pc, values)
        if state in visited:
            stop("revisited_state", pc)
            continue
        visited.add(state)
        if pc not in words:
            stop("outside_window", pc)
            continue
        word = words[pc]
        item = decode(word, pc)
        if item.effect.kind == "unknown":
            stop("unknown_effect", pc)
            continue
        if item.flow == "next":
            pending.append((pc + 4, apply_identity(values, item.effect), depth + 1))
            continue
        if pc + 4 not in words:
            stop("missing_delay_slot", pc)
            continue
        slot = decode(words[pc + 4], pc + 4)
        if item.flow == "branch" and item.likely:
            pending.append((pc + 8, values, depth + 1))
        if slot.flow != "next" or slot.effect.kind == "unknown":
            stop("unsupported_delay_slot", pc + 4)
            continue
        after = apply_identity(apply_identity(values, item.effect), slot.effect)
        if item.flow in ("call", "indirect_call"):
            stop("nested_call", pc)
        elif item.flow == "indirect":
            # JR reads its target before executing the delay slot. JALR is not a return.
            if word & 0xFC1FFFFF == 8 and (word >> 21) & 31 == 31 and values[31] == 31:
                returns.add((pc, after[register] == register))
            else:
                stop("unresolved_indirect", pc)
        else:
            pending.append((item.target, after, depth + 1))
            if item.flow == "branch" and not item.likely:
                pending.append((pc + 8, after, depth + 1))
    preserved = bool(returns) and not boundaries and all(value for _, value in returns)
    return {
        "register": register,
        "identity_scope": "low_32_bits",
        "effect": "preserved_in_model" if preserved else "unproven",
        "states": len(visited),
        "returns": [{"pc": pc, "identity_preserved": value} for pc, value in sorted(returns)],
        "boundaries": [{"kind": kind, "pc": pc} for kind, pc in sorted(boundaries)],
        "budget_exhausted": any(kind == "budget" for kind, _ in boundaries),
        "memory_identity": "not_modeled",
        "execution_reachability": "unproven",
    }
