"""SCW1: fixed placements, shared framing and explicit homogeneous coordinates."""

import math
import struct
import zlib

from tools.pipeline.character_inspection import integers
from tools.pipeline.character_space import CharacterRigid
from tools.pipeline.inspection_inputs import payload_crc


def encode_world(instances, counter, character, clip, material):
    scm = payload_crc(character, b"S3CMv1\0\0")
    san = payload_crc(clip, b"S3ANv1\0\0")
    sct = payload_crc(material, b"S3CTv1\0\0")
    nv, ni, helpers, stride = struct.unpack_from("<4I", character, 8)
    if (
        not 3 <= nv <= 2048
        or not 9 <= ni <= 4608
        or ni % 3
        or (helpers, stride) != (3, 28)
        or len(character) != 252 + nv * 28 + ni * 2
        or len(clip) != 1248
        or struct.unpack_from("<4I", clip, 8) != (3, 24, 0x1449, 3686)
        or len(material) != 3145796
        or struct.unpack_from("<4I", material, 8) != (3, 512, 3, scm)
    ):
        raise ValueError("World dependencies differ")
    counter = integers([counter], 1, 0, 98303)[0]
    if len(instances) != 3:
        raise ValueError("Expected three placements")
    ids = integers([i["id"] for i in instances], 3, 1, 65535)
    if len(set(ids)) != 3:
        raise ValueError("Duplicate instance")
    matrices = [CharacterRigid(i["model"]).columns for i in instances]
    matrices = [
        CharacterRigid(struct.unpack("<16f", struct.pack("<16f", *m))).columns for m in matrices
    ]
    center = struct.unpack_from("<3f", character, 32)
    model_scale = struct.unpack_from("<f", character, 44)[0]
    if any(not math.isfinite(x) or abs(x) > 100000 for x in center) or not 0 < model_scale <= 1:
        raise ValueError("Invalid model framing")
    centers = [CharacterRigid(m).position((*center, 1))[:3] for m in matrices]
    origin = [(min(c[r] for c in centers) + max(c[r] for c in centers)) / 2 for r in range(3)]
    origin = struct.unpack("<3f", struct.pack("<3f", *origin))
    if any(abs(x) > 1000000 for x in origin):
        raise ValueError("World origin outside profile")
    radius = max(math.dist(c, origin) + 1.004 * 1.4 / model_scale for c in centers)
    scale = struct.unpack("<f", struct.pack("<f", min(1, 1.4 / radius)))[0]
    if not scale > 0:
        raise ValueError("Unrepresentable framing")
    payload = struct.pack("<4f", *origin, scale)
    payload += b"".join(
        struct.pack("<I16f", ident, *m) for ident, m in zip(ids, matrices, strict=True)
    )
    payload += struct.pack("<I", 0)
    return (
        struct.pack("<8s8I", b"S3CWv1\0\0", 1, 3, scm, san, sct, counter, 224, zlib.crc32(payload))
        + payload
    )
