"""CPI10: validate, exclusively write, reread and reconstruct before publication."""

import json
import os

from tools.pipeline.collision_polygon_inputs import read_at, require
from tools.pipeline.collision_polygon_intermediate import verify_collision_polygon_bundle
from tools.pipeline.intermediate_assets import sha
from tools.pipeline.private_files import _identity, _inode, _open_directory
from tools.pipeline.private_texture_output import _write_bundle

MANIFEST_LIMIT = 256 * 1024
TOTAL_LIMIT = 40 * 1024 * 1024


def manifest_bytes(files, report):
    """Match the shared writer's wire format, without accepting arbitrary filenames."""
    require(type(files) is dict and type(report) is dict)
    require(all(type(k) is str and type(v) is bytes for k, v in files.items()))
    require(sum(map(len, files.values())) <= TOTAL_LIMIT)
    inventory = [dict(file=k, size=len(v), sha256=sha(v)) for k, v in sorted(files.items())]
    raw = (json.dumps({**report, "files": inventory}, sort_keys=True, indent=2) + "\n").encode()
    require(0 < len(raw) <= MANIFEST_LIMIT)
    return raw


def _read_bundle(directory, *, pending=False):
    """Directory inventory and physical bounds precede decoding and allocation."""
    manifest_name = ".manifest.pending.json" if pending else "manifest.json"
    names = set(os.listdir(directory))
    require(manifest_name in names)
    raw, identity = read_at(directory, manifest_name, MANIFEST_LIMIT)
    auxiliary = {manifest_name}
    identities = {manifest_name: identity}
    if not pending and ".manifest.pending.json" in names:
        extra, extra_identity = read_at(directory, ".manifest.pending.json", MANIFEST_LIMIT)
        require(extra == raw)
        auxiliary.add(".manifest.pending.json")
        identities[".manifest.pending.json"] = extra_identity
    logical = names - auxiliary
    require(len(logical) <= 571)
    # lstat before allocation; symlinks/special entries are also rejected by read_at.
    require(
        sum(os.stat(k, dir_fd=directory, follow_symlinks=False).st_size for k in logical)
        <= TOTAL_LIMIT
    )
    files = {}
    total = 0
    for name in sorted(logical):
        limit = 65536 if name.startswith("source-") else 1024 * 1024
        # Reapply the remaining budget if a later file grows after the initial lstat pass.
        files[name], identities[name] = read_at(directory, name, min(limit, TOTAL_LIMIT - total))
        total += len(files[name])
    rebuilt = verify_collision_polygon_bundle(raw, files)
    require(rebuilt == files)
    require(set(os.listdir(directory)) == names)
    # Catch changes to an earlier entry while later files or views were processed.
    for name, expected in identities.items():
        require(_identity(os.stat(name, dir_fd=directory, follow_symlinks=False)) == expected)
    return raw, rebuilt


def read_collision_polygon_bundle(path):
    """Load a completed directory without opening any original private source."""
    directory = _open_directory(path)
    try:
        result = _read_bundle(directory)
        current = _open_directory(path)
        try:
            require(_inode(os.fstat(current)) == _inode(os.fstat(directory)))
        finally:
            os.close(current)
        return result
    finally:
        os.close(directory)


def write_collision_polygon_bundle(root, repository, run_id, files, report, *, recheck=None):
    """Never overwrite a run; the final manifest appears only after all checks pass."""
    raw = manifest_bytes(files, report)
    # Reconstruct before creating even the output directory. The pure API validates names.
    require(verify_collision_polygon_bundle(raw, files) == files)

    def before_publish(directory, written_manifest):
        require(raw == written_manifest)
        if recheck is not None:
            recheck()
        disk_manifest, rebuilt = _read_bundle(directory, pending=True)
        require(disk_manifest == raw and rebuilt == files)

    return _write_bundle(
        root, repository, run_id, files, report, set(files), before_publish=before_publish
    )
