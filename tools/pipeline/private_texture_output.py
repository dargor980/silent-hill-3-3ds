"""Exclusive private texture bundles, using the shared anchored POSIX primitives."""

import hashlib
import json
import os
import re
from pathlib import Path

from tools.pipeline.hashing import fingerprint_stream
from tools.pipeline.private_files import DIRECTORY_FLAGS, _inode, _open_directory, _owned_stream
from tools.pipeline.profile import ProfileError
from tools.pipeline.transfer import write_all


def write_texture_bundle(
    root: Path, repository: Path, run_id: str, files: dict[str, bytes], report: dict
) -> dict:
    expected = {"indices.bin"} | {
        f"palette-{i}.{suffix}" for i in range(4) for suffix in ("bin", "rgba", "png")
    }
    return _write_bundle(root, repository, run_id, files, report, expected)


def write_inspection_bundle(
    root: Path, repository: Path, run_id: str, files: dict[str, bytes], report: dict
) -> dict:
    expected = {
        "texture.stx",
        "sh3_texture_probe.3dsx",
        "sh3_texture_probe.smdh",
        "LEEME.txt",
        "sd-card.zip",
    }
    return _write_bundle(root, repository, run_id, files, report, expected)


def write_geometry_inspection_bundle(root, repository, run_id, files, report):
    expected = {
        "geometry.sgm",
        "sh3_geometry_probe.3dsx",
        "sh3_geometry_probe.smdh",
        "LEEME.txt",
        "sd-card.zip",
    }
    return _write_bundle(root, repository, run_id, files, report, expected)


def write_material_inspection_bundle(root, repository, run_id, files, report):
    expected = {
        "geometry.sgm",
        "texture.stx",
        "sh3_material_probe.3dsx",
        "sh3_material_probe.smdh",
        "LEEME.txt",
        "sd-card.zip",
    }
    return _write_bundle(root, repository, run_id, files, report, expected)


def write_animation_inspection_bundle(root, repository, run_id, files, report):
    expected = {
        "animation.san",
        "sh3_animation_probe.3dsx",
        "sh3_animation_probe.smdh",
        "LEEME.txt",
        "sd-card.zip",
    }
    return _write_bundle(root, repository, run_id, files, report, expected)


def write_character_inspection_bundle(root, repository, run_id, files, report):
    return _write_bundle(
        root,
        repository,
        run_id,
        files,
        report,
        {
            "animation.san",
            "character.scm",
            "sh3_character_probe.3dsx",
            "sh3_character_probe.smdh",
            "LEEME.txt",
            "sd-card.zip",
        },
    )


def write_character_material_inspection_bundle(root, repository, run_id, files, report):
    return _write_bundle(
        root,
        repository,
        run_id,
        files,
        report,
        {
            "animation.san",
            "character.scm",
            "character.sct",
            "sh3_character_material_probe.3dsx",
            "sh3_character_material_probe.smdh",
            "LEEME.txt",
            "sd-card.zip",
        },
    )


def write_character_lighting_inspection_bundle(root, repository, run_id, files, report):
    return _write_bundle(
        root,
        repository,
        run_id,
        files,
        report,
        {
            "animation.san",
            "character.scm",
            "character.sct",
            "character.scl",
            "sh3_character_lighting_probe.3dsx",
            "sh3_character_lighting_probe.smdh",
            "LEEME.txt",
            "sd-card.zip",
        },
    )


def write_character_intermediate_bundle(root, repository, run_id, files, report):
    return _write_bundle(
        root,
        repository,
        run_id,
        files,
        report,
        {"intermediate.json", "animation.san", "character.scm"},
    )


def write_character_render_intermediate_bundle(root, repository, run_id, files, report):
    from tools.pipeline.character_render_intermediate import OUTPUT_NAMES

    return _write_bundle(root, repository, run_id, files, report, OUTPUT_NAMES)


def write_map_intermediate_bundle(root, repository, run_id, files, report):
    from tools.pipeline.map_intermediate import OUTPUT_NAMES

    return _write_bundle(root, repository, run_id, files, report, OUTPUT_NAMES)


def write_collision_intermediate_bundle(root, repository, run_id, files, report):
    from tools.pipeline.collision_intermediate import OUTPUT_NAMES

    return _write_bundle(root, repository, run_id, files, report, OUTPUT_NAMES)


