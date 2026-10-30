"""HRC test-only oracle: exact rationals and rectangle-edge intersections.

No production imports, slab intervals, fixed-width limb implementation or private
assets. This checks authored contract vectors, not a native implementation.
"""

import struct
from fractions import Fraction

LIMIT = 1_000_000
RADIUS = 176


def scalar_bits(value):
    if isinstance(value, str):
        if (
            not value.startswith("f32:")
            or len(value) != 12
            or any(c not in "0123456789abcdefABCDEF" for c in value[4:])
        ):
            raise ValueError("Expected f32:XXXXXXXX")
        return int(value[4:], 16)
    if type(value) is not int:
        raise ValueError("Decimal floats and booleans are not fixture scalars")
    raw = struct.pack(">f", value)
    if struct.unpack(">f", raw)[0] != value:
        raise ValueError("Integer fixture scalar is not exactly binary32")
    return int.from_bytes(raw, "big")


def rational(value):
    bits = scalar_bits(value)
    if (bits >> 23) & 255 == 255:
        return None
    return Fraction.from_float(struct.unpack(">f", bits.to_bytes(4, "big"))[0])


def _box(values, expansion):
    x0, x1, z0, z1 = map(rational, values)
    return x0 - expansion, x1 + expansion, z0 - expansion, z1 + expansion


def _inside(point, box, *, strict=False):
    x, z = point
    x0, x1, z0, z1 = box
    return x0 < x < x1 and z0 < z < z1 if strict else x0 <= x <= x1 and z0 <= z <= z1


def _orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, p):
    return (
        _orientation(a, b, p) == 0
        and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
    )


def _edges_meet(a, b, c, d):
    if any(
        (_on_segment(a, b, c), _on_segment(a, b, d), _on_segment(c, d, a), _on_segment(c, d, b))
    ):
        return True
    return _orientation(a, b, c) * _orientation(a, b, d) < 0 and (
        _orientation(c, d, a) * _orientation(c, d, b) < 0
    )


def touches_rectangle(a, b, box):
    if _inside(a, box) or _inside(b, box):
        return True
    x0, x1, z0, z1 = box
    corners = ((x0, z0), (x1, z0), (x1, z1), (x0, z1))
    return any(_edges_meet(a, b, corners[i], corners[(i + 1) % 4]) for i in range(4))


def prepare(scene, *, resident_bytes=1024, scratch_bytes=3072):
    """Budget arguments are synthetic accounting probes, not actual Python memory."""
    if (
        scene["profile"] != "static-xz-aabb-stop-v1"
        or scene["half_extent"] != 175
        or scene["guard"] != 1
    ):
        return "unsupported_profile"
    if len(scene["blockers"]) > 32:
        return "capacity_exceeded"
    if resident_bytes + scratch_bytes > 4096:
        return "budget_exceeded"
    boxes = [scene["floor"], *scene["blockers"]]
    values = [*scene["origin"], scene["floor_y"], *(v for box in boxes for v in box)]
    if any((v := rational(raw)) is None or abs(v) > LIMIT for raw in values):
        return "invalid_geometry"
    if any(rational(b[0]) > rational(b[1]) or rational(b[2]) > rational(b[3]) for b in boxes):
        return "invalid_geometry"
    x0, x1, z0, z1 = _box(scene["floor"], -RADIUS)
    return "empty_floor" if x0 >= x1 or z0 >= z1 else "ok"


def observe(scene, query):
    def error(code):
        return {
            "result": code,
            "port": "unavailable" if code == "unavailable" else "unsupported",
            "copy_from": None,
        }

    if not query.get("ready", True):
        return error("unavailable")
    if prepare(scene) != "ok":
        raise ValueError("Query vectors must reference a completely prepared scene")
    source, target = ([rational(v) for v in query[key]] for key in ("from", "requested"))
    if any(v is None for v in source + target):
        return error("invalid_query")
    if any(abs(v) > LIMIT for v in source + target):
        return error("out_of_bounds")
    if source[1] != rational(scene["floor_y"]) or target[1] != rational(scene["floor_y"]):
        return error("off_floor")
    a, b = (source[0], source[2]), (target[0], target[2])
    floor = _box(scene["floor"], -RADIUS)
    boxes = [_box(box, RADIUS) for box in scene["blockers"]]
    if not _inside(a, floor, strict=True) or any(_inside(a, box) for box in boxes):
        return error("invalid_start")
    blocked = not _inside(b, floor, strict=True) or any(
        touches_rectangle(a, b, box) for box in boxes
    )
    return {
        "result": "ok",
        "port": "accepted",
        "copy_from": "from" if blocked else "requested",
        "blocked": blocked,
    }
