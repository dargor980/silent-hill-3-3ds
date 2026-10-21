"""MG01-MG07: independent synthetic records and on-disk MAP extraction evidence."""

import hashlib
import json
import os
import struct
import subprocess
import sys

import pytest

from tools.inspectors.asset_catalog import asset_id
from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.pipeline import decode_map_geometry as pipeline
from tools.pipeline import private_texture_output as output
from tools.pipeline.decoders import ps2_map_geometry as decoder
from tools.pipeline.extract_assets import resource_plan
from tools.pipeline.geometry_obj import encode_obj
from tools.pipeline.profile import ProfileError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(position, u, v=8192, packed=(-32768, 127, 32767)):
    return struct.pack("<8h", *position, packed[0], u, v, *packed[1:])


def own_shape():
    return b"".join(
        [
            record((0, 0, 0), 1),
            record((4, 0, 0), 16385),
            record((0, 4, 0), 0),
            record((4, 4, 0), 16384),
            record((0, 8, 0), 0),
        ]
    )


def own_map():
    data = bytearray(480)
    struct.pack_into("<I", data, 0, 0xFFFFFFFF)
    struct.pack_into("<3I", data, 28, 48, 0, 48)
    for offset, size in ((48, 432), (96, 384), (144, 336)):
        struct.pack_into("<4I", data, offset, 0, 48, size, 0)
    struct.pack_into("<IIH", data, 64, 2, 0, 1)
    struct.pack_into("<4H", data, 112, 0, 1, 0, 1)
    for shape, following in ((192, 336), (336, 0)):
        struct.pack_into("<6I", data, shape, following, 64, 144, 0, 5, 7)
        data[shape + 64 : shape + 144] = own_shape()
    return bytes(data)


def test_known_strip_winding_uv_and_all_packed_words_preserved():
    raw = own_shape()
    geometry = decoder.decode_shape(raw, 5)
    assert geometry.triangles == ((0, 1, 2), (3, 2, 1), (2, 3, 4))
    assert geometry.skipped_vertices == (0, 1)
    assert geometry.degenerate_triangles == ()
    assert geometry.vertices[0].packed_attributes == (-32768, 127, 32767)
    assert geometry.vertices[0].uv_words == (1, 8192)
    assert geometry.vertices[0].uv_reference == (1 / 32768, 0.75)
    assert geometry.vertices[1].uv_reference == (0.5 + 1 / 32768, 0.75)
    assert decoder.encode_vertices(geometry.vertices) == raw


def test_skips_do_not_reset_parity_and_shapes_restart_independently():
    raw = own_shape() + record((8, 8, 0), 1) + record((4, 12, 0), 0)
    decoded = decoder.decode_shape(raw, 7)
    assert decoded.triangles[-1] == (4, 5, 6)
    assert decoded.skipped_vertices == (0, 1, 5)
    # Consecutive omissions at indices 2/3 do not change the index-4 winding.
    raw = b"".join(record((i, i % 2, 0), 1 if i < 4 else 0) for i in range(6))
    assert decoder.decode_shape(raw, 6).triangles == ((2, 3, 4), (5, 4, 3))
    assert decoder.decode_shape(own_shape(), 5).triangles[0] == (0, 1, 2)


def test_degenerates_kept_and_counted_with_exact_integer_area():
    raw = b"".join(record((i, i, i), int(i < 2)) for i in range(4))
    geometry = decoder.decode_shape(raw, 4)
    assert geometry.triangles == ((0, 1, 2), (3, 2, 1))
    assert geometry.degenerate_triangles == (0, 1)
    repeated = record((0, 0, 0), 1) * 2 + record((0, 0, 0), 0)
    assert decoder.decode_shape(repeated, 3).degenerate_triangles == (0,)


def test_all_skipped_preserved_without_inventing_faces():
    geometry = decoder.decode_shape(record((0, 0, 0), -1) * 3, 3)
    assert geometry.triangles == () and geometry.skipped_vertices == (0, 1, 2)


def test_signed_extremes_and_cross_product_not_overflowing():
    raw = (
        record((-32768, -32768, -32768), -32767, -32768)
        + record((32767, -32768, -32768), 32767, 32767)
        + record((-32768, 32767, 32767), -32768, 32767)
    )
    geometry = decoder.decode_shape(raw, 3)
    assert geometry.vertices[0].uv_reference == (-32767 / 32768, 2.0)
    assert geometry.vertices[2].uv_reference == (-1.0, 1 / 32768)
    assert geometry.degenerate_triangles == ()
    assert decoder.encode_vertices(geometry.vertices) == raw


