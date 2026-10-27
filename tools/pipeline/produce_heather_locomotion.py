"""Authenticate original MDL522/ANM525 bytes and build SRI2 in memory, without publication."""

import hashlib
import json
import math
import struct
from dataclasses import asdict

from tools.pipeline.decoders.ps2_animation import decode_animation
from tools.pipeline.decoders.ps2_indexed import render_indexed
from tools.pipeline.decoders.ps2_morph_materials import decode_morph_materials
from tools.pipeline.locomotion_inspection import heather_locomotion_rig, validate_descriptors

MODEL_SHA256 = "1aa81b56c0a079c8d98e57f17537e91b2ce20f1e46a1cc6d9816561cad03d2e9"
ANIMATION_SHA256 = "a0ad870863df5c495c453acdc2230dc8bb762394687599329f5a97a975d75181"


def produce_heather_locomotion(model, animation, pal_descriptors):
    """Never trust reported hashes or caller-edited decoded fields as provenance.

    Descriptors are exactly three twelve-byte PAL records in 101/109/113 order.
    The caller retains their acquisition evidence; bytes must match the pinned
    contract. This function has no paths, ISO/emulator access or output writes.
    """
    for data, limit, expected in (
        (model, 16 * 1024 * 1024, MODEL_SHA256),
        (animation, 512 * 1024, ANIMATION_SHA256),
    ):
        if type(data) is not bytes or not 4 < len(data) <= limit:
            raise ValueError("HL_SOURCE_SIZE")
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("HL_SOURCE_SHA256")
    validate_descriptors(pal_descriptors)
    geometry, samples, textures = _decode_sources(model, animation)
    files, report = heather_locomotion_rig(geometry, samples, textures, pal_descriptors)
    report["source_verified"] = True
    report["endpoint_profile"] = "pcsx2-hl06-f32-v1"
    report["sources"] = {
        "model": dict(resource=522, bytes=len(model), sha256=hashlib.sha256(model).hexdigest()),
        "animation": dict(
            resource=525, bytes=len(animation), sha256=hashlib.sha256(animation).hexdigest()
        ),
    }
    return files, report


def _decode_sources(model, animation):
    material = decode_morph_materials(model)
    skeleton = material.geometry.mesh.skeleton
    samples = decode_animation(animation, skeleton.model_id, skeleton.parents)
    # Same JSON representation as the existing full intermediate converters;
    # source bytes, not these derived floats, are the authenticated input.
    geometry = json.loads(json.dumps(dict(schema_version=1, **asdict(material.geometry))))
    samples = json.loads(json.dumps(dict(schema_version=1, **asdict(samples))))
    # SRI2 follows HL06's observed endpoint arithmetic. The lossless decoder
    # retains its mathematical quaternion and original words; SRI1 is unchanged.
    for frame in samples["frames"]:
        for track in frame["tracks"]:
            track["quaternion_xyzw"] = pal_endpoint(track["rotation_words"], track["flag"])
    textures = {}
    for index, (image_index, selector) in enumerate(material.geometry.mesh.texture_descriptors):
        image = material.images[image_index]
        textures[index] = (
            image.width,
            image.height,
            render_indexed(image, selector, normalize_alpha=False),
        )
    return geometry, samples, textures


def pal_endpoint(words, flag):
    """Decoded i16 XYZ, truncated f32 operations, nearest SQRT, original W sign.

    Input validation belongs to the lossless ANM decoder. This bounded policy
    implements the pinned PCSX2 profile, not arbitrary PS2 FPU emulation.
    """

    def truncate(value):
        bits = struct.unpack("<I", struct.pack("<f", value))[0]
        rounded = struct.unpack("<f", struct.pack("<I", bits))[0]
        if rounded > value:  # All intermediates here are nonnegative.
            bits -= 1
        return struct.unpack("<f", struct.pack("<I", bits))[0]

    xyz = [v / 32768 for v in words]
    squares = [truncate(v * v) for v in xyz]
    norm = truncate(truncate(squares[0] + squares[1]) + squares[2])
    radicand = truncate(max(0.0, 1.0 - norm))
    w = struct.unpack("<f", struct.pack("<f", math.sqrt(radicand)))[0]
    return [*xyz, -w if flag & 4 else w]
