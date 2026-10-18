"""LF02-03: supplied multi-range AC/MP evidence bound to one paused state."""

import hashlib
import re
from dataclasses import dataclass

from tools.inspectors.observation_capture import require
from tools.inspectors.observer_acquisition import AcquisitionPlan
from tools.inspectors.observer_capture import decode_reply
from tools.inspectors.observer_series import SeriesPoint
from tools.inspectors.observer_state import read_acquisition_state
from tools.inspectors.pcsx2_state import EEState, read_state_members
from tools.inspectors.state_memory import RAM_MEMBER, RAM_SIZE


@dataclass(frozen=True, repr=False)
class MappedPause:
    cpu: EEState
    cycle: int
    identity: tuple
    slot: int
    sequence: int
    regions: tuple
    metadata: tuple


def identity(plan):
    return (
        plan.context.session_id,
        plan.context.environment_sha256,
        plan.context.process_sha256,
        plan.pid,
        plan.crc,
        plan.serial,
    )


def validate_pause(points) -> MappedPause:
    require(
        type(points) is tuple
        and 1 <= len(points) <= 8
        and all(type(p) is SeriesPoint and type(p.plan) is AcquisitionPlan for p in points),
        "PAUSE_POINTS",
    )
    require(
        all(type(p.label) is str and re.fullmatch(r"[a-z][a-z_]{0,23}", p.label) for p in points)
        and len({p.label for p in points}) == len(points),
        "PAUSE_LABELS",
    )
    for point in points:
        point.plan.validate()
    first = points[0].plan
    raw = points[0].state
    require(type(raw) is bytes, "PAUSE_STATE")
    digest = hashlib.sha256(raw).hexdigest()
    regions, metadata, pages = [], [], {}
    cpu_state = anchor = None
    for index, point in enumerate(points):
        plan = point.plan
        require(
            identity(plan) == identity(first)
            and plan.slot == first.slot
            and plan.request.sequence == first.request.sequence + index,
            "PAUSE_IDENTITY",
        )
        require(
            type(point.state) is bytes
            and point.state == raw
            and plan.context.state_sha256 == digest,
            "PAUSE_STATE_HASH",
        )
        require(type(point.packets) is tuple and len(point.packets) == 3, "PAUSE_PACKETS")
        samples = [decode_reply(p, plan.request, plan.context) for p in point.packets]
        obs = samples[0]
        require(samples[0] == samples[1] == samples[2], "PAUSE_CHANGED")
        require((obs.pid, obs.game_crc) == (plan.pid, plan.crc), "PAUSE_IDENTITY")
        require(obs.mapping.matches_expected_backing, "PAUSE_EXPECTED_BACKING")
        current = (obs.before.ee_main, obs.before.vmap, obs.before.exposed_ram_size)
        if cpu_state is None:
            cpu_state = read_acquisition_state(
                raw, plan.crc, obs.mapping.physical_offset, plan.request.size
            )
            (ram,) = read_state_members(raw, ((RAM_MEMBER, RAM_SIZE),))
            anchor = current
        require(current == anchor, "PAUSE_BACKING")
        require((obs.pc, obs.cycle) == (cpu_state.cpu.pc, cpu_state.cycle), "PAUSE_CPU")
        offset = obs.mapping.physical_offset
        require(obs.data == ram[offset : offset + plan.request.size], "PAUSE_DATA")
        for page in obs.before.pages:
            require(pages.get(page.virtual_page, page.bias) == page.bias, "PAUSE_PAGE")
            pages[page.virtual_page] = page.bias
        regions.append((point.label, plan.request, obs))
        metadata.append(
            {
                "label": point.label,
                "sequence": plan.request.sequence,
                "state_sha256": digest,
                "packet_sha256": [hashlib.sha256(p).hexdigest() for p in point.packets],
                "content_sha256": hashlib.sha256(obs.data).hexdigest(),
                "size": len(obs.data),
                "pages": obs.mapping.page_count,
            }
        )
    return MappedPause(
        cpu_state.cpu,
        cpu_state.cycle,
        identity(first),
        first.slot,
        first.request.sequence,
        tuple(regions),
        tuple(metadata),
    )
