"""Independent reference for the captured mode-2 character lighting path.

Inputs share the post-skinning coordinate space. Normals and directional
vectors are used as supplied, without normalization. This models MSCAL 0x0C
(the observed type-0x10 local light) and 0x0E, not PS2 floating-point timing,
other light types, the additional 0x08 group, shadows or reflection.
Outputs are PS2 vertex-color units, before the GS texture modulation stage.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass


def _finite(values: Sequence[float], size: int) -> tuple[float, ...]:
    if not isinstance(values, Sequence) or len(values) != size:
        raise ValueError("Wrong vector size")
    try:
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError("Expected finite numeric components")
        return tuple(float(v) for v in values)
    except OverflowError as exc:
        raise ValueError("Numeric component out of range") from exc


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return _finite((sum(x * y for x, y in zip(a, b, strict=True)),), 1)[0]


def _saturate(value: float) -> float:
    return min(1.0, max(0.0, _finite((value,), 1)[0]))


@dataclass(frozen=True)
class DirectionalLight:
    direction: tuple[float, ...]
    color: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "direction", _finite(self.direction, 3))
        object.__setattr__(self, "color", _finite(self.color, 4))


@dataclass(frozen=True)
class Spotlight16:
    position: tuple[float, ...]
    direction: tuple[float, ...]
    color: tuple[float, ...]
    # a/r+b for distance; c*dot(direction, unit(vertex-light))+d for cone.
    attenuation: tuple[float, ...]

    def __post_init__(self) -> None:
        for field, size in (("position", 3), ("direction", 3), ("color", 4), ("attenuation", 4)):
            object.__setattr__(self, field, _finite(getattr(self, field), size))


def light_vertex(
    position: Sequence[float],
    normal: Sequence[float],
    material_diffuse: Sequence[float],
    material_ambient: Sequence[float],
    scene_ambient: Sequence[float],
    directionals: Sequence[DirectionalLight],
    spotlight: Spotlight16 | None = None,
) -> tuple[float, ...]:
    """Mode 2: zero initial color, optional type-0x10 spot, final 0x0E.

    Directional Lambert terms have a lower clamp only. The local light clamps
    its Lambert, reciprocal-distance and cone terms independently to [0,1].
    Material alpha is forced to 1 by the EE packet writer, not read from MDL.
    Singular local-light distance is outside the verified profile and rejected.
    """
    p, n = _finite(position, 3), _finite(normal, 3)
    diffuse = _finite(material_diffuse, 3) + (1.0,)
    ambient = _finite(material_ambient, 3) + (1.0,)
    scene = _finite(scene_ambient, 4)
    if (
        not isinstance(directionals, Sequence)
        or len(directionals) > 3
        or any(not isinstance(light, DirectionalLight) for light in directionals)
    ):
        raise ValueError("Expected up to three final-pass directional lights")
    if spotlight is not None and not isinstance(spotlight, Spotlight16):
        raise ValueError("Only the verified type-0x10 local light is supported")

    accumulated = [0.0] * 4
    if spotlight is not None:
        delta = _finite(tuple(x - y for x, y in zip(p, spotlight.position, strict=True)), 3)
        distance = _finite((math.hypot(*delta),), 1)[0]
        if distance == 0.0:
            raise ValueError("Singular local-light distance")
        unit = tuple(v / distance for v in delta)
        a, b, c, d = spotlight.attenuation
        intensity = (
            _saturate(_dot(n, unit))
            * _saturate(a / distance + b)
            * _saturate(c * _dot(spotlight.direction, unit) + d)
        )
        accumulated = [v * intensity for v in spotlight.color]

    for light in directionals:
        lambert = max(0.0, _dot(light.direction, n))
        accumulated = [x + c * lambert for x, c in zip(accumulated, light.color, strict=True)]
    return _finite(
        tuple(
            a * s + d * v for a, s, d, v in zip(ambient, scene, diffuse, accumulated, strict=True)
        ),
        4,
    )


def quantize_gs_color(color: Sequence[float], ceiling: Sequence[float]) -> tuple[int, ...]:
    """Output VU: clamp to [0, ceiling], then FTOI0 (toward zero)."""
    values, limits = _finite(color, 4), _finite(ceiling, 4)
    if any(not 0 <= value <= 255 for value in limits):
        raise ValueError("Expected byte-range output ceilings")
    return tuple(
        math.trunc(min(limit, max(0.0, value))) for value, limit in zip(values, limits, strict=True)
    )
