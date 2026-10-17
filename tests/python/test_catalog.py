"""F00.02 / T01: catalog evidence is applied only after matching actual bytes."""

import copy
import hashlib
import json
import zlib
from io import BytesIO

import pytest

from tools.pipeline.catalog import match_catalog, parse_catalog
from tools.pipeline.hashing import fingerprint_stream
from tools.pipeline.profile import ProfileError

PAYLOAD = b"abc"
IDENTITY = {
    "size": 3,
    "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    "sha1": "a9993e364706816aba3e25717850c26c9cd0d89d",
    "md5": "900150983cd24fb0d6963f7d28e17f72",
    "crc32": "352441c2",
}
REFERENCE = {
    "schema_version": 1,
    "id": "synthetic-catalog",
    "source_url": "https://example.invalid/synthetic",
    "retrieved_on": "2026-10-16",
    "serial": "SLES-00001",
    "region": "Europe",
    "revision": "1.02",
    "languages": ["en", "fr", "de", "es", "it"],
    "image": {key: value for key, value in IDENTITY.items() if key != "sha256"},
}
BOOT = {"serial": "SLES-00001", "system_cnf_ver": "1.02"}


def test_reference_vector_and_bounded_stream_reads():
    class BoundedReader(BytesIO):
        def read(self, size=-1):
            assert 0 < size <= 1024 * 1024
            return super().read(size)

    assert fingerprint_stream(BoundedReader(PAYLOAD), 3, include_catalog=True) == IDENTITY
    assert fingerprint_stream(BytesIO(PAYLOAD), 3) == {"size": 3, "sha256": IDENTITY["sha256"]}


def test_multiblock_hash():
    payload = b"synthetic" * 150000
    result = fingerprint_stream(BytesIO(payload), len(payload), include_catalog=True)
    assert result == {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "sha1": hashlib.sha1(payload).hexdigest(),
        "md5": hashlib.md5(payload).hexdigest(),
        "crc32": f"{zlib.crc32(payload):08x}",
    }


@pytest.mark.parametrize("payload,size", [(b"x", 0), (b"", 1)])
def test_wrong_stream_length(payload, size):
    with pytest.raises(ProfileError) as error:
        fingerprint_stream(BytesIO(payload), size, include_catalog=True)
    assert error.value.code == "SIZE_MISMATCH"


@pytest.mark.parametrize("size", [-2, -1, True, 1.5, 1 << 64])
def test_invalid_expected_size_is_rejected_before_reading(size):
    class UnreadableStream:
        def read(self, size):
            pytest.fail("Must reject size before reading")

    with pytest.raises(ProfileError) as error:
        fingerprint_stream(UnreadableStream(), size)
    assert error.value.code == "INVALID_SIZE"


def test_matching_catalog_yields_identity_evidence_only():
    reference = parse_catalog(REFERENCE)
    match_catalog(reference, IDENTITY, BOOT, "Europe")
    match_catalog(reference, IDENTITY, BOOT, "unknown")
    assert reference.languages == ("en", "fr", "de", "es", "it")
    assert not hasattr(reference, "capabilities")


@pytest.mark.parametrize("key", ["size", "sha1", "md5", "crc32"])
def test_every_required_fingerprint_must_match(key):
    identity = {**IDENTITY, key: 99 if key == "size" else "0" * len(IDENTITY[key])}
    with pytest.raises(ProfileError) as error:
        match_catalog(parse_catalog(REFERENCE), identity, BOOT, "Europe")
    assert error.value.code == "CATALOG_MISMATCH"


@pytest.mark.parametrize(
    "serial,version,region",
    [
        ("SLES-99999", "1.02", "Europe"),
        ("SLES-00001", "1.03", "Europe"),
        ("SLES-00001", "1.02", "Japan"),
    ],
)
def test_inconsistent_metadata_is_rejected(serial, version, region):
    with pytest.raises(ProfileError) as error:
        match_catalog(
            parse_catalog(REFERENCE),
            IDENTITY,
            {"serial": serial, "system_cnf_ver": version},
            region,
        )
    assert error.value.code == "CATALOG_MISMATCH"


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("id", "../bad"),
        ("source_url", "file:///local"),
        ("retrieved_on", "2026-99-99"),
        ("serial", "invalid"),
        ("region", ""),
        ("revision", ""),
        ("languages", []),
        ("languages", ["es", "es"]),
        ("languages", [{}]),
        ("languages", ["Spanish"]),
        ("image", []),
    ],
)
def test_invalid_reference(key, value):
    data = {**REFERENCE, key: value}
    with pytest.raises(ProfileError):
        parse_catalog(data)


@pytest.mark.parametrize(
    "key,value",
    [
        ("size", True),
        ("size", 0),
        ("sha1", "bad"),
        ("md5", None),
        ("crc32", "a" * 9),
    ],
)
def test_invalid_reference_image(key, value):
    data = copy.deepcopy(REFERENCE)
    data["image"][key] = value
    with pytest.raises(ProfileError):
        parse_catalog(data)


def test_reference_is_data_not_instruction():
    data = {**REFERENCE, "commands": ["do-not-run-anything"]}
    assert parse_catalog(data) == parse_catalog(REFERENCE)


def test_repository_catalog_contains_only_published_metadata():
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "docs/compatibility/catalogs/redump-1064.json"
    reference = parse_catalog(json.loads(path.read_text()))
    assert reference.serial == "SLES-51434"
    assert reference.revision == "1.02"
    assert reference.image_size == 3586785280
