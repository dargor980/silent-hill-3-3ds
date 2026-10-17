"""A01-A11: own resources, bounded hashing and reproducible private metadata."""

import hashlib
import json
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
from io import BytesIO

import pycdlib
import pytest
from test_mfa import MemoryDisc, Sectors, own_files, profile_data, sector

from tools.inspectors import asset_catalog, asset_selection, mfa
from tools.inspectors.asset_selection import load_selection, parse_selection
from tools.pipeline.hashing import CHUNK_BYTES, fingerprint_range
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile


def fixture_files():
    files = own_files()
    first = bytearray(2048)
    first[:4] = first[16:20] = b"ABCD"
    second = bytearray(2048)
    second[32:35] = b"XYZ"
    files["B0.MFA"] = (
        sector(
            ("own/same one.bin", "own/same_two.bin", "own/empty"),
            ranges=[(0, 4), (16, 4), (2048, 0)],
        )
        + bytes(first)
        + sector(("own/second",), toc=8, ranges=[(32, 3)])
        + bytes(second)
    )
    files["EXTRA.AFS"] = b"AFS\0" + bytes(4)
    return files


def selection_data(files, image_hash="a" * 64):
    return {
        "schema_version": 1,
        "profile_id": "synthetic-mfa-probe",
        "image_sha256": image_hash,
        "containers": [
            {
                "path": p,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "layout": "b8" if p == "ALT.MFA" else "d8",
            }
            for p, data in files.items()
            if p.endswith(".MFA")
        ],
    }


class MemoryAssets(MemoryDisc):
    def __init__(self, files, offsets=None):
        super().__init__(files, offsets or {p: i * 16384 for i, p in enumerate(files)})
        self.resource_reads = []

    def hash_range(self, path, offset, length):
        assert self.hashed == set(self.files)
        assert 0 <= offset <= offset + length <= len(self.files[path])
        self.resource_reads.append((path, offset, length))
        data = self.files[path][offset : offset + length]
        return len(data), hashlib.sha256(data).hexdigest()


def collect(reader=None, selection=None, profile=None):
    reader = reader or MemoryAssets(fixture_files())
    selection = selection or parse_selection(selection_data(reader.files))
    profile = profile or parse_profile(profile_data(reader.files))
    return asset_catalog.collect_assets(reader, profile, 1048576, "a" * 64, selection)


def test_expected_metadata_hashes_distinct_ids_and_unknown_dependencies():
    reader = MemoryAssets(fixture_files())
    report = collect(reader)
    assert report["summary"] == {
        "candidate_container_count": 3,
        "catalogued_container_count": 2,
        "unknown_container_count": 1,
        "block_count": 3,
        "entry_count": 5,
        "payload_bytes": 27,
        "outside_scope_file_count": 3,
    }
    assert len({e["id"] for e in report["entries"]}) == 5
    by_name = {e["source_name"]: e for e in report["entries"]}
    one, two = by_name["own/same one.bin"], by_name["own/same_two.bin"]
    assert one["sha256"] == two["sha256"] == hashlib.sha256(b"ABCD").hexdigest()
    assert one["id"] != two["id"]
    assert one["container_offset"] == 2048 and two["container_offset"] == 2064
    assert one["iso_offset"] == reader.offsets["B0.MFA"] + 2048
    assert by_name["own/empty"]["size"] == 0
    assert by_name["own/empty"]["sha256"] == hashlib.sha256(b"").hexdigest()
    second = by_name["own/second"]
    assert (
        second["block_index"],
        second["block_offset"],
        second["entry_index"],
        second["entry_ordinal"],
        second["container_offset"],
        second["source_name_offset"],
    ) == (1, 4096, 0, 4, 6176, 4128)
    assert second["sha256"] == hashlib.sha256(b"XYZ").hexdigest()
    for entry in report["entries"]:
        assert entry["dependencies"] == {"status": "not_inspected", "known": []}
        assert entry["classification"] == {"type": "unknown", "reason": "not_decoded"}
        assert entry["support"] == "metadata_and_hash_only"
        assert entry["origin"] == {
            "profile_id": "synthetic-mfa-probe",
            "image_id": "iso:" + "a" * 64,
        }
        assert entry["unknown_word"] == 0x1234
        assert entry["source_name_encoding"] == "ascii"
    assert report["capabilities"] == []
    assert report["extraction"] == report["payload_decoding"] == "not_performed"
    assert not any(path == "BAD.MFA" for path, _, _ in reader.resource_reads)
    assert {e["path"] for e in report["outside_scope"]} == {
        "SYSTEM.CNF",
        "SLES_000.01",
        "EXTRA.AFS",
    }


