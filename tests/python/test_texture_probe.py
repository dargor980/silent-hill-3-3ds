"""TEX01–TEX07: own generated headers/pixels; no original assets or Noesis."""

import hashlib
import json
import struct
import subprocess
import sys

import pytest

from tools.inspectors import texture_survey as survey
from tools.inspectors.asset_catalog import asset_id
from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.inspectors.texture_probe import MAX_TEXTURE_BYTES, TextureProbeError, probe_texture
from tools.pipeline.extract_assets import resource_plan
from tools.pipeline.profile import ProfileError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def own_block(bpp=8, width=16, height=16, count=4, pad=32, declared_pad=None):
    size = width * height * bpp // 8
    header = bytearray(48)
    struct.pack_into("<iHHHH", header, 0, 17, 3, 5, width, height)
    header[12] = bpp
    header[13] = pad if declared_pad is None else declared_pad
    struct.pack_into("<HII", header, 14, 23, size, 48 + pad + size)
    header[25] = 0x13 if bpp == 8 else 0x14
    header[26:30] = bytes((7, 9, width.bit_length() - 1, height.bit_length() - 1))
    struct.pack_into("<H", header, 30, 0x9999)
    header[32:] = bytes(range(16))
    clut = bytearray(48)
    struct.pack_into("<III", clut, 0, count * 1024, 11, 13)
    clut[12:16] = bytes((count, 19, 64, 64))
    clut[16:] = bytes(range(32))
    return bytes(header) + bytes(pad) + b"J" * size + bytes(clut) + b"K" * (count * 1024)


def own_file(*blocks, last_start=False):
    blocks = blocks or (own_block(),)
    last = 32 + sum(len(b) for b in (blocks[:-1] if last_start else blocks))
    return struct.pack("<8I", 0xFFFFFFFF, 101, 32, last, 103, len(blocks), 107, 109) + b"".join(
        blocks
    )


def probe(data):
    return probe_texture(len(data), lambda offset, length: data[offset : offset + length])


