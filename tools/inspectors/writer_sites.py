"""RW01/02: bounded static pause-site discovery; no branch-condition inference."""

import hashlib
from dataclasses import dataclass

from tools.inspectors.mips_flow import decode
from tools.inspectors.observation_capture import require

STORE_OPS = frozenset((31, 40, 41, 42, 43, 44, 45, 46, 57, 63))


@dataclass(frozen=True, repr=False)
class WriteSite:
    pc: int
    code: bytes


def discover_sites(start: int, code: bytes) -> tuple[WriteSite, ...]:
    require(
        type(start) is int
        and start % 4 == 0
        and 0x100000 <= start < 0x2000000
        and type(code) is bytes
        and 8 <= len(code) <= 4096
        and len(code) % 4 == 0
        and start + len(code) <= 0x2000000,
        "WRITES_CODE_RANGE",
    )
    end = start + len(code)
    words = {start + i: int.from_bytes(code[i : i + 4], "little") for i in range(0, len(code), 4)}
    instructions = {pc: decode(word, pc) for pc, word in words.items()}
    require(words[end - 8] == 0x03E00008 and words[end - 4] == 0, "WRITES_RETURN")
    slots = set()
    for pc, instruction in instructions.items():
        require(instruction.effect.kind != "unknown", "WRITES_UNSUPPORTED")
        require(words[pc] >> 26 not in STORE_OPS - {43}, "WRITES_UNSUPPORTED")
        require(instruction.flow in ("next", "branch", "indirect"), "WRITES_FLOW")
        if instruction.flow == "indirect":
            require(pc == end - 8 and words[pc] == 0x03E00008, "WRITES_RETURN")
        if instruction.flow != "next":
            require(pc + 4 in words and instructions[pc + 4].flow == "next", "WRITES_SLOT")
            slots.add(pc + 4)
            if words[pc + 4] >> 26 == 43:
                require(words[pc] >> 26 == 4, "WRITES_SLOT")
        if instruction.flow == "branch":
            require(not instruction.likely and instruction.target in words, "WRITES_TARGET")
    require(
        all(i.target not in slots for i in instructions.values() if i.flow == "branch"),
        "WRITES_SLOT_TARGET",
    )
    pending, visited, sites = [start], set(), []
    returned = False
    while pending:
        pc = pending.pop()
        if pc in visited:
            continue
        require(pc in words and pc not in slots, "WRITES_FLOW")
        visited.add(pc)
        instruction, word = instructions[pc], words[pc]
        if word >> 26 == 43:
            sites.append(WriteSite(pc, code[pc - start : pc - start + 4]))
        if instruction.flow == "next":
            pending.append(pc + 4)
        elif instruction.flow == "indirect":
            returned = True
        else:
            if words[pc + 4] >> 26 == 43:
                sites.append(WriteSite(pc, code[pc - start : pc - start + 8]))
            pending.append(instruction.target)
            unconditional = word >> 26 == 4 and (word >> 21) & 31 == (word >> 16) & 31
            if not unconditional:
                pending.append(pc + 8)
    require(returned and sites, "WRITES_NO_PATH")
    return tuple(sorted(sites, key=lambda site: site.pc))


def site_metadata(start: int, code: bytes) -> dict:
    sites = discover_sites(start, code)
    return {
        "status": "static_write_sites_not_execution",
        "code_sha256": hashlib.sha256(code).hexdigest(),
        "code_size": len(code),
        "site_count": len(sites),
        "direct_count": sum(len(site.code) == 4 for site in sites),
        "delay_pair_count": sum(len(site.code) == 8 for site in sites),
        "instruction_sha256": [hashlib.sha256(site.code).hexdigest() for site in sites],
    }
