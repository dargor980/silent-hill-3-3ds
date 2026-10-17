"""Own narrow instruction pattern, producing candidates without semantic claims."""

import hashlib
import struct

from tools.inspectors.elf32 import MAX_ELF_BYTES, ElfMap, ReadRange, exact_read
from tools.pipeline.profile import ProfileError

METHOD = "mips-road128-loop-candidate-v1"
WINDOW_BYTES = 24
BLOCK_BYTES = 4096
STRIDE = BLOCK_BYTES - (WINDOW_BYTES - 4)
MAX_CANDIDATES = 1024


def _fields(word: int) -> tuple[int, int, int, int]:
    return word >> 26, (word >> 21) & 31, (word >> 16) & 31, word & 0xFFFF


def match_loop(data: bytes, address: int) -> int | None:
    """Return a backward branch target for exactly six matching LE words."""
    if (
        not isinstance(data, bytes)
        or len(data) != WINDOW_BYTES
        or type(address) is not int
        or address < 0
        or address % 4
        or address + WINDOW_BYTES > 1 << 32
    ):
        raise ProfileError("MIPS_WINDOW", "Invalid pattern window")
    step, gap, load, mask, branch, delay = struct.unpack("<6I", data)
    op, base, destination, amount = _fields(step)
    if op not in (9, 25) or not base or destination != base or amount != 128 or gap or delay:
        return None
    op, source, loaded, offset = _fields(load)
    if op != 35 or source != base or loaded in (0, base) or offset != 68:
        return None
    op, source, masked, bits = _fields(mask)
    if op != 12 or source != loaded or masked in (0, base) or bits != 1:
        return None
    op, source, other, displacement = _fields(branch)
    if op != 4 or (source, other) not in ((masked, 0), (0, masked)):
        return None
    signed = displacement if displacement < 0x8000 else displacement - 0x10000
    target = address + 20 + signed * 4
    return target if 0 <= target <= address else None


def scan_loops(read: ReadRange, mapping: ElfMap) -> dict:
    segments = [s for s in mapping.segments if s.flags & 1 and s.file_size]
    total = sum(s.file_size for s in segments)
    if total > MAX_ELF_BYTES:
        raise ProfileError("MIPS_BUDGET", "Scan exceeds byte budget")
    candidates = []
    for segment in segments:
        if segment.address % 4 or segment.offset % 4 or segment.file_size % 4:
            raise ProfileError("MIPS_ALIGNMENT", "Executable segment is not word aligned")
        for start in range(0, segment.file_size, STRIDE):
            length = min(BLOCK_BYTES, segment.file_size - start)
            data = exact_read(read, segment.offset + start, length)
            for relative in range(0, max(0, len(data) - WINDOW_BYTES + 1), 4):
                window = data[relative : relative + WINDOW_BYTES]
                address = segment.address + start + relative
                target = match_loop(window, address)
                if target is None or target < segment.address:
                    continue
                # Both source and target remain inside this file-backed segment.
                offset = mapping.file_offset(address, WINDOW_BYTES, executable=True)
                target_offset = mapping.file_offset(target, 4, executable=True)
                candidates.append(
                    {
                        "segment_index": segment.index,
                        "file_offset": offset,
                        "virtual_address": address,
                        "window_size": WINDOW_BYTES,
                        "window_sha256": hashlib.sha256(window).hexdigest(),
                        "branch_target_address": target,
                        "branch_target_offset": target_offset,
                        "state": "syntactic_candidate",
                        "resource_link": "unproven",
                        "execution_reachability": "unproven",
                    }
                )
                if len(candidates) > MAX_CANDIDATES:
                    raise ProfileError("MIPS_BUDGET", "Too many pattern candidates")
    return {
        "method": METHOD,
        "scanned_file_bytes": total,
        "scanned_segment_count": len(segments),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
