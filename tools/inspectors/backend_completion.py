"""BC01-06: supplied sector completion and buffer consistency, without I/O proof."""

import hashlib
import struct
from dataclasses import dataclass

from tools.inspectors.backend_sector import BackendProfile, reconcile_backend_sector
from tools.inspectors.backend_sector import _inputs as backend_inputs
from tools.inspectors.effective_mapping import integer
from tools.inspectors.load_lineage import MAX_CYCLES, _hash
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observation_capture import require
from tools.inspectors.observer_series import _backing


@dataclass(frozen=True, repr=False)
class CompletionProfile:
    backend: BackendProfile
    status_call_pc: int
    status_target: int


def _inputs(source, request, profile, sector_sha256):
    require(type(profile) is CompletionProfile, "COMPLETION_INPUT")
    backend_inputs(source, request, profile.backend)
    require(_hash(sector_sha256), "COMPLETION_HASH")
    caller = profile.backend.caller
    integer(profile.status_target, 4, 2**32 - 4, "COMPLETION_CALL")
    integer(
        profile.status_call_pc,
        caller.address,
        caller.address + len(caller.data) - 12,
        "COMPLETION_CALL",
    )
    require(
        profile.status_call_pc % 4 == profile.status_target % 4 == 0
        and abs(profile.status_call_pc - profile.backend.call_pc) >= 12
        and profile.backend.call_pc + 8 < caller.address + len(caller.data)
        and profile.status_target != profile.backend.read_target,
        "COMPLETION_CALL",
    )
    call, delay = struct.unpack_from("<II", caller.data, profile.status_call_pc - caller.address)
    require(
        call >> 26 == 3
        and ((profile.status_call_pc + 4) & 0xF0000000) | ((call & 0x3FFFFFF) << 2)
        == profile.status_target
        and delay == 0,
        "COMPLETION_CALL",
    )


def _linked_pauses(pauses):
    first = pauses[0]
    require(len({p.slot for p in pauses}) == 3, "COMPLETION_SLOTS")
    for before, after in zip(pauses[:-1], pauses[1:], strict=True):
        require(
            before.identity == after.identity and after.sequence == before.sequence + 8,
            "COMPLETION_IDENTITY",
        )
        require(before.cycle < after.cycle <= first.cycle + MAX_CYCLES, "COMPLETION_CYCLE")
    maps = tuple({label: (r, o) for label, r, o in p.regions} for p in pauses)
    pages, anchor = {}, None
    for regions in maps:
        for _, obs in regions.values():
            current = (obs.before.ee_main, obs.before.vmap, obs.before.exposed_ram_size)
            anchor = current if anchor is None else anchor
            require(current == anchor, "COMPLETION_BACKING")
            for page in obs.before.pages:
                require(pages.get(page.virtual_page, page.bias) == page.bias, "COMPLETION_PAGE")
                pages[page.virtual_page] = page.bias
    for before, after in zip(maps[:-1], maps[1:], strict=True):
        for label in before.keys() & after.keys():
            ar, ao = before[label]
            br, bo = after[label]
            require(
                (ar.virtual_start, ar.size, ar.expected_offset)
                == (br.virtual_start, br.size, br.expected_offset)
                and _backing(ao) == _backing(bo),
                "COMPLETION_BACKING",
            )
    return maps


