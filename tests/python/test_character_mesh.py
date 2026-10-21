"""Own asymmetric MDL/VIF fixture; no game bytes or private data dependency."""

import copy
import hashlib
import json
import struct
from io import BytesIO

import pycdlib
import pytest
from test_mfa import sector

from tools.pipeline import decode_character_mesh as coordinator
from tools.pipeline.decoders.ps2_character_mesh import CharacterMeshError, decode_character_mesh
from tools.pipeline.decoders.ps2_character_vif import CharacterVifError, load_vif
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError

IDENTITY = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def command(opcode, immediate=0, count=0):
    return struct.pack("<HBB", immediate, count, opcode)


def unpack(opcode, address, rows, unsigned=False):
    code = "I" if opcode == 0x6C else ("H" if unsigned else "h")
    payload = b"".join(struct.pack("<" + code * len(row), *row) for row in rows)
    return command(opcode, address | (0x4000 if unsigned else 0), len(rows) % 256) + (
        payload + bytes(-len(payload) % 4)
    )


def packet(base=0, weights=(1023, 1023, 2048), *, overrides=None, strip=None):
    # 3 vertices mixed across 0/1/2, then 3 rigid vertices on bone 2.
    rows = [
        [2, 0, base + 6, base + 30],
        [0, 0, base + 50, base + 52],
        [3, 4, base + 6, base + 18],
        [base + 30, base + 42, base + 46, 0],
        [3, 0, base + 18, base + 30],
        [base + 38, 0, 0, 0],
    ]
    for (row, lane), value in (overrides or {}).items():
        rows[row][lane] = value
    positions = [(0, 0, 4), (16, -8, 8), (8, 24, -4), (48, 0, 32), (0, -16, 64), (-16, 32, 0)]
    if strip is None:
        strip = [
            0x8000 | (base + 6),
            0x8000 | (base + 10),
            base + 14,
            0x8000 | (base + 18),
            0x8000 | (base + 22),
            base + 26,
            base + 26,
            base + 26,
        ]
    raw = command(1, 0x101) + unpack(0x6C, base, rows, True)
    raw += command(1, 0x104) + unpack(0x69, base + 6, positions)
    raw += unpack(0x69, base + 7, [(-4096, 0, 0)] * 6)
    raw += unpack(0x69, base + 8, [weights] * 3)
    raw += unpack(0x65, base + 9, [(512 * i, -256 * i) for i in range(6)])
    raw += command(1, 0x101) + unpack(0x6D, base + 50, [strip[:4], strip[4:]], True)
    return raw + bytes(-len(raw) % 16)


def model(*, packets=None):
    if packets is None:
        packets = [packet()]
    data = bytearray(528)
    struct.pack_into("<8I", data, 0, 0, 0x123, 1, 0, 0, 32, 0, 0)
    header = [0] * 32
    header[:16] = [
        0xFFFF0003,
        3,
        128,
        3,
        320,
        2,
        336,
        352,
        1,
        496,
        len(packets) - 1,
        0,
        1,
        0,
        1,
        480,
    ]
    struct.pack_into("<32I", data, 32, *header)
    for index, at in enumerate((160, 224, 288, 384, 448)):
        matrix = list(IDENTITY)
        matrix[1], matrix[12] = -0.0, index * 10
        struct.pack_into("<16f", data, at, *matrix)
    struct.pack_into("<3b", data, 352, -1, -1, 1)
    struct.pack_into("<4b", data, 368, 0, 1, 0, 2)
    struct.pack_into("<2i", data, 512, 0, 7)
    for index, raw in enumerate(packets):
        at = len(data)
        if index == 1:
            struct.pack_into("<I", data, 32 + 11 * 4, at - 32)
        words = [0] * 36
        words[:11] = [
            160 + len(raw),
            0xACE,
            160,
            len(raw) // 16,
            0 if index == 0 else 512,
            0,
            144,
            3,
            144,
            2,
            150,
        ]
        words[14], words[16], words[35] = 154, 0x50002, 0xBABE
        data.extend(struct.pack("<36I", *words))
        data.extend(struct.pack("<6h", 0, 1, 2, 0, 1, 0) + bytes(4))
        data.extend(raw)
    return bytes(data)


def mutate(raw, at, fmt, *values):
    data = bytearray(raw)
    struct.pack_into(fmt, data, at, *values)
    return bytes(data)


