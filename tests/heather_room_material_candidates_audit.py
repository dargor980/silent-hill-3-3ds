"""Private HRM audit: anchored A/B resources and an independent GS table model.

Only hashes/counts leave memory. No emulator, renderer or asset publication.
"""

import argparse
import hashlib
import json
import os
import re
import struct
import sys
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.inspectors.map_material_candidates import inspect_candidates  # noqa: E402
from tools.pipeline.collision_polygon_inputs import PinnedInputs  # noqa: E402
from tools.pipeline.heather_room_contacts import read_profile, require  # noqa: E402
from tools.pipeline.intermediate_assets import sha  # noqa: E402
from tools.pipeline.prepare_heather_room_contacts import _prepare  # noqa: E402
from tools.pipeline.prepare_heather_room_scene import _rig  # noqa: E402
from tools.qa.texture_address_oracle import REVISION, TABLES_SHA256  # noqa: E402


class GSReference:
    """Upload PSMCT32 into local-memory addresses, then read PSMT8 and CSM1."""

    def __init__(self, source):
        require(sha(source) == TABLES_SHA256, "HRM_ORACLE_PIN")

        def table(name, count):
            match = re.search(r"\b" + name + r"\[[^=]+?=\s*\{(.*?)\};", source.decode(), re.S)
            require(match is not None, "HRM_ORACLE_TABLE")
            rows = list(map(int, re.findall(r"\d+", re.sub(r"//[^\n]*", "", match[1]))))
            require(len(rows) == count, "HRM_ORACLE_TABLE")
            return rows

        self.b32, self.c32 = table("_blockTable32", 32), table("columnTable32", 64)
        self.b8, self.c8 = table("_blockTable8", 32), table("columnTable8", 256)
        self.index_maps = {}

    def upload(self, width, height, capacity):
        memory = array("i", [-1]) * capacity
        for y in range(height):
            for x in range(width):
                page = (y // 32) * (width // 64) + x // 64
                block = self.b32[y % 32 // 8 * 8 + x % 64 // 8]
                at = page * 8192 + block * 256 + self.c32[y % 8 * 8 + x % 8] * 4
                for lane in range(4):
                    require(memory[at + lane] == -1, "HRM_ORACLE_OVERLAP")
                    memory[at + lane] = (y * width + x) * 4 + lane
        return memory

    def index_map(self, width, height):
        key = width, height
        if key in self.index_maps:
            return self.index_maps[key]
        require(len(self.index_maps) < 8, "HRM_ORACLE_CACHE")
        memory = self.upload(width // 2, height // 2, width * height)
        offsets = array("i")
        for y in range(height):
            for x in range(width):
                page = y // 64 * (width // 128) + x // 128
                block = self.b8[y % 64 // 16 * 8 + x % 128 // 16]
                address = page * 8192 + block * 256 + self.c8[y % 16 * 16 + x % 16]
                require(memory[address] >= 0, "HRM_ORACLE_UNWRITTEN")
                offsets.append(memory[address])
        self.index_maps[key] = offsets
        return offsets

    def palettes(self, raw):
        memory = self.upload(64, len(raw) // 256, 16384)
        result = {}
        for selector in range(16):
            cells = []
            for group in range(8):
                for half in range(2):
                    for row in range(2):
                        for column in range(8):
                            x, y = half * 8 + column, group * 2 + row
                            block = self.b32[y // 8 * 8 + x // 8]
                            at = selector * 1024 + block * 256 + self.c32[y % 8 * 8 + x % 8] * 4
                            cells.append(memory[at])
            if min(cells) >= 0:
                result[selector] = b"".join(raw[at : at + 4] for at in cells)
        return result

    def texture(self, raw):
        # Separate sequential parser; no production TEX decoder or CLUT address helper.
        require(struct.unpack_from("<I", raw)[0] == 0xFFFFFFFF, "HRM_ORACLE_AREA")
        (count,) = struct.unpack_from("<I", raw, 20)
        at, blocks = 32, []
        for _ in range(count):
            w, h = struct.unpack_from("<HH", raw, at + 8)
            size, total = struct.unpack_from("<II", raw, at + 16)
            require(raw[at + 12] == 8 and size == w * h, "HRM_ORACLE_FORMAT")
            end = at + total
            upload = raw[end - size : end]
            indices = bytes(upload[i] for i in self.index_map(w, h))
            (palette_size,) = struct.unpack_from("<I", raw, end)
            clut = raw[end + 48 : end + 48 + palette_size]
            colors = self.palettes(clut)
            palettes = []
            for selector, palette in colors.items():
                entries = tuple(palette[i : i + 4] for i in range(0, 1024, 4))
                rgba = b"".join(entries[i] for i in indices)
                alpha = rgba[3::4]
                palettes.append(
                    dict(
                        selector=selector,
                        palette_sha256=sha(palette),
                        rgba_sha256=sha(rgba),
                        rgba_bytes=len(rgba),
                        alpha=dict(
                            min=min(alpha),
                            max=max(alpha),
                            zero_pixels=alpha.count(0),
                            full_ps2_pixels=alpha.count(128),
                            above_ps2_pixels=sum(a > 128 for a in alpha),
                        ),
                    )
                )
            blocks.append(dict(indices_sha256=sha(indices), palettes=palettes))
            at = end + 48 + palette_size
        require(at == len(raw), "HRM_ORACLE_END")
        return blocks


def audit(args):
    custody = PinnedInputs()
    paths = {
        key: getattr(args, key).resolve() for key in ("profile", "catalog", "receipt", "copies")
    }
    contacts, _ = _prepare(paths, custody)
    profile = read_profile(contacts["copy-a"]["room-profile.json"])
    reference_raw = custody.read(args.tables.resolve(), 1024 * 1024)
    reference = GSReference(reference_raw)
    views, checks, rigs = [], [], []
    for copy, rig_path in (("copy-a", args.heather_a), ("copy-b", args.heather_b)):
        resources = {}
        for role in ("map", "external_texture"):
            pin = profile["resources"][role]
            resources[role] = custody.read(
                paths["copies"] / copy / (pin["id"][6:] + ".bin"),
                pin["size"],
                {k: pin[k] for k in ("size", "sha256")},
            )
        view = inspect_candidates(
            resources["map"], resources["external_texture"], args.embedded_offset
        )
        expected = reference.texture(resources["external_texture"]) + reference.texture(
            resources["map"][args.embedded_offset :]
        )
        require(len(view["blocks"]) == len(expected), "HRM_ORACLE_BLOCKS")
        for actual, block in zip(view["blocks"], expected, strict=True):
            require(actual["indices_sha256"] == block["indices_sha256"], "HRM_ORACLE_INDICES")
            require(len(actual["palettes"]) == len(block["palettes"]), "HRM_ORACLE_SELECTORS")
            for a, e in zip(actual["palettes"], block["palettes"], strict=True):
                require({k: a[k] for k in e} == e, "HRM_ORACLE_PIXELS")
        rig, _ = _rig(rig_path.resolve(), profile, custody)
        rigs.append({k: sha(v) for k, v in rig.items()})
        texture_bytes = sum(len(v) for k, v in rig.items() if k.endswith(".rgba"))
        checks.append(
            dict(
                copy=copy,
                blocks=len(expected),
                palettes=sum(len(b["palettes"]) for b in expected),
                compared_pixels=sum(p["rgba_bytes"] // 4 for b in expected for p in b["palettes"]),
                heather_texture_bytes=texture_bytes,
            )
        )
        views.append(view)
    require(views[0] == views[1] and rigs[0] == rigs[1], "HRM_A_B")
    custody.verify()
    total = texture_bytes + views[0]["budget"]["unique_candidate_rgba_bytes"]
    limit = profile["budgets"]["resident_texture_bytes"]
    return dict(
        schema_version=1,
        task="HM-T4c.3.1",
        status="candidate_inventory_verified",
        copies_identical=True,
        inventory=views[0],
        oracle_checks=checks,
        oracle_reference=dict(revision=REVISION, sha256=TABLES_SHA256),
        combined_candidate_texture_bytes=total,
        resident_texture_limit_bytes=limit,
        candidate_texture_budget_fits=total <= limit,
        physical_validation=False,
        original_material_binding_verified=False,
        new_vm_execution=False,
        source_pins=[
            dict(path=str(path), **values[1]) for path, values in sorted(custody.sources.items())
        ],
        tool_pins={
            str(p.relative_to(ROOT)): sha(p.read_bytes())
            for p in (
                Path(__file__),
                ROOT / "tools/inspectors/map_material_candidates.py",
                ROOT / "tools/pipeline/decoders/ps2_indexed.py",
                ROOT / "tools/inspectors/map_probe.py",
                ROOT / "tools/inspectors/map_render_probe.py",
                ROOT / "tools/inspectors/texture_probe.py",
            )
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in (
        "profile",
        "catalog",
        "receipt",
        "copies",
        "tables",
        "heather-a",
        "heather-b",
        "output",
    ):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--embedded-offset", type=int, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "HRM_OUTPUT_EXISTS")
    report = audit(args)
    raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
    require(args.output.read_bytes() == raw, "HRM_OUTPUT_READBACK")
    print(
        json.dumps(
            dict(
                status=report["status"],
                bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                summary=report["inventory"]["summary"],
                budget=report["inventory"]["budget"],
                combined_candidate_texture_bytes=report["combined_candidate_texture_bytes"],
            )
        )
    )


if __name__ == "__main__":
    main()