@pytest.mark.parametrize("count", [None, True, -1, 0, 1, 2, 65537])
def test_invalid_count(count):
    with pytest.raises(decoder.GeometryDecodeError, match="MG_VERTEX_COUNT"):
        decoder.decode_shape(b"", count)


@pytest.mark.parametrize("raw", [b"", bytes(47), bytes(49), bytearray(48), None, "x" * 48])
def test_payload_size_and_type(raw):
    with pytest.raises(decoder.GeometryDecodeError, match="MG_PAYLOAD_SIZE"):
        decoder.decode_shape(raw, 3)


@pytest.mark.parametrize("first,second", [(0, 1), (1, 0), (0, 0)])
def test_face_before_third_vertex_rejected(first, second):
    raw = record((0, 0, 0), first) + record((1, 0, 0), second) + record((0, 1, 0), 0)
    with pytest.raises(decoder.GeometryDecodeError, match="MG_STRIP_START"):
        decoder.decode_shape(raw, 3)


def test_maximum_count_roundtrips():
    raw = record((0, 0, 0), 1) * 65536
    decoded = decoder.decode_shape(raw, 65536)
    assert len(decoded.vertices) == 65536 and decoder.encode_vertices(decoded.vertices) == raw


def test_roundtrip_failure_rejected(monkeypatch):
    monkeypatch.setattr(decoder, "encode_vertices", lambda _: b"wrong")
    with pytest.raises(decoder.GeometryDecodeError, match="MG_ROUNDTRIP"):
        decoder.decode_shape(own_shape(), 5)


def test_obj_faces_reference_correct_shape_vertices_and_uvs():
    first = decoder.decode_shape(own_shape(), 5)
    second = decoder.decode_shape(record((1, 2, 3), 1) * 3, 3)
    obj = encode_obj([(192, first), (336, second)]).decode()
    vertices, uvs, faces, names = [], [], [], []
    for line in obj.splitlines():
        fields = line.split()
        if fields[0] == "v":
            vertices.append(tuple(map(int, fields[1:])))
        elif fields[0] == "vt":
            uvs.append(tuple(map(float, fields[1:])))
        elif fields[0] == "f":
            faces.append(tuple(tuple(map(int, token.split("/"))) for token in fields[1:]))
        elif fields[0] == "o":
            names.append(fields[1])
    assert names == ["shape_192", "shape_336"]
    assert vertices == [v.position for g in (first, second) for v in g.vertices]
    assert uvs == [v.uv_reference for g in (first, second) for v in g.vertices]
    assert faces == [((1, 1), (2, 2), (3, 3)), ((4, 4), (3, 3), (2, 2)), ((3, 3), (4, 4), (5, 5))]
    # A second nonempty form must advance global v/vt indices independently.
    obj = encode_obj([(192, first), (336, first)]).decode()
    assert "f 6/6 7/7 8/8\n" in obj and "f 8/8 9/9 10/10\n" in obj
    assert "usemtl" not in obj and "vn " not in obj


