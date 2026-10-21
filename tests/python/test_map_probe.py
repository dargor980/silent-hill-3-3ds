"""MP01-MP07: own MAP hierarchy and texture; no game data or plugin execution."""

import hashlib
import json
import struct
import subprocess
import sys

import pytest

from tools.inspectors import map_probe as parser
from tools.inspectors import map_survey as survey
from tools.inspectors.asset_catalog import asset_id
from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.pipeline.extract_assets import resource_plan
from tools.pipeline.profile import ProfileError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def own_map():
    data = bytearray(560)
    struct.pack_into("<I", data, 0, 0xFFFFFFFF)
    struct.pack_into("<3I", data, 28, 48, 304, 0)
    for group, following in ((48, 304), (304, 0)):
        for offset, length in ((group, 256), (group + 48, 208), (group + 96, 160)):
            struct.pack_into(
                "<4I", data, offset, following if offset == group else 0, 48, length, 7
            )
        struct.pack_into("<IIH", data, group + 16, 2, 19, 1)
        struct.pack_into("<4H", data, group + 64, 5, 9, 11, 13)
        shape = group + 144
        struct.pack_into("<6I", data, shape, 0, 64, 112, 23, 3, 29)
        data[shape + 64 : shape + 112] = b"OWN_VERTEX_DATA!" * 3
    return bytes(data)


def probe(data):
    return parser.probe_map(len(data), lambda offset, length: data[offset : offset + length])


def test_shared_roots_are_not_duplicate_groups_and_payload_is_never_read():
    data = own_map()
    reads = []
    allowed = {(0, 48)}
    for g in (48, 304):
        allowed.update({(g, 48), (g + 48, 48), (g + 96, 48), (g + 144, 64)})

    def headers_only(offset, length):
        assert (offset, length) in allowed
        reads.append((offset, length))
        return data[offset : offset + length]

    result = parser.probe_map(len(data), headers_only)
    assert len(reads) == len(set(reads)) == 9
    assert result["roots"] == [
        {"slot": 0, "offset": 48, "group_offsets": [48, 304]},
        {"slot": 1, "offset": 304, "group_offsets": [304]},
        {"slot": 2, "offset": 0, "group_offsets": []},
    ]
    assert result["summary"] == {
        "group_count": 2,
        "mesh_count": 2,
        "submesh_count": 2,
        "shape_count": 2,
        "vertices": 6,
    }
    group = result["groups"][0]
    assert group["opaque_word_16"] == 2 and group["opaque_word_20"] == 19
    mesh = group["children"][0]
    assert mesh["clut_index_unverified"] == 5 and mesh["opaque_halfwords"] == [9, 11, 13]
    shape = mesh["children"][0]["children"][0]
    assert shape["vertex_count"] == 3 and shape["transform_index_unverified"] == 29
    assert shape["data_offset"] == 256 and shape["vertex_bytes"] == 48
    assert shape["trailing_bytes"] == 0
    assert shape["header_sha256"] == digest(data[192:256])
    assert result["material_binding"] == "unverified"
    assert "OWN_VERTEX" not in json.dumps(result)


def test_reverse_root_order_and_duplicate_root_keep_same_unique_nodes():
    original = probe(own_map())
    data = bytearray(own_map())
    struct.pack_into("<3I", data, 28, 304, 48, 304)
    result = probe(bytes(data))
    assert result["groups"] == original["groups"]
    assert result["summary"] == original["summary"]


def test_relative_content_offsets_and_leaf_trailer_preserved():
    data = bytearray(own_map())
    # The last shape has space for three vertices; declare two and keep its trailer.
    struct.pack_into("<I", data, 464, 2)
    shape = probe(bytes(data))["groups"][1]["children"][0]["children"][0]["children"][0]
    assert shape["vertex_bytes"] == 32 and shape["trailing_bytes"] == 16
    # Use an additional 16-byte gap before first shape payload.
    struct.pack_into("<I", data, 452, 80)
    shape = probe(bytes(data))["groups"][1]["children"][0]["children"][0]["children"][0]
    assert shape["data_offset"] == 528 and shape["trailing_bytes"] == 0