def test_selection_order_and_reader_order_do_not_change_catalog():
    raw = selection_data(fixture_files())
    base = collect(selection=parse_selection(raw))
    raw["containers"].reverse()
    assert collect(selection=parse_selection(raw)) == base
    assert parse_selection(raw).digest() == base["selection"]["canonical_sha256"]


def test_ids_bind_parent_and_position_not_payload_or_name():
    identity = asset_catalog.asset_id("entry:parent", 0, 0)
    assert identity != asset_catalog.asset_id("entry:other", 0, 0)
    assert identity != asset_catalog.asset_id("entry:parent", 4096, 0)
    assert identity != asset_catalog.asset_id("entry:parent", 0, 1)


def test_parser_descriptors_are_frozen_and_match_summary():
    data = fixture_files()["B0.MFA"]
    index = mfa.parse_layout(Sectors({0: data[:2048], 4096: data[4096:6144]}), len(data), "d8")
    assert len(index.entries) == index.summary["entry_count"] == 4
    with pytest.raises(FrozenInstanceError):
        index.entries[0].size = 999
    assert index.summary == mfa.inspect_d8(
        Sectors({0: data[:2048], 4096: data[4096:6144]}), len(data)
    )


def test_late_invalid_name_never_exposes_or_hashes_partial_container():
    files = fixture_files()
    bad = bytearray(sector(("late/name",), toc=8))
    bad[32] = 255
    files["LATE.MFA"] = sector(("late/first",)) + bytes(2048) + bytes(bad) + bytes(2048)
    reader = MemoryAssets(files)
    with pytest.raises(mfa.MfaError):
        mfa.parse_layout(Sectors({0: files["LATE.MFA"][:2048], 4096: bytes(bad)}), 8192, "d8")
    report = collect(reader)
    assert report["summary"]["entry_count"] == 5
    assert not any(p == "LATE.MFA" for p, _, _ in reader.resource_reads)
    assert not any(e["source_name"].startswith("late/") for e in report["entries"])
    failed = next(c for c in report["containers"] if c["path"] == "LATE.MFA")
    assert failed["result"]["details"]["entry_ordinal"] == 2
    assert "entry_count" not in failed["result"]


def test_changed_payload_rejected_by_profile_before_parsing_or_resource_hashes():
    files = fixture_files()
    profile = parse_profile(profile_data(files))
    selection = parse_selection(selection_data(files))
    files["B0.MFA"] = files["B0.MFA"][:2048] + b"Z" + files["B0.MFA"][2049:]
    reader = MemoryAssets(files)
    with pytest.raises(ProfileError) as error:
        collect(reader, selection, profile)
    assert error.value.code == "HASH_MISMATCH"
    assert reader.resource_reads == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("profile_id", ""),
        ("profile_id", "UPPER"),
        ("profile_id", None),
        ("image_sha256", "wrong"),
        ("containers", []),
        ("containers", None),
        ("containers", [None]),
        ("containers", [{}]),
    ],
)
def test_invalid_selection_fields(field, value):
    raw = selection_data(fixture_files())
    raw[field] = value
    with pytest.raises(ProfileError):
        parse_selection(raw)


@pytest.mark.parametrize("raw", [None, [], {}, {"schema_version": 1}])
def test_selection_requires_exact_object(raw):
    with pytest.raises(ProfileError):
        parse_selection(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", "/absolute"),
        ("path", "../escape"),
        ("path", None),
        ("size", True),
        ("size", -1),
        ("size", 1 << 63),
        ("size", 1.5),
        ("sha256", "F" * 64),
        ("sha256", None),
        ("layout", "auto"),
        ("layout", 216),
    ],
)
def test_invalid_choice_fields(field, value):
    raw = selection_data(fixture_files())
    raw["containers"][0][field] = value
    with pytest.raises(ProfileError):
        parse_selection(raw)


