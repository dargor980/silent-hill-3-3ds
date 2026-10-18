"""JR01-07: joint catalog/copy consistency; continuous lifetime fails closed."""

import struct

from tools.inspectors.buffer_copy import _inputs as copy_inputs
from tools.inspectors.buffer_copy import reconcile_buffer_copy
from tools.inspectors.catalog_open import _inputs as catalog_inputs
from tools.inspectors.catalog_open import reconcile_catalog_open
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observation_capture import require
from tools.inspectors.observer_series import _backing


def _inputs(catalog, opening, source, request, copy, sector_sha256):
    catalog_inputs(catalog, opening)
    copy_inputs(source, request, copy, sector_sha256)
    require(
        (
            catalog.container_sha256,
            catalog.resource_sha256,
            catalog.file_size,
            catalog.offset,
            catalog.size,
        )
        == (
            source.container_sha256,
            source.resource_sha256,
            source.file_size,
            source.offset,
            source.size,
        ),
        "JOINT_SOURCE",
    )


def _linked(pauses):
    require(len({p.slot for p in pauses}) == 11, "JOINT_SLOTS")
    for before, after in zip(pauses[:-1], pauses[1:], strict=True):
        require(
            before.identity == after.identity
            and after.sequence == before.sequence + len(before.regions),
            "JOINT_IDENTITY",
        )
        require(before.cycle < after.cycle <= pauses[0].cycle + MAX_CYCLES, "JOINT_CYCLE")
    anchor, pages = None, {}
    for pause in pauses:
        for _, _, obs in pause.regions:
            current = (obs.before.ee_main, obs.before.vmap, obs.before.exposed_ram_size)
            anchor = current if anchor is None else anchor
            require(current == anchor, "JOINT_BACKING")
            for page in obs.before.pages:
                require(pages.get(page.virtual_page, page.bias) == page.bias, "JOINT_PAGE")
                pages[page.virtual_page] = page.bias


def _bridge(opened, reading, opening, request):
    a = {label: (r, o) for label, r, o in opened.regions}
    b = {label: (r, o) for label, r, o in reading.regions}
    require(opened.cpu.gpr_low32[16] == request.handle, "JOINT_HANDLE")
    for label in ("root", "vtable"):
        ar, ao = a[f"driver_{label}"]
        br, bo = b[label]
        require(
            (ar.virtual_start, ar.size, ar.expected_offset, _backing(ao))
            == (br.virtual_start, br.size, br.expected_offset, _backing(bo)),
            "JOINT_DRIVER_BACKING",
        )
        require(ao.data == bo.data, "JOINT_DRIVER_CHANGED")
    block, observed = a["driver_pool"]
    header, pool = b["pool"]
    obj, row = b["object"]
    count = struct.unpack_from("<I", pool.data, 12)[0]  # CP validated this pool and row.
    require(len(observed.data) == 24 + 48 * count, "JOINT_POOL_SIZE")
    offset = obj.virtual_start - header.virtual_start
    require(
        (block.virtual_start, block.expected_offset)
        == (header.virtual_start, header.expected_offset)
        and obj.expected_offset == block.expected_offset + offset,
        "JOINT_POOL_BACKING",
    )
    require(
        observed.data[:24] == pool.data and observed.data[offset : offset + 48] == row.data,
        "JOINT_POOL_CHANGED",
    )
    words = struct.unpack("<12I", row.data)
    require(
        words[5] == int(bool(opening.flags & 0x2000)) and words[9] == words[11] == 0xFFFFFFFF,
        "JOINT_INITIAL",
    )


def reconcile_joint_open_read(
    catalog, opening, source, request, copy, sector_sha256, stages, *, require_continuity=True
):
    _inputs(catalog, opening, source, request, copy, sector_sha256)
    require(type(require_continuity) is bool, "JOINT_POLICY")
    require(type(stages) is tuple and len(stages) == 11, "JOINT_STAGES")
    pauses = tuple(validate_pause(points) for points in stages)
    require(
        tuple(r[0] for r in pauses[3].regions)
        == (
            "code",
            "config",
            "descriptor",
            "path",
            "range",
            "driver_root",
            "driver_pool",
            "driver_vtable",
        ),
        "JOINT_REGIONS",
    )
    _linked(pauses)
    selected = reconcile_catalog_open(catalog, opening, (*stages[:3], stages[3][:5]))
    copied = reconcile_buffer_copy(source, request, copy, sector_sha256, stages[4:])
    _bridge(pauses[3], pauses[4], opening, request)
    for index, label in ((4, "destination"), (7, "buffer")):
        target = next(o for name, _, o in pauses[index].regions if name == label)
        at = target.mapping.physical_offset
        for pause in pauses[:4]:
            for _, _, other in pause.regions:
                offset = other.mapping.physical_offset
                require(
                    at + len(target.data) <= offset or offset + len(other.data) <= at,
                    "JOINT_OVERLAP",
                )
    require(not require_continuity, "JOINT_LIFETIME_UNPROVEN")
    return {
        **selected,
        **copied,
        "status": "consistent_supplied_catalog_open_copy_lifetime_unproven",
        "points": [m for p in pauses for m in p.metadata],
        "joint_catalog_open_copy_consistent": True,
        "post_open_position_and_generation_consistent": True,
        "continuous_lifetime_verified": False,
        "discovery_budget_included": False,
        "load_provenance": "pending_continuity_worker_discovery_and_guarded_capture",
    }
