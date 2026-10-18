"""CP01-07: supplied dispatch, sector completion and copy consistency; no Read."""

import struct
from dataclasses import dataclass

from tools.inspectors.backend_completion import CompletionProfile, reconcile_backend_completion
from tools.inspectors.backend_completion import _inputs as completion_inputs
from tools.inspectors.driver_object import inspect_driver
from tools.inspectors.driver_transfer import DriverCode, DriverProfile
from tools.inspectors.driver_transfer import _inputs as transfer_inputs
from tools.inspectors.effective_mapping import integer
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observation_capture import require
from tools.inspectors.observer_series import _backing

OUTER = ("root", "pool", "object", "vtable", "dispatch", "reader", "destination", "args")
INNER = ("driver", "backend", "code", "copier", "args", "buffer", "destination", "return")


@dataclass(frozen=True, repr=False)
class CopyProfile:
    completion: CompletionProfile
    driver: DriverProfile
    copier: DriverCode
    reader_call_pc: int
    copy_call_pc: int


def _call(code, pc, target):
    integer(pc, code.address, code.address + len(code.data) - 12, "COPY_CALL")
    require(pc % 4 == 0, "COPY_CALL")
    call, delay = struct.unpack_from("<II", code.data, pc - code.address)
    require(
        call >> 26 == 3
        and ((pc + 4) & 0xF0000000) | ((call & 0x3FFFFFF) << 2) == target
        and delay == 0,
        "COPY_CALL",
    )


def _frame(code):
    word = struct.unpack_from("<I", code.data)[0]
    size = 65536 - (word & 65535)
    require(word >> 16 == 0x27BD and 16 <= size <= 4096 and size % 16 == 0, "COPY_FRAME")
    return size


def _inputs(source, request, profile, sector_sha256):
    require(type(profile) is CopyProfile, "COPY_INPUT")
    completion_inputs(source, request, profile.completion, sector_sha256)
    transfer_inputs(request, profile.driver)
    code = profile.copier
    require(type(code) is DriverCode, "COPY_CODE")
    integer(code.address, 4, 2**32 - 4096, "COPY_CODE")
    require(
        code.address % 4 == 0
        and type(code.data) is bytes
        and 8 <= len(code.data) <= 4096
        and len(code.data) % 4 == 0,
        "COPY_CODE",
    )
    caller = profile.completion.backend.caller
    _call(profile.driver.reader, profile.reader_call_pc, caller.address)
    _call(caller, profile.copy_call_pc, code.address)
    require(
        profile.copy_call_pc >= profile.completion.status_call_pc + 12
        and profile.reader_call_pc >= profile.driver.reader.address + 4,
        "COPY_CALL",
    )
    helper_frame = _frame(caller)
    require(helper_frame >= 112, "COPY_FRAME")
    return _frame(profile.driver.reader) + helper_frame


def _linked(pauses):
    require(len({p.slot for p in pauses}) == 7, "COPY_SLOTS")
    for before, after in zip(pauses[:-1], pauses[1:], strict=True):
        require(
            after.identity == before.identity and after.sequence == before.sequence + 8,
            "COPY_IDENTITY",
        )
        require(before.cycle < after.cycle <= pauses[0].cycle + MAX_CYCLES, "COPY_CYCLE")
    maps, seen, pages = [], {}, {}
    anchor = None
    for i, pause in enumerate(pauses):
        current_map = {}
        for label, r, o in pause.regions:
            label = "driver" if label == "object" else label
            label = "outer_args" if label == "args" and i in (0, 6) else label
            current_map[label] = (r, o)
            current = (o.before.ee_main, o.before.vmap, o.before.exposed_ram_size)
            anchor = current if anchor is None else anchor
            require(current == anchor, "COPY_BACKING")
            for page in o.before.pages:
                require(pages.get(page.virtual_page, page.bias) == page.bias, "COPY_PAGE")
                pages[page.virtual_page] = page.bias
            signature = (r.virtual_start, r.size, r.expected_offset, _backing(o))
            require(seen.get(label, signature) == signature, "COPY_BACKING")
            seen[label] = signature
        maps.append(current_map)
    return tuple(maps)