@pytest.mark.parametrize("change", ["duplicate", "case", "extra_root", "extra_choice", "too_many"])
def test_ambiguous_or_extra_selection_fields(change):
    raw = selection_data(fixture_files())
    if change == "duplicate":
        raw["containers"].append(raw["containers"][0].copy())
    elif change == "case":
        raw["containers"].append({**raw["containers"][0], "path": "b0.mfa"})
    elif change == "extra_root":
        raw["guess"] = True
    elif change == "extra_choice":
        raw["containers"][0]["guess"] = True
    else:
        raw["containers"] = [raw["containers"][0]] * 10001
    with pytest.raises(ProfileError):
        parse_selection(raw)


@pytest.mark.parametrize(
    "change", ["image", "profile", "size", "hash", "missing", "extra", "non_mfa"]
)
def test_selection_mismatch_rejected_before_any_reader_access(change):
    files = fixture_files()
    raw = selection_data(files)
    if change == "image":
        raw["image_sha256"] = "b" * 64
    elif change == "profile":
        raw["profile_id"] = "other-profile"
    elif change == "size":
        raw["containers"][0]["size"] += 1
    elif change == "hash":
        raw["containers"][0]["sha256"] = "0" * 64
    elif change == "missing":
        raw["containers"].pop()
    elif change == "extra":
        raw["containers"].append({**raw["containers"][0], "path": "EXTRA.MFA"})
    else:
        raw["containers"][0]["path"] = "EXTRA.AFS"
    with pytest.raises(ProfileError) as error:
        asset_catalog.collect_assets(
            None, parse_profile(profile_data(files)), 1048576, "a" * 64, parse_selection(raw)
        )
    assert error.value.code == "SELECTION_MISMATCH"


def test_duplicate_typed_choices_also_rejected():
    selection = parse_selection(selection_data(fixture_files()))
    with pytest.raises(ProfileError):
        collect(
            selection=replace(selection, containers=selection.containers + selection.containers[:1])
        )


@pytest.mark.parametrize(
    "data",
    [
        b"not json",
        b"\xff",
        b'{"schema_version":1,"schema_version":1}',
        b'{"nested":{"x":1,"x":2}}',
        b"[" * 1500 + b"]" * 1500,
    ],
)
def test_selection_load_errors_are_typed(tmp_path, data):
    path = tmp_path / "selection.json"
    path.write_bytes(data)
    with pytest.raises(ProfileError):
        load_selection(path)


def test_selection_load_size_limit_and_io(tmp_path, monkeypatch):
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(selection_data(fixture_files())))
    assert (
        load_selection(path).digest() == parse_selection(selection_data(fixture_files())).digest()
    )
    monkeypatch.setattr(asset_selection, "MAX_SELECTION_BYTES", 8)
    with pytest.raises(ProfileError, match="size limit"):
        load_selection(path)
    with pytest.raises(ProfileError, match="Cannot read"):
        load_selection(tmp_path / "missing")


def test_global_resource_limit_is_enforced_before_hashing_excess_container(monkeypatch):
    reader = MemoryAssets(fixture_files())
    monkeypatch.setattr(asset_catalog, "MAX_ASSETS", 2)
    with pytest.raises(ProfileError) as error:
        collect(reader)
    assert error.value.code == "CATALOG_LIMIT"
    assert all(path == "ALT.MFA" for path, _, _ in reader.resource_reads)


@pytest.mark.parametrize("returned", [(0, "a" * 64), (True, "a" * 64), (16, "bad"), (16, "A" * 64)])
def test_hash_port_contract_rejected(returned):
    reader = MemoryAssets(fixture_files())
    reader.hash_range = lambda *args: returned
    with pytest.raises(ProfileError):
        collect(reader)


class TrackingStream(BytesIO):
    def __init__(self, data, short=False):
        super().__init__(data)
        self.calls = []
        self.short = short

    def read(self, limit=-1):
        self.calls.append(limit)
        return super().read(min(limit, 7) if self.short else limit)


