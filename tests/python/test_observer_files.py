"""AC05/08/09: real temporary files, cooperative locking and injected I/O failures."""

import hashlib
import json
import os
import stat
from contextlib import contextmanager

import pytest

from tools.inspectors import observer_files as files
from tools.inspectors.observation_capture import ProfileError


@pytest.fixture
def setup(tmp_path):
    root, repository = tmp_path / "private", tmp_path / "repo"
    root.mkdir(mode=0o700)
    repository.mkdir()
    return root, repository


def put(root, name="state.p2s", data=b"own state"):
    target = root / name
    target.write_bytes(data)
    target.chmod(0o600)
    return target


def test_owned_read_write_lock_reuse_and_no_overwrite(setup):
    root, repository = setup
    store = files.PrivateAcquisitionStore(root, repository)
    with store:
        store.absent("state.p2s")
        put(root)
        assert store.read("state.p2s") == (b"own state", hashlib.sha256(b"own state").hexdigest())
        store.put("packet.bin", b"private packet")
        with pytest.raises(FileExistsError):
            store.put("packet.bin", b"replacement")
    assert store.parent is store.lock is None
    assert (root / "packet.bin").read_bytes() == b"private packet"
    with pytest.raises(ProfileError):
        store.__enter__()
    with files.PrivateAcquisitionStore(root, repository):
        pass


def test_lock_excludes_second_coordinator_and_cannot_be_replaced(setup):
    root, repository = setup
    with files.PrivateAcquisitionStore(root, repository):
        second = files.PrivateAcquisitionStore(root, repository)
        with pytest.raises(BlockingIOError):
            second.__enter__()
        assert second.parent is second.lock is None
    with pytest.raises(ProfileError):
        with files.PrivateAcquisitionStore(root, repository):
            (root / ".observer.lock").rename(root / "old.lock")
            put(root, ".observer.lock", b"")


@pytest.mark.parametrize("variant", ["mode", "symlink", "hardlink", "empty", "fifo", "large"])
def test_state_file_rejections(setup, variant):
    root, repository = setup
    path = put(root)
    if variant == "mode":
        path.chmod(0o644)
    if variant == "symlink":
        path.rename(root / "target")
        path.symlink_to(root / "target")
    if variant == "hardlink":
        os.link(path, root / "link")
    if variant == "empty":
        path.write_bytes(b"")
    if variant == "fifo":
        path.unlink()
        os.mkfifo(path, 0o600)
    if variant == "large":
        with path.open("wb") as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
    with files.PrivateAcquisitionStore(root, repository) as store:
        with pytest.raises((ProfileError, OSError)):
            store.read("state.p2s")


@pytest.mark.parametrize("name", ["../state", "a/b", "a\\b", "a\0b", ".", "..", "", "a" * 129])
def test_path_rejected_before_io(setup, name):
    with files.PrivateAcquisitionStore(*setup) as store:
        with pytest.raises(ProfileError):
            store.absent(name)


@pytest.mark.parametrize("name", ["state.p2s", "state.p2s.backup"])
def test_prior_state_or_backup_rejected(setup, name):
    root, repository = setup
    put(root, name)
    with files.PrivateAcquisitionStore(root, repository) as store:
        with pytest.raises(ProfileError):
            store.absent("state.p2s")


@pytest.mark.parametrize("variant", ["state", "packet", "directory"])
def test_late_changes_prevent_successful_close(setup, variant):
    root, repository = setup
    store = files.PrivateAcquisitionStore(root, repository)
    with pytest.raises(ProfileError):
        with store:
            put(root)
            store.read("state.p2s")
            store.put("packet.bin", b"packet")
            if variant == "directory":
                root.rename(root.parent / "moved")
                root.mkdir(mode=0o700)
            else:
                (root / ("state.p2s" if variant == "state" else "packet.bin")).write_bytes(
                    b"changed"
                )
    assert store.parent is store.lock is None


@pytest.mark.parametrize(
    "variant", ["root_mode", "root_symlink", "lock_mode", "in_repo", "ancestor"]
)
def test_root_and_lock_rejected(setup, variant):
    root, repository = setup
    if variant == "root_mode":
        root.chmod(0o755)
    if variant == "root_symlink":
        root.rename(root.parent / "target")
        root.symlink_to(root.parent / "target")
    if variant == "lock_mode":
        put(root, ".observer.lock").chmod(0o644)
    if variant == "in_repo":
        root = repository
    if variant == "ancestor":
        root = repository.parent
    with pytest.raises((ProfileError, OSError)):
        with files.PrivateAcquisitionStore(root, repository):
            pass