def write_character_world_inspection_bundle(root, repository, run_id, files, report):
    return _write_bundle(
        root,
        repository,
        run_id,
        files,
        report,
        {
            "animation.san",
            "character.scm",
            "character.sct",
            "character.scw",
            "sh3_character_world_probe.3dsx",
            "sh3_character_world_probe.smdh",
            "LEEME.txt",
            "sd-card.zip",
        },
    )


def write_geometry_bundle(
    root: Path, repository: Path, run_id: str, files: dict[str, bytes], report: dict
) -> dict:
    return _write_bundle(
        root, repository, run_id, files, report, {"geometry.json", "inspection.obj"}
    )


def write_skeleton_animation_bundle(root, repository, run_id, files, report):
    return _write_bundle(
        root, repository, run_id, files, report, {"skeleton.json", "animation.json"}
    )


def write_character_mesh_bundle(root, repository, run_id, files, report):
    return _write_bundle(root, repository, run_id, files, report, {"mesh.json"})


def write_character_material_bundle(root, repository, run_id, files, report):
    summary = report["summary"]
    images, textures = summary["images"], summary["textures"]
    if (
        type(images) is not int
        or type(textures) is not int
        or not 1 <= images <= 16
        or not 1 <= textures <= 256
    ):
        raise ProfileError("CT_OUTPUT_COUNT", "Invalid image/texture counts")
    expected = {"materials.json"}
    for image in range(images):
        expected.add(f"image-{image}.indices")
        expected.update(f"image-{image}-palette-{p}.bin" for p in range(4))
    expected.update(f"texture-{i}.{suffix}" for i in range(textures) for suffix in ("rgba", "png"))
    return _write_bundle(root, repository, run_id, files, report, expected)


def _write_bundle(root, repository, run_id, files, report, expected):
    resolved, checkout = root.resolve(), repository.resolve()
    if resolved.is_relative_to(checkout) or checkout.is_relative_to(resolved):
        raise ProfileError("PRIVATE_DATA_IN_REPO", "Texture output must be external")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", run_id):
        raise ProfileError("INVALID_DESTINATION", "Invalid texture session")
    if (
        set(files) != expected
        or any(type(data) is not bytes or not data for data in files.values())
        or sum(map(len, files.values())) > 40 * 1024 * 1024
    ):
        raise ProfileError("PX_OUTPUT_SET", "Invalid texture output set or budget")
    inventory = [
        {"file": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(files.items())
    ]
    manifest = {**report, "files": inventory}
    raw = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    root_fd, session_fd = _open_directory(root), None
    try:
        os.mkdir(run_id, mode=0o700, dir_fd=root_fd)
        session_fd = os.open(run_id, DIRECTORY_FLAGS, dir_fd=root_fd)

        def attached():
            current = _open_directory(root / run_id)
            try:
                if _inode(os.fstat(current)) != _inode(os.fstat(session_fd)):
                    raise ProfileError("OUTPUT_CHANGED", "Texture directory was replaced")
            finally:
                os.close(current)

        def write(name, data):
            attached()
            fd = os.open(
                name,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                mode=0o600,
                dir_fd=session_fd,
            )
            with _owned_stream(fd, "w+b") as stream:
                write_all(stream, data)
                stream.flush()
                os.fsync(stream.fileno())
                stream.seek(0)
                if (
                    fingerprint_stream(stream, len(data))["sha256"]
                    != hashlib.sha256(data).hexdigest()
                ):
                    raise ProfileError("OUTPUT_HASH_MISMATCH", "Texture write differs")
            attached()

        for name, data in sorted(files.items()):
            write(name, data)
        if set(os.listdir(session_fd)) != expected:
            raise ProfileError("OUTPUT_SET_MISMATCH", "Texture output set changed")
        write(".manifest.pending.json", raw)
        os.link(
            ".manifest.pending.json",
            "manifest.json",
            src_dir_fd=session_fd,
            dst_dir_fd=session_fd,
            follow_symlinks=False,
        )
    finally:
        try:
            if session_fd is not None:
                os.close(session_fd)
        finally:
            os.close(root_fd)
    return manifest
