"""Own MDL/texture fixture with distinct images and explicit palette-zero bindings."""

import copy
import hashlib
import json
import struct
from io import BytesIO

import pycdlib
import pytest
from test_character_mesh import model, mutate, packet
from test_mfa import sector
from test_texture_probe import own_block, own_file

from tools.pipeline import decode_character_materials as coordinator
from tools.pipeline.decoders import ps2_character_materials as decoder
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.private_texture_output import write_character_material_bundle
from tools.pipeline.profile import ProfileError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def textured_model():
    raw = bytearray(model(packets=[packet(), packet(512)]))
    image_table = len(raw)
    raw.extend(struct.pack("<2I", 0, 1))
    descriptors = len(raw)
    raw.extend(struct.pack("<4i", 0, 0, 1, 0))
    struct.pack_into("<4I", raw, 32 + 12 * 4, 2, image_table - 32, 2, descriptors - 32)
    second = 32 + struct.unpack_from("<I", raw, 32 + 11 * 4)[0]
    struct.pack_into("<h", raw, second + 154, 1)
    raw.extend(bytes(-len(raw) % 16))
    area = len(raw)
    struct.pack_into("<3I", raw, 8, 2, area, area)
    blocks = []
    for i, (w, h) in enumerate(((128, 64), (256, 128))):
        block = bytearray(own_block(width=w, height=h, pad=32 + i * 16))
        block[26] = 1
        start = 80 + i * 16
        block[start : start + w * h] = bytes((7 + 4 * i + j * 17) % 256 for j in range(w * h))
        clut = start + w * h + 48
        for slot in range(1024):
            block[clut + slot * 4 : clut + slot * 4 + 4] = bytes(
                (slot % 256, (slot // 64) * 13, 23 + i * 10, (slot % 5) * 32)
            )
        blocks.append(bytes(block))
    raw.extend(own_file(*blocks))
    return bytes(raw), area, image_table, descriptors


def test_two_images_all_stored_palettes_opaque_headers_and_bindings():
    raw, area, _, _ = textured_model()
    result = decoder.decode_character_materials(raw)
    assert result.sector_offset == area and result.image_table == (0, 1)
    assert result.mesh.texture_descriptors == ((0, 0), (1, 0))
    assert [p.texture_index for p in result.mesh.submeshes] == [0, 1]
    assert [p.blend_partition for p in result.mesh.submeshes] == [False, True]
    assert [(i.width, i.height) for i in result.images] == [(128, 64), (256, 128)]
    assert result.images[0].indices[0] == 7 and result.images[1].indices[0] == 11
    assert result.images[0].palettes[3][28:32] == bytes((55, 0, 23, 0))
    assert result.images[1].palettes[1][44:48] == bytes((83, 13, 33, 96))
    assert bytes.fromhex(result.headers[0]["image_header_hex"]) == raw[area + 32 : area + 112]


@pytest.mark.parametrize(
    "kind,value,code",
    [
        ("file_count", 0, "CT_IMAGE_COUNT"),
        ("file_count", 17, "CT_IMAGE_COUNT"),
        ("file_count", 1, "CT_IMAGE_COUNT"),
        ("sector", 33, "CT_SECTOR_RANGE"),
        ("sector", 0x1000000, "CT_SECTOR_RANGE"),
        ("table", 1, "CT_IMAGE_TABLE_RANGE"),
        ("table", 0x1000000, "CT_IMAGE_TABLE_RANGE"),
        ("table_value", 2, "CT_IMAGE_TABLE_VARIANT"),
        ("palette", 4, "CT_PALETTE_REFERENCE"),
        ("palette", 1, "CT_PALETTE_VARIANT"),
        ("shift", 2, "CT_TRANSFER_VARIANT"),
        ("padding", 0, "CT_TRANSFER_VARIANT"),
        ("area_count", 1, "TEX_TRAILING"),
    ],
)
def test_invalid_headers_and_references(kind, value, code):
    raw, area, table, descriptors = textured_model()
    positions = {
        "file_count": (8, "I"),
        "sector": (12, "I"),
        "table": (32 + 13 * 4, "I"),
        "table_value": (table, "I"),
        "palette": (descriptors + 4, "i"),
        "shift": (area + 32 + 26, "B"),
        "padding": (area + 32 + 13, "B"),
        "area_count": (area + 20, "I"),
    }
    at, fmt = positions[kind]
    with pytest.raises(ValueError, match=code):
        decoder.decode_character_materials(mutate(raw, at, "<" + fmt, value))


def test_image_table_overlap_is_rejected_even_with_valid_values():
    raw, _, _, _ = textured_model()
    # File model already stores (0,1,2) as bone palette; a fake image table
    # containing (0,1) cannot alias the actual descriptor table.
    data = bytearray(raw)
    descriptors = 32 + struct.unpack_from("<I", raw, 32 + 15 * 4)[0]
    struct.pack_into("<4i", data, descriptors, 0, 1, 1, 1)
    struct.pack_into("<I", data, 32 + 13 * 4, descriptors - 32)
    with pytest.raises(decoder.CharacterMaterialError, match="CT_SECTION_OVERLAP"):
        decoder.decode_character_materials(bytes(data))


@pytest.mark.parametrize("delta", [-1, -48, -4096, 1])
def test_exact_sector_length(delta):
    raw, *_ = textured_model()
    changed = raw[:delta] if delta < 0 else raw + b"X"
    with pytest.raises(ValueError):
        decoder.decode_character_materials(changed)


def test_budget_precedes_pixel_decode(monkeypatch):
    raw, *_ = textured_model()
    monkeypatch.setattr(decoder, "MAX_PIXELS", 1)
    monkeypatch.setattr(decoder, "decode_indexed8", lambda *_: pytest.fail("Pixels before budget"))
    with pytest.raises(decoder.CharacterMaterialError, match="CT_PIXEL_BUDGET"):
        decoder.decode_character_materials(raw)


def test_sector_count_disagrees_with_both_model_counts():
    raw, area, *_ = textured_model()
    block = bytearray(own_block(width=128, height=64))
    block[26] = 1
    with pytest.raises(decoder.CharacterMaterialError, match="CT_IMAGE_COUNT"):
        decoder.decode_character_materials(raw[:area] + own_file(bytes(block)))


@pytest.mark.parametrize("bpp,count", [(4, 4), (8, 8)])
def test_other_index_or_clut_variants_are_explicitly_rejected(bpp, count):
    raw, area, *_ = textured_model()
    block = bytearray(own_block(bpp=bpp, count=count, width=128, height=64))
    block[26] = 1
    with pytest.raises(decoder.CharacterMaterialError, match="CT_TRANSFER_VARIANT"):
        decoder.decode_character_materials(raw[:area] + own_file(bytes(block), bytes(block)))


@pytest.fixture
def material_iso(tmp_path):
    mdl, *_ = textured_model()
    anm = b"own animation identity"
    second = (len(mdl) + 2047) // 2048 * 2048
    payload = bytearray(second + 2048)
    payload[: len(mdl)] = mdl
    payload[second : second + len(anm)] = anm
    archive = (
        sector(("mdl", "anm"), data_size=len(payload), ranges=[(0, len(mdl)), (second, len(anm))])
        + payload
    )
    disc = pycdlib.PyCdlib()
    disc.new(interchange_level=3, vol_ident="OWNMATERIAL")
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


def arguments(fixture, run="materials-a"):
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
        run,
    ]


def test_private_output_determinism_palette_and_no_overwrite(material_iso):
    iso, selection, _, private = material_iso
    with IsoImage(iso) as reader:
        files, report = coordinator.decode_selected_materials(reader, selection)
    assert report["summary"]["referenced_palettes"] == [0]
    assert files["texture-0.rgba"][:4] == bytes((7, 0, 23, 64))
    assert files["texture-1.rgba"][:4] == bytes((67, 13, 33, 64))
    document = json.loads(files["materials.json"])
    assert document["bindings"][1]["image"] == 1 and document["bindings"][1]["palette"] == 0
    assert document["bindings"][1]["material_type_candidate"] == 2
    assert document["bindings"][1]["display_group_candidate"] == 5
    assert report["capabilities"] == [] and report["pending"][0] == "runtime_gs_material"
    assert coordinator.main(arguments(material_iso)) == 0
    assert coordinator.main(arguments(material_iso, "materials-b")) == 0
    a, b = private / "materials-a", private / "materials-b"
    assert (a / "manifest.json").read_bytes() == (b / "manifest.json").read_bytes()
    for name, data in files.items():
        assert (a / name).read_bytes() == (b / name).read_bytes() == data
    assert coordinator.main(arguments(material_iso)) == 1


@pytest.mark.parametrize("target", ["image", "container", "model", "animation"])
def test_identity_failure(material_iso, target):
    selection = copy.deepcopy(material_iso[1])
    if target == "image":
        selection["image_sha256"] = "0" * 64
    else:
        selection[target]["sha256"] = "0" * 64
    with IsoImage(material_iso[0]) as reader, pytest.raises(ProfileError):
        coordinator.decode_selected_materials(reader, selection)


@pytest.mark.parametrize("error", [decoder.CharacterMaterialError("CT_OWN"), OSError("own")])
def test_decoder_or_io_error_never_publishes(material_iso, monkeypatch, error):
    def fail(*_):
        raise error

    monkeypatch.setattr(coordinator, "decode_character_materials", fail)
    assert coordinator.main(arguments(material_iso)) == 1
    assert not (material_iso[3] / "materials-a").exists()


def test_disc_changed_on_close_never_publishes(material_iso, monkeypatch):
    original = coordinator.decode_selected_materials

    def change(reader, selection):
        result = original(reader, selection)
        with material_iso[0].open("ab") as stream:
            stream.write(b"own mutation")
        return result

    monkeypatch.setattr(coordinator, "decode_selected_materials", change)
    assert coordinator.main(arguments(material_iso)) == 1
    assert not (material_iso[3] / "materials-a").exists()


@pytest.mark.parametrize(
    "images,textures", [(0, 1), (17, 1), (1, 0), (1, 257), (True, 1), (1, True)]
)
def test_output_count_limits(tmp_path, images, textures):
    with pytest.raises(ProfileError, match="Invalid image/texture counts"):
        write_character_material_bundle(
            tmp_path / "private",
            tmp_path / "repo",
            "x",
            {},
            {"summary": {"images": images, "textures": textures}},
        )


def test_extra_output_cannot_escape_private_bundle(tmp_path):
    with pytest.raises(ProfileError, match="Invalid texture output set"):
        write_character_material_bundle(
            tmp_path / "private",
            tmp_path / "repo",
            "x",
            {"../bad": b"own"},
            {"summary": {"images": 1, "textures": 1}},
        )