def test_integer_geometry_bindings_and_both_partitions():
    mesh = decode_character_mesh(model(packets=[packet(), packet(512)]))
    assert mesh.skeleton.model_id == 0x123
    assert mesh.helpers == ((0, 1), (0, 2))
    assert mesh.helper_matrix_words[0][1] == 0x80000000
    assert mesh.texture_descriptors == ((0, 7),)
    assert [part.blend_partition for part in mesh.submeshes] == [False, True]
    first = mesh.submeshes[0]
    assert first.header_words[1] == 0xACE and first.header_words[35] == 0xBABE
    assert first.groups[0].helper_indices == (0, 1)
    assert first.vertices[1].position_q4 == (16, -8, 8)
    assert first.vertices[1].normal_q12 == (-4096, 0, 0)
    assert first.vertices[1].uv_q12 == (512, -256)
    assert first.vertices[1].weights_q12 == (1023, 1023, 2048)
    assert first.vertices[1].bones == (0, 1, 2)
    assert first.vertices[4].primary_bone == 2
    assert first.vertices[4].weights_q12 == (4096,)
    assert first.triangles == ((0, 1, 2), (5, 4, 3))
    assert first.suppressed_commands == 4 and first.degenerate_triangles == 2
    assert first.vertices == mesh.submeshes[1].vertices


@pytest.mark.parametrize(
    ("at", "fmt", "value", "code"),
    [
        (32 + 17 * 4, "I", 1, "CM_MORPH_UNSUPPORTED"),
        (32 + 19 * 4, "I", 1, "CM_MORPH_UNSUPPORTED"),
        (32 + 5 * 4, "I", 129, "CM_HELPER_COUNT"),
        (32 + 8 * 4, "I", 257, "CM_SUBMESH_COUNT"),
        (32 + 8 * 4, "I", 0, "CM_SUBMESH_COUNT"),
        (32 + 14 * 4, "I", 0, "CM_TEXTURE_COUNT"),
        (32 + 12 * 4, "I", 257, "CM_TEXTURE_COUNT"),
        (32 + 6 * 4, "I", 1, "CM_SECTION_RANGE"),
        (32 + 7 * 4, "I", 0xFFFFFFF0, "CM_SECTION_RANGE"),
        (368, "b", -1, "CM_HELPER_REFERENCE"),
        (369, "b", 0, "CM_HELPER_REFERENCE"),
        (369, "b", 3, "CM_HELPER_REFERENCE"),
        (384, "f", float("nan"), "CM_HELPER_NONFINITE"),
        (384 + 60, "f", 0, "CM_HELPER_AFFINE"),
        (512, "i", 1, "CM_TEXTURE_REFERENCE"),
        (516, "i", -1, "CM_TEXTURE_REFERENCE"),
        (528, "I", 128, "CM_SUBMESH_LENGTH"),
        (528, "I", 161, "CM_SUBMESH_LENGTH"),
        (528, "I", 1 << 20, "CM_SECTION_RANGE"),
        (528 + 20, "I", 1, "CM_MORPH_UNSUPPORTED"),
        (528 + 28, "I", 0, "CM_EMPTY_BONE_PALETTE"),
        (528 + 28, "I", 4, "CM_PALETTE_COUNT"),
        (528 + 32, "I", 145, "CM_SECTION_RANGE"),
        (528 + 144, "h", -1, "CM_PALETTE_REFERENCE"),
        (528 + 144, "h", 1, "CM_PALETTE_REFERENCE"),
        (528 + 152, "h", 2, "CM_PALETTE_REFERENCE"),
        (528 + 154, "h", 1, "CM_TEXTURE_REFERENCE"),
        (528 + 8, "I", 144, "CM_SECTION_OVERLAP"),
        (528 + 12, "I", 0, "CM_VIF_SIZE"),
        (528 + 16, "I", 1024, "CM_VU_ADDRESS"),
    ],
)
def test_invalid_model_sections(at, fmt, value, code):
    with pytest.raises((CharacterMeshError, CharacterVifError), match=code):
        decode_character_mesh(mutate(model(), at, "<" + fmt, value))


@pytest.mark.parametrize(
    ("row", "lane", "value", "code"),
    [
        (0, 0, 65, "CM_VU_LAYOUT"),
        (1, 2, 1024, "CM_VU_LAYOUT"),
        (1, 3, 1025, "CM_VU_LAYOUT"),
        (2, 1, 3, "CM_VERTEX_GROUP"),
        (2, 0, 0, "CM_VERTEX_GROUP"),
        (2, 3, 17, "CM_VERTEX_RANGE"),
        (2, 2, 7, "CM_VERTEX_RANGE"),
        (3, 0, 29, "CM_BONE_ADDRESS"),
        (3, 0, 31, "CM_BONE_ADDRESS"),
        (3, 0, 42, "CM_BONE_ADDRESS"),
        (3, 1, 38, "CM_BONE_ADDRESS"),
        (3, 1, 50, "CM_BONE_ADDRESS"),
        (3, 0, 34, "CM_HELPER_BASE"),
        (3, 2, 42, "CM_HELPER_BASE"),
        (1, 2, 30, "CM_SECTION_OVERLAP"),
    ],
)
def test_bad_vu_groups(row, lane, value, code):
    raw = packet(overrides={(row, lane): value})
    with pytest.raises(CharacterMeshError, match=code):
        decode_character_mesh(model(packets=[raw]))


