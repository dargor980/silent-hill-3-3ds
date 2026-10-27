"""Lossless inventory of an actor prefix; no movement or transform authorization."""

import math
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class ActorSpatial:
    kind: int
    scale: tuple[float, ...]
    position: tuple[float, ...]
    rotation: tuple[float, ...]
    matrix_columns: tuple[float, ...]
    raw: bytes
    observations: tuple[str, ...]


def inspect_actor_spatial(data: bytes, *, expected_kind: int) -> ActorSpatial:
    """Read exactly 128 caller-delimited bytes without following any pointers.

    The caller owns identity, address mapping and provenance. Semantic anomalies
    remain observations: even an empty list does not prove rigidity or physics.
    """
    if type(data) is not bytes or len(data) != 128:
        raise ValueError("Actor prefix must be exactly 128 immutable bytes")
    if type(expected_kind) is not int or not 1 <= expected_kind <= 65535:
        raise ValueError("Expected actor kind outside uint16 nonzero range")
    (kind,) = struct.unpack_from("<H", data, 12)
    if kind != expected_kind:
        raise ValueError("Actor kind mismatch")
    values = struct.unpack_from("<27f", data, 20)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Nonfinite actor spatial component")
    scale, position, rotation, matrix = values[:3], values[3:7], values[7:11], values[11:]
    observations = []
    if scale != (1, 1, 1):
        observations.append("non_unit_scale")
    if position[3] != 1:
        observations.append("non_unit_position_w")
    if rotation[0] != 0 or rotation[2] != 0:
        observations.append("nonzero_rotation_xz")
    if rotation[3] != 0:
        observations.append("nonzero_rotation_w")
    if tuple(matrix[i] for i in (3, 7, 11, 15)) != (0, 0, 0, 1):
        observations.append("non_affine_matrix")
    if data[32:48] != data[112:128]:
        observations.append("matrix_translation_differs")
    return ActorSpatial(kind, scale, position, rotation, matrix, data, tuple(observations))