def test_failed_lock_close_still_closes_parent_once(setup, monkeypatch):
    store = files.PrivateAcquisitionStore(*setup)
    store.__enter__()
    lock, parent = store.lock, store.parent
    close = os.close
    calls = []

    def failing(fd):
        calls.append(fd)
        close(fd)
        if fd == lock:
            raise OSError("private close")

    monkeypatch.setattr(os, "close", failing)
    with pytest.raises(ProfileError) as caught:
        store.__exit__(None, None, None)
    assert caught.value.code == "ACQUIRE_CLOSE"
    assert calls.count(lock) == calls.count(parent) == 1


@pytest.mark.parametrize("operation", ["write", "flush", "fsync", "close", "readback"])
def test_packet_write_failures_reject(setup, monkeypatch, operation):
    owned = files._owned_stream

    @contextmanager
    def wrapped(fd, mode):
        with owned(fd, mode) as stream:

            class Proxy:
                def __getattr__(self, name):
                    if name == operation or operation == "readback" and name == "read":
                        return lambda *_: (_ for _ in ()).throw(OSError("private"))
                    return getattr(stream, name)

            yield Proxy()
            if operation == "close":
                raise OSError("private close")

    with files.PrivateAcquisitionStore(*setup) as store:
        if operation == "fsync":
            monkeypatch.setattr(os, "fsync", lambda *_: (_ for _ in ()).throw(OSError()))
        else:
            monkeypatch.setattr(files, "_owned_stream", wrapped)
        with pytest.raises(OSError):
            store.put("packet.bin", b"payload")


def test_atomic_publication_and_no_overwrite(tmp_path):
    target = tmp_path / "report.json"
    files.publish_acquisition(target, {"own": True})
    assert json.loads(target.read_text()) == {"own": True}
    with pytest.raises(files.PublicationError) as caught:
        files.publish_acquisition(target, {"own": False})
    assert not caught.value.committed and json.loads(target.read_text()) == {"own": True}


@pytest.mark.parametrize("stage", ["write", "fsync_file", "link", "fsync_directory", "close"])
def test_publication_failure_tracks_commit_point(tmp_path, monkeypatch, stage):
    target = tmp_path / "report.json"
    fsync, close = os.fsync, os.close

    def fail(*_args, **_kwargs):
        raise OSError("private path")

    def syncing(fd):
        directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        if directory == (stage == "fsync_directory"):
            fail()
        return fsync(fd)

    def closing(fd):
        directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        close(fd)
        if directory and target.exists():
            fail()

    if stage == "write":
        monkeypatch.setattr(files, "write_all", fail)
    elif stage.startswith("fsync"):
        monkeypatch.setattr(os, "fsync", syncing)
    elif stage == "link":
        monkeypatch.setattr(os, "link", fail)
    else:
        monkeypatch.setattr(os, "close", closing)
    with pytest.raises(files.PublicationError) as caught:
        files.publish_acquisition(target, {"own": True})
    committed = stage in ("fsync_directory", "close")
    assert caught.value.committed == committed and target.exists() == committed
    assert "private path" not in str(caught.value)


def test_publication_cannot_open_parent(tmp_path, monkeypatch):
    def fail(*_):
        raise OSError("private parent")

    monkeypatch.setattr(files, "_open_directory", fail)
    with pytest.raises(files.PublicationError) as caught:
        files.publish_acquisition(tmp_path / "report.json", {})
    assert not caught.value.committed


@pytest.mark.parametrize("stage", ["read", "mutate", "replace_after_close", "close"])
def test_read_failures_and_changes_before_return(setup, monkeypatch, stage):
    root, repository = setup
    path = put(root)
    owned = files._owned_stream

    @contextmanager
    def wrapped(fd, mode):
        with owned(fd, mode) as stream:

            class Proxy:
                def __getattr__(self, name):
                    return getattr(stream, name)

                def read(self, size):
                    if stage == "read":
                        raise OSError("private read")
                    data = stream.read(size)
                    if stage == "mutate":
                        path.write_bytes(b"changed")
                    return data

            yield Proxy()
        if stage == "replace_after_close":
            path.rename(root / "original")
            put(root)
        if stage == "close":
            raise OSError("private close")

    with files.PrivateAcquisitionStore(root, repository) as store:
        monkeypatch.setattr(files, "_owned_stream", wrapped)
        with pytest.raises((OSError, ProfileError)):
            store.read("state.p2s")
