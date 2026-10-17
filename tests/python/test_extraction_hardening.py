"""H01-H06: deterministic adversarial cases and descriptor ownership regressions."""

import errno
import os

import pytest
from test_asset_catalog import catalog_source as catalog_source
from test_extraction import inputs as inputs
from test_extraction import run

from tools.pipeline.private_output import PrivateOutput
from tools.pipeline.profile import ProfileError


@pytest.mark.parametrize("phase", ["payload", "readback", "receipt"])
def test_fdopen_failure_closes_untransferred_descriptor(inputs, monkeypatch, phase):
    real_open, real_fdopen = os.open, os.fdopen
    kinds, failed_fd = {}, []

    def tracked(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        name = str(path)
        if name.endswith(".bin"):
            kinds[fd] = "payload" if flags & os.O_WRONLY else "readback"
        elif name.endswith(".pending"):
            kinds[fd] = "receipt"
        else:
            kinds.pop(fd, None)
        return fd

    def fail(fd, *args, **kwargs):
        if not failed_fd and kinds.get(fd) == phase:
            failed_fd.append(fd)
            raise OSError(errno.EMFILE, "own fdopen failure")
        return real_fdopen(fd, *args, **kwargs)

    monkeypatch.setattr(os, "open", tracked)
    monkeypatch.setattr(os, "fdopen", fail)
    try:
        with pytest.raises(ProfileError) as error:
            run(inputs)
        assert error.value.code == "OUTPUT_IO_ERROR"
        assert len(failed_fd) == 1
        assert not (inputs.root / "run/verified.json").exists()
        with pytest.raises(OSError) as closed:
            os.fstat(failed_fd[0])
        assert closed.value.errno == errno.EBADF
    finally:
        for fd in failed_fd:
            try:
                os.close(fd)
            except OSError:
                pass


@pytest.mark.parametrize("active_error", [False, True])
def test_directory_cleanup_attempts_every_close_and_preserves_primary_error(
    inputs, monkeypatch, active_error
):
    output = PrivateOutput(inputs.root, inputs.repository, "run")
    output.__enter__()
    output.reserve(0, 1)
    owned = [*output.copy_fds.values(), output.session_fd, output.root_fd]
    real_close, attempted = os.close, []

    def failing(fd):
        attempted.append(fd)
        real_close(fd)
        if fd == owned[0]:
            raise OSError(errno.EIO, "own close failure after release")

    monkeypatch.setattr(os, "close", failing)
    primary = ProfileError("OWN_PRIMARY", "original operation failed")
    try:
        if active_error:
            assert output.__exit__(ProfileError, primary, None) is None
        else:
            with pytest.raises(OSError) as caught:
                output.__exit__(None, None, None)
            assert caught.value.errno == errno.EIO
        assert attempted == owned
        for fd in owned:
            with pytest.raises(OSError):
                os.fstat(fd)
    finally:
        for fd in owned:
            try:
                real_close(fd)
            except OSError:
                pass


@pytest.mark.parametrize(
    "operation,target",
    [
        ("mkdir", "run"),
        ("mkdir", "copy-a"),
        ("mkdir", "copy-b"),
        ("open", "run"),
        ("open", "copy-a"),
        ("open", "copy-b"),
        ("open", "payload"),
        ("open", "readback"),
        ("open", "receipt"),
        ("listdir", "copy"),
        ("link", "verified.json"),
    ],
)
@pytest.mark.parametrize("error_number", [errno.EACCES, errno.ENOSPC, errno.EIO])
def test_filesystem_failure_matrix(inputs, monkeypatch, operation, target, error_number):
    original, fired, opened = getattr(os, operation), [], []
    real_open = os.open

    def track(path, flags, *args, **kwargs):
        descriptor = real_open(path, flags, *args, **kwargs)
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(os, "open", track)
    if operation == "open":
        original = track

    def broken(*args, **kwargs):
        match = False
        if operation in ("mkdir", "open"):
            name = str(args[0])
            if target in ("run", "copy-a", "copy-b"):
                match = name == target
            elif target == "payload":
                match = name.endswith(".bin") and bool(args[1] & os.O_WRONLY)
            elif target == "readback":
                match = name.endswith(".bin") and not args[1] & os.O_WRONLY
            elif target == "receipt":
                match = name == ".started.json.pending"
        elif operation == "listdir":
            match = isinstance(args[0], int)
        elif operation == "link":
            match = args[1] == target
        if match and not fired:
            fired.append(True)
            raise OSError(error_number, "own filesystem failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(os, operation, broken)
    with pytest.raises(ProfileError) as caught:
        run(inputs)
    assert caught.value.code == "OUTPUT_IO_ERROR" and fired
    assert not (inputs.root / "run/verified.json").exists()
    for fd in set(opened):
        with pytest.raises(OSError) as closed:
            os.fstat(fd)
        assert closed.value.errno == errno.EBADF


@pytest.mark.parametrize("phase", ["payload", "receipt"])
@pytest.mark.parametrize("operation", ["write", "flush", "fsync"])
def test_stream_and_sync_failure_does_not_publish_success(inputs, monkeypatch, phase, operation):
    real_open, real_fdopen, real_fsync = os.open, os.fdopen, os.fsync
    kinds, fired = {}, []

    def opened(path, flags, *args, **kwargs):
        fd = real_open(path, flags, *args, **kwargs)
        name = str(path)
        kinds[fd] = (
            "payload"
            if name.endswith(".bin")
            else "receipt"
            if name == ".started.json.pending"
            else None
        )
        return fd

    def fail(fd, step):
        if not fired and kinds.get(fd) == phase and step == operation:
            fired.append(step)
            raise OSError(errno.EIO, "own buffered I/O failure")

    class Stream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, data):
            fail(self.stream.fileno(), "write")
            return self.stream.write(data)

        def flush(self):
            fail(self.stream.fileno(), "flush")
            return self.stream.flush()

        def fileno(self):
            return self.stream.fileno()

        def __getattr__(self, name):
            return getattr(self.stream, name)

    def wrapped(fd, *args, **kwargs):
        return Stream(real_fdopen(fd, *args, **kwargs))

    def sync(fd):
        fail(fd, "fsync")
        return real_fsync(fd)

    monkeypatch.setattr(os, "open", opened)
    monkeypatch.setattr(os, "fdopen", wrapped)
    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(ProfileError) as caught:
        run(inputs)
    expected = "COPY_IO_ERROR" if phase == "payload" and operation == "write" else "OUTPUT_IO_ERROR"
    assert caught.value.code == expected and fired
    assert not (inputs.root / "run/verified.json").exists()
    for fd in kinds:
        with pytest.raises(OSError):
            os.fstat(fd)


def test_directory_walk_closes_new_fd_when_previous_close_reports_failure(inputs, monkeypatch):
    from tools.pipeline.private_output import _open_directory

    real_open, real_close = os.open, os.close
    opened, closed = [], []

    def opening(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        opened.append(fd)
        return fd

    def closing(fd):
        closed.append(fd)
        real_close(fd)
        if len(closed) == 1:
            raise OSError(errno.EIO, "own close result")

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "close", closing)
    try:
        with pytest.raises(OSError) as caught:
            _open_directory(inputs.root)
        assert caught.value.errno == errno.EIO
        assert len(opened) == 2 and closed == opened
        for fd in opened:
            with pytest.raises(OSError):
                os.fstat(fd)
    finally:
        for fd in opened:
            try:
                real_close(fd)
            except OSError:
                pass


def test_fdopen_primary_error_survives_cleanup_error(tmp_path, monkeypatch):
    from tools.pipeline.private_output import _owned_stream

    fd = os.open(tmp_path / "own", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    real_close = os.close

    def wrap(*args):
        raise OSError(errno.EMFILE, "own primary")

    def close(descriptor):
        real_close(descriptor)
        raise OSError(errno.EIO, "own cleanup")

    monkeypatch.setattr(os, "fdopen", wrap)
    monkeypatch.setattr(os, "close", close)
    with pytest.raises(OSError) as caught:
        with _owned_stream(fd, "wb"):
            pytest.fail("stream unexpectedly opened")
    assert caught.value.errno == errno.EMFILE
    assert caught.value.__notes__


def test_close_error_after_commit_reports_verified_with_cleanup_warning(
    inputs, monkeypatch, capsys
):
    import json

    from test_extraction import args

    from tools.pipeline import extract_assets

    original = PrivateOutput.__exit__

    def close_error(self, *args):
        original(self, *args)
        raise OSError(errno.EIO, "own post-commit cleanup failure")

    monkeypatch.setattr(PrivateOutput, "__exit__", close_error)
    assert extract_assets.main(args(inputs)) == 0
    message = json.loads(capsys.readouterr().out)
    assert message["status"] == "verified" and message["cleanup_warning"] == "OUTPUT_CLOSE_ERROR"
    result = json.loads((inputs.root / "run/verified.json").read_text())
    assert result["status"] == "verified"
    assert not (inputs.root / "run/failed.json").exists()