def reconcile_buffer_copy(source, request, profile, sector_sha256, stages):
    stack_delta = _inputs(source, request, profile, sector_sha256)
    require(type(stages) is tuple and len(stages) == 7, "COPY_STAGES")
    completion = reconcile_backend_completion(
        source, request, profile.completion, sector_sha256, stages[1:4]
    )
    pauses = tuple(validate_pause(points) for points in stages)
    require(
        all(tuple(r[0] for r in pauses[i].regions) == OUTER for i in (0, 6))
        and all(tuple(r[0] for r in pauses[i].regions) == INNER for i in (4, 5)),
        "COPY_REGIONS",
    )
    caller = profile.completion.backend.caller
    require(
        all(
            tuple(len(r[2].data) for r in pauses[i].regions)
            == (48, 56, len(caller.data), len(profile.copier.data), 52, 2048, source.size, 4)
            for i in (4, 5)
        ),
        "COPY_LAYOUT",
    )
    maps = _linked(pauses)
    first, last = maps[0], maps[6]
    for label in ("root", "pool", "vtable", "dispatch", "reader", "outer_args"):
        require(first[label][1].data == last[label][1].data, "COPY_OUTER_CHANGED")
    for label, code in (("dispatch", profile.driver.dispatch), ("reader", profile.driver.reader)):
        require(
            first[label][0].virtual_start == code.address and first[label][1].data == code.data,
            "COPY_CODE",
        )
    require(first["root"][0].virtual_start == profile.driver.root_address, "COPY_ROOT")
    views = tuple(
        inspect_driver(
            stages[i][:4], request.handle, source.file_size, pos, profile.driver.reader.address
        )
        for i, pos in ((0, source.offset), (6, source.offset + source.size))
    )
    original = views[0].words
    sector = source.offset // 2048
    for i, m in enumerate(maps):
        words = struct.unpack("<12I", m["driver"][1].data)
        require(
            all(words[j] == original[j] for j in range(12) if j not in (8, 11)),
            "COPY_DRIVER_CHANGED",
        )
        require(
            words[8] == source.offset + (source.size if i == 6 else 0)
            and words[11] == (original[11] if i < 4 else sector),
            "COPY_DRIVER_POSITION",
        )
    start, before, after, end = (pauses[i].cpu for i in (0, 4, 5, 6))
    require(
        (start.pc, before.pc, after.pc, end.pc)
        == (
            profile.driver.call_pc,
            profile.copy_call_pc,
            profile.copy_call_pc + 8,
            profile.driver.call_pc + 8,
        ),
        "COPY_PC",
    )
    g, h, j, k = (cpu.gpr_low32 for cpu in (start, before, after, end))
    require(
        g[29] == k[29] == h[29] + stack_delta
        and all(p.cpu.gpr_low32[29] == h[29] for p in pauses[1:6]),
        "COPY_STACK",
    )
    args = first["outer_args"]
    destination = first["destination"][0].virtual_start
    require(
        args[0].virtual_start == g[29] + 48
        and len(args[1].data) == 36
        and first["destination"][0].size == source.size
        and g[29] % 16 == 0
        and 0 < destination <= 2**32 - source.size,
        "COPY_OUTER_ARGS",
    )
    require(
        tuple(struct.unpack_from("<I", args[1].data, at)[0] for at in (0, 16, 32))
        == (request.handle, destination, source.size),
        "COPY_OUTER_ARGS",
    )
    require(
        g[16] == k[16] == first["driver"][0].virtual_start
        and g[4] == g[16]
        and g[2] == profile.driver.reader.address
        and g[5] == destination
        and g[6] == source.size
        and k[31] == end.pc
        and k[2] == source.size,
        "COPY_OUTER_ABI",
    )
    for label in ("backend", "code", "args", "buffer"):
        require(
            maps[3][label][1].data == maps[4][label][1].data == maps[5][label][1].data,
            "COPY_INNER_CHANGED",
        )
    for label in ("copier", "return"):
        require(maps[4][label][1].data == maps[5][label][1].data, "COPY_INNER_CHANGED")
    require(
        maps[4]["copier"][0].virtual_start == profile.copier.address
        and maps[4]["copier"][1].data == profile.copier.data,
        "COPY_CODE",
    )
    require(
        maps[4]["return"][0].virtual_start == h[29] + 32
        and struct.unpack("<I", maps[4]["return"][1].data)[0] == profile.reader_call_pc + 8,
        "COPY_PARENT",
    )
    inner_destination = struct.unpack_from("<I", maps[4]["args"][1].data, 16)[0]
    require(
        inner_destination == destination
        and h[4] == destination
        and h[5] == original[10] + source.offset % 2048
        and h[6] == source.size
        and h[17] == j[17] == source.size
        and j[31] == after.pc
        and j[2] == destination,
        "COPY_ABI",
    )
    offset = source.offset % 2048
    payload = maps[4]["buffer"][1].data[offset : offset + source.size]
    require(
        first["destination"][1].data == maps[4]["destination"][1].data
        and maps[5]["destination"][1].data == last["destination"][1].data == payload,
        "COPY_PAYLOAD",
    )
    for target_label, target in (
        ("destination", first["destination"][1]),
        ("buffer", maps[3]["buffer"][1]),
    ):
        at = target.mapping.physical_offset
        for m in maps:
            for label, (_, obs) in m.items():
                if label != target_label:
                    other = obs.mapping.physical_offset
                    require(
                        at + len(target.data) <= other or other + len(obs.data) <= at,
                        "COPY_OVERLAP",
                    )
    return {
        **completion,
        "status": "consistent_supplied_completion_copy_and_driver_return",
        "points": [m for p in pauses for m in p.metadata],
        "copy_and_driver_return_consistent": True,
        "driver_generation_matches_at_endpoints": True,
        "destination_preexisting": first["destination"][1].data == payload,
        "writes_outside_destination_verified": False,
        "load_provenance": "pending_joint_opening_lifetime_guarded_capture",
    }