@pytest.mark.parametrize(
    "size,code",
    [
        (True, "MAP_SIZE"),
        (-1, "MAP_SIZE"),
        (None, "MAP_SIZE"),
        (parser.MAX_MAP_BYTES + 1, "MAP_BUDGET"),
    ],
)
def test_bad_size_before_read(size, code):
    with pytest.raises(parser.MapProbeError, match=code):
        parser.probe_map(size, lambda *_: pytest.fail("Unexpected read"))


@pytest.mark.parametrize("value", [b"", bytes(47), bytes(49), bytearray(48), None, "x" * 48])
def test_reader_contract(value):
    with pytest.raises(parser.MapProbeError, match="MAP_READ_CONTRACT"):
        parser.probe_map(48, lambda *_: value)


@pytest.mark.parametrize(
    "offset,fmt,value,code",
    [
        (0, "I", 0, "MAP_AREA_VARIANT"),
        (28, "I", 16, "MAP_LINK"),
        (28, "I", 49, "MAP_LINK"),
        (28, "I", 0xFFFFFFF0, "MAP_RANGE"),
        (32, "I", 96, "MAP_OVERLAP"),
        (48, "I", 48, "MAP_LINK"),
        (48, "I", 96, "MAP_LINK"),
        (48, "I", 560, "MAP_LINK"),
        (48, "I", 305, "MAP_LINK"),
        (52, "I", 32, "MAP_NODE_RANGE"),
        (52, "I", 49, "MAP_NODE_RANGE"),
        (52, "I", 272, "MAP_NODE_RANGE"),
        (56, "I", 257, "MAP_NODE_RANGE"),
        (56, "I", 0xFFFFFFF0, "MAP_NODE_RANGE"),
        (72, "H", 2, "MAP_MESH_COUNT"),
        (96, "I", 96, "MAP_LINK"),
        (104, "I", 224, "MAP_NODE_RANGE"),
        (144, "I", 48, "MAP_LINK"),
        (192, "I", 192, "MAP_LINK"),
        (196, "I", 48, "MAP_NODE_RANGE"),
        (208, "I", 0, "MAP_VERTEX_RANGE"),
        (208, "I", 4, "MAP_VERTEX_RANGE"),
        (208, "I", 0xFFFFFFFF, "MAP_VERTEX_RANGE"),
    ],
)
def test_malformed_map_rejected_without_partial_result(offset, fmt, value, code):
    data = bytearray(own_map())
    struct.pack_into("<" + fmt, data, offset, value)
    with pytest.raises(parser.MapProbeError, match=code):
        probe(bytes(data))


@pytest.mark.parametrize("end", [0, 47, 48, 95, 191, 255, 303, 559])
def test_truncated_map(end):
    with pytest.raises(parser.MapProbeError):
        probe(own_map()[:end])


def test_no_groups_not_accepted():
    data = bytearray(48)
    struct.pack_into("<I", data, 0, 0xFFFFFFFF)
    with pytest.raises(parser.MapProbeError, match="MAP_EMPTY"):
        probe(bytes(data))


@pytest.mark.parametrize("limit,value", [("MAX_NODES", 7), ("MAX_VERTICES", 5)])
def test_budgets(limit, value, monkeypatch):
    monkeypatch.setattr(parser, limit, value)
    with pytest.raises(parser.MapProbeError, match="MAP_BUDGET"):
        probe(own_map())


