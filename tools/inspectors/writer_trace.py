"""RW03-RW08: streaming reconciliation of supplied AC points and SW effects."""

import hashlib
import struct

from tools.inspectors.observation_capture import require
from tools.inspectors.observer_acquisition import AcquisitionPlan
from tools.inspectors.observer_capture import decode_reply
from tools.inspectors.observer_series import SeriesPoint, _backing, _identity
from tools.inspectors.observer_state import MAX_ACQUISITION_INTERNALS, read_acquisition_state
from tools.inspectors.origin_compare import compare_ranges
from tools.inspectors.pcsx2_state import INTERNALS_MEMBER, read_state_members
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE
from tools.inspectors.store_pair import validate_sw
from tools.inspectors.writer_sites import discover_sites
from tools.inspectors.writer_state import WriterState

MAX_PAIRS = 48  # Entry + pairs + return fit distinct PINE slots 1..99.
MAX_ACTIVE_CYCLES = 60 * 294912000  # Pinned PCSX2 Common.h: PS2CLK.


def _read_point(point, start, code):
    require(type(point) is SeriesPoint and type(point.plan) is AcquisitionPlan, "TRACE_POINT")
    plan = point.plan
    plan.validate()
    require(
        type(point.state) is bytes
        and hashlib.sha256(point.state).hexdigest() == plan.context.state_sha256,
        "TRACE_STATE_HASH",
    )
    require(type(point.packets) is tuple and len(point.packets) == 3, "TRACE_PACKETS")
    observations = [decode_reply(p, plan.request, plan.context) for p in point.packets]
    observation = observations[0]
    require(observations[0] == observations[1] == observations[2], "TRACE_CHANGED")
    require((observation.pid, observation.game_crc) == (plan.pid, plan.crc), "TRACE_IDENTITY")
    state = read_acquisition_state(
        point.state, plan.crc, observation.mapping.physical_offset, plan.request.size
    )
    require(
        (state.cpu.pc, state.cycle, state.data)
        == (observation.pc, observation.cycle, observation.data),
        "TRACE_STATE",
    )
    internal, ram = read_state_members(
        point.state, ((INTERNALS_MEMBER, MAX_ACQUISITION_INTERNALS), (RAM_MEMBER, RAM_SIZE))
    )
    require(ram[start : start + len(code)] == code, "TRACE_CODE")
    offset = 333 + struct.unpack_from("<I", internal, 296)[0]
    low64 = tuple(struct.unpack_from("<Q", internal, offset + r * 16)[0] for r in range(32))
    return observation, WriterState(state.cpu, low64, state.data)


def reconcile_trace(points, code_start: int, code: bytes) -> dict:
    sites = {site.pc: site.code for site in discover_sites(code_start, code)}
    try:
        iterator = iter(points)
    except TypeError:
        require(False, "TRACE_POINTS")
    first = prior = entry = before = modeled = None
    slots, pairs, metadata = set(), [], []
    returned = False
    for index, point in enumerate(iterator):
        require(index < 2 + MAX_PAIRS * 2, "TRACE_BUDGET")
        require(not returned and type(point) is SeriesPoint, "TRACE_ORDER")
        observation, state = _read_point(point, code_start, code)
        plan = point.plan
        if first is None:
            first, anchor, entry, modeled = plan, _backing(observation), state, state.data
            first_cycle = observation.cycle
            require(point.label == "entry" and state.cpu.pc == code_start, "TRACE_ENTRY")
            require(state.cpu.gpr_low32[4] == plan.request.virtual_start, "TRACE_BASE")
        else:
            require(
                _identity(plan) == _identity(first)
                and plan.request.sequence == first.request.sequence + index,
                "TRACE_IDENTITY",
            )
            require(_backing(observation) == anchor, "TRACE_BACKING")
            require(observation.cycle > prior.cycle, "TRACE_CYCLE")
            require(observation.cycle - first_cycle <= MAX_ACTIVE_CYCLES, "TRACE_ACTIVE_BUDGET")
            if point.label == "returned":
                require(before is None and pairs, "TRACE_ORDER")
                require(state.cpu.pc == entry.cpu.gpr_low32[31], "TRACE_RETURN")
                require(state.data == modeled, "TRACE_RETURN_GAP")
                returned = True
            elif before is None:
                require(point.label == "before" and state.cpu.pc in sites, "TRACE_SITE")
                require(state.data == modeled, "TRACE_GAP")
                before = state
            else:
                require(point.label == "after", "TRACE_ORDER")
                instructions = sites[before.cpu.pc]
                pair = validate_sw(
                    before, state, first.request.virtual_start, instructions, instructions
                )
                relative = pair["relative_offset"]
                word = int.from_bytes(instructions[-4:], "little")
                register = (word >> 16) & 31
                value = (before.cpu.gpr_low32[register] if register else 0).to_bytes(4, "little")
                modeled = modeled[:relative] + value + modeled[relative + 4 :]
                pairs.append(
                    {
                        "before_sequence": plan.request.sequence - 1,
                        "after_sequence": plan.request.sequence,
                        **pair,
                    }
                )
                before = None
        require(plan.slot not in slots, "TRACE_SLOT")
        slots.add(plan.slot)
        prior = observation
        metadata.append(
            {
                "label": point.label,
                "sequence": plan.request.sequence,
                "state_sha256": plan.context.state_sha256,
                "packet_sha256": [hashlib.sha256(p).hexdigest() for p in point.packets],
                "content_sha256": hashlib.sha256(state.data).hexdigest(),
            }
        )
    require(returned, "TRACE_INCOMPLETE")
    return {
        "schema_version": 1,
        "status": "reconciled_supplied_write_effects",
        "session_id": first.context.session_id,
        "environment_sha256": first.context.environment_sha256,
        "process_sha256": first.context.process_sha256,
        "code_sha256": hashlib.sha256(code).hexdigest(),
        "content_size": len(modeled),
        "points": metadata,
        "pairs": pairs,
        "pair_count": len(pairs),
        "no_change_pairs": sum(p["comparison"]["equal"] for p in pairs),
        "backing_continuous": True,
        "matches_expected_backing": prior.mapping.matches_expected_backing,
        "entry_to_returned": compare_ranges(entry.data, modeled),
        "reconstructed_sha256": hashlib.sha256(modeled).hexdigest(),
        "unexplained_net_bytes": 0,
        "unobserved_transient_writes_excluded": False,
        "code_page_translation_verified": False,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "resource_links": [],
        "capabilities": [],
    }
