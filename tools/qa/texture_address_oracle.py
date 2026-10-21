"""Compare the decoder with page/block/column tables from a pinned external PCSX2 file."""

import argparse
import hashlib
import json
import re
import struct
from array import array
from pathlib import Path

from tools.pipeline.decoders.ps2_indexed8 import upload_offset

TABLES_SHA256 = "a9a226297ede32b89177d7bdb04e9d8e21728e7d55799405f6112e97fe4969e8"
REVISION = "fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3"


def compare_tables(data: bytes) -> dict:
    if hashlib.sha256(data).hexdigest() != TABLES_SHA256:
        raise ValueError("ORACLE_REFERENCE_HASH")
    source = data.decode()

    def table(name, width, height):
        match = re.search(r"\b" + name + r"\[[^=]+?=\s*\{(.*?)\};", source, re.S)
        if match is None:
            raise ValueError("ORACLE_TABLE_MISSING")
        text = re.sub(r"//[^\n]*", "", match[1])
        values = list(map(int, re.findall(r"\d+", text)))
        if len(values) != width * height:
            raise ValueError("ORACLE_TABLE_SIZE")
        return [values[i : i + width] for i in range(0, len(values), width)]

    block32, block8 = table("_blockTable32", 8, 4), table("_blockTable8", 8, 4)
    column32, column8 = table("columnTable32", 8, 8), table("columnTable8", 16, 16)
    results = []
    dimensions = [(w, h) for w in (128, 256, 512, 1024) for h in (64, 128, 256, 512, 1024)]
    for width, height in dimensions:
        memory = array("I", [0xFFFFFFFF]) * (width * height)
        transfer_width = width // 2
        for y in range(height // 2):
            for x in range(transfer_width):
                page = (y // 32) * (transfer_width // 64) + x // 64
                block = block32[(y % 32) // 8][(x % 64) // 8]
                address = page * 8192 + block * 256 + column32[y % 8][x % 8] * 4
                for lane in range(4):
                    if memory[address + lane] != 0xFFFFFFFF:
                        raise ValueError("ORACLE_OVERLAP")
                    memory[address + lane] = (y * transfer_width + x) * 4 + lane
        digest = hashlib.sha256()
        mismatches = 0
        for y in range(height):
            for x in range(width):
                page = (y // 64) * (width // 128) + x // 128
                block = block8[(y % 64) // 16][(x % 128) // 16]
                address = page * 8192 + block * 256 + column8[y % 16][x % 16]
                expected = memory[address]
                if expected == 0xFFFFFFFF:
                    raise ValueError("ORACLE_UNWRITTEN")
                mismatches += upload_offset(x, y, width) != expected
                digest.update(struct.pack("<I", expected))
        results.append(
            {
                "width": width,
                "height": height,
                "pixels": width * height,
                "mismatches": mismatches,
                "map_u32le_sha256": digest.hexdigest(),
            }
        )
    return {
        "reference": {"revision": REVISION, "sha256": TABLES_SHA256},
        "cases": results,
        "passed": all(r["mismatches"] == 0 for r in results),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    result = compare_tables(args.tables.read_bytes())
    with args.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": result["passed"], "cases": len(result["cases"])}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
