"""MP02-MP04: bounded MAP header graph; no vertex or material decoding."""

import hashlib
import struct
from collections.abc import Callable

METHOD = "sh3-ps2-map-structure-v1"
MAX_MAP_BYTES = 32 * 1024 * 1024
MAX_NODES = 8192
MAX_VERTICES = 2_000_000
KINDS = ("group", "mesh", "submesh", "shape")


class MapProbeError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise MapProbeError(code)


def probe_map(size: int, read: Callable[[int, int], bytes]) -> dict:
    """Read fixed headers only. Root chains can alias complete group tails."""
    _require(type(size) is int and size >= 0, "MAP_SIZE")
    _require(size <= MAX_MAP_BYTES, "MAP_BUDGET")
    counts = dict.fromkeys(KINDS, 0)
    vertices = 0
    groups = {}

    def header(offset, length, end):
        _require(0 <= offset <= end <= size and length <= end - offset, "MAP_RANGE")
        data = read(offset, length)
        _require(type(data) is bytes and len(data) == length, "MAP_READ_CONTRACT")
        return data

    def chain(offset, lower, end, level):
        nonlocal vertices
        result = []
        while offset:
            _require(offset >= lower and offset % 16 == 0, "MAP_LINK")
            if level == 0 and offset in groups:
                node = groups[offset]
            else:
                _require(sum(counts.values()) < MAX_NODES, "MAP_BUDGET")
                length = 64 if level == 3 else 48
                raw = header(offset, length, end)
                following, delta, total, _ = struct.unpack_from("<4I", raw)
                _require(
                    length <= delta <= total <= end - offset
                    and delta % 16 == 0
                    and total % 16 == 0,
                    "MAP_NODE_RANGE",
                )
                node_end = offset + total
                _require(
                    following == 0 or node_end <= following < end and following % 16 == 0,
                    "MAP_LINK",
                )
                if level == 0:
                    _require(
                        all(
                            node_end <= start or offset >= start + other["size"]
                            for start, other in groups.items()
                        ),
                        "MAP_OVERLAP",
                    )
                counts[KINDS[level]] += 1
                node = {
                    "offset": offset,
                    "size": total,
                    "next_offset": following,
                    "data_offset": offset + delta,
                    "header_sha256": hashlib.sha256(raw).hexdigest(),
                }
                if level == 3:
                    count, transform = struct.unpack_from("<2I", raw, 16)
                    _require(count > 0 and count * 16 <= total - delta, "MAP_VERTEX_RANGE")
                    vertices += count
                    _require(vertices <= MAX_VERTICES, "MAP_BUDGET")
                    node.update(
                        vertex_count=count,
                        transform_index_unverified=transform,
                        vertex_bytes=count * 16,
                        trailing_bytes=total - delta - count * 16,
                    )
                else:
                    node["children"] = chain(offset + delta, offset + delta, node_end, level + 1)
                    if level == 0:
                        declared = struct.unpack_from("<H", raw, 24)[0]
                        _require(declared == len(node["children"]), "MAP_MESH_COUNT")
                        node.update(
                            opaque_word_16=struct.unpack_from("<I", raw, 16)[0],
                            opaque_word_20=struct.unpack_from("<I", raw, 20)[0],
                            declared_mesh_count=declared,
                        )
                        groups[offset] = node
                    elif level == 1:
                        node["clut_index_unverified"] = struct.unpack_from("<H", raw, 16)[0]
                        node["opaque_halfwords"] = list(struct.unpack_from("<3H", raw, 18))
                # Hash preserves unparsed fields without reproducing header bytes.
            result.append(node if level else node["offset"])
            lower = node["offset"] + node["size"]
            offset = node["next_offset"]
        return result

    area = header(0, 48, size)
    words = struct.unpack("<12I", area)
    _require(words[0] == 0xFFFFFFFF, "MAP_AREA_VARIANT")
    roots = [
        {"slot": slot, "offset": offset, "group_offsets": chain(offset, 48, size, 0)}
        for slot, offset in enumerate(words[7:10])
    ]
    _require(bool(groups), "MAP_EMPTY")
    return {
        "status": "structural_candidate",
        "area": {
            "header_sha256": hashlib.sha256(area).hexdigest(),
            "opaque_words": {str(i * 4): words[i] for i in (1, 2, 3, 4, 5, 6, 10, 11)},
        },
        "roots": roots,
        "groups": [groups[offset] for offset in sorted(groups)],
        "summary": {
            **{kind + "_count": count for kind, count in counts.items()},
            "vertices": vertices,
        },
        "vertex_decoding": "not_performed",
        "material_binding": "unverified",
        "unvisited_data": "not_interpreted",
    }
