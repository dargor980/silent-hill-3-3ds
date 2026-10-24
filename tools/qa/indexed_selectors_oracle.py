"""Independent upload/read tables from pinned PCSX2, for PSMT4 and CSM1."""

import argparse
import hashlib
import json
import re
from array import array
from pathlib import Path

from tools.pipeline.decoders.ps2_indexed import clut_offset, upload_nibble_offset
from tools.qa.texture_address_oracle import REVISION, TABLES_SHA256


def compare(data: bytes) -> dict:
    if hashlib.sha256(data).hexdigest() != TABLES_SHA256:
        raise ValueError("ORACLE_REFERENCE_HASH")

    def table(name, size):
        match = re.search(r"\b" + name + r"\[[^=]+?=\s*\{(.*?)\};", data.decode(), re.S)
        if match is None:
            raise ValueError("ORACLE_TABLE_MISSING")
        values = list(map(int, re.findall(r"\d+", re.sub(r"//[^\n]*", "", match[1]))))
        if len(values) != size:
            raise ValueError("ORACLE_TABLE_SIZE")
        return values

    b32, c32 = table("_blockTable32", 32), table("columnTable32", 64)
    b4, c4 = table("_blockTable4", 32), table("columnTable4", 512)

    def upload(width, height):
        # Full GS address space makes unwritten cells explicit, even when a
        # short upload occupies non-contiguous blocks of a page.
        memory = array("i", [-1]) * (4 * 1024 * 1024)
        for y in range(height):
            for x in range(width):
                page = (y // 32) * (width // 64) + x // 64
                block = b32[(y % 32) // 8 * 8 + (x % 64) // 8]
                at = page * 8192 + block * 256 + c32[y % 8 * 8 + x % 8] * 4
                for lane in range(4):
                    if memory[at + lane] != -1:
                        raise ValueError("ORACLE_OVERLAP")
                    memory[at + lane] = (y * width + x) * 4 + lane
        return memory

    cases = []
    for width in (128, 256, 512, 1024):
        for height in (128, 256, 512, 1024):
            memory = upload(width // 2, height // 4)
            mismatches = 0
            for y in range(height):
                for x in range(width):
                    page = (y // 128) * (width // 128) + x // 128
                    block = b4[(y % 128) // 16 * 4 + (x % 128) // 32]
                    at = page * 16384 + block * 512 + c4[y % 16 * 32 + x % 32]
                    if memory[at // 2] < 0:
                        raise ValueError("ORACLE_UNWRITTEN")
                    expected = memory[at // 2] * 2 + at % 2
                    mismatches += upload_nibble_offset(x, y, width) != expected
            cases.append(
                dict(width=width, height=height, pixels=width * height, mismatches=mismatches)
            )
    palettes = []
    for count in (4, 8, 16):
        memory = upload(64, count * 4)
        # CSM1 8-bit palette reads visit two 8-column halves, with bit 3
        # selecting the next row before bit 4 selects the second half.
        valid = []
        for selector in range(16):
            expected = []
            for group in range(8):
                for half in range(2):
                    for row in range(2):
                        for column in range(8):
                            x, y = half * 8 + column, group * 2 + row
                            block = b32[y // 8 * 8 + x // 8]
                            addr = selector * 1024 + block * 256 + c32[y % 8 * 8 + x % 8] * 4
                            expected.append(memory[addr])
            if min(expected) < 0:
                continue
            valid.append(selector)
            mismatches = sum(clut_offset(i, selector) != v for i, v in enumerate(expected))
            palettes.append(dict(units=count, selector=selector, colors=256, mismatches=mismatches))
        if valid != (list((0, 1, 4, 5)) if count == 4 else list(range(count))):
            raise ValueError("ORACLE_SELECTOR_SET")
    return dict(
        reference=dict(revision=REVISION, sha256=TABLES_SHA256),
        cases=cases,
        palettes=palettes,
        passed=all(c["mismatches"] == 0 for c in cases + palettes),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = compare(args.tables.read_bytes())
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps(
            dict(
                passed=result["passed"],
                cases=len(result["cases"]),
                palettes=len(result["palettes"]),
            )
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
