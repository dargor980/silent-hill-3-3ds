import os
import subprocess
from pathlib import Path

import pytest

from tools.qa import custody
from tools.qa.check_repository import check_architecture, check_custody, check_specs, main

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.architecture
def test_repository_contracts():
    assert check_architecture(ROOT) == []
    assert check_custody(ROOT) == []
    assert check_specs(ROOT) == []
    assert main(["--root", str(ROOT)]) == 0


@pytest.mark.parametrize(
    "include",
    ["3ds.h", "filesystem", "sh3/platform/adapter.hpp", "../platform/test.hpp", "citro3d.h"],
)
def test_detects_forbidden_dependency(tmp_path, include):
    path = tmp_path / "engine/domain/test.cpp"
    path.parent.mkdir(parents=True)
    path.write_text(f"#include <{include}>\n")
    assert len(check_architecture(tmp_path)) == 1


def test_allows_domain_dependency(tmp_path):
    path = tmp_path / "engine/application/test.cpp"
    path.parent.mkdir(parents=True)
    path.write_text('#include "sh3/domain/lifecycle.hpp"\n#include <array>\n')
    assert check_architecture(tmp_path) == []


def test_custody_checks_ignored_binary_extensions(tmp_path):
    (tmp_path / "B0.MFA").write_bytes(b"synthetic test only")
    generated = tmp_path / "build/diagnostic.3dsx"
    generated.parent.mkdir()
    generated.write_bytes(b"synthetic test only")
    assert len(check_custody(tmp_path)) == 1


def test_private_inbox_requires_git_ignore_and_rejects_tracked_content(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init")
    inbox = tmp_path / "binaries"
    inbox.mkdir()
    (inbox / "test.iso").write_bytes(b"synthetic only")
    assert check_custody(tmp_path)
    (inbox / ".gitignore").write_text("*\n!.gitignore\n")
    assert check_custody(tmp_path) == []
    (inbox / "test.mfa").write_bytes(b"synthetic only")
    assert check_custody(tmp_path)
    (inbox / "test.mfa").unlink()
    git("add", "-f", "binaries/test.iso")
    assert any("tracked by Git" in error for error in check_custody(tmp_path))


def test_force_added_private_report_is_rejected(tmp_path):
    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, capture_output=True)
    report = tmp_path / "reports/local/test.json"
    report.parent.mkdir(parents=True)
    report.write_text("{}")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
    assert any("tracked by Git" in error for error in check_custody(tmp_path))


@pytest.fixture
def private_repository(tmp_path):
    """A real Git index, containing only synthetic bytes, exercises ignore policy."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
    (root / ".gitignore").write_text(
        "/binaries/*\n!/binaries/.gitignore\n/reports/local/\n/build/\n"
    )
    return root


@pytest.mark.parametrize(
    "name",
    [
        "binaries/notes.txt",
        "binaries/archive.afs",
        "binaries/nested/build/B0.MFA",
        "reports/local/copy.iso",
        "reports/local/converted.bin",
        "build/original.iso",
        "src/build/B0.MFA",
        "src/.venv/audio.afs",
        "src/.git/disc.img",
        "assets/driver.irx",
    ],
)
def test_rejects_private_data_in_wrong_locations(private_repository, name):
    path = private_repository / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"synthetic custody test only")
    assert check_custody(private_repository), name


@pytest.mark.parametrize("name", ["binaries", "binaries/linked", "reports/local"])
def test_rejects_symlinked_private_directories(private_repository, tmp_path, name):
    external = tmp_path / "external"
    external.mkdir()
    link = private_repository / name
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(external, target_is_directory=True)
    assert check_custody(private_repository)


@pytest.mark.parametrize("exists", [True, False])
def test_rejects_regular_and_dangling_iso_symlinks(private_repository, tmp_path, exists):
    external = tmp_path / "synthetic.iso"
    if exists:
        external.write_bytes(b"synthetic only")
    inbox = private_repository / "binaries"
    inbox.mkdir()
    (inbox / "link.iso").symlink_to(external)
    assert check_custody(private_repository)


def test_metadata_reports_must_be_ignored(private_repository):
    report = private_repository / "reports/local/profile.json"
    report.parent.mkdir(parents=True)
    report.write_text("{}")
    assert check_custody(private_repository) == []
    (private_repository / ".gitignore").write_text("")
    assert check_custody(private_repository)


def test_iso_exception_requires_a_regular_file(private_repository):
    (private_repository / "binaries/fake.iso").mkdir(parents=True)
    assert check_custody(private_repository)


def test_accepts_local_metadata_iso_and_generated_builds(private_repository):
    for name in [
        "binaries/disc.iso",
        "binaries/.gitignore",
        "reports/local/profile.json",
        "build/diagnostic.3dsx",
        "build/compiler-probe.bin",
        "build/diagnostic.elf",
    ]:
        path = private_repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic only")
    assert check_custody(private_repository) == []


def test_rejects_force_added_build_and_inbox_metadata(private_repository):
    for name in ["binaries/disguised.json", "build/diagnostic.elf"]:
        path = private_repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic only")
        subprocess.run(
            ["git", "-C", str(private_repository), "add", "-f", name],
            check=True,
            capture_output=True,
        )
    errors = check_custody(private_repository)
    assert sum("tracked by Git" in error for error in errors) == 2


def test_known_build_environment_is_excluded_without_hiding_nested_assets(private_repository):
    environment = private_repository / "build/linux-venv/bin"
    environment.mkdir(parents=True)
    (environment / "python").symlink_to("missing-interpreter")
    assert check_custody(private_repository) == []
    (private_repository / "build/B0.MFA").write_bytes(b"synthetic only")
    assert check_custody(private_repository)


def test_custody_fails_closed_when_git_is_unavailable(private_repository, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("synthetic failure")

    monkeypatch.setattr(custody.subprocess, "run", fail)
    assert "Cannot verify Git custody" in check_custody(private_repository)[0]


def test_custody_cannot_accept_unreadable_root(tmp_path):
    assert check_custody(tmp_path / "missing") == ["Cannot inspect repository directory metadata"]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX special-file regression")
def test_custody_rejects_fifo_without_opening_it(private_repository):
    inbox = private_repository / "binaries"
    inbox.mkdir()
    os.mkfifo(inbox / "pipe.iso")
    assert check_custody(private_repository)


def test_spec_validator_fails_on_missing_coverage_and_bad_link(tmp_path):
    path = tmp_path / "docs/specs/sh3-3ds"
    path.mkdir(parents=True)
    (path / "requirements.md").write_text("- **RF01.01 [E]** WHEN test THEN app SHALL test.\n")
    (path / "tasks.md").write_text("RF01.02 [bad](missing.md)\n")
    (path / "validation.md").write_text("")
    errors = check_specs(tmp_path)
    assert len(errors) == 4


def test_spec_validator_rejects_duplicates_and_cross_ranges(tmp_path):
    path = tmp_path / "docs/specs/sh3-3ds"
    path.mkdir(parents=True)
    (path / "requirements.md").write_text("- **RF01.01 [E]** test\n" * 2)
    (path / "tasks.md").write_text("RF01.01")
    (path / "validation.md").write_text("| V01 | RF01.01-RF02.01 |")
    assert len(check_specs(tmp_path)) == 3
