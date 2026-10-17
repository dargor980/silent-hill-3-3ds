"""Conservative prefix classification; no filesystem, extraction or game offsets."""

from tools.pipeline.disc import parse_boot_config
from tools.pipeline.profile import ProfileError

PREFIX_LIMIT = 4096


def classify(path: str, prefix: bytes, size: int) -> dict:
    if len(prefix) != min(size, PREFIX_LIMIT):
        raise ProfileError("PREFIX_SIZE_MISMATCH", "Reader returned an incomplete prefix")
    if path == "SYSTEM.CNF":
        if size > PREFIX_LIMIT:
            raise ProfileError("INVALID_BOOT_CONFIG", "SYSTEM.CNF exceeds prefix limit")
        boot = parse_boot_config(prefix)
        return {
            "type": "ps2_boot_config",
            "recognition": "parsed",
            "rule": "ps2-boot-v1",
            "boot": boot,
        }
    if prefix.startswith(b"\x7fELF"):
        if len(prefix) < 52:
            reason = "truncated_elf_header"
        elif (
            prefix[4:7] == b"\x01\x01\x01"
            and prefix[18:24] == b"\x08\x00\x01\x00\x00\x00"
            and prefix[40:42] == b"\x34\x00"
        ):
            return {
                "type": "elf32_le_mips",
                "recognition": "header_checked",
                "rule": "elf32-le-mips-v1",
            }
        else:
            reason = "unsupported_elf_header"
    elif prefix.startswith(b"AFS\x00"):
        if len(prefix) >= 8:
            return {
                "type": "afs_candidate",
                "recognition": "signature_only",
                "rule": "afs-magic-v1",
            }
        reason = "truncated_afs_header"
    else:
        reason = "empty" if size == 0 else "no_registered_signature"
    return {"type": "unknown", "recognition": "unknown", "rule": "unknown-v1", "reason": reason}
