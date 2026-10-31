"""Inventory production frames for HG, with an explicit allowance for SDK/libc.

Sum all selected frames, including mutually exclusive loaders. Add 26 extra
levels of every emitted introsort frame (at most 6032 triangles), then 8 KiB
reserved for external libraries. This is a compiler bound plus a reservation,
not an ARM stack watermark or a bound on unaudited SDK internals.
"""

import json
import re
import sys
from pathlib import Path

UNITS = {
    f"engine/{group}/{name}.cpp"
    for group, names in {
        "domain": (
            "lifecycle locomotion_clock locomotion_pose locomotion_update inspection_movement "
            "inspection_locomotion inspection_rig room_contacts room_scene"
        ),
        "application": "inspection_actor movement_controller room_loop",
        "platform/common": (
            "inspection_locomotion inspection_rig room_movement_contacts room_scene room_runtime "
            "inspection_crc32 inspection_texture"
        ),
        "platform/3ds": "movement_controls",
        "platform/3ds/render": "room_renderer room_main room_material_state material_state",
    }.items()
    for name in names.split()
}


def analyze(lines, graphs=()):
    frames = {}
    for line in lines:
        label, count, kind = line.rsplit("\t", 2)
        n = int(count)
        if kind not in {"static", "dynamic,bounded"} or not 0 <= n <= 8192:
            raise ValueError(f"Unbounded or oversized frame: {line}")
        frames[label] = max(frames.get(label, 0), n)
    if not frames:
        raise ValueError("Missing stack frames")
    defined, edges, external = set(), {}, set()
    for graph in graphs:
        for title, label in re.findall(r'node: \{ title: "([^"]+)" label: "([^"]+)"', graph):
            if re.search(r"\d+ bytes \((?:static|dynamic,bounded)\)", label):
                defined.add(title)
        for source, target in re.findall(
            r'edge: \{ sourcename: "([^"]+)" targetname: "([^"]+)"', graph
        ):
            edges.setdefault(source, set()).add(target)
    if graphs and not defined:
        raise ValueError("Empty GCC graph")
    visited = set()

    def walk(node, active):
        if node in active:
            raise ValueError(f"Unexpected direct recursion: {node}")
        if node not in defined:
            external.add(node)
            return
        if node in visited:
            return
        for child in edges.get(node, ()):
            if child == node and "introsort" in node:
                continue
            walk(child, active | {node})
        visited.add(node)

    for node in defined:
        walk(node, set())
    frame_sum = sum(frames.values())
    sort_extra = 26 * sum(n for label, n in frames.items() if "introsort" in label)
    owned = frame_sum + sort_extra
    total = owned + 8192
    if total > 32768:
        raise ValueError(f"HG stack allowance exceeded: {total}")
    return {
        "frame_count": len(frames),
        "frame_sum": frame_sum,
        "largest_frame": max(frames.values()),
        "sort_recursion_extra": sort_extra,
        "owned_conservative_bound": owned,
        "external_library_reserve": 8192,
        "total_with_reserve": total,
        "budget": 32768,
        "direct_graph_checked": bool(graphs),
        "external_calls": sorted(external),
        "physical_stack_measured": False,
    }


def verify(directory, units=UNITS):
    build = Path(directory)
    frames, graphs, found, reports = [], [], set(), 0
    for path in sorted((build / "CMakeFiles").rglob("*.su")):
        if ".dir/engine/" not in path.as_posix():
            continue
        unit = "engine/" + path.as_posix().split(".dir/engine/", 1)[1].removesuffix(".su")
        if not unit.endswith(".cpp"):
            unit += ".cpp"
        if unit not in units:
            continue
        found.add(unit)
        reports += 1
        frames.extend(path.read_text().splitlines())
        graph = path.with_suffix(".ci")
        if graph.exists():
            graphs.append(graph.read_text())
    if found != units:
        raise ValueError(f"Missing production reports: {sorted(units - found)}")
    if graphs and len(graphs) != reports:
        raise ValueError("Incomplete GCC graph reports")
    result = analyze(frames, graphs)
    result["units"] = sorted(found)
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == "__main__":
    verify(sys.argv[1])
