"""HRB01–06: reproduce original hp34 assignments from pinned private evidence.

Read-only, no emulator launch; emits hashes, addresses, counts and draw states.
"""

import argparse
import json
import os
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.inspectors.elf32 import parse_elf  # noqa: E402
from tools.inspectors.map_material_binding import (  # noqa: E402
    Memory,
    apply_packet,
    initial_gs_state,
    match_strip,
    prepared_mesh,
    project_vertices,
    require,
)
from tools.inspectors.observer_state import MAX_CPU_PREFIX  # noqa: E402
from tools.inspectors.pcsx2_gs_dump import Dump  # noqa: E402
from tools.inspectors.pcsx2_state import (  # noqa: E402
    INTERNALS_MEMBER,
    VERSION_MEMBER,
    decode_ee_state,
    read_state_members,
)
from tools.inspectors.texture_probe import probe_texture  # noqa: E402
from tools.pipeline.collision_polygon_inputs import PinnedInputs  # noqa: E402
from tools.pipeline.intermediate_assets import sha  # noqa: E402
from tools.pipeline.iso9660 import IsoImage  # noqa: E402
from tools.qa.gs_material_oracle import decode_draw_state  # noqa: E402

INVENTORY_PIN = "959ea2a0861120936b135a30416c57649c23c4d4844b294f1e12ee2e53ff7719"
ELF_PIN = "cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789"
DUMP_PIN = "4ce2e101e325e92ef68ac521bd6329fcd12cdf68ea09275aeab3d2e68ab2c801"
CAPTURES = (
    (3, 12, 0x1B2440, "cfd63522148af2ebea750425b7c3eae5fb1053392aa08cd2f5cf242663be89d6"),
    (5, 6, 0x1B175C, "025b82b6c0d9b7b263f85d3045545f3b9d755a55c0aa1a81dd2b74774d6808f2"),
)
WINDOWS = (
    (0x1ABCC0, 0x20),
    (0x1ABD00, 0x20),
    (0x1ABD90, 0x50),
    (0x1AC1D0, 0x210),
    (0x1AC5A0, 0x480),
    (0x1ACA20, 0x410),
    (0x1AD8D0, 0x120),
    (0x1ADEB0, 0xF0),
    (0x1AE3F0, 0x350),
    (0x1AE9F0, 0x2B0),
    (0x1B0720, 0x10),
    (0x1B5F20, 0x80),
)
REGISTERS = (
    0,
    6,
    8,
    0x14,
    0x18,
    0x1A,
    0x22,
    0x3B,
    0x3D,
    0x40,
    0x42,
    0x45,
    0x46,
    0x47,
    0x49,
    0x4A,
    0x4C,
    0x4E,
)


def read_pinned(custody, path, digest, limit=64 * 1024 * 1024):
    raw = custody.read(path.resolve(), limit)
    require(sha(raw) == digest, "HRB_INPUT_PIN")
    return raw


def original_elf(iso_path):
    with IsoImage(iso_path) as iso:
        n, digest = iso.inspect("SLES_514.34")
        require((n, digest) == (3395784, ELF_PIN), "HRB_ELF")
        raw = b"".join(
            iso.read_range("SLES_514.34", i, min(4096, n - i)) for i in range(0, n, 4096)
        )
        require(sha(raw) == ELF_PIN, "HRB_ELF")
    mapping = parse_elf(lambda o, n: raw[o : o + n], len(raw))
    return [
        (
            a,
            raw[
                mapping.file_offset(a, n, executable=True) : mapping.file_offset(
                    a, n, executable=True
                )
                + n
            ],
        )
        for a, n in WINDOWS
    ]


