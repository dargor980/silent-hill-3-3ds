"""Bounded syntactic references and backward GPR origins over a partial local graph."""

import hashlib
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass

from tools.inspectors.elf32 import MAX_ELF_BYTES, ElfMap, ReadRange, exact_read
from tools.inspectors.mips_flow import Effect, decode
from tools.pipeline.profile import ProfileError

MAX_SITES = 16
MAX_REFERENCES = 4096
MAX_EDGES = 2048
MAX_STATES = 2048
MAX_DEPTH = 512
Node = tuple[int, int]  # instruction address and delay-slot owner (-1 for ordinary context)


@dataclass(frozen=True)
class Edge:
    source: Node | None
    effects: tuple[tuple[int, Effect], ...] = ()
    external_pc: int | None = None


def references(read: ReadRange, mapping: ElfMap, windows: list[tuple[int, int]]) -> dict:
    segments = [s for s in mapping.segments if s.flags & 1 and s.file_size]
    if sum(s.file_size for s in segments) > MAX_ELF_BYTES:
        raise ProfileError("POINTER_BUDGET", "Reference scan exceeds byte budget")
    refs, counts = [], Counter()
    for segment in segments:
        if (segment.offset | segment.address | segment.file_size) & 3:
            raise ProfileError("POINTER_ALIGNMENT", "Unaligned reference segment")
        for offset in range(0, segment.file_size, 4096):
            data = exact_read(read, segment.offset + offset, min(4096, segment.file_size - offset))
            for index, (word,) in enumerate(struct.iter_unpack("<I", data)):
                pc = segment.address + offset + index * 4
                item = decode(word, pc)
                if item.flow in ("indirect", "indirect_call"):
                    counts["indirect_transfer_words"] += 1
                if item.target is None:
                    continue
                counts["direct_transfer_words"] += 1
                try:
                    target_offset = mapping.file_offset(item.target, 4, executable=True)
                except ProfileError:
                    counts["unbacked_direct_targets"] += 1
                    continue
                if any(start <= item.target < end for start, end in windows):
                    refs.append(
                        {
                            "pc": pc,
                            "target": item.target,
                            "target_offset": target_offset,
                            "kind": item.flow,
                            "likely": item.likely,
                            "state": "syntactic_reference",
                        }
                    )
                    if len(refs) > MAX_REFERENCES:
                        raise ProfileError("POINTER_BUDGET", "Too many selected references")
    return {"references": refs, "counts": dict(sorted(counts.items()))}


def local_graph(data: bytes, start: int, refs: list[dict]) -> tuple[dict, dict]:
    if (
        not isinstance(data, bytes)
        or not 4 <= len(data) <= 4096
        or len(data) % 4
        or type(start) is not int
        or start < 0
        or start % 4
        or start + len(data) > 1 << 32
    ):
        raise ProfileError("POINTER_WINDOW", "Invalid local graph window")
    end = start + len(data)
    instructions = {
        start + i * 4: decode(w, start + i * 4)
        for i, (w,) in enumerate(struct.iter_unpack("<I", data))
    }
    predecessors = defaultdict(list)
    count = 0
    unsupported_slots = 0
    delay_addresses = {pc + 4 for pc, item in instructions.items() if item.flow != "next"}
    direct_targets = {ref["target"] for ref in refs}
    direct_targets.update(i.target for i in instructions.values() if i.target is not None)

    def add(target: Node, edge: Edge) -> None:
        nonlocal count
        if not start <= target[0] < end:
            return
        count += 1
        if count > MAX_EDGES:
            raise ProfileError("POINTER_BUDGET", "Local graph exceeds edge budget")
        predecessors[target].append(edge)

    for pc, item in instructions.items():
        if pc in delay_addresses and pc not in direct_targets:
            continue  # A delay slot is not also an invented ordinary entry.
        node = (pc, -1)
        if item.flow == "next":
            add((pc + 4, -1), Edge(node, ((pc, item.effect),)))
            continue
        slot = instructions.get(pc + 4)
        if slot is None:
            continue
        slot_node = (pc + 4, pc)
        add(slot_node, Edge(node, ((pc, item.effect),)))
        if item.flow == "branch" and item.likely:
            add((pc + 8, -1), Edge(node))
        if slot.flow != "next":
            unsupported_slots += 1
            continue
        effects = ((pc + 4, slot.effect),)
        if item.flow in ("call", "indirect_call"):
            add((pc + 8, -1), Edge(slot_node, effects + ((pc, Effect("call")),)))
        elif item.flow in ("jump", "branch"):
            add((item.target, -1), Edge(slot_node, effects))
            if item.flow == "branch" and not item.likely:
                add((pc + 8, -1), Edge(slot_node, effects))
        # Indirect jumps have no invented continuation or destination.
    for ref in refs:
        if not start <= ref["pc"] < end and start <= ref["target"] < end:
            add((ref["target"], -1), Edge(None, external_pc=ref["pc"]))
    return predecessors, {
        "instruction_words": len(instructions),
        "edge_count": count,
        "unknown_effect_words": sum(i.effect.kind == "unknown" for i in instructions.values()),
        "unsupported_delay_slots": unsupported_slots,
        "scope": "partial_syntactic_graph",
        "function_boundaries": "not_inferred",
    }


