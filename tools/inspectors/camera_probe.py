"""Numeric SH2 road128 hypothesis; never identify or decode an SH3 camera."""

import hashlib
import math
import struct

MAX_CAMERA_BYTES = 4096
RECORD_BYTES = 128
METHOD = "sh2-road128-reference-v1"
REFERENCE_MAXIMA = {72: 3, 76: 5, 92: 1, 108: 5}


class CameraProbeError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def probe_camera(data: bytes) -> dict:
    if not isinstance(data, bytes):
        raise CameraProbeError("CAMERA_INPUT_TYPE")
    if len(data) > MAX_CAMERA_BYTES:
        raise CameraProbeError("CAMERA_BUDGET")
    if not data or len(data) % RECORD_BYTES:
        raise CameraProbeError("CAMERA_ALIGNMENT")
    disagreements = dict.fromkeys((str(offset) for offset in REFERENCE_MAXIMA), 0)
    for index in range(len(data) // RECORD_BYTES):
        start = index * RECORD_BYTES
        flag = struct.unpack_from("<I", data, start + 68)[0]
        if flag & 1:
            tail = data[start + RECORD_BYTES :]
            return {
                "status": "hypothesis_match",
                "method": METHOD,
                "prefix_record_count": index,
                "marker_record_index": index,
                "marker_has_other_bits": flag != 1,
                "opaque_tail": {"size": len(tail), "sha256": hashlib.sha256(tail).hexdigest()},
                "reference_range_disagreements": disagreements,
            }
        if not all(math.isfinite(value) for value in struct.unpack_from("<16f", data, start)):
            raise CameraProbeError("CAMERA_NONFINITE_PREFIX")
        for offset, maximum in REFERENCE_MAXIMA.items():
            value = struct.unpack_from("<I", data, start + offset)[0]
            disagreements[str(offset)] += value > maximum
    raise CameraProbeError("CAMERA_NO_MARKER")
