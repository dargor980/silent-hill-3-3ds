"""Source pin enforcement and decoder wiring, with exclusively invented resources."""

import hashlib
import random
import struct

import pytest
from test_locomotion_inspection import PAL, own_locomotion_shape
from test_morph_materials import textured_morph
from test_skeleton_animation import anm

from tools.pipeline import produce_heather_locomotion as producer
from tools.qa.animation_precision import reconstruct_quaternion_f32


def test_endpoint_policy_matches_independent_bounded_reference():
    rng = random.Random(61439924454)
    words = [[0, 0, 0], [32767, 256, 1], [-32768, 0, 0], [17237, -9183, 26115]]
    words += [[rng.randint(-18000, 18000) for _ in range(3)] for _ in range(2000)]
    for xyz in words:
        for flag in (1, 5):
            assert tuple(producer.pal_endpoint(xyz, flag)) == reconstruct_quaternion_f32(
                xyz, negative_w=bool(flag & 4)
            )


def own_source_pair():
    model, _, _ = textured_morph()
    model = bytearray(model)
    struct.pack_into("<I", model, 4, 0x209)
    return bytes(model), anm()


def test_pins_match_contract_without_caller_override():
    assert (
        producer.MODEL_SHA256 == "1aa81b56c0a079c8d98e57f17537e91b2ce20f1e46a1cc6d9816561cad03d2e9"
    )
    assert (
        producer.ANIMATION_SHA256
        == "a0ad870863df5c495c453acdc2230dc8bb762394687599329f5a97a975d75181"
    )


@pytest.mark.parametrize(
    "bad", [None, "string", bytearray(b"12345"), b"", b"1234", bytes(16 * 1024 * 1024 + 1)]
)
def test_bad_source_type_size_precedes_decoders(monkeypatch, bad):
    monkeypatch.setattr(producer, "_decode_sources", lambda *_: pytest.fail("decoder called"))
    with pytest.raises(ValueError, match="HL_SOURCE_SIZE"):
        producer.produce_heather_locomotion(bad, b"fake-animation", PAL)


@pytest.mark.parametrize("which", ["model", "animation", "oversize_animation", "descriptor"])
def test_hashes_and_descriptors_precede_decode(monkeypatch, which):
    model, animation, descriptors = b"invented-model", b"invented-animation", PAL
    monkeypatch.setattr(producer, "_decode_sources", lambda *_: pytest.fail("decoder called"))
    if which != "model":
        monkeypatch.setattr(producer, "MODEL_SHA256", hashlib.sha256(model).hexdigest())
    if which == "oversize_animation":
        animation = bytes(512 * 1024 + 1)
    if which == "descriptor":
        monkeypatch.setattr(producer, "ANIMATION_SHA256", hashlib.sha256(animation).hexdigest())
        descriptors = PAL[:-1]
    expected = {"oversize_animation": "HL_SOURCE_SIZE", "descriptor": "HL_DESCRIPTORS"}.get(
        which, "HL_SOURCE_SHA256"
    )
    with pytest.raises(ValueError, match=expected):
        producer.produce_heather_locomotion(model, animation, descriptors)


def test_authenticated_orchestration_computes_hashes_and_never_mutates(monkeypatch):
    # Only a unit seam: these bytes are not proprietary, nor a private fidelity proof.
    model, animation = b"unit-model", b"unit-animation"
    monkeypatch.setattr(producer, "MODEL_SHA256", hashlib.sha256(model).hexdigest())
    monkeypatch.setattr(producer, "ANIMATION_SHA256", hashlib.sha256(animation).hexdigest())
    decoded = own_locomotion_shape()
    calls = []

    def decode(m, a):
        calls.append((m, a))
        return decoded

    monkeypatch.setattr(producer, "_decode_sources", decode)
    files, report = producer.produce_heather_locomotion(model, animation, PAL)
    assert calls == [(model, animation)]
    assert len(files["heather.sri"]) == 290156
    assert report["source_verified"] is True
    for key, resource, data in (("model", 522, model), ("animation", 525, animation)):
        assert report["sources"][key] == dict(
            resource=resource, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()
        )
    # Same hashes cannot conceal a later malformed derived input.
    decoded[1]["frames"][199]["tracks"] = []
    with pytest.raises(ValueError, match="HI_TRACKS"):
        producer.produce_heather_locomotion(model, animation, PAL)


def test_real_decoder_adapter_preserves_original_ps2_alpha_and_json_shape():
    model, sample_bytes = own_source_pair()
    geometry, animation, textures = producer._decode_sources(model, sample_bytes)
    assert geometry["schema_version"] == animation["schema_version"] == 1
    assert geometry["mesh"]["skeleton"]["parents"] == [-1, -1, 1]
    assert len(animation["frames"]) == 2 and animation["frame_bytes"] == 46
    assert set(textures) == {0}
    width, height, rgba = textures[0]
    assert (width, height, len(rgba)) == (128, 128, 65536)
    # Compare direct palette words rather than the producer's renderer.
    material = producer.decode_morph_materials(model)
    image = material.images[0]
    palette = image.palettes[image.selectors.index(7)]
    expected = b"".join(palette[p * 4 : p * 4 + 4] for p in image.indices)
    assert rgba == expected


def test_valid_synthetic_sources_of_another_model_are_rejected_by_profile(monkeypatch):
    model, animation = own_source_pair()
    monkeypatch.setattr(producer, "MODEL_SHA256", hashlib.sha256(model).hexdigest())
    monkeypatch.setattr(producer, "ANIMATION_SHA256", hashlib.sha256(animation).hexdigest())
    with pytest.raises(ValueError, match="HI_PROFILE"):
        producer.produce_heather_locomotion(model, animation, PAL)


def test_decode_failure_is_not_promoted_to_verified_result(monkeypatch):
    model = b"invented-bad-mdl"
    animation = struct.pack("<I", 0x100) + b"bad"
    monkeypatch.setattr(producer, "MODEL_SHA256", hashlib.sha256(model).hexdigest())
    monkeypatch.setattr(producer, "ANIMATION_SHA256", hashlib.sha256(animation).hexdigest())
    with pytest.raises(ValueError, match="SA_MODEL_SIZE"):
        producer.produce_heather_locomotion(model, animation, PAL)
