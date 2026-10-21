"""PX01–PX07, synthetic asymmetric images and independent GS-map fingerprints."""

import hashlib
import json
import os
import struct
import zlib
from dataclasses import replace

import pytest

from tools.inspectors.asset_catalog import asset_id
from tools.pipeline import decode_texture as pipeline
from tools.pipeline import private_texture_output as output
from tools.pipeline.decoders.ps2_indexed8 import (
    TextureDecodeError,
    decode_indexed8,
    render_palette,
    upload_offset,
)
from tools.pipeline.extract_assets import resource_plan
from tools.pipeline.preview_png import encode_rgba_png
from tools.pipeline.profile import ProfileError
from tools.qa.texture_address_oracle import compare_tables


@pytest.mark.parametrize(
    "width,height,expected",
    [
        (128, 64, "49128ece148d5dc998c2960d982edcae11c7e9c91d8d6390d9f593294c78a159"),
        (256, 128, "167f8f7d0409ef9e668882cf8e5e2ab706aa3b170ca7760e90b622988022dc93"),
        (256, 256, "b4408a996c085fd00e3f18176519c1d2bc3b977adadf2559d232a001e6ca3aa4"),
        (512, 512, "d535d054eac52bb4c3e0df4f8f409b1a7c64f37aca1efffa31314997cd5ee6e9"),
    ],
)
def test_complete_map_matches_independent_gs_oracle(width, height, expected):
    # Generated with PSMCT32 write + PSMT8 read of the pinned PCSX2 tables.
    addresses = [upload_offset(x, y, width) for y in range(height) for x in range(width)]
    assert sorted(addresses) == list(range(width * height))
    encoded = struct.pack("<" + "I" * len(addresses), *addresses)
    assert hashlib.sha256(encoded).hexdigest() == expected


def test_reference_must_match_pinned_tables():
    with pytest.raises(ValueError, match="ORACLE_REFERENCE_HASH"):
        compare_tables(b"own unrelated reference")


