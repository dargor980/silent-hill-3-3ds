"""Bound production HRC frames, including preparation staging and both adapters.

Sum every emitted frame (even mutually exclusive ones) plus a 128-byte reserve
for memcpy/memset. The pinned ARM leaf implementations are audited separately.
GCC's graph must be acyclic and have no other external calls from either entry.
Clang emits .su only; the same source's nonrecursive graph is checked with GCC.
"""

import json
import re
import sys
from pathlib import Path


def verify(directory):
    build = Path(directory)
    folders = [
        build / "CMakeFiles/sh3_domain.dir/engine/domain",
        build / "CMakeFiles/sh3_diagnostics.dir/engine/platform/common",
    ]
    names = ["room_contacts", "room_movement_contacts"]
    if not (build / "CMakeFiles").exists():
        folders = [build, build]  # Archived compiler reports retain their original basenames.
    frames, graphs = [], []
    for folder, name in zip(folders, names, strict=True):
        usage = list(folder.glob(name + "*.su"))
        if len(usage) != 1:
            raise ValueError(f"Expected one stack report for {name}: {usage}")
        lines = usage[0].read_text().splitlines()
        if not lines:
            raise ValueError(f"Empty stack report: {usage[0]}")
        for line in lines:
            label, count, kind = line.rsplit("\t", 2)
            if kind != "static" or int(count) < 0:
                raise ValueError(f"Unbounded stack frame: {line}")
            frames.append((label, int(count)))
        graphs += list(folder.glob(name + "*.ci"))
    graph_checked = False
    if graphs:
        if len(graphs) != 2:
            raise ValueError("Incomplete GCC call graph")
        defined, edges, roots = set(), {}, set()
        for path in graphs:
            text = path.read_text()
            for title, label in re.findall(r'node: \{ title: "([^"]+)" label: "([^"]+)"', text):
                if "bytes (static)" in label:
                    defined.add(title)
                    if (
                        "RoomMovementContacts::prepare(" in label
                        or "RoomMovementContacts::resolve(" in label
                    ):
                        roots.add(title)
            for source, target in re.findall(
                r'edge: \{ sourcename: "([^"]+)" targetname: "([^"]+)"', text
            ):
                edges.setdefault(source, set()).add(target)
        if len(roots) != 2:
            raise ValueError("Missing adapter roots")

        def walk(node, active):
            if node in active:
                raise ValueError(f"Recursive HRC call graph: {node}")
            if node not in defined:
                if node not in {"memcpy", "memset"}:
                    raise ValueError(f"Unaudited external/indirect HRC call: {node}")
                return
            for child in edges.get(node, ()):
                walk(child, active | {node})

        for root in roots:
            walk(root, set())
        graph_checked = True
    header = (
        Path(__file__).resolve().parents[1] / "engine/domain/include/sh3/domain/room_contacts.hpp"
    ).read_text()

    def constant(name):
        return int(re.search(rf"{name} = (\d+);", header)[1])

    frame_sum = sum(count for _, count in frames)
    stack = frame_sum + 128
    resident = constant("room_contact_resident_bound")
    if stack > constant("room_contact_stack_bound") or resident + stack > constant(
        "room_contact_budget"
    ):
        raise ValueError(f"HRC memory budget exceeded: resident={resident}, stack={stack}")
    result = {
        "frame_sum": frame_sum,
        "external_leaf_reserve": 128,
        "conservative_stack": stack,
        "resident_bound": resident,
        "conservative_total": resident + stack,
        "gcc_graph_checked": graph_checked,
    }
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == "__main__":
    verify(sys.argv[1])