def test_external_matrix_bank_must_fit_vu_memory():
    raw = packet(overrides={(0, 3): 1010, (3, 0): 1010, (3, 1): 1022, (3, 2): 1026, (5, 0): 1018})
    with pytest.raises(CharacterMeshError, match="CM_BONE_ADDRESS"):
        decode_character_mesh(model(packets=[raw]))


def test_two_influences_preserve_one_unit_deficit():
    raw = packet(weights=(2048, 2047, 0), overrides={(2, 1): 2})
    vertex = decode_character_mesh(model(packets=[raw])).submeshes[0].vertices[0]
    assert vertex.bones == (0, 1) and vertex.weights_q12 == (2048, 2047)


def test_partitions_cannot_alias_the_same_mesh():
    raw = mutate(model(), 32 + 10 * 4, "<2I", 1, 496)
    with pytest.raises(CharacterMeshError, match="CM_SECTION_OVERLAP"):
        decode_character_mesh(raw)


def test_source_may_use_no_helpers_for_rigid_geometry():
    raw = packet(overrides={(2, 1): 0})
    data = mutate(model(packets=[raw]), 32 + 5 * 4, "<I", 0)
    data = mutate(data, 528 + 9 * 4, "<I", 0)
    # The unused helper matrix gap remains uninterpreted source bytes.
    mesh = decode_character_mesh(data)
    assert mesh.helpers == () and mesh.helper_matrix_words == ()
    assert all(len(v.bones) == 1 for v in mesh.submeshes[0].vertices)


@pytest.mark.parametrize(
    "weights", [(-1, 1023, 3072), (4097, 0, 0), (1000, 1000, 2000), (2048, 2048, 1)]
)
def test_invalid_weights_are_never_fixed(weights):
    with pytest.raises(CharacterMeshError, match="CM_WEIGHTS"):
        decode_character_mesh(model(packets=[packet(weights=weights)]))


@pytest.mark.parametrize(
    ("index", "value", "code"),
    [
        (2, 15, "CM_STRIP_ADDRESS"),
        (2, 30, "CM_STRIP_ADDRESS"),
        (2, 2, "CM_STRIP_ADDRESS"),
        (0, 6, "CM_STRIP_PREFIX"),
    ],
)
def test_bad_strip_addresses_and_prefix(index, value, code):
    strip = [0x8006, 0x800A, 14, 0x8012, 0x8016, 26, 26, 26]
    strip[index] = value
    with pytest.raises(CharacterMeshError, match=code):
        decode_character_mesh(model(packets=[packet(strip=strip)]))


def test_vif_signed_unsigned_skip_and_unspecified_lanes():
    data = command(1, 0x204) + unpack(0x65, 2, [(-32768, 32767)] * 3)
    data += unpack(0x6D, 20, [(0x8001, 65535, 0, 1)], True)
    memory = load_vif(data)
    for address in (2, 3, 6):
        assert memory.read(address, 2, signed=True) == (-32768, 32767)
    assert memory.read(20) == (32769, 65535, 0, 1)
    with pytest.raises(CharacterVifError, match="CM_VU_UNINITIALIZED"):
        memory.read(2)
    with pytest.raises(CharacterVifError, match="CM_VU_UNINITIALIZED"):
        memory.read(4, 1)
    assert memory.unpacks[0].cycle_length == 4


def test_zero_num_means_256_and_memory_does_not_leak_between_packets():
    memory = load_vif(unpack(0x6C, 768, [(1, 2, 3, 4)] * 256))
    assert memory.read(1023) == (1, 2, 3, 4)
    empty = load_vif(bytes(4))
    with pytest.raises(CharacterVifError, match="CM_VU_UNINITIALIZED"):
        empty.read(1023)


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", "CM_VIF_SIZE"),
        (bytes(65540), "CM_VIF_SIZE"),
        (b"abc", "CM_VIF_SIZE"),
        (bytearray(4), "CM_VIF_SIZE"),
        (command(0, 1), "CM_VIF_NOP"),
        (command(0, count=1), "CM_VIF_NOP"),
        (command(1, 0), "CM_VIF_CYCLE"),
        (command(1, 0x201), "CM_VIF_CYCLE"),
        (command(1, 0x101, 1), "CM_VIF_CYCLE"),
        (command(0x7C), "CM_VIF_UNSUPPORTED"),
        (command(0xEC), "CM_VIF_UNSUPPORTED"),
        (command(0x6C, 0x8000, 1), "CM_VIF_UNSUPPORTED"),
        (command(0x6C, 0x400, 1), "CM_VIF_UNSUPPORTED"),
        (command(0x30), "CM_VIF_UNSUPPORTED"),
        (command(0x6C, 0, 1), "CM_VIF_TRUNCATED"),
        (command(1, 0x104) + unpack(0x65, 1023, [(0, 0)] * 2), "CM_VIF_RANGE"),
        (unpack(0x69, 0, [(1, 2, 3)])[:-1] + b"x", "CM_VIF_PADDING"),
    ],
)
def test_vif_rejects_unsupported_or_malformed(data, code):
    with pytest.raises(CharacterVifError, match=code):
        load_vif(data)