def check_profile(state, mode):
    decoded = decode_draw_state(state)
    require(not state.get(0x100, False), "HRB_TEX2")
    require(state[0] == (0x7C if mode == 1 else 0x3C), "HRB_GS_PRIM")
    require(state[0x14] == 0x60 and state[8] == 0, "HRB_FILTER_WRAP")
    require(state[0x47] == (0x5800D if mode == 3 else 0x5800C), "HRB_GS_TEST")
    require(state[0x42] == 0x44 and state[0x4E] == 0x3A0001C0, "HRB_BLEND_DEPTH")
    require(state[0x4C] in (0x80100, 0x80000), "HRB_FRAME")
    require(state[0x3B] == 0x8000000040 and state[0x3D] == 0, "HRB_TEXA_FOG")
    require(all(state[r] == 0 for r in (0x22, 0x45, 0x49, 0x4A)) and state[0x46] == 1, "HRB_GLOBAL")
    tex = decoded["texture"]
    require(
        all(
            tex[k] == v
            for k, v in dict(
                tbw=8, psm=19, tw=9, th=9, tcc=1, tfx=0, cpsm=0, csm=0, csa=0, cld=1
            ).items()
        ),
        "HRB_TEXTURE",
    )
    return decoded


def consume(dump, lookup, meshes, raw_map, sequences):
    source = raw_map[258048:]
    catalog = probe_texture(len(source), lambda o, n: source[o : o + n])
    uploads = []
    for b in catalog["blocks"]:
        for kind, off, size in (
            ("indices", b["indices"]["offset"], b["indices"]["size"]),
            ("clut", b["clut"]["data_offset"], b["clut"]["size"]),
        ):
            uploads.append((b["ordinal"], kind, source[off : off + size]))
    shape_map = {s["shape_offset"]: (m, s) for m in meshes for s in m["shapes"]}
    state = initial_gs_state(dump.state)
    active, transfer, transfers, shapes, order = {}, None, [], {}, defaultdict(list)
    pending = bytearray()

    def flush():
        if not pending:
            return
        require(transfer is not None and transfer["direction"] == 0, "HRB_TRANSFER")
        bitblt, position = transfer["bitblt"], transfer["position"]
        base, psm = bitblt >> 32 & 16383, bitblt >> 56 & 63
        matches = [(i, kind) for i, kind, raw in uploads if raw == pending]
        # Every transfer invalidates overlapping recorded uploads, including unknown data.
        end = base + (len(pending) + 255) // 256
        for key, value in list(active.items()):
            if max(key, base) < min(value["end"], end):
                del active[key]
        if matches:
            require(len(matches) == 1 and psm == 0 and position == 0, "HRB_UPLOAD_MATCH")
            block, kind = matches[0]
            require(bitblt >> 48 & 63 == (4 if kind == "indices" else 1), "HRB_UPLOAD_WIDTH")
            require(
                transfer["extent"] == (0x10000000100 if kind == "indices" else 0x4000000040),
                "HRB_UPLOAD_EXTENT",
            )
            row = dict(
                frame=transfer["frame"],
                packet=transfer["packet"],
                base=base,
                block=block,
                kind=kind,
                bytes=len(pending),
                sha256=sha(pending),
            )
            transfers.append(row)
            active[base] = dict(end=end, **row)
        pending.clear()

    for ordinal, packet in enumerate(dump.packets()):
        f = packet.fields
        if f["flag"] == 2:
            require(len(pending) + len(packet.payload) <= 4 * 1024 * 1024, "HRB_UPLOAD_LIMIT")
            pending.extend(packet.payload)
            continue
        flush()
        apply_packet(state, packet)
        if f["flag"] == 0:
            for j in range(f["nloop"] * f["nreg"]):
                if (f["regs"] >> ((j % f["nreg"]) * 4)) & 15 == 14:
                    value, reg = struct.unpack_from("<QQ", packet.payload, j * 16)
                    if reg == 0x53:
                        transfer = dict(
                            frame=packet.frame,
                            packet=ordinal,
                            direction=value,
                            bitblt=state[0x50],
                            position=state[0x51],
                            extent=state[0x52],
                        )
        if not (f["flag"] == 0 and f["nreg"] == 3 and f["regs"] == 0x412 and f["nloop"]):
            continue
        tex0 = state[6]
        index = active.get(tex0 & 16383)
        if index is None or index["kind"] != "indices":
            continue
        shape, error = match_strip(packet.payload, lookup)
        require(shape in shape_map, "HRB_FOREIGN_SHAPE")
        mesh, prepared = shape_map[shape]
        require(prepared["submitted"] and index["block"] == mesh["group_index"], "HRB_GS_BINDING")
        clut_base = (tex0 >> 37 & 16383) - mesh["selector"] * 4
        clut = active.get(clut_base)
        require(
            clut is not None and clut["kind"] == "clut" and clut["block"] == index["block"],
            "HRB_GS_CLUT",
        )
        check_profile(state, mesh["mode"])
        require(packet.path == 3 and packet.frame in (1, 3), "HRB_GS_FRAME")
        key = (packet.frame, shape)
        require(key not in shapes or order[packet.frame][-1] == shape, "HRB_DRAW_INTERLEAVE")
        if key not in shapes:
            order[packet.frame].append(shape)
            shapes[key] = dict(
                frame=packet.frame,
                shape_offset=shape,
                packets=0,
                vertices=0,
                max_xyz_error=0,
                registers={},
                rgba_min=[255] * 4,
                rgba_max=[0] * 4,
                fog_min=255,
                fog_max=0,
                enabled_triangles=0,
                transfer_packets=[index["packet"], clut["packet"]],
            )
        row = shapes[key]
        cursor = row["vertices"]
        match_strip(packet.payload, lookup, sequences[shape][cursor : cursor + f["nloop"]])
        registers = {f"{r:02x}": f"{state[r]:016x}" for r in REGISTERS}
        require(not row["registers"] or row["registers"] == registers, "HRB_STATE_CHANGED")
        row["registers"] = registers
        row["packets"] += 1
        row["vertices"] += f["nloop"]
        row["max_xyz_error"] = max(error, row["max_xyz_error"])
        for i in range(f["nloop"]):
            rgba = struct.unpack_from("<4I", packet.payload, i * 48 + 16)
            fog_word = struct.unpack_from("<I", packet.payload, i * 48 + 44)[0]
            require(max(rgba) <= 255, "HRB_COLOR")
            for c in range(4):
                row["rgba_min"][c] = min(row["rgba_min"][c], rgba[c])
                row["rgba_max"][c] = max(row["rgba_max"][c], rgba[c])
            fog = fog_word >> 4 & 255
            row["fog_min"], row["fog_max"] = min(row["fog_min"], fog), max(row["fog_max"], fog)
            row["enabled_triangles"] += int(i >= 2 and not fog_word & 0x8000)
    flush()
    expected_order = [s["shape_offset"] for m in meshes for s in m["shapes"] if s["submitted"]]
    require(
        set(order) == {1, 3} and all(v == expected_order for v in order.values()), "HRB_DRAW_ORDER"
    )
    for (_, shape), row in shapes.items():
        _, p = shape_map[shape]
        require(row["vertices"] == p["vertices"] + 2 * (p["batches"] - 1), "HRB_GS_COVERAGE")
    require(
        Counter((t["frame"], t["block"], t["kind"]) for t in transfers)
        == Counter((f, b, k) for f in (1, 3) for b in range(7) for k in ("indices", "clut")),
        "HRB_UPLOAD_COVERAGE",
    )
    return dict(
        transfers=transfers,
        draws=list(shapes.values()),
        order=dict(order),
        submitted_shapes=len(expected_order),
        frames=2,
        matched_vertex_records=sum(r["vertices"] for r in shapes.values()),
    )


