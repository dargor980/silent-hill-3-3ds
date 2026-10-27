"""Independent reconstruction, producer/native interoperability and malformed packages."""

import ast
import copy
import math
import shlex
import struct
import subprocess
import zlib
from pathlib import Path

import pytest
import yaml
from test_locomotion_inspection import PAL, SAMPLES, own_locomotion_shape, own_wire

from tests.locomotion_rig_fixtures import changed, invalid_sri2, own_sri2
from tests.locomotion_rig_wire_oracle import check_dump
from tools.pipeline.locomotion_inspection import encode_locomotion_rig, heather_locomotion_rig
from tools.qa.locomotion_rig_oracle import reconstruct_sri2, reconstruct_sri2_bundle


@pytest.fixture(scope="module")
def native_sri2(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    out = tmp_path_factory.mktemp("native-sri2") / "reader"
    sources = [
        "tests/cpp/test_inspection_locomotion.cpp",
        "engine/domain/inspection_locomotion.cpp",
        "engine/domain/inspection_rig.cpp",
        "engine/domain/locomotion_clock.cpp",
        "engine/domain/locomotion_pose.cpp",
        "engine/domain/locomotion_update.cpp",
        "engine/domain/render_scene.cpp",
        "engine/domain/lifecycle.cpp",
        "engine/application/render_probe.cpp",
        "engine/application/locomotion_probe.cpp",
        "engine/platform/common/inspection_locomotion.cpp",
        "engine/platform/common/inspection_rig.cpp",
        "engine/platform/common/inspection_crc32.cpp",
        "engine/platform/common/stdio_files.cpp",
    ]
    includes = [
        "tests/cpp",
        "engine/domain/include",
        "engine/ports/include",
        "engine/application/include",
        "engine/platform/common/include",
    ]
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-O1",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            *["-I" + str(root / i) for i in includes],
            *[str(root / s) for s in sources],
            "-o",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return out


def test_all_producer_fields_reconstructed_independently_and_match_native(native_sri2, tmp_path):
    geometry, animation, textures = own_locomotion_shape()
    files, receipt = heather_locomotion_rig(geometry, animation, textures, PAL)
    expected = reconstruct_sri2_bundle(files)
    assert expected["sample_sources"] == list(SAMPLES)
    assert expected["clips"] == [
        [101, 10, 307, 0, 9, 1, 0, 0, 0],
        [109, 24, 1996, 80, 103, 1, 0, 10, 0],
        [113, 24, 2227, 176, 199, 1, 0, 34, 0],
    ]
    for i, bone in enumerate(expected["bones"]):
        mapping = receipt["bones"][i]
        assert bone == dict(
            source=mapping["source"], parent=mapping["compact_parent"], channel=mapping["channel"]
        )
    for packed, source in enumerate(SAMPLES):
        for bone, tr in zip(expected["bones"], expected["samples"][packed], strict=True):
            track = next(
                t
                for t in animation["frames"][source]["tracks"]
                if t["bone_index"] == bone["source"]
            )
            assert tr[3:] == pytest.approx(track["quaternion_xyzw"], rel=0, abs=1e-7)
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    for args in ([str(tmp_path / "heather.sri")], [str(tmp_path), "bundle"]):
        run = subprocess.run([native_sri2, *args], check=True, capture_output=True, text=True)
        check_dump(run.stdout, expected)
    subprocess.run([native_sri2], check=True, capture_output=True, text=True)


def test_exhaustive_truncation_rejects_every_byte_boundary():
    good = own_sri2()["heather.sri"]
    for end in range(len(good)):
        with pytest.raises(ValueError):
            reconstruct_sri2(good[:end])


def test_native_replay_anchor_uses_samples_and_retains_cache(native_sri2, tmp_path):
    files = own_sri2()
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    # The root's model translation
    # is its interpolated local value; the diagnostic anchor is an odd phase.
    for clip, first, count, inc in ((101, 0, 10, 614), (109, 80, 24, 3992), (113, 176, 24, 4454)):
        phase = (count - 1) * 4096 + 2048
        run = subprocess.run(
            [native_sri2, tmp_path, "trace"],
            input=f"{clip} {phase}\n0\n",
            capture_output=True,
            text=True,
            check=True,
        )
        rows = [list(map(float, line.split())) for line in run.stdout.splitlines()]
        assert len(rows) == 2 and len(rows[0]) == 6 + 36 * 16
        assert rows[0][:6] == [clip, clip, 1, (phase + inc) % (count * 4096), 0, 0]
        assert rows[0][6 + 12] == (first + (count - 1) / 2) / 16
    run = subprocess.run(
        [native_sri2, tmp_path, "trace"],
        input="109 2048\n101\n0\n",
        capture_output=True,
        text=True,
        check=True,
    )
    rows = [list(map(float, line.split())) for line in run.stdout.splitlines()]
    assert rows[1][:6] == [109, 101, 3, 0, 1280, 1]
    assert rows[2][:6] == [109, 101, 3, 0, 1640, 1]
    assert rows[2][18] == pytest.approx(rows[0][18] * (1 - 1640 / 4096), abs=1e-6)
    for bad in ("", "101", "999 0\n", "101 40960\n", "101 0\nx\n", "101 0\n113\n"):
        run = subprocess.run(
            [native_sri2, tmp_path, "trace"], input=bad, capture_output=True, text=True
        )
        assert run.returncode == 3


CASES = list(invalid_sri2(own_sri2()["heather.sri"]))


@pytest.mark.parametrize(("name", "raw"), CASES, ids=[name for name, _ in CASES])
def test_independent_reader_rejects_corrupt_wire(name, raw):
    with pytest.raises(ValueError, match="SRI2:"):
        reconstruct_sri2(raw)


@pytest.mark.parametrize("bad", [None, 0, "bytes", bytearray(own_sri2()["heather.sri"]), b""])
def test_input_types_are_explicit(bad):
    with pytest.raises(ValueError, match="SRI2:header"):
        reconstruct_sri2(bad)


@pytest.mark.parametrize(
    "fault",
    [
        "type",
        "missing_sri",
        "extra",
        "missing_first",
        "missing_last",
        "short",
        "long",
        "crc",
        "mutable",
    ],
)
def test_bundle_errors_leave_caller_and_previous_reconstruction_intact(fault):
    files = own_sri2()
    previous = reconstruct_sri2_bundle(files)
    saved = copy.deepcopy(previous)
    if fault == "type":
        files = []
    elif fault == "missing_sri":
        del files["heather.sri"]
    elif fault == "extra":
        files["unexpected.rgba"] = b""
    elif fault.startswith("missing"):
        del files["texture-00.rgba" if fault == "missing_first" else "texture-01.rgba"]
    elif fault == "short":
        files["texture-01.rgba"] = files["texture-01.rgba"][:-1]
    elif fault == "long":
        files["texture-01.rgba"] += b"\0"
    elif fault == "crc":
        files["texture-01.rgba"] = bytes(len(files["texture-01.rgba"]))
    elif fault == "mutable":
        files["texture-01.rgba"] = bytearray(files["texture-01.rgba"])
    before = copy.deepcopy(files)
    with pytest.raises(ValueError):
        previous = reconstruct_sri2_bundle(files)
    assert previous == saved and before == files


def test_unrepresented_data_and_texture_crc_do_not_claim_source_authentication():
    model = reconstruct_sri2_bundle(own_sri2())
    assert "source_verified" not in model
    assert len(model["samples"]) == 58 and len(model["bones"]) == 36
    assert "unselected_samples" not in model and "morph_targets" not in model


def test_minimum_geometry_and_padded_influences():
    d = own_wire()
    d["helpers"], d["targets"] = [], []
    for v in d["vertices"]:
        v.update(weights_q12=[4096], helper_indices=[])
    raw = encode_locomotion_rig(**d)
    model = reconstruct_sri2(raw)
    assert model["helpers"] == [] and model["vertices"][0][13:15] == [255, 255]
    vertex = 460 + 28 * 36 * 58
    for at, fmt, value in ((vertex + 18, "H", 1), (vertex + 24, "B", 0)):
        with pytest.raises(ValueError):
            reconstruct_sri2(changed(raw, at, fmt, value))


@pytest.mark.parametrize("norm", [0.999, 0.99900001, 0.99900002])
def test_producer_rejects_norm_that_rounds_outside_the_wire_contract(norm):
    d = own_wire()
    d["frames"][0][0][1] = [0, 0, 0, math.sqrt(norm)]
    with pytest.raises(ValueError, match="RI_ROTATION_F32"):
        encode_locomotion_rig(**d)


@pytest.mark.parametrize("norm", [0.9990001, 1.00099998, 1.001])
def test_representable_norm_boundary_agrees_with_native(native_sri2, tmp_path, norm):
    d = own_wire()
    d["frames"][0][0][1] = [0, 0, 0, math.sqrt(norm)]
    raw = encode_locomotion_rig(**d)
    expected = reconstruct_sri2(raw)
    path = tmp_path / "boundary.sri"
    path.write_bytes(raw)
    run = subprocess.run([native_sri2, path], capture_output=True, text=True, check=True)
    check_dump(run.stdout, expected)


def test_total_pixel_budget_is_independent_of_single_material_validity():
    raw = own_sri2()["heather.sri"]
    at = 460 + 28 * 36 * 58 + 2 * 68 + 3 * 28
    expanded = bytearray(raw[:at] + struct.pack("<27H", *([0, 1, 2] * 9)))
    for i in range(9):
        expanded.extend(struct.pack("<7I", i * 3, 3, i, 1024, 1024, 0, 0))
    struct.pack_into("<I", expanded, 24, 27)
    struct.pack_into("<I", expanded, 28, 9)
    struct.pack_into("<II", expanded, 56, len(expanded) - 96, zlib.crc32(expanded[96:]))
    with pytest.raises(ValueError, match="material_coverage"):
        reconstruct_sri2(bytes(expanded))


def test_oracle_imports_no_producer_or_runtime_and_has_ci_gate():
    path = Path("tools/qa/locomotion_rig_oracle.py")
    tree = ast.parse(path.read_text())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imports == {"math", "struct", "zlib"}
    assert not any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree))
    workflow = yaml.load(Path(".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    commands = [
        shlex.split(line)
        for s in workflow["jobs"]["quality"]["steps"]
        for line in s.get("run", "").splitlines()
    ]
    assert any(
        "tools.qa.coverage_gate" in c and "--files" in c and str(path) in c for c in commands
    )