@pytest.mark.parametrize("bpp", [4, 8])
@pytest.mark.parametrize("count", [4, 8, 16])
@pytest.mark.parametrize("last_start", [False, True])
def test_valid_indexed_blocks_and_exact_ranges(bpp, count, last_start):
    data = own_file(own_block(bpp, count=count), last_start=last_start)
    result = probe(data)
    assert result["status"] == "structural_candidate" and result["consumed_bytes"] == len(data)
    block = result["blocks"][0]
    assert block["texture_id"] == 17
    assert (block["width"], block["height"], block["bpp"]) == (16, 16, bpp)
    assert block["indices"] == {"offset": 112, "size": 256 * bpp // 8}
    assert block["padding_declared"] == block["padding_computed"] == 32
    assert block["clut"]["data_offset"] == 112 + 256 * bpp // 8 + 48
    assert block["clut"]["declared_count"] == count
    assert block["end_offset"] == len(data)


def test_opaque_fields_preserved_without_claiming_giftag_or_material():
    result = probe(own_file())
    assert result["area"]["opaque_words"] == {"4": 101, "16": 103, "24": 107, "28": 109}
    block = result["blocks"][0]
    assert block["opaque"] == {"x": 3, "y": 5, "importance": 23, "bit_shift": 7, "tag_point": 9}
    assert block["header_sha256"] == digest(own_block()[:48])
    assert block["clut"]["opaque_gs_offset"] == 11
    assert block["clut"]["opaque_raw_offset"] == 13
    assert block["clut"]["opaque_trans_cluts"] == 19
    assert block["clut"]["header_sha256"] == digest(own_block()[336:384])


def test_mixed_blocks_use_computed_padding_and_never_read_payloads():
    data = own_file(own_block(declared_pad=48), own_block(4, count=8), last_start=True)
    calls = []

    def headers_only(offset, length):
        calls.append((offset, length))
        assert (offset, length) in {(0, 32), (32, 48), (368, 48), (4512, 48), (4720, 48)}
        return data[offset : offset + length]

    result = probe_texture(len(data), headers_only)
    assert len(calls) == 5
    assert result["blocks"][0]["padding_computed"] == 32
    assert result["blocks"][0]["padding_declared"] == 48
    assert [b["bpp"] for b in result["blocks"]] == [8, 4]


@pytest.mark.parametrize("width,height", [(1, 2), (17, 18), (1024, 1024)])
def test_dimensions_include_non_power_of_two_and_upper_bound(width, height):
    result = probe(own_file(own_block(4, width, height)))
    assert result["blocks"][0]["indices"]["size"] == width * height // 2


def test_count_upper_bound_is_bounded_and_accepted():
    result = probe(own_file(*([own_block()] * 256)))
    assert len(result["blocks"]) == 256


@pytest.mark.parametrize(
    "size,code",
    [
        (True, "TEX_SIZE"),
        (-1, "TEX_SIZE"),
        (None, "TEX_SIZE"),
        (MAX_TEXTURE_BYTES + 1, "TEX_BUDGET"),
    ],
)
def test_invalid_size_rejected_before_port_call(size, code):
    with pytest.raises(TextureProbeError, match=code):
        probe_texture(size, lambda *_: pytest.fail("Unexpected read"))


@pytest.mark.parametrize("value", [b"", b"x" * 31, b"x" * 33, "x" * 32, bytearray(32), None])
def test_invalid_port_response_is_not_structural_acceptance(value):
    with pytest.raises(TextureProbeError, match="TEX_READ_CONTRACT"):
        probe_texture(32, lambda *_: value)


@pytest.mark.parametrize(
    "offset,fmt,value,code",
    [
        (0, "I", 0, "TEX_AREA_VARIANT"),
        (8, "I", 48, "TEX_AREA_VARIANT"),
        (20, "I", 0, "TEX_COUNT"),
        (20, "I", 257, "TEX_COUNT"),
        (12, "I", 1, "TEX_LAST_OFFSET"),
        (40, "H", 0, "TEX_DIMENSION"),
        (42, "H", 1025, "TEX_DIMENSION"),
        (60, "B", 255, "TEX_EXPONENT"),
        (61, "B", 3, "TEX_EXPONENT"),
        (62, "H", 0, "TEX_MARKER"),
        (44, "B", 24, "TEX_BPP"),
        (56, "B", 1, "TEX_PSM"),
        (57, "B", 0x14, "TEX_PSM"),
        (48, "I", 255, "TEX_DATA_SIZE"),
        (52, "I", 303, "TEX_BLOCK_SIZE"),
        (52, "I", 0xFFFFFFFF, "TEX_BLOCK_SIZE"),
        (368, "I", 4095, "TEX_CLUT_VARIANT"),
        (380, "B", 0, "TEX_CLUT_VARIANT"),
        (380, "B", 255, "TEX_CLUT_VARIANT"),
        (382, "B", 32, "TEX_CLUT_VARIANT"),
        (383, "B", 32, "TEX_CLUT_VARIANT"),
    ],
)
def test_malformed_headers_are_typed(offset, fmt, value, code):
    data = bytearray(own_file())
    struct.pack_into("<" + fmt, data, offset, value)
    with pytest.raises(TextureProbeError, match=code):
        probe(bytes(data))


@pytest.mark.parametrize("end", [0, 31, 32, 79, 367, 368, 415, 4511])
def test_truncation_rejected_without_partial_result(end):
    with pytest.raises(TextureProbeError):
        probe(own_file()[:end])


def test_trailing_bytes_and_truncated_second_block_rejected():
    with pytest.raises(TextureProbeError, match="TEX_TRAILING"):
        probe(own_file() + b"x")
    with pytest.raises(TextureProbeError, match="TEX_RANGE"):
        probe(own_file(own_block(), own_block())[:-1])


def test_odd_four_bit_pixel_count_rejected():
    with pytest.raises(TextureProbeError, match="TEX_DATA_SIZE"):
        probe(own_file(own_block(4, 1, 1)))


@pytest.fixture
def evidence(tmp_path):
    payloads = [
        own_file(own_block(declared_pad=48)),
        own_file(own_block(4)),
        b"own bad",
        b"own bin",
    ]
    source_hash = digest(b"own source")
    source = {
        "id": "iso:" + source_hash,
        "sha256": source_hash,
        "size": 65536,
        "profile": {"id": "own-profile", "platform": "ps2"},
    }
    parent = {
        "id": "entry:" + "2" * 64,
        "path": "OWN.MFA",
        "size": 65536,
        "result": {"status": "structural_candidate"},
    }
    entries = [
        {
            "id": asset_id(parent["id"], 0, i),
            "container_id": parent["id"],
            "origin": {"image_id": source["id"], "profile_id": "own-profile"},
            "block_offset": 0,
            "entry_index": i,
            "container_offset": 128 + i * 8192,
            "size": len(data),
            "sha256": digest(data),
            "source_name": f"own/sample-{i}." + ("TEX" if i < 3 else "bin"),
        }
        for i, data in enumerate(payloads)
    ]
    catalog = {
        "schema_version": 1,
        "scope": "selected_mfa_entries",
        "tool": {"name": "sh3-asset-catalog", "version": 1},
        "source": source,
        "selection": {"canonical_sha256": "a" * 64},
        "containers": [parent],
        "entries": entries,
        "outside_scope": [],
        "summary": {"entry_count": len(entries), "payload_bytes": sum(map(len, payloads))},
        "capabilities": [],
        "payload_decoding": "not_performed",
    }
    resources = resource_plan(catalog)
    catalog_bytes = json.dumps(catalog).encode()
    files = [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in resources]
    receipt = {
        "schema_version": 1,
        "tool": {"name": "sh3-mfa-extract", "version": 1},
        "status": "verified",
        "catalog_sha256": digest(catalog_bytes),
        "source": source,
        "selection": catalog["selection"],
        "summary": catalog["summary"],
        "resources": resources,
        "copies": {"copy-a": files, "copy-b": files},
        "exclusions": {"containers": [], "outside_scope_ids": []},
        "capabilities": [],
        "payload_decoding": "not_performed",
    }
    root = tmp_path.resolve()
    for copy in ("copy-a", "copy-b"):
        (root / copy).mkdir()
        for r in resources:
            index = next(i for i, e in enumerate(entries) if e["id"] == r["id"])
            (root / copy / r["file"]).write_bytes(payloads[index])
    (root / "catalog.json").write_bytes(catalog_bytes)
    receipt_bytes = json.dumps(receipt).encode()
    (root / "receipt.json").write_bytes(receipt_bytes)
    return {
        "root": root,
        "catalog": catalog,
        "receipt": receipt,
        "catalog_hash": digest(catalog_bytes),
        "receipt_hash": digest(receipt_bytes),
    }


def documents(evidence):
    return {k: evidence[k] for k in ("catalog", "receipt", "catalog_hash", "receipt_hash")}


def run(evidence, copy="copy-a"):
    with VerifiedPrivateReader(evidence["root"] / copy, evidence["root"] / "checkout") as reader:
        return survey.survey_textures(reader, **documents(evidence))


def test_two_copies_repeat_without_promoting_support_or_leaking_payload(evidence):
    result = run(evidence)
    assert result == run(evidence, "copy-b")
    evidence["catalog"]["entries"].reverse()
    assert result == run(evidence)
    assert result["summary"] == {
        "selected_count": 3,
        "structural_candidate_count": 2,
        "unknown_count": 1,
        "unknown_codes": {"TEX_RANGE": 1},
        "block_count": 2,
        "blocks_by_bpp": {"4": 1, "8": 1},
        "padding_disagreement_count": 1,
    }
    assert result["capabilities"] == [] and result["payload_decoding"] == "not_performed"
    assert all(e["classification"] == {"type": "unknown"} for e in result["entries"])
    assert "sample-" not in json.dumps(result) and "JJJJ" not in json.dumps(result)
    assert str(evidence["root"]) not in json.dumps(result)


def test_mixed_receipt_fails_before_reads(evidence):
    evidence["receipt"]["catalog_sha256"] = "0" * 64
    with pytest.raises(ProfileError, match="Candidate evidence"):
        survey.survey_textures(None, **documents(evidence))


def test_empty_selection_fails_before_reads(evidence):
    for entry in evidence["catalog"]["entries"]:
        entry["source_name"] += ".bin"
    with pytest.raises(ProfileError) as error:
        survey.survey_textures(None, **documents(evidence))
    assert error.value.code == "TEX_EMPTY_SELECTION"


@pytest.mark.parametrize("fault", ["short", "hash", "final_set"])
def test_reader_error_aborts_survey(evidence, fault):
    class Reader:
        checks = 0

        def verify_set(self, resources):
            self.checks += 1
            if fault == "final_set" and self.checks == 2:
                raise ProfileError("PRIVATE_SET_MISMATCH", "changed")

        def read_verified(self, resource, offset, length):
            if fault == "short":
                return b""
            if fault == "hash":
                raise ProfileError("PRIVATE_HASH_MISMATCH", "changed")
            return b"x" * length

    with pytest.raises(ProfileError):
        survey.survey_textures(Reader(), **documents(evidence))


def cli_args(evidence, output):
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
        str(root / "copy-a"),
        "--output",
        str(output),
    ]


