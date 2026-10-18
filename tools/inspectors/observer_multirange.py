"""DA05-08: one state/slot, multiple AC ranges, existing isolated I/O ports."""

import hashlib
import re
import struct
import time
from dataclasses import dataclass, replace

from tools.inspectors.mapped_pause import identity, validate_pause
from tools.inspectors.observation_capture import ProfileError, require
from tools.inspectors.observer_acquisition import AcquisitionPlan, _identity, _memory, _pine
from tools.inspectors.observer_capture import decode_reply
from tools.inspectors.observer_series import SeriesPoint


@dataclass(frozen=True, repr=False)
class RegionPlan:
    label: str
    plan: AcquisitionPlan


def validate_regions(regions):
    require(
        type(regions) is tuple
        and 1 <= len(regions) <= 8
        and all(type(r) is RegionPlan and type(r.plan) is AcquisitionPlan for r in regions),
        "MULTI_PLAN",
    )
    require(
        all(type(r.label) is str and re.fullmatch(r"[a-z][a-z_]{0,23}", r.label) for r in regions)
        and len({r.label for r in regions}) == len(regions),
        "MULTI_LABELS",
    )
    for region in regions:
        region.plan.validate()
    first = regions[0].plan
    for i, region in enumerate(regions):
        plan = region.plan
        require(
            identity(plan) == identity(first)
            and plan.slot == first.slot
            and plan.request.expected_pc == first.request.expected_pc
            and plan.request.sequence == first.request.sequence + i,
            "MULTI_IDENTITY",
        )


def _collect(regions, channel, store, guard, *, timeout=30, clock=time.monotonic, wait=time.sleep):
    validate_regions(regions)
    require(type(timeout) in (int, float) and 0 < timeout <= 30, "MULTI_TIMEOUT")
    deadline = clock() + timeout

    def budget():
        remaining = deadline - clock()
        require(remaining > 0, "MULTI_DEADLINE")
        return remaining

    first = regions[0].plan
    contexts = [replace(r.plan.context, state_sha256="0" * 64) for r in regions]
    guarded = guard.check(first)
    budget()
    with store:
        store.absent(first.state_name)
        with channel:
            require(channel.peer_pid() == first.pid, "ACQUIRE_PEER")
            _identity(channel, first)

            def sample(index):
                budget()
                r = regions[index]
                packet = channel.exchange(r.plan.request.encode())
                obs = decode_reply(packet, r.plan.request, contexts[index])
                require((obs.pid, obs.game_crc) == (first.pid, first.crc), "MULTI_IDENTITY")
                return packet, obs

            a = [sample(i) for i in range(len(regions))]
            store.absent(first.state_name)
            _pine(channel, struct.pack("<BB", 9, first.slot), 0)
            for _ in range(256):
                try:
                    initial = sample(0)
                except ProfileError as error:
                    if error.code != "OBSERVER_SAVE_PENDING":
                        raise
                    wait(min(0.05, budget()))
                    continue
                break
            else:
                require(False, "MULTI_POLL_BUDGET")
            b = [initial, *(sample(i) for i in range(1, len(regions)))]
            require(a == b, "MULTI_CHANGED")
            raw, digest = store.read(first.state_name)
            require(
                type(raw) is bytes and hashlib.sha256(raw).hexdigest() == digest,
                "ACQUIRE_STATE_HASH",
            )
            for i, region in enumerate(regions):
                budget()
                require(_memory(channel, region.plan.request) == a[i][1].data, "ACQUIRE_MEMORY")
            _identity(channel, first)
            c = [sample(i) for i in range(len(regions))]
            require(a == c, "MULTI_CHANGED")
            current, current_digest = store.read(first.state_name)
            require(current == raw and current_digest == digest, "ACQUIRE_STATE_CHANGED")
            points = tuple(
                SeriesPoint(
                    r.label,
                    replace(r.plan, context=replace(r.plan.context, state_sha256=digest)),
                    raw,
                    (a[i][0], b[i][0], c[i][0]),
                )
                for i, r in enumerate(regions)
            )
            checked = validate_pause(points)
            budget()
            for point in points:
                for label, packet in zip(("a", "b", "c"), point.packets, strict=True):
                    request = point.plan.request
                    store.put(f"{request.session_id}-{request.sequence:03d}-{label}.bin", packet)
                    budget()
    require(guard.check(first) == guarded, "ACQUIRE_IDENTITY_CHANGED")
    budget()
    return {
        "schema_version": 1,
        "status": "consistent_supplied_multirange_acquisition",
        "state_sha256": digest,
        "saved_states": 1,
        "region_count": len(regions),
        "points": list(checked.metadata),
        "state_binding_verified": True,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "file_identity_verified": False,
        "disk_read_verified": False,
        "read_events_produced": 0,
        "resource_links": [],
        "capabilities": [],
    }


def collect_regions(*args, **kwargs):
    try:
        return _collect(*args, **kwargs)
    except OSError:
        raise ProfileError("MULTI_IO", "Multirange acquisition I/O failed") from None


def acquire_regions_and_publish(regions, channel, store, guard, output, *, publish, **kwargs):
    result = collect_regions(regions, channel, store, guard, **kwargs)
    publish(output, result)
    return result


def acquire_regions_local(regions, guard, repository, output):
    validate_regions(regions)
    from tools.inspectors.observer_files import PrivateAcquisitionStore, publish_acquisition
    from tools.inspectors.observer_transport import Session

    return acquire_regions_and_publish(
        regions,
        Session(str(guard.socket_path), timeout=30),
        PrivateAcquisitionStore(guard.state_root, repository),
        guard,
        output,
        publish=publish_acquisition,
    )
