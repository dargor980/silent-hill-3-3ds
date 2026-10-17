"""Inspect one call boundary with separate argument, return and callee hypotheses."""

import hashlib
import struct

from tools.inspectors.callee_flow import summarize_callee
from tools.inspectors.elf32 import ElfMap, ReadRange, exact_read
from tools.inspectors.mips_flow import decode
from tools.inspectors.pointer_graph import Edge, local_graph, references, trace_origins
from tools.pipeline.profile import ProfileError

MAX_BOUNDARIES = 16


def read_window(read: ReadRange, mapping: ElfMap, start: int, end: int) -> tuple[bytes, dict]:
    offset = mapping.file_offset(start, end - start, executable=True)
    data = exact_read(read, offset, end - start)
    return data, {
        "start": start,
        "end": end,
        "file_offset": offset,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def backed_segment(mapping: ElfMap, pc: int):
    mapping.file_offset(pc, 4, executable=True)
    return next(s for s in mapping.segments if s.address <= pc < s.address + s.file_size)


def inspect_boundaries(read: ReadRange, mapping: ElfMap, sites: list[dict]) -> dict:
    selected = {}
    for site in sites:
        for origin in site["trace"]["origins"]:
            if origin["kind"] not in ("external_reference", "call"):
                continue
            key = (site["site_address"], origin["kind"], origin["pc"], origin["register"])
            selected.setdefault(key, set()).add(origin["arithmetic_seen"])
    if len(selected) > MAX_BOUNDARIES:
        raise ProfileError("BOUNDARY_BUDGET", "Too many call boundaries")
    windows = []
    for _, _, pc, _ in sorted(selected):
        segment = backed_segment(mapping, pc)
        windows.append((max(segment.address, pc - 512), pc + 12))
    scan = references(read, mapping, windows) if windows else {"references": [], "counts": {}}
    results = []
    for key, (start, end) in zip(sorted(selected), windows, strict=True):
        site, kind, pc, register = key
        data, window = read_window(read, mapping, start, end)
        word, delay_word = struct.unpack_from("<II", data, pc - start)
        call, slot = decode(word, pc), decode(delay_word, pc + 4)
        base = {
            "site_address": site,
            "origin_kind": kind,
            "call_pc": pc,
            "register": register,
            "arithmetic_states": sorted(selected[key]),
            "caller_window": window,
            "resource_link": "unproven",
        }
        if call.flow != "call":
            results.append({**base, "status": "unsupported_transfer"})
            continue
        segment = backed_segment(mapping, call.target)
        callee_data, callee_window = read_window(
            read, mapping, call.target, min(call.target + 4096, segment.address + segment.file_size)
        )
        refs = [r for r in scan["references"] if start <= r["target"] < end]
        graph, graph_summary = local_graph(data, start, refs)
        before = trace_origins(graph, pc, register)
        after_return = trace_origins(graph, pc + 8, register)
        entry = None
        if slot.flow == "next":
            # Private query endpoint: PC+8 denotes after-slot state only in this copied graph.
            entry_graph = dict(graph)
            entry_graph[(pc + 8, -1)] = [Edge((pc, -1), ((pc, call.effect), (pc + 4, slot.effect)))]
            entry = trace_origins(entry_graph, pc + 8, register)
        callee = summarize_callee(callee_data, call.target, register)
        watched = {register, 31}
        if slot.effect.kind in ("copy", "adjust"):
            watched.add(slot.effect.source)
        if entry is not None:
            for origin in entry["origins"]:
                watched.update((origin["register"], origin["source_register"]))
        registers = sorted(watched - {0})
        results.append(
            {
                **base,
                "status": "analyzed" if entry is not None else "unsupported_delay_slot",
                "target": call.target,
                "caller_graph": graph_summary,
                "caller_references": refs,
                "before_call": before,
                "entry_after_slot": entry,
                "after_return_hypothesis": after_return,
                "callee_window": callee_window,
                "callee": callee,
                "capture_plan": {
                    "status": "not_performed",
                    "executable_identity": "report.executable.sha256",
                    "code_ranges": [window, callee_window],
                    "points": [
                        {"pc": pc, "phase": "before_call", "registers": registers},
                        {
                            "pc": call.target,
                            "phase": "entry_after_slot",
                            "registers": registers,
                        },
                        {"pc": pc + 8, "phase": "return_if_reached", "registers": registers},
                    ],
                    "unresolved_code_points": callee["boundaries"],
                    "data_range": "derive_from_observed_pointer_and_verified_catalog",
                    "expected_resource_sha256": None,
                    "resource_identity": "unknown_do_not_invent_expected_payload",
                },
            }
        )
    return {
        "method": "mips-call-boundary-subset-v1",
        "boundaries": results,
        "reference_scan": scan["counts"],
        "interprocedural_depth": 1,
        "confirmed_resource_links": 0,
        "function_boundaries": "not_inferred",
    }
