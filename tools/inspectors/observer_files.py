"""AC05/08/09: anchored private custody and an explicit publication commit point."""

import fcntl
import hashlib
import json
import os
import stat

from tools.inspectors.observation_capture import ProfileError, require
from tools.inspectors.pcsx2_state import MAX_ARCHIVE
from tools.pipeline.private_files import _identity, _inode, _open_directory, _owned_stream
from tools.pipeline.transfer import write_all


def _private(info, directory=False):
    require(
        (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)
        and info.st_uid == os.getuid()
        and (directory or info.st_nlink == 1),
        "ACQUIRE_PRIVATE_FILE",
    )


class PrivateAcquisitionStore:
    """One cooperative lock per state directory, never unlink a live lock inode."""

    def __init__(self, root, repository):
        resolved, checkout = root.resolve(), repository.resolve()
        require(
            not resolved.is_relative_to(checkout) and not checkout.is_relative_to(resolved),
            "PRIVATE_DATA_IN_REPO",
        )
        self.root = root
        self.parent = self.lock = None
        self.used = False
        self.state_identity = None
        self.packets = {}

    def __enter__(self):
        require(not self.used, "ACQUIRE_STORE_REUSE")
        self.used = True
        try:
            self.parent = _open_directory(self.root)
            _private(os.fstat(self.parent), True)
            self.anchor = _inode(os.fstat(self.parent))
            self.lock = os.open(
                ".observer.lock",
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=self.parent,
            )
            _private(os.fstat(self.lock))
            self.lock_identity = _inode(os.fstat(self.lock))
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException as error:
            self.__exit__(type(error), error, None)
            raise
        return self

    def check(self):
        require(self.parent is not None, "ACQUIRE_STORE_CLOSED")
        current = _open_directory(self.root)
        try:
            _private(os.fstat(current), True)
            require(_inode(os.fstat(current)) == self.anchor, "ACQUIRE_DIRECTORY_CHANGED")
            lock = os.stat(".observer.lock", dir_fd=self.parent, follow_symlinks=False)
            _private(lock)
            require(_inode(lock) == self.lock_identity, "ACQUIRE_LOCK_CHANGED")
            identities = dict(self.packets)
            if self.state_identity is not None:
                identities[self.state_identity[0]] = self.state_identity[1]
            for name, expected in identities.items():
                info = os.stat(name, dir_fd=self.parent, follow_symlinks=False)
                _private(info)
                require(_identity(info) == expected, "ACQUIRE_STATE_CHANGED")
        finally:
            os.close(current)

    def __exit__(self, kind, error, traceback):
        failure = None
        try:
            if error is None:
                self.check()
        except BaseException as caught:
            failure = caught
        for name in ("lock", "parent"):
            fd = getattr(self, name)
            setattr(self, name, None)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    failure = ProfileError("ACQUIRE_CLOSE", "Private descriptor close failed")
        if failure is not None:
            raise failure from None
        return False

    def _name(self, name):
        require(
            isinstance(name, str)
            and 1 <= len(name) <= 128
            and name not in (".", "..")
            and not any(c in name for c in "/\\\0"),
            "ACQUIRE_PATH",
        )
        self.check()

    def absent(self, name):
        self._name(name)
        for candidate in (name, name + ".backup"):
            try:
                os.stat(candidate, dir_fd=self.parent, follow_symlinks=False)
            except FileNotFoundError:
                continue
            require(False, "ACQUIRE_STATE_EXISTS")

    def read(self, name):
        self._name(name)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.parent)
        with _owned_stream(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            _private(before)
            require(1 <= before.st_size <= MAX_ARCHIVE, "ACQUIRE_STATE_BUDGET")
            raw = stream.read(MAX_ARCHIVE + 1)
            require(
                len(raw) == before.st_size
                and _identity(os.fstat(stream.fileno())) == _identity(before),
                "ACQUIRE_STATE_CHANGED",
            )
        self.check()
        after = os.stat(name, dir_fd=self.parent, follow_symlinks=False)
        require(_identity(before) == _identity(after), "ACQUIRE_STATE_CHANGED")
        identity = (name, _identity(after), hashlib.sha256(raw).hexdigest())
        require(
            self.state_identity is None or self.state_identity == identity, "ACQUIRE_STATE_CHANGED"
        )
        self.state_identity = identity
        return raw, identity[2]

    def put(self, name, raw):
        self._name(name)
        require(type(raw) is bytes and 1 <= len(raw) <= 4333, "ACQUIRE_PACKET_BUDGET")
        fd = os.open(
            name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.parent
        )
        with _owned_stream(fd, "w+b") as stream:
            write_all(stream, raw)
            stream.flush()
            os.fsync(stream.fileno())
            stream.seek(0)
            require(stream.read(4334) == raw, "ACQUIRE_PACKET_WRITE")
            info = os.fstat(stream.fileno())
            _private(info)
            self.packets[name] = _identity(info)
        self.check()


class PublicationError(ProfileError):
    def __init__(self, committed):
        self.committed = committed
        super().__init__(
            "ACQUIRE_PUBLISH_COMMITTED" if committed else "ACQUIRE_PUBLISH",
            "Publication failed; do not retry automatically",
        )


def publish_acquisition(path, report):
    """No overwrite. A failure after link is explicitly not a rollback."""
    parent = None
    committed = False
    try:
        raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
        parent = _open_directory(path.parent)
        staging = "." + path.name + ".pending.json"
        fd = os.open(
            staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent
        )
        with _owned_stream(fd, "wb") as stream:
            write_all(stream, raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(staging, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        committed = True
        os.fsync(parent)
    except (OSError, ProfileError):
        raise PublicationError(committed) from None
    finally:
        if parent is not None:
            try:
                os.close(parent)
            except OSError:
                raise PublicationError(committed) from None