@pytest.fixture
def evidence(tmp_path):
    # A single 8-bit texture with own bytes, accepted by the existing TEX contract.
    texture = bytearray(4512)
    struct.pack_into("<8I", texture, 0, 0xFFFFFFFF, 0, 32, len(texture), 0, 1, 0, 0)
    struct.pack_into("<HHBBHII", texture, 40, 16, 16, 8, 32, 0, 256, 336)
    texture[57] = 0x13
    texture[60:64] = bytes((4, 4, 0x99, 0x99))
    struct.pack_into("<I", texture, 368, 4096)
    texture[380:384] = bytes((4, 0, 64, 64))
    payloads = [own_map() + bytes(texture), bytes(texture)]
    source_hash = digest(b"own map source")
    source = {
        "id": "iso:" + source_hash,
        "sha256": source_hash,
        "size": 65536,
        "profile": {"id": "own-profile", "platform": "ps2"},
    }
    parent = {
        "id": "entry:" + "3" * 64,
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
            "source_name": ["own-room.map", "own-roomTR.tex"][i],
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
        "summary": {"entry_count": 2, "payload_bytes": sum(map(len, payloads))},
        "capabilities": [],
        "payload_decoding": "not_performed",
    }
    resources = resource_plan(catalog)
    raw = json.dumps(catalog).encode()
    files = [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in resources]
    receipt = {
        "schema_version": 1,
        "tool": {"name": "sh3-mfa-extract", "version": 1},
        "status": "verified",
        "catalog_sha256": digest(raw),
        "source": source,
        "selection": catalog["selection"],
        "summary": catalog["summary"],
        "resources": resources,
        "copies": {"copy-a": files, "copy-b": files},
        "exclusions": {"containers": [], "outside_scope_ids": []},
        "capabilities": [],
        "payload_decoding": "not_performed",
    }
    for copy in ("copy-a", "copy-b"):
        (tmp_path / copy).mkdir()
        for resource in resources:
            i = next(i for i, entry in enumerate(entries) if entry["id"] == resource["id"])
            (tmp_path / copy / resource["file"]).write_bytes(payloads[i])
    receipt_raw = json.dumps(receipt).encode()
    (tmp_path / "catalog.json").write_bytes(raw)
    (tmp_path / "receipt.json").write_bytes(receipt_raw)
    return {
        "root": tmp_path,
        "catalog": catalog,
        "receipt": receipt,
        "catalog_hash": digest(raw),
        "receipt_hash": digest(receipt_raw),
        "map_id": entries[0]["id"],
        "texture_id": entries[1]["id"],
    }


def inputs(evidence):
    return {k: v for k, v in evidence.items() if k != "root"}


def run(evidence, copy="copy-a"):
    with VerifiedPrivateReader(evidence["root"] / copy, evidence["root"] / "checkout") as reader:
        return survey.inspect_pair(reader, **inputs(evidence))


def cli_args(evidence, output):
    root = evidence["root"]
    values = {
        "catalog": root / "catalog.json",
        "receipt": root / "receipt.json",
        "private-copy": root / "copy-a",
        "output": output,
        "catalog-sha256": evidence["catalog_hash"],
        "receipt-sha256": evidence["receipt_hash"],
        "map-id": evidence["map_id"],
        "texture-id": evidence["texture_id"],
    }
    return [str(part) for key, value in values.items() for part in ("--" + key, value)]


def test_two_copies_identical_only_hint_no_names_or_vertices(evidence):
    report = run(evidence)
    assert report == run(evidence, "copy-b")
    assert report["selection"]["name_hint"] == "same_stem_tr_suffix"
    assert report["material_binding"] == "unverified" and report["capabilities"] == []
    for value in ("OWN_VERTEX_DATA", "own-room", str(evidence["root"])):
        assert value not in json.dumps(report)


@pytest.mark.parametrize("name", ["unrelated.tex", "own-roomTR.bin", "own-room.tex"])
def test_nonmatching_names_never_infer_binding(evidence, name):
    evidence["catalog"]["entries"][1]["source_name"] = name
    report = run(evidence)
    assert report["selection"]["name_hint"] == "none"
    assert report["material_binding"] == "unverified"


