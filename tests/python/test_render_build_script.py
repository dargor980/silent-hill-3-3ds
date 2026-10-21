"""The synthetic renderer build must preserve prior evidence and fail closed."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(
    params=[
        "build_render_probe.sh",
        "build_texture_probe.sh",
        "build_geometry_probe.sh",
        "build_material_probe.sh",
        "build_animation_probe.sh",
        "build_character_probe.sh",
    ]
)
def script(request):
    return Path(__file__).resolve().parents[2] / "scripts" / request.param


@pytest.mark.parametrize("sdk", [None, ""])
def test_render_requires_sdk(tmp_path, sdk, script):
    env = {key: value for key, value in os.environ.items() if key != "DEVKITPRO"}
    if sdk is not None:
        env["DEVKITPRO"] = sdk
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", str(script), str(output)], env=env, capture_output=True, text=True, timeout=10
    )
    assert result.returncode != 0
    assert "DEVKITPRO" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("kind", ["directory", "file", "dangling_symlink"])
def test_render_preserves_existing_output(tmp_path, kind, script):
    output = tmp_path / "output"
    if kind == "directory":
        output.mkdir()
        (output / "sentinel").write_text("prior evidence")
    elif kind == "file":
        output.write_text("prior evidence")
    else:
        output.symlink_to(tmp_path / "missing")
    result = subprocess.run(
        ["bash", str(script), str(output)],
        env=dict(os.environ, DEVKITPRO=str(tmp_path)),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "already exists" in result.stderr
    if kind == "directory":
        assert (output / "sentinel").read_text() == "prior evidence"
        assert len(list(output.iterdir())) == 1
    elif kind == "file":
        assert output.read_text() == "prior evidence"
    else:
        assert output.is_symlink()


def test_configuration_failure_produces_no_success_hashes(tmp_path, script):
    fake_cmake = tmp_path / "cmake"
    fake_cmake.write_text("#!/bin/sh\nexit 17\n")
    fake_cmake.chmod(0o755)
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", str(script), str(output)],
        env=dict(os.environ, DEVKITPRO=str(tmp_path), PATH=f"{tmp_path}:{os.environ['PATH']}"),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 17
    assert not output.exists()
