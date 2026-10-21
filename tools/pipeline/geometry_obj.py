"""Serialize decoded local geometry for inspection without assigning a material."""

from collections.abc import Sequence

from tools.pipeline.decoders.ps2_map_geometry import MapGeometry


def encode_obj(shapes: Sequence[tuple[int, MapGeometry]]) -> bytes:
    lines = [
        "# SH3 local geometry inspection; transforms and material unverified",
        "# UV reference: U/32768, 1-V/32768; control bit retained",
    ]
    base = 1
    for offset, geometry in shapes:
        lines.append(f"o shape_{offset}")
        for vertex in geometry.vertices:
            lines.append("v " + " ".join(str(value) for value in vertex.position))
        for vertex in geometry.vertices:
            # Dyadic UV values are exactly representable; repr roundtrips them.
            lines.append("vt " + " ".join(repr(value) for value in vertex.uv_reference))
        for face in geometry.triangles:
            lines.append("f " + " ".join(f"{base + i}/{base + i}" for i in face))
        base += len(geometry.vertices)
    return ("\n".join(lines) + "\n").encode("ascii")
