"""OS01-OS05: pure four-stop consistency; acquisition and custody are external."""

import hashlib
from dataclasses import dataclass

from tools.inspectors.observation_capture import require
from tools.inspectors.observer_acquisition import AcquisitionPlan
from tools.inspectors.observer_capture import decode_reply
from tools.inspectors.observer_state import read_acquisition_state
from tools.inspectors.origin_compare import compare_ranges

LABELS = ("entry", "before", "after", "returned")


@dataclass(frozen=True, repr=False)
class SeriesPoint:
    label: str
    plan: AcquisitionPlan
    state: bytes
    packets: tuple[bytes, ...]


def _identity(plan):
    request, context = plan.request, plan.context
    return (
        context.session_id,
        context.environment_sha256,
        context.process_sha256,
        plan.pid,
        plan.crc,
        plan.serial,
        request.virtual_start,
        request.size,
        request.expected_offset,
    )


def _backing(observation):
    snapshot = observation.before
    return (
        snapshot.ee_main,
        snapshot.vmap,
        snapshot.exposed_ram_size,
        snapshot.pages,
        observation.mapping,
    )


def validate_series(points):
    require(
        type(points) is tuple
        and len(points) == 4
        and all(type(p) is SeriesPoint and type(p.plan) is AcquisitionPlan for p in points),
        "SERIES_POINTS",
    )
    require(tuple(p.label for p in points) == LABELS, "SERIES_ORDER")
    for point in points:
        point.plan.validate()
    first = points[0].plan
    require(
        all(_identity(p.plan) == _identity(first) for p in points)
        and [p.plan.request.sequence for p in points]
        == list(range(first.request.sequence, first.request.sequence + 4))
        and len({p.plan.slot for p in points}) == 4,
        "SERIES_IDENTITY",
    )
    observations, states, metadata = [], [], []
    for point in points:
        plan = point.plan
        require(type(point.state) is bytes, "SERIES_STATE")
        require(
            hashlib.sha256(point.state).hexdigest() == plan.context.state_sha256,
            "SERIES_STATE_HASH",
        )
        require(type(point.packets) is tuple and len(point.packets) == 3, "SERIES_PACKETS")
        samples = [decode_reply(packet, plan.request, plan.context) for packet in point.packets]
        observation = samples[0]
        require(samples[0] == samples[1] == samples[2], "SERIES_CHANGED")
        require((observation.pid, observation.game_crc) == (plan.pid, plan.crc), "SERIES_IDENTITY")
        state = read_acquisition_state(
            point.state, plan.crc, observation.mapping.physical_offset, plan.request.size
        )
        require(
            (state.cpu.pc, state.cycle, state.data)
            == (observation.pc, observation.cycle, observation.data),
            "SERIES_STATE",
        )
        observations.append(observation)
        states.append(state)
        metadata.append(
            {
                "label": point.label,
                "sequence": plan.request.sequence,
                "state_sha256": plan.context.state_sha256,
                "packet_sha256": [hashlib.sha256(p).hexdigest() for p in point.packets],
                "content_sha256": hashlib.sha256(state.data).hexdigest(),
            }
        )
    require(all(_backing(o) == _backing(observations[0]) for o in observations), "SERIES_BACKING")
    require(
        all(a.cycle < b.cycle for a, b in zip(observations[:-1], observations[1:], strict=True)),
        "SERIES_CYCLE",
    )
    require(states[0].cpu.gpr_low32[4] == first.request.virtual_start, "SERIES_BASE")
    require(states[-1].cpu.pc == states[0].cpu.gpr_low32[31], "SERIES_RETURN")
    return {
        "schema_version": 1,
        "status": "consistent_supplied_four_stop_series",
        "session_id": first.context.session_id,
        "environment_sha256": first.context.environment_sha256,
        "process_sha256": first.context.process_sha256,
        "content_size": first.request.size,
        "points": metadata,
        "backing_continuous": True,
        "matches_expected_backing": observations[0].mapping.matches_expected_backing,
        "entry_to_before": compare_ranges(states[0].data, states[1].data),
        "before_to_after": compare_ranges(states[1].data, states[2].data),
        "entry_to_returned": compare_ranges(states[0].data, states[3].data),
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "resource_links": [],
        "capabilities": [],
    }
