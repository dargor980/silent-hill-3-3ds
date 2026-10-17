"""RF01.01-.06, RNF06.04: synthetic inputs only."""

import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.pipeline.profile import ProfileError, parse_profile, safe_relative_path, verify_profile
from tools.pipeline.verify import LocalFileInspector, load_profile, main, verify_local

PAYLOAD = b"SH3 synthetic fixture; no game data.\n"


@pytest.fixture
def profile():
    return {
        "schema_version": 1,
        "id": "synthetic-v1",
        "platform": "synthetic",
        "region": "test",
        "revision": "1",
        "serial": "SYNTHETIC",
        "language": "es",
        "extractor_version": "not-applicable",
        "capabilities": ["identification"],
        "files": [
            {
                "path": "sample.txt",
                "size": len(PAYLOAD),
                "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
            }
        ],
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    [
        "/abs",
        "../escape",
        "a/../b",
        "a//b",
        "./a",
        "a/",
        "C:/a",
        "a\\b",
        "a\x00b",
        "a\nb",
        "",
        42,
        "x" * 1025,
    ],
)
def test_reject_unsafe_paths(path):
    with pytest.raises(ProfileError, match="path"):
        safe_relative_path(path)


@pytest.mark.unit
@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("id", "bad id"),
        ("platform", "pc"),
        ("region", ""),
        ("serial", None),
        ("revision", "x" * 257),
        ("language", []),
        ("extractor_version", ""),
        ("capabilities", ["a", "a"]),
        ("capabilities", [" "]),
        ("capabilities", [{}]),
        ("capabilities", "not-a-list"),
        ("files", []),
        ("files", ["bad"]),
        ("files", [1] * 10001),
    ],
)
def test_reject_invalid_profile(profile, field, value):
    profile[field] = value
    with pytest.raises(ProfileError):
        parse_profile(profile)


@pytest.mark.unit
@pytest.mark.parametrize(
    "field,value",
    [
        ("size", True),
        ("size", -1),
        ("size", 1 << 64),
        ("size", 1.5),
        ("sha256", "abc"),
        ("sha256", 42),
    ],
)
def test_reject_invalid_file_metadata(profile, field, value):
    profile["files"][0][field] = value
    with pytest.raises(ProfileError):
        parse_profile(profile)


def test_reject_non_object():
    with pytest.raises(ProfileError):
        parse_profile([])


def test_case_ambiguous_duplicates(profile):
    duplicate = copy.deepcopy(profile["files"][0])
    duplicate["path"] = "SAMPLE.txt"
    profile["files"].append(duplicate)
    with pytest.raises(ProfileError, match="Duplicate"):
        parse_profile(profile)


@pytest.mark.integration
def test_real_files_and_inspector_contract(profile, tmp_path):
    (tmp_path / "sample.txt").write_bytes(PAYLOAD)
    parsed = parse_profile(profile)

    class MemoryInspector:
        def inspect(self, path):
            assert path == "sample.txt"
            return len(PAYLOAD), hashlib.sha256(PAYLOAD).hexdigest()

    # Same policy with a filesystem and memory adapter: LSP/DIP contract.
    for inspector in (MemoryInspector(), LocalFileInspector(tmp_path)):
        verify_profile(parsed, inspector)
    assert (tmp_path / "sample.txt").read_bytes() == PAYLOAD


@pytest.mark.integration
@pytest.mark.parametrize(
    "data,code", [(b"short", "SIZE_MISMATCH"), (b"x" * len(PAYLOAD), "HASH_MISMATCH")]
)
def test_modified_file_rejected(profile, tmp_path, data, code):
    (tmp_path / "sample.txt").write_bytes(data)
    with pytest.raises(ProfileError) as error:
        verify_profile(parse_profile(profile), LocalFileInspector(tmp_path))
    assert error.value.code == code


def test_missing_and_symlink(profile, tmp_path):
    inspector = LocalFileInspector(tmp_path)
    with pytest.raises(ProfileError, match="Missing"):
        verify_profile(parse_profile(profile), inspector)
    (tmp_path / "actual.txt").write_bytes(PAYLOAD)
    (tmp_path / "sample.txt").symlink_to(tmp_path / "actual.txt")
    with pytest.raises(ProfileError, match="Symlinks"):
        verify_profile(parse_profile(profile), inspector)


def test_bad_root_and_nested_symlink(tmp_path):
    with pytest.raises(ProfileError, match="directory"):
        LocalFileInspector(tmp_path / "absent")
    (tmp_path / "link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ProfileError, match="Symlinks"):
        LocalFileInspector(tmp_path).inspect("link/test.txt")


@pytest.mark.parametrize("platform", ["synthetic", "ps2"])
def test_data_root_symlink_is_rejected_before_reading(profile, tmp_path, platform):
    profile["platform"] = platform
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "sample.txt").write_bytes(PAYLOAD)
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ProfileError) as error:
        verify_local(parse_profile(profile), alias, tmp_path / "repo")
    assert error.value.code == "INVALID_PATH"


@pytest.mark.parametrize(
    "key",
    [
        "schema_version",
        "id",
        "platform",
        "region",
        "revision",
        "serial",
        "language",
        "extractor_version",
        "capabilities",
        "files",
    ],
)
def test_required_profile_field_cannot_be_omitted(profile, key):
    del profile[key]
    with pytest.raises(ProfileError) as error:
        parse_profile(profile)
    assert error.value.code == "INVALID_PROFILE"


def test_io_error_is_typed(tmp_path):
    (tmp_path / "sample.txt").write_bytes(PAYLOAD)
    with patch.object(Path, "open", side_effect=PermissionError):
        with pytest.raises(ProfileError) as error:
            LocalFileInspector(tmp_path).inspect("sample.txt")
    assert error.value.code == "READ_ERROR"


@pytest.mark.parametrize("location", ["inside", "ancestor"])
def test_ps2_data_cannot_be_in_checkout(profile, tmp_path, location):
    repository = tmp_path / "repo"
    repository.mkdir()
    profile["platform"] = "ps2"
    root = repository if location == "inside" else tmp_path
    with pytest.raises(ProfileError) as error:
        verify_local(parse_profile(profile), root, repository)
    assert error.value.code == "PRIVATE_DATA_IN_REPO"


@pytest.mark.parametrize("raw", [b"not json", b"\xff", b" " * (1024 * 1024 + 1)])
def test_bad_profile_files(tmp_path, raw):
    file = tmp_path / "profile.json"
    file.write_bytes(raw)
    with pytest.raises(ProfileError):
        load_profile(file)


def test_missing_profile(tmp_path):
    with pytest.raises(ProfileError) as error:
        load_profile(tmp_path / "missing.json")
    assert error.value.code == "PROFILE_READ_ERROR"


@pytest.mark.integration
def test_cli_success_and_rejection(profile, tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    args = ["--profile", str(path), "--data-root", str(tmp_path)]
    assert main(args) == 1
    failure = json.loads(capsys.readouterr().out)
    assert failure["code"] == "MISSING_FILE"
    assert str(tmp_path) not in failure["message"]
    (tmp_path / "sample.txt").write_bytes(PAYLOAD)
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["extraction"] == "not_performed"
