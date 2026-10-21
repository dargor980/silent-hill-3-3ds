"""MR01-MR05: counted draw roots and base transform metadata, never payload export."""

import hashlib
import math
import struct
from collections.abc import Callable

from tools.inspectors.map_probe import MapProbeError, probe_map

METHOD = "sh3-ps2-map-render-metadata-v1"


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise MapProbeError(code)


def probe_render_metadata(size: int, read: Callable[[int, int], bytes]) -> dict:
    structure = probe_map(size, read)
    first_group = min(group["offset"] for group in structure["groups"])

    def exact(offset, length, end):
        _require(0 <= offset <= end <= size and length <= end - offset, "MR_RANGE")
        raw = read(offset, length)
        _require(type(raw) is bytes and len(raw) == length, "MR_READ_CONTRACT")
        return raw

    _require(first_group >= 80, "MR_PREFIX")
    control = exact(48, 32, first_group)
    total, count_0, count_2, count_1 = struct.unpack_from("<4H", control, 16)
    counts = (count_0, count_1, count_2)
    _require(total == sum(counts) == len(structure["groups"]), "MR_ROOT_COUNTS")
    roots, seen = [], set()
    for root, count in zip(structure["roots"], counts, strict=True):
        chain = root["group_offsets"]
        _require(bool(count) == bool(root["offset"]) and count <= len(chain), "MR_ROOT_COUNTS")
        selected = chain[:count]
        _require(not seen.intersection(selected), "MR_ROOT_OVERLAP")
        seen.update(selected)
        roots.append(
            {
                "slot": root["slot"],
                "offset": root["offset"],
                "declared_count": count,
                "group_offsets": selected,
                "structural_tail_excluded": chain[count:],
            }
        )
    # Equal total plus distinct prefixes drawn from the graph implies full coverage.

    offset = structure["area"]["opaque_words"]["24"]
    _require(offset >= 80 and offset % 16 == 0, "MR_TRANSFORM_OFFSET")
    header = exact(offset, 32, first_group)
    following, delta, length = struct.unpack_from("<3I", header)
    _require(following == 0, "MR_TRANSFORM_CHAIN_UNSUPPORTED")
    _require(
        delta >= 32
        and delta % 16 == 0
        and length == delta + 192
        and length <= first_group - offset,
        "MR_TRANSFORM_RANGE",
    )
    payload = exact(offset + delta, 192, offset + length)
    values = struct.unpack("<48f", payload)
    _require(all(math.isfinite(value) for value in values), "MR_NONFINITE")
    matrix = values[:16]
    affine = tuple(matrix[i] for i in (3, 7, 11, 15)) == (0.0, 0.0, 0.0, 1.0)
    basis_identity = all(
        matrix[col * 4 + row] == float(col == row) for col in range(3) for row in range(3)
    )
    modes = []
    for group in structure["groups"]:
        for mesh in group["children"]:
            for submesh in mesh["children"]:
                for shape in submesh["children"]:
                    raw = exact(shape["offset"] + 20, 8, shape["offset"] + 64)
                    mode, auxiliary = struct.unpack("<2I", raw)
                    modes.append(
                        {
                            "shape_offset": shape["offset"],
                            "group_offset": group["offset"],
                            "mode_word_20": mode,
                            "auxiliary_word_24": auxiliary,
                        }
                    )
    return {
        "method": METHOD,
        "status": "structural_metadata_only",
        "control_sha256": hashlib.sha256(control).hexdigest(),
        "declared_group_count": total,
        "counted_roots": roots,
        "base_transform": {
            "record_offset": offset,
            "record_size": length,
            "header_sha256": hashlib.sha256(header).hexdigest(),
            "matrix_offset": offset + delta,
            "matrix_sha256": hashlib.sha256(payload[:64]).hexdigest(),
            "bounds_offset": offset + delta + 64,
            "bounds_sha256": hashlib.sha256(payload[64:]).hexdigest(),
            "finite": True,
            "affine_if_column_major": affine,
            "identity_basis_if_column_major": basis_identity,
            "zero_translation_if_column_major": matrix[12:15] == (0.0, 0.0, 0.0),
            "application": "not_performed",
        },
        "shape_words": modes,
        "material_binding": "unverified",
        "runtime_comparison": "pending",
        "payload_export": "not_performed",
    }