def test_cli_publishes_once_and_matches_pure_result(evidence, capsys):
    output = evidence["root"] / "report.json"
    assert survey.main(cli_args(evidence, output)) == 0
    first = output.read_bytes()
    assert json.loads(first) == run(evidence)
    assert survey.main(cli_args(evidence, output)) == 1
    assert output.read_bytes() == first
    assert "OUTPUT_EXISTS" in capsys.readouterr().out


def test_cli_corruption_not_downgraded_to_unknown(evidence, capsys):
    identity = evidence["catalog"]["entries"][0]["id"]
    file = next(r["file"] for r in evidence["receipt"]["resources"] if r["id"] == identity)
    path = evidence["root"] / "copy-a" / file
    data = path.read_bytes()
    path.write_bytes(bytes([data[0] ^ 1]) + data[1:])
    output = evidence["root"] / "rejected.json"
    assert survey.main(cli_args(evidence, output)) == 1
    assert not output.exists()
    assert "PRIVATE_HASH_MISMATCH" in capsys.readouterr().out


def test_cli_publish_failure_and_close_order(evidence, monkeypatch, capsys):
    events = []
    original = survey.VerifiedPrivateReader

    class Reader(original):
        def __exit__(self, *args):
            result = super().__exit__(*args)
            events.append("closed")
            return result

    def failed_publish(*args):
        assert events == ["closed"]
        raise OSError("own disk error")

    monkeypatch.setattr(survey, "VerifiedPrivateReader", Reader)
    monkeypatch.setattr(survey, "publish_report", failed_publish)
    output = evidence["root"] / "failed.json"
    assert survey.main(cli_args(evidence, output)) == 1
    assert not output.exists()
    assert "TEX_IO_ERROR" in capsys.readouterr().out


def test_module_entrypoint_uses_real_cli(evidence):
    output = evidence["root"] / "module.json"
    result = subprocess.run(
        [sys.executable, "-m", "tools.inspectors.texture_survey", *cli_args(evidence, output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "surveyed"
    assert json.loads(output.read_text()) == run(evidence)