@pytest.mark.parametrize(("address", "count"), [(-1, 4), (1024, 4), (0, 0), (0, 5)])
def test_vu_read_bounds(address, count):
    with pytest.raises(CharacterVifError, match="CM_VU_ADDRESS"):
        load_vif(bytes(4)).read(address, count)


@pytest.fixture
def mesh_iso(tmp_path):
    mdl = model()
    # Pair acquisition validates ANM identity; this decoder does not parse ANM.
    anm = b"own second resource"
    metadata = sector(("../mdl", "../anm"), ranges=[(0, len(mdl)), (1536, len(anm))])
    payload = bytearray(2048)
    payload[: len(mdl)] = mdl
    payload[1536 : 1536 + len(anm)] = anm
    archive = bytes(metadata + payload)
    disc = pycdlib.PyCdlib()
    disc.new(interchange_level=3, vol_ident="OWNMESH")
    disc.add_fp(BytesIO(archive), len(archive), iso_path="/OWN.MFA;1")
    path = tmp_path / "own.iso"
    disc.write(str(path))
    disc.close()
    selection = {
        "schema_version": 1,
        "image_size": path.stat().st_size,
        "image_sha256": digest(path.read_bytes()),
        "container": {
            "path": "OWN.MFA",
            "size": len(archive),
            "sha256": digest(archive),
            "layout": "d8",
        },
        "model": {"ordinal": 1, "size": len(mdl), "sha256": digest(mdl)},
        "animation": {"ordinal": 2, "size": len(anm), "sha256": digest(anm)},
    }
    selected = tmp_path / "selection.json"
    selected.write_text(json.dumps(selection))
    private = tmp_path / "private"
    private.mkdir()
    return path, selection, selected, private


def arguments(fixture):
    iso, _, selected, private = fixture
    return [
        "--iso",
        str(iso),
        "--selection",
        str(selected),
        "--selection-sha256",
        digest(selected.read_bytes()),
        "--private-root",
        str(private),
        "--run-id",
        "mesh-a",
    ]


def test_iso_identity_private_output_determinism_and_no_overwrite(mesh_iso):
    iso, selection, _, private = mesh_iso
    with IsoImage(iso) as reader:
        files, report = coordinator.decode_selected_mesh(reader, selection)
    assert report["summary"]["vertices"] == 6 and report["summary"]["triangles"] == 2
    assert report["summary"]["weight_sums_q12"] == {4094: 3, 4096: 3}
    assert report["capabilities"] == [] and "runtime_skinning_and_helpers" in report["pending"]
    args = arguments(mesh_iso)
    assert coordinator.main(args) == 0
    assert (private / "mesh-a/mesh.json").read_bytes() == files["mesh.json"]
    args[-1] = "mesh-b"
    assert coordinator.main(args) == 0
    assert (private / "mesh-a/manifest.json").read_bytes() == (
        private / "mesh-b/manifest.json"
    ).read_bytes()
    assert coordinator.main(args) == 1


@pytest.mark.parametrize("target", ["image", "container", "model", "animation"])
def test_identity_rejections_do_not_decode(mesh_iso, target):
    selection = copy.deepcopy(mesh_iso[1])
    if target == "image":
        selection["image_sha256"] = "0" * 64
    else:
        selection[target]["sha256"] = "0" * 64
    with IsoImage(mesh_iso[0]) as reader, pytest.raises(ProfileError):
        coordinator.decode_selected_mesh(reader, selection)


def test_decoder_failure_and_iso_close_change_never_publish(mesh_iso, monkeypatch):
    def fail(data):
        raise CharacterMeshError("CM_OWN_FAILURE")

    with monkeypatch.context() as patch:
        patch.setattr(coordinator, "decode_mesh", fail)
        assert coordinator.main(arguments(mesh_iso)) == 1
    assert not (mesh_iso[3] / "mesh-a").exists()
    decode = coordinator.decode_selected_mesh

    def change(reader, selection):
        result = decode(reader, selection)
        with mesh_iso[0].open("ab") as stream:
            stream.write(b"own mutation")
        return result

    monkeypatch.setattr(coordinator, "decode_selected_mesh", change)
    assert coordinator.main(arguments(mesh_iso)) == 1
    assert not (mesh_iso[3] / "mesh-a").exists()