@pytest.fixture
def evidence(tmp_path):
    payload = own_map()
    source_hash = digest(b"own geometry fixture")
    source = {
        "id": "iso:" + source_hash,
        "sha256": source_hash,
        "size": 65536,
        "profile": {"id": "own-profile", "platform": "ps2"},
    }
    parent = {
        "id": "entry:" + "4" * 64,
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
        "sha256": digest(payload),
        "source_name": "own.map",
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
    raw = json.dumps(catalog).encode()
    files = [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in resources]
    receipt = {
        "schema_version": 1,
        "tool": {"name": "sh3-mfa-extract", "version": 1},
        "status": "verified",
        "catalog_sha256": digest(raw),
        "source": source,
        "selection": {},
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
        (root / copy / resources[0]["file"]).write_bytes(payload)
    (root / "out").mkdir()
    receipt_raw = json.dumps(receipt).encode()
    (root / "catalog.json").write_bytes(raw)
    (root / "receipt.json").write_bytes(receipt_raw)
    return {
        "root": root,
        "catalog": catalog,
        "receipt": receipt,
        "catalog_hash": digest(raw),
        "receipt_hash": digest(receipt_raw),
        "identity": entry["id"],
        "group_offset": 48,
    }


def inputs(evidence):
    return {key: value for key, value in evidence.items() if key != "root"}


def run(evidence, copy="copy-a"):
    with VerifiedPrivateReader(evidence["root"] / copy, evidence["root"] / "checkout") as reader:
        return pipeline.decode_group(reader, **inputs(evidence))


def replace_fixture_payload(evidence, payload):
    catalog, receipt = evidence["catalog"], evidence["receipt"]
    catalog["entries"][0].update(size=len(payload), sha256=digest(payload))
    catalog["summary"]["payload_bytes"] = len(payload)
    resources = resource_plan(catalog)
    raw = json.dumps(catalog).encode()
    evidence["catalog_hash"] = receipt["catalog_sha256"] = digest(raw)
    receipt["resources"] = resources
    inventory = [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in resources]
    receipt["copies"] = {"copy-a": inventory, "copy-b": inventory}
    receipt_raw = json.dumps(receipt).encode()
    evidence["receipt_hash"] = digest(receipt_raw)
    root = evidence["root"]
    (root / "catalog.json").write_bytes(raw)
    (root / "receipt.json").write_bytes(receipt_raw)
    for copy in ("copy-a", "copy-b"):
        (root / copy / resources[0]["file"]).write_bytes(payload)


def args(evidence, run_id="own"):
    root = evidence["root"]
    values = {
        "catalog": root / "catalog.json",
        "receipt": root / "receipt.json",
        "catalog-sha256": evidence["catalog_hash"],
        "receipt-sha256": evidence["receipt_hash"],
        "private-copy": root / "copy-a",
        "private-root": root / "out",
        "resource-id": evidence["identity"],
        "group-offset": evidence["group_offset"],
        "run-id": run_id,
    }
    return [str(part) for key, value in values.items() for part in ("--" + key, value)]


def test_repeated_copies_and_private_json_obj_consistency(evidence):
    files, report = run(evidence)
    assert (files, report) == run(evidence, "copy-b")
    assert report["summary"] == {
        "shapes": 2,
        "vertices": 10,
        "triangles": 6,
        "degenerate_triangles": 0,
    }
    doc = json.loads(files["geometry.json"])
    assert len(doc["shapes"]) == 2 and "vertices" not in report["shapes"][0]
    for shape in doc["shapes"]:
        assert shape["triangles"] == [[0, 1, 2], [3, 2, 1], [2, 3, 4]]
        raw = b"".join(
            record(tuple(v["position"]), *v["uv_words"], tuple(v["packed_attributes"]))
            for v in shape["vertices"]
        )
        assert digest(raw) == shape["source_sha256"]
    assert report["material_binding"] == "unverified" and report["geometry_3ds"] == "pending"
    assert "own.map" not in json.dumps(report) and "usemtl" not in files["inspection.obj"].decode()


@pytest.mark.parametrize(
    "offset,code",
    [
        (True, "MG_GROUP_OFFSET"),
        (0, "MG_GROUP_OFFSET"),
        (49, "MG_GROUP_OFFSET"),
        (64, "MG_GROUP_MISSING"),
    ],
)
def test_bad_group_selection(evidence, offset, code):
    evidence["group_offset"] = offset
    with pytest.raises(decoder.GeometryDecodeError, match=code):
        run(evidence)


def test_missing_resource_and_wrong_receipt(evidence):
    original = evidence["identity"]
    evidence["identity"] = "asset:" + "f" * 64
    with pytest.raises(decoder.GeometryDecodeError, match="MG_RESOURCE_MISSING"):
        pipeline.decode_group(None, **inputs(evidence))
    evidence["identity"] = original
    evidence["receipt"]["catalog_sha256"] = "0" * 64
    with pytest.raises(ProfileError):
        pipeline.decode_group(None, **inputs(evidence))


def test_group_budget_precedes_payload_read(evidence, monkeypatch):
    monkeypatch.setattr(pipeline, "MAX_VERTICES", 9)
    with pytest.raises(decoder.GeometryDecodeError, match="MG_GROUP_BUDGET"):
        run(evidence)


def test_short_shape_count_rejected_before_its_payload(evidence):
    payload = bytearray(own_map())
    struct.pack_into("<I", payload, 208, 2)
    replace_fixture_payload(evidence, bytes(payload))
    with pytest.raises(decoder.GeometryDecodeError, match="MG_VERTEX_COUNT"):
        run(evidence)


def test_large_shape_read_in_bounded_fragments(evidence):
    count = 600
    raw = record((0, 0, 0), 1) * count
    shape_size = 64 + len(raw)
    data = bytearray(192 + shape_size)
    struct.pack_into("<I", data, 0, 0xFFFFFFFF)
    struct.pack_into("<I", data, 28, 48)
    for start in (48, 96, 144):
        struct.pack_into("<4I", data, start, 0, 48, len(data) - start, 0)
    struct.pack_into("<H", data, 72, 1)
    struct.pack_into("<6I", data, 192, 0, 64, shape_size, 0, count, 1)
    data[256:] = raw
    replace_fixture_payload(evidence, bytes(data))
    reads = []

    class Reader(VerifiedPrivateReader):
        def read_verified(self, resource, offset, length):
            reads.append((offset, length))
            assert length <= 4096
            return super().read_verified(resource, offset, length)

    with Reader(evidence["root"] / "copy-a", evidence["root"] / "checkout") as reader:
        files, report = pipeline.decode_group(reader, **inputs(evidence))
    assert reads[-3:] == [(256, 4096), (4352, 4096), (8448, 1408)]
    assert report["summary"]["vertices"] == 600 and report["summary"]["triangles"] == 0
    assert len(json.loads(files["geometry.json"])["shapes"][0]["vertices"]) == 600


@pytest.mark.parametrize("fault", ["short", "hash", "final_set"])
def test_reader_failure_no_partial_acceptance(evidence, fault):
    class Reader(VerifiedPrivateReader):
        checks = 0

        def verify_set(self, resources):
            self.checks += 1
            if fault == "final_set" and self.checks == 2:
                raise ProfileError("PRIVATE_SET_MISMATCH", "changed")
            return super().verify_set(resources)

        def read_verified(self, resource, offset, length):
            if offset == 256:
                if fault == "short":
                    return b""
                if fault == "hash":
                    raise ProfileError("PRIVATE_HASH_MISMATCH", "changed")
            return super().read_verified(resource, offset, length)

    with Reader(evidence["root"] / "copy-a", evidence["root"] / "checkout") as reader:
        with pytest.raises(ProfileError):
            pipeline.decode_group(reader, **inputs(evidence))


def test_private_bundle_manifest_permissions_and_occupied_session(evidence):
    files, report = run(evidence)
    root, checkout = evidence["root"] / "out", evidence["root"] / "checkout"
    first = output.write_geometry_bundle(root, checkout, "one", files, report)
    assert first == output.write_geometry_bundle(root, checkout, "two", files, report)
    for item in first["files"]:
        path = root / "one" / item["file"]
        assert digest(path.read_bytes()) == item["sha256"]
        assert os.stat(path).st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        output.write_geometry_bundle(root, checkout, "one", files, report)


@pytest.mark.parametrize("kind", ["missing", "extra", "empty", "repo"])
def test_invalid_bundle(evidence, kind):
    files, report = run(evidence)
    root, checkout = evidence["root"] / "out", evidence["root"] / "checkout"
    if kind == "missing":
        files.pop("inspection.obj")
    elif kind == "extra":
        files["unexpected"] = b"x"
    elif kind == "empty":
        files["geometry.json"] = b""
    else:
        checkout = root
    with pytest.raises(ProfileError):
        output.write_geometry_bundle(root, checkout, "bad", files, report)
    assert not (root / "bad").exists()


def test_cli_success_and_error_codes(evidence, capsys):
    assert pipeline.main(args(evidence)) == 0
    session = evidence["root"] / "out" / "own"
    assert json.loads((session / "manifest.json").read_text())["summary"]["triangles"] == 6
    assert pipeline.main(args(evidence)) == 1
    evidence["group_offset"] = 64
    assert pipeline.main(args(evidence, "missing")) == 1
    assert not (evidence["root"] / "out" / "missing").exists()
    assert "MG_GROUP_MISSING" in capsys.readouterr().out


def test_cli_corrupt_copy_fails_before_output(evidence, capsys):
    resource = evidence["receipt"]["resources"][0]
    path = evidence["root"] / "copy-a" / resource["file"]
    data = path.read_bytes()
    path.write_bytes(b"X" + data[1:])
    assert pipeline.main(args(evidence)) == 1
    assert not (evidence["root"] / "out" / "own").exists()
    assert "PRIVATE_HASH_MISMATCH" in capsys.readouterr().out


def test_writer_called_after_reader_closed(evidence, monkeypatch):
    original = pipeline.VerifiedPrivateReader
    events = []

    class Reader(original):
        def __exit__(self, *arguments):
            result = super().__exit__(*arguments)
            events.append("closed")
            return result

    def fail(*arguments):
        assert events == ["closed"]
        raise OSError("own disk failure")

    monkeypatch.setattr(pipeline, "VerifiedPrivateReader", Reader)
    monkeypatch.setattr(pipeline, "write_geometry_bundle", fail)
    assert pipeline.main(args(evidence)) == 1
    assert not (evidence["root"] / "out" / "own").exists()


def test_module_entrypoint(evidence):
    result = subprocess.run(
        [sys.executable, "-m", "tools.pipeline.decode_map_geometry", *args(evidence)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["triangles"] == 6