def test_bounded_hash_uses_one_mib_chunks_and_never_reads_adjacent_bytes():
    payload = b"x" * (CHUNK_BYTES + 17)
    stream = TrackingStream(b"HEAD" + payload + b"NEXT")
    stream.seek(4)
    assert fingerprint_range(stream, len(payload)) == {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    assert stream.calls == [CHUNK_BYTES, 17]
    assert stream.tell() == 4 + len(payload)
    assert stream.getvalue()[stream.tell() :] == b"NEXT"


def test_range_short_positive_reads_and_zero_length():
    stream = TrackingStream(b"own data" * 10 + b"NEXT", short=True)
    assert fingerprint_range(stream, 80)["sha256"] == hashlib.sha256(b"own data" * 10).hexdigest()
    assert stream.tell() == 80
    stream.calls.clear()
    assert fingerprint_range(stream, 0) == {"size": 0, "sha256": hashlib.sha256(b"").hexdigest()}
    assert stream.calls == []


@pytest.mark.parametrize("length", [-1, True, 1.0, 1 << 63])
def test_invalid_hash_lengths_do_not_read(length):
    stream = TrackingStream(b"own")
    with pytest.raises(ProfileError):
        fingerprint_range(stream, length)
    assert stream.calls == []


def test_truncated_and_over_returning_hash_streams_rejected():
    with pytest.raises(ProfileError):
        fingerprint_range(BytesIO(b"short"), 9)

    class OverReader:
        def read(self, length):
            return b"x" * (length + 1)

    with pytest.raises(ProfileError):
        fingerprint_range(OverReader(), 4)


@pytest.fixture
def catalog_source(tmp_path):
    files = fixture_files()
    image = pycdlib.PyCdlib()
    image.new(interchange_level=3, vol_ident="OWNASSETS")
    for path, data in files.items():
        image.add_fp(BytesIO(data), len(data), iso_path=f"/{path};1")
    iso = tmp_path / "own.iso"
    image.write(str(iso))
    image.close()
    digest = hashlib.sha256(iso.read_bytes()).hexdigest()
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps(profile_data(files)))
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps(selection_data(files, digest)))
    return iso, profile, selection


def cli_args(source, tmp_path):
    iso, profile, selection = source
    return [
        "--iso",
        str(iso),
        "--profile",
        str(profile),
        "--selection",
        str(selection),
        "--image-sha256",
        hashlib.sha256(iso.read_bytes()).hexdigest(),
        "--output",
        str(tmp_path / "out.json"),
    ]


def test_iso_memory_contract_actual_bytes_and_repeat_cli(catalog_source, tmp_path, capsys):
    iso, profile, selection = catalog_source
    original = iso.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    profile = parse_profile(json.loads(profile.read_text()))
    selection = load_selection(selection)
    with IsoImage(iso) as image:
        offsets = {p: image.file_offset(p) for p in image.paths()}
        result = asset_catalog.collect_assets(image, profile, len(original), digest, selection)
    expected = asset_catalog.collect_assets(
        MemoryAssets(fixture_files(), offsets), profile, len(original), digest, selection
    )
    assert result == expected
    for e in result["entries"]:
        raw = original[e["iso_offset"] : e["iso_offset"] + e["size"]]
        assert len(raw) == e["size"] and hashlib.sha256(raw).hexdigest() == e["sha256"]
    args = cli_args(catalog_source, tmp_path)
    assert asset_catalog.main(args) == 0
    stdout = capsys.readouterr().out
    assert json.loads(stdout)["entry_count"] == 5 and "own/" not in stdout
    data = (tmp_path / "out.json").read_bytes()
    assert b"own/same one.bin" in data and b"ABCD" not in data and b"XYZ" not in data
    assert str(tmp_path).encode() not in data
    args[-1] = str(tmp_path / "repeat.json")
    assert asset_catalog.main(args) == 0
    assert (tmp_path / "repeat.json").read_bytes() == data
    assert asset_catalog.main(args) == 1
    assert (tmp_path / "repeat.json").read_bytes() == data
    assert iso.read_bytes() == original


@pytest.mark.parametrize(
    "change", ["hash", "profile", "selection", "output_dir", "output_link", "absent_iso"]
)
def test_cli_invalid_inputs_do_not_create_catalog(catalog_source, tmp_path, capsys, change):
    args = cli_args(catalog_source, tmp_path)
    if change == "hash":
        args[7] = "0" * 64
    elif change == "profile":
        args[3] += "missing"
    elif change == "selection":
        args[5] += "missing"
    elif change == "output_dir":
        args[-1] = str(tmp_path / "absent/out.json")
    elif change == "output_link":
        (tmp_path / "out.json").symlink_to(tmp_path / "absent")
    else:
        args[1] += "missing"
    assert asset_catalog.main(args) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"
    assert not (tmp_path / "out.json").exists()


def test_cli_image_mismatch_after_valid_selection(catalog_source, tmp_path, capsys):
    args = cli_args(catalog_source, tmp_path)
    args[7] = "0" * 64
    raw = json.loads(catalog_source[2].read_text())
    raw["image_sha256"] = "0" * 64
    catalog_source[2].write_text(json.dumps(raw))
    assert asset_catalog.main(args) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "IMAGE_MISMATCH"
    assert not (tmp_path / "out.json").exists()


