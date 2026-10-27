"""SRI2 producer for Heather's audited PAL clips; no I/O or source authentication."""

import hashlib
import struct
import zlib

from tools.pipeline.character_inspection import integers
from tools.pipeline.rig_inspection import encode_rig_payload, prepare_heather_rig

MAGIC = b"S3RIv2\0\0"
PROFILE = "heather-original-pal-525-v1"
CHANNEL2 = (1, 3, 5, 7, 8, 10, 12, 13, 14, 16, 17, 21, 27, 33, 35)
CHANNEL1 = (0, 2, 4, 6, 9, 11, 15, 24, 25, 26, 30, 31, 32, 34, 36, 37, 38, 39, 40, 41, 42)
BONES = tuple(sorted(CHANNEL1 + CHANNEL2))
CHANNELS = tuple(2 if b in CHANNEL2 else 1 for b in BONES)
DESCRIPTORS = (
    (101, 10, 307, 0, 9, 1, 0),
    (109, 24, 1996, 80, 103, 1, 0),
    (113, 24, 2227, 176, 199, 1, 0),
)
PACKED_FIRST = (0, 10, 34)
SAMPLES = tuple(i for d in DESCRIPTORS for i in range(d[3], d[4] + 1))


def validate_descriptors(descriptors):
    """Require three original PAL records, not inferred or converted speeds."""
    expected = b"".join(struct.pack("<HHhHHBB", *d) for d in DESCRIPTORS)
    if type(descriptors) is not bytes or descriptors != expected:
        raise ValueError("HL_DESCRIPTORS")


def encode_locomotion_rig(
    *,
    parents,
    frames,
    targets,
    helpers,
    vertices,
    indices,
    materials,
    center,
    scale,
    source_bones,
    channels,
    descriptors,
):
    """Encode exact profile metadata plus bounded shared SRI geometry sections.

    Synthetic geometry may use SRI's structural limits. The private reducer
    below additionally enforces the original outfit's geometry counts.
    """
    validate_descriptors(descriptors)
    if integers(source_bones, 36, 0, 72) != BONES or integers(channels, 36, 1, 2) != CHANNELS:
        raise ValueError("HL_BINDINGS")
    if len(parents) != 36 or len(frames) != 58:
        raise ValueError("HL_COUNTS")
    common = encode_rig_payload(
        parents, frames, targets, helpers, vertices, indices, materials, center, scale
    )
    boundary = 16 + 4 * len(parents)
    bindings = b"".join(struct.pack("<HBB", b, c, 0) for b, c in zip(BONES, CHANNELS, strict=True))
    clips = b"".join(
        descriptors[i * 12 : (i + 1) * 12] + struct.pack("<II", first, 0)
        for i, first in enumerate(PACKED_FIRST)
    )
    payload = common[:boundary] + bindings + clips + common[boundary:]
    return (
        struct.pack(
            "<8s22I",
            MAGIC,
            *map(len, (parents, frames, targets, vertices, indices, materials)),
            3,
            2,
            25,
            1,
            522,
            525,
            len(payload),
            zlib.crc32(payload),
            *([0] * 8),
        )
        + payload
    )


def heather_locomotion_rig(geometry, animation, textures, descriptors):
    """Reduce decoded intermediates; receipt explicitly leaves provenance unverified.

    Use produce_heather_locomotion for source authentication. No caller-supplied
    digest can turn this synthetic/decoded entry point into a verified package.
    """
    validate_descriptors(descriptors)
    try:
        rig, files, selection = prepare_heather_rig(geometry, animation, textures, SAMPLES)
        raw = encode_locomotion_rig(
            **rig, source_bones=selection["bones"], channels=CHANNELS, descriptors=descriptors
        )
        files["heather.sri"] = raw
        report = _receipt(geometry, rig, files, selection, descriptors)
    except (KeyError, IndexError, TypeError, OverflowError, struct.error) as error:
        raise ValueError("HL_INPUT") from error
    return files, report


def _receipt(geometry, rig, files, selection, descriptors):
    skeleton = geometry["mesh"]["skeleton"]
    bones = [
        dict(
            source=b,
            compact=i,
            channel=CHANNELS[i],
            source_parent=skeleton["parents"][b],
            compact_parent=rig["parents"][i],
        )
        for i, b in enumerate(BONES)
    ]
    helpers = [
        dict(
            source=h,
            compact=i,
            source_target=BONES[rig["targets"][i]],
            compact_target=rig["targets"][i],
        )
        for i, h in enumerate(selection["helpers"])
    ]
    submeshes, first_vertex, first_index = [], 0, 0
    for material, texture in enumerate(selection["textures"]):
        for source in selection["submeshes"]:
            part = geometry["mesh"]["submeshes"][source]
            if part["texture_index"] != texture:
                continue
            nv, ni = len(part["vertices"]), 3 * len(part["triangles"])
            submeshes.append(
                dict(
                    source=source,
                    material=material,
                    first_vertex=first_vertex,
                    vertex_count=nv,
                    first_index=first_index,
                    index_count=ni,
                )
            )
            first_vertex += nv
            first_index += ni
    clips = [
        dict(
            clip_id=d[0],
            sample_count=d[1],
            pal_speed=d[2],
            source_first=d[3],
            source_last=d[4],
            loop_byte=d[5],
            trailing_byte=d[6],
            packed_first=first,
            descriptor_hex=descriptors[i * 12 : (i + 1) * 12].hex(),
            source_samples=list(range(d[3], d[4] + 1)),
            packed_samples=list(range(first, first + d[1])),
        )
        for i, (d, first) in enumerate(zip(DESCRIPTORS, PACKED_FIRST, strict=True))
    ]
    materials = [
        dict(
            source_texture=t,
            texture=i,
            file=f"texture-{i:02}.rgba",
            first_index=m[0],
            index_count=m[1],
            width=m[3],
            height=m[4],
            blend=m[5],
            crc32=m[6],
        )
        for i, (t, m) in enumerate(zip(selection["textures"], rig["materials"], strict=True))
    ]
    return dict(
        schema_version=1,
        format="SRI2",
        profile=PROFILE,
        source_verified=False,
        model_resource=522,
        animation_resource=525,
        model_id=0x100,
        outfit_mask=0x3021,
        source_bone_count=73,
        source_sample_count=1763,
        source_frame_bytes=264,
        bones=bones,
        helpers=helpers,
        clips=clips,
        submeshes=submeshes,
        materials=materials,
        descriptors_sha256=hashlib.sha256(descriptors).hexdigest(),
        framing=dict(
            center=list(rig["center"]),
            scale=rig["scale"],
            radius=selection["framing_radius"],
            source_frame=0,
            bounded_samples=58,
        ),
        clock=dict(ticks=2, inspection_hz=25, speed_offset=0, speeds_already_pal=True),
        files={
            name: dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            for name, data in sorted(files.items())
        },
        appearance="original_normal_game",
        lighting="neutral",
        morphs_applied=False,
        reconstruction="selected_local_TR_and_shared_materials_only",
        excluded=[
            "unselected_ANM_samples",
            "inactive_bones_and_submeshes",
            "morph_targets",
            "world_movement",
            "visible_weapon",
            "PS2_lighting",
        ],
    )