def own_texture():
    # Input bytes encode the uploaded x/y and lane asymmetrically.
    data = bytes((i * 29 + (i // 128) * 17) % 256 for i in range(128 * 64))
    clut = b"".join(
        bytes((row * 16 + col, palette, 255 - col, (row * 16 + col)))
        for row in range(16)
        for palette in range(4)
        for col in range(16)
    )
    return decode_indexed8(128, 64, data, clut)


def test_palette_columns_and_bit_permutation_have_independent_expected_values():
    texture = own_texture()
    # Rows 0/1 are exchanged in each group through the PS2 8-entry swap.
    for palette, colors in enumerate(texture.palettes):
        for index, source in (
            (0, 0),
            (7, 7),
            (8, 16),
            (15, 23),
            (16, 8),
            (23, 15),
            (24, 24),
            (255, 255),
        ):
            assert colors[index * 4 : index * 4 + 4] == bytes(
                (source, palette, 255 - source % 16, source)
            )
    assert len(texture.indices) == 8192
    # Explicit raster landmarks, obtained from the separate GS oracle.
    raw = bytes((i * 29 + (i // 128) * 17) % 256 for i in range(8192))
    for x, y, offset in ((0, 0, 0), (1, 0, 4), (8, 0, 2), (0, 1, 256), (0, 2, 17), (127, 63, 8191)):
        assert texture.indices[y * 128 + x] == raw[offset]


def test_original_alpha_preserved_and_preview_saturates_only_alpha():
    texture = own_texture()
    # Force every index to occur repeatedly, so all 256 alpha values are tested.
    texture = replace(texture, indices=bytes(range(256)) * 32)
    original = render_palette(texture, 2, normalize_alpha=False)
    preview = render_palette(texture, 2, normalize_alpha=True)
    for i in range(8192):
        assert original[i * 4 : i * 4 + 3] == preview[i * 4 : i * 4 + 3]
        assert preview[i * 4 + 3] == min(255, original[i * 4 + 3] * 2)
    assert set(original[3::4]) == set(range(256))
    assert original != preview


@pytest.mark.parametrize("fill", [0, 204])
def test_uniform_palettes_are_retained(fill):
    texture = decode_indexed8(128, 64, bytes(8192), bytes([fill]) * 4096)
    assert texture.palettes == (bytes([fill]) * 1024,) * 4


@pytest.mark.parametrize(
    "width,height",
    [(True, 64), (128, False), (0, 64), (127, 64), (2048, 64), (128, 63), (128, 2048)],
)
def test_dimensions_rejected_before_buffers(width, height):
    with pytest.raises(TextureDecodeError, match="PX_DIMENSIONS"):
        decode_indexed8(width, height, b"", b"")


@pytest.mark.parametrize(
    "data,clut,code",
    [
        (b"", bytes(4096), "PX_INDEX_SIZE"),
        (bytes(8193), bytes(4096), "PX_INDEX_SIZE"),
        (bytearray(8192), bytes(4096), "PX_INDEX_SIZE"),
        (bytes(8192), b"", "PX_CLUT_SIZE"),
        (bytes(8192), bytes(4097), "PX_CLUT_SIZE"),
        (bytes(8192), None, "PX_CLUT_SIZE"),
    ],
)
def test_lengths_and_types(data, clut, code):
    with pytest.raises(TextureDecodeError, match=code):
        decode_indexed8(128, 64, data, clut)


@pytest.mark.parametrize("palette,normalize", [(-1, False), (4, False), (True, False), (0, 1)])
def test_render_options_are_explicit(palette, normalize):
    with pytest.raises(TextureDecodeError, match="PX_IMAGE_INPUT"):
        render_palette(own_texture(), palette, normalize_alpha=normalize)


@pytest.mark.parametrize("change", [{"indices": b""}, {"palettes": ()}, {"palettes": (b"",) * 4}])
def test_inconsistent_canonical_image_rejected(change):
    with pytest.raises(TextureDecodeError, match="PX_IMAGE_INPUT"):
        render_palette(replace(own_texture(), **change), 0, normalize_alpha=False)


def test_png_chunks_crc_dimensions_and_unfiltered_rgba():
    rgba = bytes(range(24))
    png = encode_rgba_png(3, 2, rgba)
    assert png == encode_rgba_png(3, 2, rgba)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, chunks = 8, {}
    while pos < len(png):
        size = struct.unpack_from(">I", png, pos)[0]
        kind, data = png[pos + 4 : pos + 8], png[pos + 8 : pos + 8 + size]
        crc = struct.unpack_from(">I", png, pos + 8 + size)[0]
        assert zlib.crc32(kind + data) == crc
        chunks[kind] = data
        pos += 12 + size
    assert list(chunks) == [b"IHDR", b"IDAT", b"IEND"]
    assert struct.unpack(">IIBBBBB", chunks[b"IHDR"]) == (3, 2, 8, 6, 0, 0, 0)
    assert zlib.decompress(chunks[b"IDAT"]) == b"\0" + rgba[:12] + b"\0" + rgba[12:]


@pytest.mark.parametrize(
    "w,h,data",
    [(0, 1, b""), (1, 1025, b""), (True, 1, bytes(4)), (1, 1, b""), (1, 1, bytearray(4))],
)
def test_png_invalid_input(w, h, data):
    with pytest.raises(ValueError, match="PNG_INPUT"):
        encode_rgba_png(w, h, data)


@pytest.fixture
def bundle():
    texture = own_texture()
    files = {"indices.bin": texture.indices}
    for i in range(4):
        files[f"palette-{i}.bin"] = texture.palettes[i]
        files[f"palette-{i}.rgba"] = render_palette(texture, i, normalize_alpha=False)
        files[f"palette-{i}.png"] = encode_rgba_png(
            128, 64, render_palette(texture, i, normalize_alpha=True)
        )
    return files


def test_private_output_repeats_exclusively_and_hashes_every_file(tmp_path, bundle):
    root = tmp_path.resolve() / "private"
    root.mkdir()
    repo = tmp_path.resolve() / "checkout"
    one = output.write_texture_bundle(root, repo, "own-a", bundle, {"recipe": "own"})
    two = output.write_texture_bundle(root, repo, "own-b", bundle, {"recipe": "own"})
    assert one == two
    for entry in one["files"]:
        data = (root / "own-a" / entry["file"]).read_bytes()
        assert data == bundle[entry["file"]]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert os.stat(root / "own-a" / entry["file"]).st_mode & 0o777 == 0o600
    assert json.loads((root / "own-a" / "manifest.json").read_text()) == one
    with pytest.raises(FileExistsError):
        output.write_texture_bundle(root, repo, "own-a", bundle, {})


@pytest.mark.parametrize("kind", ["repository", "parent", "name", "files", "empty"])
def test_invalid_destinations_and_output_sets(tmp_path, bundle, kind):
    root = tmp_path.resolve() / "private"
    root.mkdir()
    repo, run_id = tmp_path.resolve() / "repo", "own"
    if kind == "repository":
        root = repo / "child"
    if kind == "parent":
        repo = root.parent
    if kind == "name":
        run_id = "../own"
    if kind == "files":
        bundle["../escape"] = b"x"
    if kind == "empty":
        bundle["indices.bin"] = b""
    with pytest.raises(ProfileError):
        output.write_texture_bundle(root, repo, run_id, bundle, {})
    assert not (root / "own").exists()


def test_symlink_destination_rejected(tmp_path, bundle):
    root = tmp_path.resolve() / "private"
    root.mkdir()
    (root / "linked").symlink_to(root, target_is_directory=True)
    with pytest.raises(OSError):
        output.write_texture_bundle(root / "linked", tmp_path.resolve() / "repo", "own", bundle, {})
    assert not (root / "own").exists()


def test_failed_write_retains_partial_without_final_manifest(tmp_path, bundle, monkeypatch):
    def fail(*args):
        raise OSError("own disk full")

    monkeypatch.setattr(output, "write_all", fail)
    root = tmp_path.resolve() / "private"
    root.mkdir()
    with pytest.raises(OSError):
        output.write_texture_bundle(root, tmp_path.resolve() / "repo", "own", bundle, {})
    assert (root / "own").is_dir()
    assert not (root / "own" / "manifest.json").exists()


@pytest.fixture
def evidence(tmp_path):
    # One synthetic indexed block; independent from any original file.
    size = 128 * 64
    header = bytearray(48)
    struct.pack_into("<HH", header, 8, 128, 64)
    header[12:14] = bytes((8, 0))
    struct.pack_into("<II", header, 16, size, 48 + size)
    header[25] = 0x13
    header[28:32] = bytes((7, 6, 0x99, 0x99))
    clut = bytearray(48)
    struct.pack_into("<I", clut, 0, 4096)
    clut[12:16] = bytes((4, 0, 64, 64))
    payload = (
        struct.pack("<8I", 0xFFFFFFFF, 0, 32, 32, 0, 1, 0, 0)
        + bytes(header)
        + bytes(range(256)) * 32
        + bytes(clut)
        + bytes(range(256)) * 16
    )
    source_hash = hashlib.sha256(b"own fixture source").hexdigest()
    source = {
        "id": "iso:" + source_hash,
        "sha256": source_hash,
        "size": 65536,
        "profile": {"id": "own-profile", "platform": "ps2"},
    }
    parent = {
        "id": "entry:" + "1" * 64,
        "path": "OWN.MFA",
        "size": 65536,
        "result": {"status": "structural_candidate"},
    }
    entry = {
        "id": asset_id(parent["id"], 0, 0),
        "container_id": parent["id"],
        "origin": {"image_id": source["id"], "profile_id": "own-profile"},
        "block_offset": 0,
        "entry_index": 0,
        "container_offset": 0,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "source_name": "own.tex",
    }
    catalog = {
        "schema_version": 1,
        "scope": "selected_mfa_entries",
        "tool": {"name": "sh3-asset-catalog", "version": 1},
        "source": source,
        "selection": {},
        "containers": [parent],
        "entries": [entry],
        "outside_scope": [],
        "summary": {"entry_count": 1, "payload_bytes": len(payload)},
        "capabilities": [],
        "payload_decoding": "not_performed",
    }
    resources = resource_plan(catalog)
    cat_bytes = json.dumps(catalog).encode()
    cat_hash = hashlib.sha256(cat_bytes).hexdigest()
    files = [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in resources]
    receipt = {
        "schema_version": 1,
        "tool": {"name": "sh3-mfa-extract", "version": 1},
        "status": "verified",
        "catalog_sha256": cat_hash,
        "source": source,
        "selection": {},
        "summary": catalog["summary"],
        "resources": resources,
        "copies": {"copy-a": files, "copy-b": files},
        "exclusions": {"containers": [], "outside_scope_ids": []},
        "capabilities": [],
        "payload_decoding": "not_performed",
    }
    receipt_bytes = json.dumps(receipt).encode()
    root = tmp_path.resolve()
    (root / "copy").mkdir()
    (root / "out").mkdir()
    (root / "copy" / resources[0]["file"]).write_bytes(payload)
    (root / "catalog.json").write_bytes(cat_bytes)
    (root / "receipt.json").write_bytes(receipt_bytes)
    return {
        "root": root,
        "catalog": catalog,
        "receipt": receipt,
        "catalog_hash": cat_hash,
        "receipt_hash": hashlib.sha256(receipt_bytes).hexdigest(),
        "identity": entry["id"],
        "ordinal": 0,
        "payload": payload,
    }


def documents(evidence):
    return {
        k: evidence[k]
        for k in ("catalog", "receipt", "catalog_hash", "receipt_hash", "identity", "ordinal")
    }


def args(evidence):
    root = evidence["root"]
    return [
        "--catalog",
        str(root / "catalog.json"),
        "--receipt",
        str(root / "receipt.json"),
        "--catalog-sha256",
        evidence["catalog_hash"],
        "--receipt-sha256",
        evidence["receipt_hash"],
        "--private-copy",
        str(root / "copy"),
        "--private-root",
        str(root / "out"),
        "--resource-id",
        evidence["identity"],
        "--ordinal",
        "0",
        "--run-id",
        "own",
    ]


def test_real_cli_decodes_and_publishes_outside_repository(evidence):
    assert pipeline.main(args(evidence)) == 0
    report = json.loads((evidence["root"] / "out/own/manifest.json").read_text())
    assert report["resource"]["id"] == evidence["identity"]
    assert len(report["files"]) == 13
    assert report["visual_comparison"] == "pending"
    assert report["capabilities"] == []
    assert pipeline.main(args(evidence)) == 1


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("identity", "asset:" + "0" * 64, "PX_RESOURCE_MISSING"),
        ("ordinal", -1, "PX_ORDINAL"),
        ("ordinal", True, "PX_ORDINAL"),
        ("ordinal", 256, "PX_ORDINAL"),
    ],
)
def test_invalid_selection_before_io(evidence, field, value, code):
    evidence[field] = value
    with pytest.raises(TextureDecodeError, match=code):
        pipeline.decode_resource(None, **documents(evidence))


@pytest.mark.parametrize("fault", ["ordinal", "variant", "short", "final_set"])
def test_selection_and_port_failures_never_publish(evidence, fault):
    data = bytearray(evidence["payload"])
    if fault == "variant":
        # A structurally valid 8-unit CLUT unsupported by this decoder.
        struct.pack_into("<I", data, 8272, 8192)
        data[8284] = 8
        data.extend(bytes(4096))
        evidence["catalog"]["entries"][0]["size"] = len(data)

    class Reader:
        calls = 0

        def verify_set(self, resources):
            self.calls += 1
            if self.calls == 2 and fault == "final_set":
                raise ProfileError("PRIVATE_SET_MISMATCH", "own changed set")

        def read_verified(self, resource, offset, length):
            if fault == "short" and length == 4096:
                return b""
            return bytes(data[offset : offset + length])

    if fault == "ordinal":
        evidence["ordinal"] = 1
    if fault == "variant":
        # Update synthetic evidence coherently after changing the fixture.
        entry = evidence["catalog"]["entries"][0]
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        evidence["catalog"]["summary"]["payload_bytes"] = len(data)
        resources = resource_plan(evidence["catalog"])
        evidence["receipt"]["resources"] = resources
        files = [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in resources]
        evidence["receipt"]["copies"] = {"copy-a": files, "copy-b": files}
    with pytest.raises((TextureDecodeError, ProfileError)) as error:
        pipeline.decode_resource(Reader(), **documents(evidence))
    code = getattr(error.value, "code", str(error.value))
    assert (
        code
        == {
            "ordinal": "PX_ORDINAL",
            "variant": "PX_UNSUPPORTED_VARIANT",
            "short": "PX_READ_CONTRACT",
            "final_set": "PRIVATE_SET_MISMATCH",
        }[fault]
    )


def test_corrupt_private_input_prevents_output(evidence, capsys):
    resource = evidence["receipt"]["resources"][0]
    path = evidence["root"] / "copy" / resource["file"]
    path.write_bytes(b"x" * resource["size"])
    assert pipeline.main(args(evidence)) == 1
    assert "PRIVATE_HASH_MISMATCH" in capsys.readouterr().out
    assert not (evidence["root"] / "out/own").exists()


def test_cli_reports_unsupported_selection(evidence, capsys):
    evidence["identity"] = "asset:" + "0" * 64
    assert pipeline.main(args(evidence)) == 1
    assert "PX_RESOURCE_MISSING" in capsys.readouterr().out
    assert not (evidence["root"] / "out/own").exists()


@pytest.mark.parametrize("fault", ["hash", "extra", "replaced"])
def test_writer_detects_changed_outputs_without_manifest(tmp_path, bundle, monkeypatch, fault):
    root = tmp_path.resolve() / "private"
    root.mkdir()
    repo = tmp_path.resolve() / "repo"
    if fault == "hash":
        monkeypatch.setattr(output, "fingerprint_stream", lambda *_: {"sha256": "0" * 64})
    else:
        original = output.write_all
        calls = 0

        def changed(stream, data):
            nonlocal calls
            calls += 1
            original(stream, data)
            if calls == 1:
                if fault == "extra":
                    (root / "own" / "unexpected").write_bytes(b"own")
                else:
                    (root / "own").rename(root / "moved")
                    (root / "own").mkdir()

        monkeypatch.setattr(output, "write_all", changed)
    with pytest.raises(ProfileError) as error:
        output.write_texture_bundle(root, repo, "own", bundle, {})
    assert (
        error.value.code
        == {
            "hash": "OUTPUT_HASH_MISMATCH",
            "extra": "OUTPUT_SET_MISMATCH",
            "replaced": "OUTPUT_CHANGED",
        }[fault]
    )
    assert not (root / "own/manifest.json").exists()