def audit(args):
    custody = PinnedInputs()
    previous = json.loads(
        read_pinned(
            custody, ROOT / "reports/local/heather-room-material-candidates-v1.json", INVENTORY_PIN
        )
    )
    historical = json.loads(
        read_pinned(
            custody,
            ROOT / "reports/local/f03-02-map-runtime-binding-v1.json",
            "e7ca63fee6277bac68fa6cbe00d616eb3c1ae9c685a7b0e6d318fdb61d7b5344",
        )
    )
    gs_history = json.loads(
        read_pinned(
            custody,
            ROOT / "reports/local/f03-02-map-gs-v1.json",
            "aa7c2bdde2d0fed8b3bcd5743f57184ea8ee68d55ab578f8a45aebc07d696661",
        )
    )
    require(
        historical["mounted_load"]["captures"][-1]["state_sha256"] == CAPTURES[0][3]
        and gs_history["captures"][-1]["state_sha256"] == CAPTURES[1][3]
        and gs_history["dump_sha256"] == DUMP_PIN
        and gs_history["provenance"]
        == dict(
            diagnostic_replay=True,
            camera_override_each_game_frame=True,
            normal_playthrough=False,
            model_or_asset_modified=False,
            gs_dump_packets_modified=False,
        ),
        "HRB_PROVENANCE",
    )
    inventory = previous["inventory"]
    # Preserve the previous A/B + independent GS-table custody, not just its conclusion.
    for pin in previous["source_pins"]:
        custody.read(Path(pin["path"]), pin["size"], {k: pin[k] for k in ("size", "sha256")})
    resources = []
    for copy in ("copy-a", "copy-b"):
        pin = next(
            p
            for p in previous["source_pins"]
            if f"/{copy}/" in p["path"] and p["sha256"] == inventory["source_map_sha256"]
        )
        resources.append(custody.read(Path(pin["path"]), pin["size"]))
    require(resources[0] == resources[1], "HRB_AB")
    raw_map = resources[0]
    code = original_elf(args.iso)
    captures, memory = [], None
    for version, slot, pc, digest in CAPTURES:
        stage = args.private / f"f03-02-map-runtime-v{version}"
        raw = read_pinned(custody, stage / f"states/SLES-51434 (5088CCDB).{slot:02}.p2s", digest)
        ver, inn, ram = read_state_members(
            raw,
            (
                (VERSION_MEMBER, 36),
                (INTERNALS_MEMBER, 16 * 1024 * 1024),
                ("eeMemory.bin", 33554432),
            ),
        )
        cpu = decode_ee_state(ver, inn[:MAX_CPU_PREFIX], 0x5088CCDB)
        require(cpu.pc == pc and not cpu.delay_slot, "HRB_CAPTURE_PC")
        memory = Memory(ram)
        require(memory.read(0x18D2200, len(raw_map)) == raw_map, "HRB_MAP_IN_RAM")
        require(all(memory.read(a, len(b)) == b for a, b in code), "HRB_CODE_IN_RAM")
        require(
            memory.u32(0x1D0B3A0) == 0x18D2200 and memory.u32(0x1D0B3A0 + 0x14) == 7, "HRB_CONTEXT"
        )
        rows = []
        for i, group in enumerate(inventory["groups"][1:]):
            require(
                memory.u32(0x1D0B3A0 + 0x120 + i * 4) == 0x18D2200 + group["group_offset"],
                "HRB_GROUP",
            )
            block = inventory["blocks"][i + 1]
            for j, mesh in enumerate(group["meshes"]):
                row = prepared_mesh(
                    memory, 0x1D0B3A0, 0x18D2200, i, j, mesh, block["source_header_offset"]
                )
                palette = next(p for p in block["palettes"] if p["selector"] == row["selector"])
                row.update(
                    block=block["key"],
                    source_header_offset=block["source_header_offset"],
                    palette_sha256=palette["palette_sha256"],
                    rgba_sha256=palette["rgba_sha256"],
                    rgba_bytes=palette["rgba_bytes"],
                )
                for shape in row["shapes"]:
                    source_gate = memory.words(0x18D2200 + shape["shape_offset"] + 20, 2)
                    shape["source_visibility_words"] = list(source_gate)
                    if not shape["submitted"]:
                        require(
                            source_gate[0] == 2 and shape["gate"] == 0x10000 | source_gate[1],
                            "HRB_OMISSION_GATE",
                        )
                rows.append(row)
        captures.append(dict(version=version, slot=slot, pc=pc, sha256=digest, meshes=rows))
    require(captures[0]["meshes"] == captures[1]["meshes"], "HRB_CAPTURE_STABILITY")
    meshes = captures[-1]["meshes"]
    all_shapes = [s for m in meshes for s in m["shapes"]]
    require(len(all_shapes) == 29, "HRB_SHAPES")
    require(
        [s["shape_offset"] for s in all_shapes if not s["submitted"]] == [149504, 222736, 245648],
        "HRB_SKIPPED",
    )
    # Same frozen VU0 projection used by the prior glass oracle; no matrix inference from layout.
    tag = b"vuMicroRegs" + bytes(21)
    require(inn.count(tag) == 1, "HRB_VU_REGS")
    start = inn.index(tag) + 64
    matrix = [struct.unpack_from("<4f", inn, start + i * 16) for i in range(4)]
    lookup, sequences = defaultdict(list), {}
    for shape in all_shapes:
        offset, n = shape["shape_offset"], shape["vertices"]
        points = project_vertices(raw_map[offset + 64 : offset + 64 + n * 16], matrix)
        sequences[offset] = [
            point
            for first, count in shape["source_ranges"]
            for point in points[first : first + count]
        ]
        for uv, xyz in points:
            lookup[uv].append((offset, xyz))
    dump_raw = read_pinned(
        custody,
        args.private
        / "f03-02-map-runtime-v6/profile/PCSX2/snaps/Silent Hill 3_SLES-51434_20261020112709.gs",
        DUMP_PIN,
    )
    dump = Dump(dump_raw)
    require(dump.crc == 0x5088CCDB and dump.serial == "SLES-51434", "HRB_GAME")
    consumed = consume(dump, lookup, meshes, raw_map, sequences)
    profiles = []
    for mode, name in ((0, "opaque"), (3, "alpha_test_greater_zero"), (1, "source_alpha_blend")):
        row = next(
            r
            for r in consumed["draws"]
            if next(
                m for m in meshes if r["shape_offset"] in [s["shape_offset"] for s in m["shapes"]]
            )["mode"]
            == mode
        )
        profile = decode_draw_state({int(r, 16): int(v, 16) for r, v in row["registers"].items()})
        profiles.append(
            dict(
                mode=mode,
                name=name,
                shape_count=sum(len(m["shapes"]) for m in meshes if m["mode"] == mode),
                decoded=profile,
            )
        )
    custody.verify()
    require(original_elf(args.iso) == code, "HRB_ELF_CHANGED")
    return dict(
        schema_version=1,
        task="HM-T4c.3.2",
        status="original_material_assignments_verified",
        assigned_shapes=29,
        consumed_shapes=26,
        omitted_shapes=3,
        copies_identical=True,
        new_vm_execution=False,
        diagnostic_replay=True,
        normal_playthrough=False,
        pixel_fidelity_verified=False,
        hardware_validation=False,
        current_build_changed=False,
        captures=captures,
        gs=consumed,
        profiles=profiles,
        projection_sha256=sha(inn[start : start + 64]),
        code_windows=[dict(address=a, size=len(b), sha256=sha(b)) for a, b in code],
        inputs=[dict(path=str(p), **v[1]) for p, v in sorted(custody.sources.items())],
        tools={
            str(p.relative_to(ROOT)): sha(p.read_bytes())
            for p in (
                Path(__file__),
                ROOT / "tools/inspectors/map_material_binding.py",
                ROOT / "tools/inspectors/pcsx2_gs_dump.py",
                ROOT / "tools/qa/gs_material_oracle.py",
            )
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("private", "iso", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "HRB_OUTPUT_EXISTS")
    report = audit(args)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    with os.fdopen(
        os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
    ) as stream:
        stream.write(raw)
    require(args.output.read_bytes() == raw, "HRB_OUTPUT_READBACK")
    print(
        json.dumps(
            dict(
                status=report["status"],
                bytes=len(raw),
                sha256=sha(raw),
                shapes=report["assigned_shapes"],
                consumed_shapes=report["consumed_shapes"],
                matched_vertex_records=report["gs"]["matched_vertex_records"],
            )
        )
    )


if __name__ == "__main__":
    main()