def reconcile_backend_completion(source, request, profile, sector_sha256, stages):
    _inputs(source, request, profile, sector_sha256)
    require(type(stages) is tuple and len(stages) == 3, "COMPLETION_STAGES")
    initial = reconcile_backend_sector(source, request, profile.backend, stages[0])
    pauses = tuple(validate_pause(points) for points in stages)
    a, b, c = pauses
    labels = ("driver", "backend", "stream", "file", "disc", "code", "args", "buffer")
    require(all(tuple(r[0] for r in p.regions) == labels for p in (b, c)), "COMPLETION_REGIONS")
    require(
        all(
            tuple(len(o.data) for _, _, o in p.regions)
            == (48, 56, 72, 8, 72, len(profile.backend.caller.data), 52, 2048)
            for p in (b, c)
        ),
        "COMPLETION_LAYOUT",
    )
    maps = _linked_pauses(pauses)
    x, y, z = maps
    for label in ("driver", "file", "code", "args"):
        require(x[label][1].data == y[label][1].data == z[label][1].data, "COMPLETION_CHANGED")
    require(
        (b.cpu.pc, c.cpu.pc) == (profile.backend.call_pc + 8, profile.status_call_pc + 8),
        "COMPLETION_PC",
    )
    require(
        a.cpu.gpr_low32[29] == b.cpu.gpr_low32[29] == c.cpu.gpr_low32[29]
        and b.cpu.gpr_low32[31] == b.cpu.pc
        and c.cpu.gpr_low32[31] == c.cpu.pc,
        "COMPLETION_ABI",
    )
    require(b.cpu.gpr_low32[2] == 1 and c.cpu.gpr_low32[2] == 3, "COMPLETION_RESULT")
    rows = tuple(
        {
            label: struct.unpack("<" + str(len(o.data) // 4) + "I", o.data)
            for label, (_, o) in m.items()
            if label in ("driver", "backend", "stream", "disc")
        }
        for m in maps
    )
    sector = source.offset // 2048
    buffer = rows[0]["driver"][10]
    require(rows[0]["backend"][2] == 0, "COMPLETION_ADMISSION")
    for i, m in enumerate(maps[1:], 1):
        backend, stream, disc = (rows[i][label] for label in ("backend", "stream", "disc"))
        flags = tuple(m[label][1].data[:4] for label in ("backend", "stream", "disc"))
        require(flags[0] == bytes((1, i + 1, 0, 0)), "COMPLETION_STATE")
        require(flags[1] == bytes((1, i + 1, 0, 0)) and stream[17] == 0, "COMPLETION_STREAM")
        require(
            all(backend[j] == rows[0]["backend"][j] for j in (1, 3, 4, 11, 12, 13))
            and stream[2] == rows[0]["stream"][2]
            and all(disc[j] == rows[0]["disc"][j] for j in (1, 2, *range(8, 18)))
            and flags[2][0:2] == x["disc"][1].data[0:2]
            and flags[2][3] == x["disc"][1].data[3],
            "COMPLETION_CHAIN",
        )
        require(
            backend[5:11] == (sector + i - 1, sector, 1, i - 1, buffer, 2048),
            "COMPLETION_PROGRESS",
        )
        require(
            stream[3:6] == (0, sector, 2048) and stream[12] == 1 and stream[13] == (i - 1) * 2048,
            "COMPLETION_STREAM_PROGRESS",
        )
        require(m["buffer"][0].virtual_start == buffer, "COMPLETION_BUFFER")
        start = m["buffer"][1].mapping.physical_offset
        controls = [o for regions in maps for label, (_, o) in regions.items() if label != "buffer"]
        for other in controls:
            at = other.mapping.physical_offset
            require(start + 2048 <= at or at + len(other.data) <= start, "COMPLETION_OVERLAP")
    submitted, completed = rows[1], rows[2]
    require(
        submitted["backend"][2] >= 4
        and submitted["backend"][2] % 4 == 0
        and submitted["stream"][1] == submitted["backend"][2]
        and completed["backend"][2] == 0
        and completed["stream"][1] == submitted["stream"][1],
        "COMPLETION_WRAPPER",
    )
    require(
        y["disc"][1].data[2] in (0, 1)
        and submitted["disc"][3] == sector
        and submitted["disc"][7] == 0
        and z["disc"][1].data[2] == 1
        and completed["disc"][3:8] == (sector + 1, 1, 1, buffer, 0)
        and completed["stream"][8] == 1,
        "COMPLETION_DISC",
    )
    valid_size = min(2048, source.file_size - sector * 2048)
    data = z["buffer"][1].data
    require(hashlib.sha256(data[:valid_size]).hexdigest() == sector_sha256, "COMPLETION_SECTOR")
    offset = source.offset % 2048
    require(
        hashlib.sha256(data[offset : offset + source.size]).hexdigest() == source.resource_sha256,
        "COMPLETION_RESOURCE",
    )
    return {
        **initial,
        "status": "consistent_supplied_backend_completion_and_buffer",
        "points": [m for p in pauses for m in p.metadata],
        "completed_sectors": 1,
        "valid_sector_size": valid_size,
        "valid_sector_sha256": sector_sha256,
        "completion_and_buffer_consistent": True,
        "buffer_preexisting_at_submission": y["buffer"][1].data[:valid_size] == data[:valid_size],
        "buffer_fill_verified": False,
        "inner_copy_verified": False,
        "load_provenance": "pending_copy_joint_profile_continuity_and_live_capture",
    }
