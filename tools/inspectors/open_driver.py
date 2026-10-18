"""OD01-07: opening witness and endpoint consistency; lifetime fails closed."""

import struct

from tools.inspectors.catalog_open import _inputs as catalog_inputs
from tools.inspectors.driver_object import inspect_driver
from tools.inspectors.driver_transfer import _inputs as transfer_inputs
from tools.inspectors.driver_transfer import reconcile_driver_transfer
from tools.inspectors.load_lineage import MAX_CYCLES
from tools.inspectors.mapped_pause import validate_pause
from tools.inspectors.observation_capture import require
from tools.inspectors.observer_series import _backing


def reconcile_open_driver(source, opening, request, driver, stages, *, require_continuity=True):
    catalog_inputs(source, opening)
    transfer_inputs(request, driver)
    require(type(require_continuity) is bool, "OPEN_DRIVER_POLICY")
    require(
        (source.file_size, source.offset, source.size, source.resource_sha256)
        == (request.file_size, request.offset, request.size, request.resource_sha256)
        and request.requested == source.size,
        "OPEN_DRIVER_SOURCE",
    )
    require(type(stages) is tuple and len(stages) == 3, "OPEN_DRIVER_STAGES")
    pauses = tuple(validate_pause(points) for points in stages)
    a, b, c = pauses
    require(
        tuple(r[0] for r in a.regions)
        == ("root", "pool", "object", "vtable", "code", "path", "descriptor", "range"),
        "OPEN_DRIVER_REGIONS",
    )
    require(len({p.slot for p in pauses}) == 3, "OPEN_DRIVER_SLOTS")
    for before, after in zip(pauses[:-1], pauses[1:], strict=True):
        require(
            before.identity == after.identity and after.sequence == before.sequence + 8,
            "OPEN_DRIVER_IDENTITY",
        )
        require(before.cycle < after.cycle <= a.cycle + MAX_CYCLES, "OPEN_DRIVER_CYCLE")
    transfer = reconcile_driver_transfer(request, driver, stages[1:])
    maps = tuple({label: (r, o) for label, r, o in p.regions} for p in pauses)
    x, y, _ = maps
    pages = {}
    anchor = None
    for regions in maps:
        for _, obs in regions.values():
            current = (obs.before.ee_main, obs.before.vmap, obs.before.exposed_ram_size)
            anchor = current if anchor is None else anchor
            require(current == anchor, "OPEN_DRIVER_BACKING")
            for page in obs.before.pages:
                require(pages.get(page.virtual_page, page.bias) == page.bias, "OPEN_DRIVER_PAGE")
                pages[page.virtual_page] = page.bias
    for label in ("root", "pool", "object", "vtable"):
        ar, ao = x[label]
        br, bo = y[label]
        require(
            (ar.virtual_start, ar.size, ar.expected_offset)
            == (br.virtual_start, br.size, br.expected_offset)
            and _backing(ao) == _backing(bo),
            "OPEN_DRIVER_BACKING",
        )
        require(label == "object" or ao.data == bo.data, "OPEN_DRIVER_CHANGED")
    require(x["root"][0].virtual_start == driver.root_address, "OPEN_DRIVER_ROOT")
    require(
        x["code"][0].virtual_start == opening.wrapper.address
        and x["code"][1].data == opening.wrapper.data,
        "OPEN_DRIVER_CODE",
    )
    require(a.cpu.pc == opening.open_pc + 8, "OPEN_DRIVER_PC")
    g = a.cpu.gpr_low32
    require(
        g[2] == request.handle
        and g[31] == opening.open_pc + 8
        and g[29] % 16 == 0
        and g[16] == opening.mode
        and g[18] == opening.flags
        and g[17] == x["descriptor"][0].virtual_start
        and g[17] % 16 == 0
        and x["path"][0].virtual_start == g[29] + 80
        and x["range"][0].virtual_start == g[29] + 600,
        "OPEN_DRIVER_ABI",
    )
    path = x["path"][1].data
    require(
        path.startswith(b"cdrom0:/")
        and path.endswith(b"\0")
        and path[8:-1].upper() == source.iso_path,
        "OPEN_DRIVER_PATH",
    )
    require(
        x["range"][1].data == struct.pack("<II", source.offset, source.size), "OPEN_DRIVER_RANGE"
    )
    row = x["descriptor"][1].data
    require(
        len(row) == 16 and struct.unpack_from("<I", row)[0] == 0xFFFFFFFE,
        "OPEN_DRIVER_RESERVATION",
    )
    opened = inspect_driver(
        stages[0][:4], request.handle, source.file_size, 0, driver.reader.address
    )
    reading = inspect_driver(
        stages[1][:4], request.handle, source.file_size, source.offset, driver.reader.address
    )
    require(
        opened.words[5] == int(bool(opening.flags & 0x2000))
        and opened.words[9] == opened.words[11] == 0xFFFFFFFF,
        "OPEN_DRIVER_INITIAL",
    )
    require(
        all(opened.words[i] == reading.words[i] for i in range(12) if i not in (8, 11)),
        "OPEN_DRIVER_OBJECT_CHANGED",
    )
    require(not require_continuity, "OPEN_DRIVER_LIFETIME_UNPROVEN")
    return {
        "schema_version": 1,
        "status": "consistent_supplied_open_driver_endpoints_lifetime_unproven",
        "catalog_sha256": source.catalog_sha256,
        "container_sha256": source.container_sha256,
        "resource_sha256": source.resource_sha256,
        "resource_size": source.size,
        "points": [*a.metadata, *transfer["points"]],
        "opening_result_and_driver_consistent": True,
        "driver_generation_matches_at_endpoints": True,
        "object_and_position_consistent": True,
        "destination_preexisting": transfer["destination_preexisting"],
        "initial_cache_index_matches": transfer["initial_cache_index_matches"],
        "source_anchor_reverified": False,
        "profile_semantics_authenticated": False,
        "catalog_selection_reconciled": False,
        "continuous_lifetime_verified": False,
        "file_identity_verified": False,
        "inner_route_verified": False,
        "cache_origin_verified": False,
        "disk_read_verified": False,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "read_events_produced": 0,
        "load_provenance": "pending_joint_catalog_lifetime_backend_and_live_capture",
        "resource_links": [],
        "capabilities": [],
    }
