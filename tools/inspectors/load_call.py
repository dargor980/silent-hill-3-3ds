"""LF04-07: bounded call/return evidence, deliberately no file/read attribution."""

import hashlib
import struct

from tools.inspectors.effective_mapping import integer
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observation_capture import require
from tools.inspectors.observer_series import _backing


def validate_call(before, after, site: int, code: bytes, target: int) -> dict:
    integer(site, 0, 2**32 - 12, "CALL_SITE")
    integer(target, 0, 2**32 - 1, "CALL_TARGET")
    require(site % 4 == target % 4 == 0, "CALL_ALIGNMENT")
    require(type(code) is bytes and len(code) == 12, "CALL_CODE")
    call, delay = struct.unpack_from("<II", code)
    require(
        call >> 26 == 3 and ((site + 4) & 0xF0000000) | ((call & 0x3FFFFFF) << 2) == target,
        "CALL_OPCODE",
    )
    # Only the observed DADDU a2,rs,zero family. JAL changes RA before the slot.
    source = (delay >> 21) & 31
    require(delay == 0 or (source != 31 and delay == (source << 21 | 6 << 11 | 0x2D)), "CALL_DELAY")
    a, b = validate_pause(before), validate_pause(after)
    require(
        tuple(r[0] for r in a.regions) == tuple(r[0] for r in b.regions) == ("code", "destination"),
        "CALL_REGIONS",
    )
    require(a.identity == b.identity and b.sequence == a.sequence + 2, "CALL_IDENTITY")
    require(a.slot != b.slot, "CALL_SLOT")
    require(a.cycle < b.cycle <= a.cycle + MAX_CYCLES, "CALL_CYCLE")
    require((a.cpu.pc, b.cpu.pc) == (site, site + 8), "CALL_PC")
    require(
        a.cpu.gpr_low32[29] == b.cpu.gpr_low32[29] and b.cpu.gpr_low32[31] == site + 8,
        "CALL_FRAME",
    )
    for (_, ar, ao), (_, br, bo) in zip(a.regions, b.regions, strict=True):
        require(
            (ar.virtual_start, ar.size, ar.expected_offset)
            == (br.virtual_start, br.size, br.expected_offset)
            and _backing(ao) == _backing(bo),
            "CALL_BACKING",
        )
    require(
        all(p.regions[0][1].virtual_start == site and p.regions[0][2].data == code for p in (a, b)),
        "CALL_CODE",
    )
    request = a.regions[1][1]
    size = a.cpu.gpr_low32[6 if delay == 0 else source] if source or delay == 0 else 0
    require(a.cpu.gpr_low32[5] == request.virtual_start and size == request.size, "CALL_ARGUMENTS")
    require(b.cpu.gpr_low32[2] == size, "CALL_SHORT_OR_ERROR")
    return {
        "schema_version": 1,
        "status": "consistent_supplied_call_transfer",
        "requested_size": size,
        "returned_size": size,
        "code_sha256": hashlib.sha256(code).hexdigest(),
        "destination_sha256": hashlib.sha256(b.regions[1][2].data).hexdigest(),
        "destination_unchanged": a.regions[1][2].data == b.regions[1][2].data,
        "points": [*a.metadata, *b.metadata],
        "code_and_destination_maps_checked": True,
        "mapping_scope": "two_supplied_pauses_not_all_instants",
        "callee_execution_verified": False,
        "file_identity_verified": False,
        "disk_read_verified": False,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "read_events_produced": 0,
        "load_provenance": "pending_file_binding_and_live_capture",
        "resource_links": [],
        "capabilities": [],
    }
