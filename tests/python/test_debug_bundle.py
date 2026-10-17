import json
import os
from pathlib import Path

import pytest

from tools.debug.bundle import FILES, MANIFEST, BundleError, create, main, verify

BUILD = "0123456789ab"


@pytest.fixture
def bundle(tmp_path):
    for name in FILES:
        (tmp_path / name).write_bytes(b"synthetic fixture: " + name.encode())
    create(tmp_path, BUILD)
    return tmp_path


def test_round_trip_and_cli(bundle, capsys):
    document = verify(bundle, bundle / MANIFEST, BUILD)
    assert set(document["files"]) == set(FILES)
    assert main(["verify", "--directory", str(bundle), "--build-id", BUILD]) == 0
    assert "PASS" in capsys.readouterr().out


@pytest.mark.parametrize("name", FILES)
@pytest.mark.parametrize("operation", ["different_build", "truncated", "missing", "empty"])
def test_mismatched_pair_rejected(bundle, name, operation):
    path = bundle / name
    if operation == "different_build":
        original = path.read_bytes()
        path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    elif operation == "truncated":
        path.write_bytes(path.read_bytes()[:-1])
    elif operation == "missing":
        path.unlink()
    else:
        path.write_bytes(b"")
    with pytest.raises((BundleError, OSError)):
        verify(bundle, bundle / MANIFEST, BUILD)


def test_wrong_session_id(bundle):
    with pytest.raises(BundleError, match="BUILD_ID_MISMATCH"):
        verify(bundle, bundle / MANIFEST, "abcdef012345")


@pytest.mark.parametrize("identity", ["", "123", "../../secret", "0" * 13, "A" * 12, None])
def test_invalid_id_does_not_write(tmp_path, identity):
    with pytest.raises(BundleError, match="INVALID_BUILD_ID"):
        create(tmp_path, identity)
    assert not (tmp_path / MANIFEST).exists()


def test_preserve_recorded_evidence(bundle):
    before = (bundle / MANIFEST).read_bytes()
    with pytest.raises(FileExistsError):
        create(bundle, BUILD)
    assert (bundle / MANIFEST).read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: [],
        lambda d: {**d, "schema_version": True},
        lambda d: {**d, "schema_version": 2},
        lambda d: {**d, "extra": 1},
        lambda d: {**d, "files": []},
        lambda d: {**d, "files": {"../unexpected": {}}},
        lambda d: {**d, "files": {**d["files"], FILES[0]: []}},
        lambda d: {**d, "files": {**d["files"], FILES[0]: {"bytes": True, "sha256": "0" * 64}}},
        lambda d: {**d, "files": {**d["files"], FILES[0]: {"bytes": 0, "sha256": "0" * 64}}},
        lambda d: {**d, "files": {**d["files"], FILES[0]: {"bytes": 1, "sha256": 0}}},
        lambda d: {**d, "files": {**d["files"], FILES[0]: {"bytes": 1, "sha256": "bad"}}},
    ],
)
def test_invalid_manifest(bundle, mutation):
    path = bundle / MANIFEST
    path.write_text(json.dumps(mutation(json.loads(path.read_text()))))
    with pytest.raises(BundleError):
        verify(bundle, path, BUILD)


@pytest.mark.parametrize("contents", ["{broken", "x" * 4097, "\ud800"])
def test_malformed_or_large_manifest(bundle, contents):
    (bundle / MANIFEST).write_bytes(contents.encode("utf-8", errors="surrogatepass"))
    assert main(["verify", "--directory", str(bundle), "--build-id", BUILD]) == 1


@pytest.mark.parametrize("name", [*FILES, MANIFEST])
@pytest.mark.parametrize("kind", ["symlink", "fifo", "directory"])
def test_special_files_rejected(bundle, name, kind):
    path = bundle / name
    path.unlink()
    if kind == "symlink":
        target = bundle / "target"
        target.write_bytes(b"not evidence")
        path.symlink_to(target)
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.mkdir()
    with pytest.raises(BundleError):
        verify(bundle, bundle / MANIFEST, BUILD)


def test_cli_create_and_explicit_manifest(tmp_path):
    for name in FILES:
        (tmp_path / name).write_bytes(b"synthetic")
    args = ["--directory", str(tmp_path), "--build-id", BUILD]
    assert main(["create", *args]) == 0
    manifest = tmp_path / "session.json"
    (tmp_path / MANIFEST).rename(manifest)
    assert main(["verify", *args, "--manifest", str(manifest)]) == 0
    with pytest.raises(SystemExit):
        main(["create", *args, "--manifest", str(manifest)])


def test_build_preserves_bundle_before_compilation(bundle):
    import subprocess

    root = Path(__file__).resolve().parents[2]
    scripts = bundle / "scripts"
    scripts.mkdir()
    (scripts / "build_3ds.sh").write_bytes((root / "scripts/build_3ds.sh").read_bytes())
    output = bundle / "build/3ds"
    output.mkdir(parents=True)
    recorded = output / MANIFEST
    recorded.write_text("earlier evidence")
    result = subprocess.run(
        ["bash", str(scripts / "build_3ds.sh")],
        env={**os.environ, "DEVKITPRO": "/unused"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 1
    assert "Recorded debug bundle already exists" in result.stderr
    assert recorded.read_text() == "earlier evidence"
