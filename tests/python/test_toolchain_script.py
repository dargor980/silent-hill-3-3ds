"""Build entry points must fail before writing misleading SDK evidence."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_3ds_toolchain.sh"


@pytest.mark.parametrize("devkitpro", [None, ""])
def test_missing_sdk_creates_no_evidence(tmp_path, devkitpro):
    env = {k: v for k, v in os.environ.items() if k not in {"DEVKITPRO", "DEVKITARM"}}
    if devkitpro is not None:
        env["DEVKITPRO"] = devkitpro
    output = tmp_path / "evidence"
    result = subprocess.run(
        ["bash", str(SCRIPT), str(output)], env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "DEVKITPRO is required" in result.stderr
    assert not output.exists()


def test_invalid_sdk_creates_no_evidence(tmp_path):
    env = dict(os.environ, DEVKITPRO=str(tmp_path), DEVKITARM=str(tmp_path / "arm"))
    output = tmp_path / "evidence"
    result = subprocess.run(
        ["bash", str(SCRIPT), str(output)], env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "Incomplete SDK" in result.stderr
    assert not output.exists()


def test_missing_devkitarm_creates_no_evidence(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "DEVKITARM"}
    env["DEVKITPRO"] = str(tmp_path)
    output = tmp_path / "evidence"
    result = subprocess.run(
        ["bash", str(SCRIPT), str(output)], env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "DEVKITARM is required" in result.stderr
    assert not output.exists()


def test_existing_evidence_is_preserved(tmp_path):
    output = tmp_path / "evidence"
    output.mkdir()
    sentinel = output / "result.txt"
    sentinel.write_text("previous failed build\n")
    result = subprocess.run(["bash", str(SCRIPT), str(output)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Output already exists" in result.stderr
    assert sentinel.read_text() == "previous failed build\n"
    assert list(output.iterdir()) == [sentinel]