def trace_origins(predecessors: dict, site: int, register: int) -> dict:
    pending = [((site, -1), register, False, 0)]
    visited, terminals = set(), set()
    budget_exhausted = False

    def terminal(kind, pc, reg, adjusted, source=0):
        terminals.add((kind, pc, reg, adjusted, source))

    while pending:
        node, reg, adjusted, depth = pending.pop()
        state = (node, reg, adjusted)
        if len(visited) >= MAX_STATES or depth > MAX_DEPTH:
            terminal("budget", node[0], reg, adjusted)
            budget_exhausted = True
            continue
        if reg == 0:
            terminal("zero_register", node[0], 0, adjusted)
            continue
        if state in visited:
            terminal("revisited_state", node[0], reg, adjusted)
            continue
        visited.add(state)
        edges = predecessors.get(node, [])
        if not edges:
            terminal("no_known_predecessor", node[0], reg, adjusted)
        for edge in edges:
            current, changed = reg, adjusted
            if edge.source is None:
                terminal("external_reference", edge.external_pc, current, changed)
                continue
            stopped = False
            for pc, effect in reversed(edge.effects):
                if not current:
                    break
                if effect.kind in ("unknown", "call"):
                    terminal(effect.kind, pc, current, changed)
                    stopped = True
                    break
                if effect.kind == "preserve" or effect.destination != current:
                    continue
                if effect.kind in ("copy", "adjust"):
                    current = effect.source
                    changed |= effect.kind == "adjust"
                else:
                    terminal(effect.kind, pc, current, changed, effect.source)
                    stopped = True
                    break
            if not stopped:
                pending.append((edge.source, current, changed, depth + 1))
    origins = [
        {"kind": k, "pc": p, "register": r, "arithmetic_seen": a, "source_register": s}
        for k, p, r, a, s in sorted(terminals)
    ]
    return {
        "state_count": len(visited),
        "budget_exhausted": budget_exhausted,
        "origins": origins,
        "resource_link": "unproven",
        "execution_reachability": "unproven",
        "analysis_completeness": "partial",
    }


def inspect_pointers(read: ReadRange, mapping: ElfMap, candidates: list[dict]) -> dict:
    if not 1 <= len(candidates) <= MAX_SITES:
        raise ProfileError("POINTER_BUDGET", "Expected a bounded nonempty site selection")
    windows = []
    for candidate in candidates:
        segment = next(s for s in mapping.segments if s.index == candidate["segment_index"])
        start = max(segment.address, candidate["branch_target_address"] - 512)
        end = candidate["virtual_address"] + candidate["window_size"]
        if end - start > 4096 or end <= start:
            raise ProfileError("POINTER_BUDGET", "Candidate window exceeds budget")
        mapping.file_offset(start, end - start, executable=True)
        windows.append((start, end))
    reference_scan = references(read, mapping, windows)
    sites = []
    for candidate, (start, end) in zip(candidates, windows, strict=True):
        offset = mapping.file_offset(start, end - start, executable=True)
        data = exact_read(read, offset, end - start)
        refs = [r for r in reference_scan["references"] if start <= r["target"] < end]
        graph, summary = local_graph(data, start, refs)
        pc = candidate["virtual_address"]
        first = struct.unpack_from("<I", data, pc - start)[0]
        register = (first >> 21) & 31
        origins = trace_origins(graph, pc, register)
        sites.append(
            {
                "site_address": pc,
                "base_register": register,
                "window": {
                    "start": start,
                    "end": end,
                    "file_offset": offset,
                    "sha256": hashlib.sha256(data).hexdigest(),
                },
                "references": refs,
                "graph": summary,
                "trace": origins,
            }
        )
    return {
        "method": "mips-pointer-origin-subset-v1",
        "sites": sites,
        "reference_scan": reference_scan["counts"],
        "site_count": len(sites),
        "confirmed_resource_links": 0,
        "interprocedural_depth": 0,
    }