def test_embedded_texture_explicit_offset_is_relative_and_not_a_material_link(evidence):
    evidence["embedded_offset"] = 560
    report = run(evidence)
    assert report == run(evidence, "copy-b")
    embedded = report["embedded_texture"]
    assert embedded["base_offset"] == 560
    assert embedded["offsets_relative_to"] == "embedded_area_start"
    assert embedded["structure"] == report["texture"]
    assert embedded["structure"]["blocks"][0]["header_offset"] == 32
    assert report["material_binding"] == "unverified"


@pytest.mark.parametrize("offset", [-16, 0, 48, 304, 559, 561, 5072, True])
def test_embedded_range_rejected(evidence, offset):
    evidence["embedded_offset"] = offset
    with pytest.raises(ProfileError) as exc:
        run(evidence)
    assert exc.value.code == "MAP_EMBEDDED_RANGE"


def test_embedded_bad_structure_is_not_accepted(evidence):
    from tools.inspectors.texture_probe import TextureProbeError

    evidence["embedded_offset"] = 576
    with pytest.raises(TextureProbeError):
        run(evidence)


@pytest.mark.parametrize("selection", ["missing_map", "missing_texture", "same"])
def test_bad_selection_before_reader(evidence, selection):
    values = inputs(evidence)
    if selection == "same":
        values["texture_id"] = values["map_id"]
    else:
        values["map_id" if selection == "missing_map" else "texture_id"] = "asset:" + "f" * 64
    with pytest.raises(ProfileError) as exc:
        survey.inspect_pair(None, **values)
    assert exc.value.code == "MAP_SELECTION"


def test_mixed_receipt_rejected(evidence):
    evidence["receipt"]["catalog_sha256"] = "0" * 64
    with pytest.raises(ProfileError):
        survey.inspect_pair(None, **inputs(evidence))


def test_cli_publish_once(evidence, capsys):
    output = evidence["root"] / "report.json"
    assert survey.main(cli_args(evidence, output)) == 0
    assert json.loads(output.read_bytes()) == run(evidence)
    before = output.read_bytes()
    assert survey.main(cli_args(evidence, output)) == 1
    assert output.read_bytes() == before
    assert "OUTPUT_EXISTS" in capsys.readouterr().out


@pytest.mark.parametrize("fault", ["corrupt", "short", "final_set", "publish"])
def test_cli_failure_never_publishes_success(evidence, monkeypatch, capsys, fault):
    original = survey.VerifiedPrivateReader
    events = []

    class Reader(original):
        checks = 0

        def verify_set(self, resources):
            self.checks += 1
            if fault == "final_set" and self.checks == 2:
                raise ProfileError("PRIVATE_SET_MISMATCH", "changed")
            return super().verify_set(resources)

        def read_verified(self, *args):
            if fault == "short":
                return b""
            return super().read_verified(*args)

        def __exit__(self, *args):
            result = super().__exit__(*args)
            events.append("closed")
            return result

    monkeypatch.setattr(survey, "VerifiedPrivateReader", Reader)
    if fault == "corrupt":
        resource = evidence["receipt"]["resources"][0]
        path = evidence["root"] / "copy-a" / resource["file"]
        data = path.read_bytes()
        path.write_bytes(bytes((data[0] ^ 1,)) + data[1:])
    if fault == "publish":

        def failed_publish(*args):
            assert events == ["closed"]
            raise OSError("disk")

        monkeypatch.setattr(survey, "publish_report", failed_publish)
    output = evidence["root"] / "failed.json"
    assert survey.main(cli_args(evidence, output)) == 1
    assert not output.exists() and events == ["closed"]
    assert '"status": "rejected"' in capsys.readouterr().out


def test_module_entrypoint(evidence):
    output = evidence["root"] / "module.json"
    result = subprocess.run(
        [sys.executable, "-m", "tools.inspectors.map_survey", *cli_args(evidence, output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text()) == run(evidence)


def test_cli_embedded_offset(evidence):
    output = evidence["root"] / "embedded.json"
    assert survey.main([*cli_args(evidence, output), "--embedded-offset", "560"]) == 0
    evidence["embedded_offset"] = 560
    assert json.loads(output.read_text()) == run(evidence)
