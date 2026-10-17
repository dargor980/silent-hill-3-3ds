"""Artifact integrity and build failure propagation with synthetic bytes only."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.debug.bundle import MANIFEST, create, fingerprint
from tools.qa.build_artifacts import CHECKSUM_FILES, FILES, RECEIPT, check, main

ROOT = Path(__file__).resolve().parents[2]
BUILD_ID = "0123456789ab"


def checksums(directory):
    (directory / "SHA256SUMS").write_text(
        "".join(
            f"{fingerprint(directory / name)['sha256']}  build/3ds/{name}\n"
            for name in CHECKSUM_FILES
        )
    )


@pytest.fixture
def artifacts(tmp_path):
    directory = tmp_path / "artifacts"
    directory.mkdir()
    (directory / "sh3_diagnostic.3dsx").write_bytes(b"3DSXsynthetic")
    (directory / "sh3_diagnostic.elf").write_bytes(b"\x7fELF\x01\x01" + bytes(12) + b"\x28\x00")
    (directory / "sh3_diagnostic.smdh").write_bytes(b"SMDH" + bytes(14012))
    probe = tmp_path / "probe.txt"
    probe.write_text("synthetic probe\n")
    shutil.copyfile(probe, directory / "probe.txt")
    sdk = tmp_path / "sdk.txt"
    sdk.write_text("devkitpro/devkitarm@sha256:" + "a" * 64 + "\n")
    (directory / "build-id.txt").write_text(BUILD_ID + "\n")
    (directory / "toolchain-packages.txt").write_text("synthetic-package 1.0\n")
    create(directory, BUILD_ID)
    checksums(directory)
    return directory, probe, sdk


def arguments(artifacts):
    directory, probe, sdk = artifacts
    return ["--directory", str(directory), "--probe", str(probe), "--sdk-image", str(sdk)]


def test_complete_build_and_exclusive_receipt(artifacts, capsys):
    directory, _, _ = artifacts
    assert main(arguments(artifacts) + ["--record"]) == 0
    before = (directory / RECEIPT).read_bytes()
    document = json.loads(before)
    assert document["build_id"] == BUILD_ID
    assert set(document["files"]) == set(FILES)
    assert document == check(*artifacts)
    assert main(arguments(artifacts)) == 0  # Read-only repeat verification.
    assert main(arguments(artifacts) + ["--record"]) == 1
    assert (directory / RECEIPT).read_bytes() == before
    assert "FAIL" in capsys.readouterr().out


@pytest.mark.parametrize(
    "mutation", ["missing", "empty", "symlink", "large", "altered", "packages", "sdk"]
)
def test_read_only_verification_requires_unchanged_receipt(artifacts, mutation):
    directory, probe, sdk = artifacts
    assert main(arguments(artifacts) + ["--record"]) == 0
    receipt = directory / RECEIPT
    original = receipt.read_bytes()
    if mutation in {"missing", "empty", "symlink"}:
        receipt.unlink()
        if mutation == "empty":
            receipt.touch()
        elif mutation == "symlink":
            receipt.symlink_to(probe)
    elif mutation == "large":
        receipt.write_text("x" * 8193)
    elif mutation == "altered":
        receipt.write_text("{}")
    elif mutation == "packages":
        (directory / "toolchain-packages.txt").write_text("another-package 1.0\n")
    else:
        sdk.write_text("devkitpro/devkitarm@sha256:" + "b" * 64 + "\n")
    assert main(arguments(artifacts)) == 1
    if mutation in {"packages", "sdk"}:
        assert receipt.read_bytes() == original


@pytest.mark.parametrize("name", FILES)
@pytest.mark.parametrize("mutation", ["missing", "empty", "symlink"])
def test_every_required_output_is_enforced(artifacts, name, mutation):
    directory, probe, _ = artifacts
    path = directory / name
    path.unlink()
    if mutation == "empty":
        path.write_bytes(b"")
    elif mutation == "symlink":
        path.symlink_to(probe)
    assert main(arguments(artifacts) + ["--record"]) == 1
    assert not (directory / RECEIPT).exists()


@pytest.mark.parametrize("name", FILES[:5])
def test_mixed_build_rejected(artifacts, name):
    directory, _, _ = artifacts
    path = directory / name
    data = path.read_bytes()
    path.write_bytes(bytes([data[0] ^ 1]) + data[1:])
    assert main(arguments(artifacts)) == 1


@pytest.mark.parametrize(
    "name,data,error",
    [
        ("sh3_diagnostic.3dsx", b"wrong magic", "INVALID_HEADER"),
        ("sh3_diagnostic.elf", b"wrong magic", "INVALID_HEADER"),
        ("sh3_diagnostic.elf", b"\x7fELF\x01\x01" + bytes(14), "ELF_NOT_ARM"),
        ("sh3_diagnostic.smdh", b"wrong magic", "INVALID_HEADER"),
        ("sh3_diagnostic.smdh", b"SMDH", "INVALID_SMDH_SIZE"),
        ("probe.txt", b"a different synthetic probe", "FIXTURE_MISMATCH"),
    ],
)
def test_invalid_outputs_rejected_even_with_matching_hashes(artifacts, name, data, error):
    directory, _, _ = artifacts
    (directory / name).write_bytes(data)
    (directory / MANIFEST).unlink()
    create(directory, BUILD_ID)
    checksums(directory)
    with pytest.raises(ValueError, match=error):
        check(*artifacts)


@pytest.mark.parametrize(
    "name,data,error",
    [
        ("build-id.txt", BUILD_ID, "INVALID_BUILD_ID_FILE"),
        ("build-id.txt", "a" * 14, "METADATA_TOO_LARGE"),
        (MANIFEST, "a" * 4097, "METADATA_TOO_LARGE"),
        ("SHA256SUMS", "a" * 4097, "METADATA_TOO_LARGE"),
        ("toolchain-packages.txt", "a" * 1048577, "METADATA_TOO_LARGE"),
        ("SHA256SUMS", "a" * 64 + "  ../../other\n", "CHECKSUMS_MISMATCH"),
    ],
)
def test_invalid_metadata(artifacts, name, data, error):
    directory, _, _ = artifacts
    (directory / name).write_text(data)
    with pytest.raises(ValueError, match=error):
        check(*artifacts)


@pytest.mark.parametrize("image", ["devkitpro/devkitarm:latest\n", "a" * 257])
def test_sdk_must_be_pinned(artifacts, image):
    _, _, sdk = artifacts
    sdk.write_text(image)
    with pytest.raises(ValueError, match="INVALID_SDK_IMAGE"):
        check(*artifacts)


@pytest.fixture
def build_project(tmp_path, artifacts):
    """The real shell script runs with injected tool failures, no compiler required."""
    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/build_3ds.sh", root / "scripts/build_3ds.sh")
    shutil.copytree(ROOT / "tools", root / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    (root / "tests/fixtures/synthetic").mkdir(parents=True)
    shutil.copyfile(artifacts[1], root / "tests/fixtures/synthetic/probe.txt")
    (root / "toolchains").mkdir()
    shutil.copyfile(artifacts[2], root / "toolchains/devkitpro-image.txt")
    output = root / "build/3ds"
    shutil.copytree(artifacts[0], output)
    (output / MANIFEST).unlink()
    binaries = tmp_path / "bin"
    binaries.mkdir()
    (binaries / "python3").symlink_to(sys.executable)
    # sha256sum is not installed on every macOS host. This double uses real hashes.
    (binaries / "sha256sum").write_text(
        f"#!{sys.executable}\nimport hashlib, pathlib, sys\n"
        "for arg in sys.argv[1:]:\n"
        " print(hashlib.sha256(pathlib.Path(arg).read_bytes()).hexdigest() + '  ' + arg)\n"
    )
    (binaries / "sha256sum").chmod(0o755)
    return root, binaries


@pytest.mark.parametrize("failure", ["configure", "compile", "packages", "missing_smdh", None])
def test_build_script_propagates_failures(build_project, failure):
    root, binaries = build_project
    (binaries / "cmake").write_text(
        '#!/bin/bash\nif [[ "$1" == "--build" ]]; then\n'
        f"exit {23 if failure == 'compile' else 0}\nelse\n"
        f"exit {22 if failure == 'configure' else 0}\nfi\n"
    )
    (binaries / "dkp-pacman").write_text(
        '#!/bin/bash\nprintf "synthetic-package 1.0\\n"\n'
        f"exit {24 if failure == 'packages' else 0}\n"
    )
    for name in ["cmake", "dkp-pacman"]:
        (binaries / name).chmod(0o755)
    if failure == "missing_smdh":
        (root / "build/3ds/sh3_diagnostic.smdh").unlink()
    env = dict(os.environ, DEVKITPRO="synthetic-sdk", PATH=f"{binaries}:{os.environ['PATH']}")
    result = subprocess.run(
        [
            "bash",
            "-e",
            "-o",
            "pipefail",
            "-c",
            "bash scripts/build_3ds.sh 2>&1 | tee build.log",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == (failure is None), result.stdout + result.stderr
    assert (root / "build.log").is_file()
    receipt = root / "build/3ds" / RECEIPT
    assert receipt.exists() == (failure is None)
    if failure is None:
        before = receipt.read_bytes()
        repeat = subprocess.run(
            ["bash", "scripts/build_3ds.sh"], cwd=root, env=env, capture_output=True, text=True
        )
        assert repeat.returncode != 0
        assert "Recorded debug bundle" in repeat.stderr
        assert receipt.read_bytes() == before


@pytest.mark.parametrize("preset", ["host-debug", "host-release", "host-sanitize", "host-coverage"])
@pytest.mark.parametrize("scenario", ["empty", "failure", "success"])
def test_ctest_presets_fail_closed(tmp_path, preset, scenario):
    shutil.copyfile(ROOT / "CMakePresets.json", tmp_path / "CMakePresets.json")
    directory = tmp_path / "build" / preset
    directory.mkdir(parents=True)
    command = (
        ""
        if scenario == "empty"
        else f'add_test(case "cmake" "-E" "{"true" if scenario == "success" else "false"}")\n'
    )
    (directory / "CTestTestfile.cmake").write_text(command)
    result = subprocess.run(
        ["ctest", "--preset", preset, "--output-junit", "test-results.xml"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == (scenario == "success"), result.stdout + result.stderr
    if scenario == "empty":
        assert "No tests were found" in result.stderr
    else:
        assert (directory / "test-results.xml").stat().st_size > 0
