"""Bounded file reads and verified code artifacts shared by private viewers."""

import hashlib
import os
import re
import stat
import struct
import zlib
from pathlib import Path


def bounded_read(path: Path, maximum: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= maximum:
            raise ValueError("Invalid input type or size")
        data = stream.read(maximum + 1)
    if len(data) != info.st_size:
        raise ValueError("Input changed or is too large")
    return data


def checked(data: bytes, digest: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Input SHA-256 mismatch")
    return data


def read_build(build: Path, stem: str) -> tuple[dict[str, bytes], str]:
    expected = {f"{stem}.{ext}" for ext in ("elf", "3dsx", "smdh")} | {
        "build-id.txt",
        "toolchain-packages.txt",
        "sdk-image.txt",
    }
    sums = bounded_read(build / "SHA256SUMS", 4096).decode().splitlines()
    artifacts = {}
    for line in sums:
        match = re.fullmatch(r"([0-9a-f]{64})  ([a-zA-Z0-9_.-]+)", line)
        if not match or match[2] not in expected or match[2] in artifacts:
            raise ValueError("Invalid build inventory")
        artifacts[match[2]] = checked(bounded_read(build / match[2], 16 * 1024 * 1024), match[1])
    if set(artifacts) != expected:
        raise ValueError("Incomplete build inventory")
    build_id = artifacts["build-id.txt"].decode().strip()
    if not re.fullmatch(r"[0-9a-f]{12}", build_id):
        raise ValueError("Invalid build identity")
    if not artifacts[f"{stem}.3dsx"].startswith(b"3DSX"):
        raise ValueError("Invalid 3DSX")
    if not artifacts[f"{stem}.smdh"].startswith(b"SMDH"):
        raise ValueError("Invalid SMDH")
    return artifacts, build_id


def payload_crc(raw, magic):
    if (
        type(raw) is not bytes
        or len(raw) < 32
        or raw[:8] != magic
        or struct.unpack_from("<I", raw, 24)[0] != len(raw) - 32
        or struct.unpack_from("<I", raw, 28)[0] != zlib.crc32(raw[32:])
    ):
        raise ValueError("Invalid inspection dependency")
    return zlib.crc32(raw[32:])
