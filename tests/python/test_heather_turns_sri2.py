"""HG-T4.2: profile boundaries, five-clip transport and source/publication seams."""

import copy
import hashlib
import json
import subprocess

import pytest
from test_locomotion_inspection import PAL, own_locomotion_shape, own_wire
from test_locomotion_rig_reconstruction import native_sri2 as reader_fixture

from tests.locomotion_rig_fixtures import changed
from tests.locomotion_rig_wire_oracle import check_dump
from tools.pipeline import produce_heather_locomotion as producer
from tools.pipeline import publish_heather_locomotion as publisher
from tools.pipeline.locomotion_inspection import encode_locomotion_rig, heather_locomotion_rig
from tools.pipeline.rig_inspection import encode_rig, encode_rig_payload, prepare_heather_rig
from tools.qa.locomotion_rig_oracle import reconstruct_sri2, reconstruct_sri2_bundle
from tools.qa.locomotion_source_audit import audit_selection

TURN_PAL = PAL + bytes.fromhex("6b000a0080043c00450001006c000a00800446004f000100")
SELECTED = [*range(10), *range(80, 104), *range(176, 200), *range(60, 80)]
native_sri2 = reader_fixture


@pytest.fixture(scope="module")
def turn_source():
    g, a, t = own_locomotion_shape(turns=True)
    for frame in a["frames"]:
        for track in frame["tracks"]:
            track.update(rotation_words=[0, 0, 0], flag=1, quaternion_xyzw=[0, 0, 0, 1])
    files, report = heather_locomotion_rig(g, a, t, TURN_PAL, profile=2)
    return g, a, t, files, report


def test_every_selected_field_native_and_independent(native_sri2, tmp_path, turn_source):
    g, a, t, files, report = turn_source
    view = reconstruct_sri2_bundle(files)
    assert len(files["heather.sri"]) == 310356
    assert view["profile"] == 2 and view["sample_sources"] == SELECTED
    assert [c[0] for c in view["clips"]] == [101, 109, 113, 107, 108]
    assert [c[7] for c in view["clips"]] == [0, 10, 34, 58, 68]
    assert report["framing"]["bounded_samples"] == 78 and not report["source_verified"]
    assert audit_selection(files, g, a, t, TURN_PAL)["all_selected_fields_exact"]
    old, _ = heather_locomotion_rig(g, a, t, PAL)
    legacy = reconstruct_sri2_bundle(old)
    for key in ("bones", "helpers", "vertices", "indices", "materials"):
        assert view[key] == legacy[key]
    assert view["samples"][:58] == legacy["samples"]
    assert all(files[n] == old[n] for n in files if n != "heather.sri")
    for name, raw in files.items():
        (tmp_path / name).write_bytes(raw)
    for args in ([tmp_path / "heather.sri"], [tmp_path, "bundle"]):
        run = subprocess.run([native_sri2, *args], capture_output=True, text=True, check=True)
        check_dump(run.stdout, view)
    for clip, start in ((107, 60), (108, 70)):
        run = subprocess.run(
            [native_sri2, tmp_path, "trace"],
            input=f"{clip} 38912\n0\n",
            capture_output=True,
            text=True,
            check=True,
        )
        rows = [list(map(float, line.split())) for line in run.stdout.splitlines()]
        assert rows[0][:6] == [clip, clip, 1, 256, 0, 0]
        assert rows[0][18] == (start + 4.5) / 8


@pytest.mark.parametrize("profile", [0, 3, True, 2.0, None, "2"])
def test_unknown_profile(profile):
    with pytest.raises(ValueError, match="HL_PROFILE"):
        encode_locomotion_rig(**own_wire(), profile=profile)


@pytest.mark.parametrize("count", [58, 64, 77, 79, 80, 81])
def test_profile_two_requires_exact_count(count):
    rig = own_wire()
    rig["descriptors"] = TURN_PAL
    rig["frames"] = [rig["frames"][0]] * count
    with pytest.raises(ValueError, match="HL_COUNTS"):
        encode_locomotion_rig(**rig, profile=2)


@pytest.mark.parametrize(
    ("offset", "value"),
    [
        (12, 58),
        (12, 79),
        (12, 80),
        (12, 81),
        (32, 3),
        (32, 6),
        (32, 0xFFFFFFFF),
        (44, 1),
        (44, 3),
        (44, 0xFFFFFFFF),
    ],
)
def test_crossed_headers_rejected_by_both(native_sri2, tmp_path, turn_source, offset, value):
    raw = changed(turn_source[3]["heather.sri"], offset, "I", value)
    with pytest.raises(ValueError):
        reconstruct_sri2(raw)
    path = tmp_path / "bad.sri"
    path.write_bytes(raw)
    assert subprocess.run([native_sri2, path], capture_output=True).returncode == 2


def test_added_descriptor_bytes_and_truncations(turn_source):
    raw = turn_source[3]["heather.sri"]
    for offset in range(460, 500):
        bad = changed(raw, offset, "B", raw[offset] ^ 1)
        with pytest.raises(ValueError):
            reconstruct_sri2(bad)
    for end in (95, 459, 499, 500, 500 + 58 * 36 * 28, 500 + 78 * 36 * 28, len(raw) - 1):
        with pytest.raises(ValueError):
            reconstruct_sri2(raw[:end])


def test_sri1_limit_independent_from_payload_capacity():
    rig = own_wire()
    for name in ("source_bones", "channels", "descriptors"):
        del rig[name]
    rig["frames"] = [rig["frames"][0]] * 65
    with pytest.raises(ValueError, match="RI_COUNTS"):
        encode_rig(**rig, clip_id=101, increment=614)
    assert encode_rig_payload(**rig, max_samples=80)
    with pytest.raises(ValueError, match="RI_COUNTS"):
        encode_rig_payload(**rig, max_samples=81)
    with pytest.raises(ValueError, match="HI_SAMPLE_SELECTION"):
        prepare_heather_rig({}, {}, {}, range(78), max_samples=81)


def test_authenticated_publication_selects_profile_two(tmp_path, monkeypatch, turn_source):
    g, a, t, expected, _ = turn_source
    model, animation = b"invented-model", b"invented-animation"
    monkeypatch.setattr(producer, "MODEL_SHA256", hashlib.sha256(model).hexdigest())
    monkeypatch.setattr(producer, "ANIMATION_SHA256", hashlib.sha256(animation).hexdigest())
    monkeypatch.setattr(producer, "_decode_sources", lambda *_: (g, a, t))
    private, repo = tmp_path / "private", tmp_path / "repo"
    private.mkdir()
    repo.mkdir()
    report = publisher.publish_heather_locomotion(
        private, repo, "turns", model, animation, TURN_PAL, profile=2
    )
    assert report["source_verified"] and report["profile"] == "heather-original-pal-525-turns-v1"
    assert json.loads((private / "turns/manifest.json").read_text()) == report
    for name, raw in expected.items():
        assert (private / "turns" / name).read_bytes() == raw
    with pytest.raises(ValueError, match="HL_DESCRIPTORS"):
        producer.produce_heather_locomotion(model, animation, PAL, profile=2)
    altered = copy.deepcopy(a)
    altered["frames"][79]["tracks"][0]["translation"][0] += 1
    with pytest.raises(ValueError, match="HL_SOURCE_RECONSTRUCTION:TR"):
        audit_selection(expected, g, altered, t, TURN_PAL)