@pytest.mark.parametrize("operation", ["image_identity", "inspect", "read_range", "hash_range"])
def test_cli_transport_failure_aborts(catalog_source, tmp_path, monkeypatch, capsys, operation):
    def fail(*args):
        raise ProfileError("ISO_READ_ERROR", "Own fault injection")

    monkeypatch.setattr(IsoImage, operation, fail)
    assert asset_catalog.main(cli_args(catalog_source, tmp_path)) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "ISO_READ_ERROR"
    assert not (tmp_path / "out.json").exists()


def test_changed_image_before_close_prevents_catalog(catalog_source, tmp_path, monkeypatch, capsys):
    original = asset_catalog.collect_assets

    def mutate(*args):
        report = original(*args)
        with catalog_source[0].open("ab") as f:
            f.write(b"own mutation")
        return report

    monkeypatch.setattr(asset_catalog, "collect_assets", mutate)
    assert asset_catalog.main(cli_args(catalog_source, tmp_path)) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "INPUT_CHANGED"
    assert not (tmp_path / "out.json").exists()


@pytest.mark.parametrize(
    "offset,length",
    [(-1, 1), (0, -1), (True, 1), (0, True), (0, 1.0), (1.0, 1), (8192, 1), (0, 8193)],
)
def test_iso_hash_ranges_confined(catalog_source, offset, length):
    with IsoImage(catalog_source[0]) as image, pytest.raises(ProfileError) as error:
        image.hash_range("B0.MFA", offset, length)
    assert error.value.code == "READ_RANGE"


def test_iso_hash_range_single_open_and_exact_seek(catalog_source, monkeypatch):
    original = pycdlib.PyCdlib.open_file_from_iso
    opens = []

    @contextmanager
    def tracked(self, **kwargs):
        opens.append(kwargs)
        with original(self, **kwargs) as stream:
            yield stream

    with IsoImage(catalog_source[0]) as image:
        monkeypatch.setattr(pycdlib.PyCdlib, "open_file_from_iso", tracked)
        assert image.hash_range("B0.MFA", 6176, 3) == (3, hashlib.sha256(b"XYZ").hexdigest())
        assert len(opens) == 1
        assert image.hash_range("B0.MFA", 8192, 0) == (0, hashlib.sha256(b"").hexdigest())
        assert len(opens) == 2


@pytest.mark.parametrize("failure", ["seek", "read", "short"])
def test_iso_range_hash_io_failures_are_typed(catalog_source, monkeypatch, failure):
    class Broken(BytesIO):
        def seek(self, *args):
            if failure == "seek":
                raise OSError("own seek fault")
            return super().seek(*args)

        def read(self, *args):
            if failure == "read":
                raise OSError("own read fault")
            return super().read(*args)

    @contextmanager
    def broken(self, **kwargs):
        yield Broken(b"xx")

    with IsoImage(catalog_source[0]) as image:
        monkeypatch.setattr(pycdlib.PyCdlib, "open_file_from_iso", broken)
        with pytest.raises(ProfileError) as error:
            image.hash_range("B0.MFA", 0, 4)
    assert error.value.code == ("SIZE_MISMATCH" if failure == "short" else "ISO_READ_ERROR")


def test_failure_after_first_hash_block_never_returns_digest():
    class FailsAfterBlock:
        def __init__(self):
            self.calls = 0

        def read(self, length):
            self.calls += 1
            if self.calls > 1:
                raise OSError("own second block failure")
            return b"a" * length

    with pytest.raises(OSError):
        fingerprint_range(FailsAfterBlock(), CHUNK_BYTES + 1)


def test_failure_after_first_resource_never_persists_partial_catalog(
    catalog_source, tmp_path, monkeypatch, capsys
):
    original = IsoImage.hash_range
    calls = []

    def later_failure(self, *args):
        calls.append(args)
        if len(calls) == 2:
            raise ProfileError("ISO_READ_ERROR", "Own failure after one resource")
        return original(self, *args)

    monkeypatch.setattr(IsoImage, "hash_range", later_failure)
    assert asset_catalog.main(cli_args(catalog_source, tmp_path)) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "ISO_READ_ERROR"
    assert len(calls) == 2
    assert not (tmp_path / "out.json").exists()
