"""CAM01-CAM08: own numeric fixtures, never original camera records."""

import hashlib
import json
import struct

import pytest

from tools.inspectors import camera_survey as survey
from tools.inspectors.asset_catalog import asset_id
from tools.inspectors.camera_probe import (
    MAX_CAMERA_BYTES,
    REFERENCE_MAXIMA,
    CameraProbeError,
    probe_camera,
)
from tools.inspectors.candidates import collect_candidates
from tools.inspectors.private_reader import VerifiedPrivateReader
from tools.pipeline.extract_assets import resource_plan
from tools.pipeline.profile import ProfileError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def own_record(*, flags=0, fields=None):
    data = bytearray(128)
    struct.pack_into("<16f", data, 0, *(float(i) / 4 for i in range(16)))
    struct.pack_into("<I", data, 68, flags)
    for offset, value in (fields or {}).items():
        struct.pack_into("<I", data, offset, value)
    return bytes(data)


@pytest.mark.parametrize("count", [0, 1, 30, 31])
def test_boundaries_and_marker_count(count):
    data = own_record() * count + own_record(flags=1)
    result = probe_camera(data)
    assert result["status"] == "hypothesis_match"
    assert result["prefix_record_count"] == result["marker_record_index"] == count
    assert result["opaque_tail"] == {"size": 0, "sha256": digest(b"")}
    assert not result["marker_has_other_bits"]
    assert not any(result["reference_range_disagreements"].values())


@pytest.mark.parametrize(
    "data,code",
    [
        (None, "CAMERA_INPUT_TYPE"),
        (bytearray(128), "CAMERA_INPUT_TYPE"),
        (b"", "CAMERA_ALIGNMENT"),
        (b"x" * 127, "CAMERA_ALIGNMENT"),
        (b"x" * 129, "CAMERA_ALIGNMENT"),
        (b"x" * 4097, "CAMERA_BUDGET"),
        (own_record() * 32, "CAMERA_NO_MARKER"),
        (bytes(128), "CAMERA_NO_MARKER"),
    ],
)
def test_invalid_hypothesis_is_typed(data, code):
    with pytest.raises(CameraProbeError) as error:
        probe_camera(data)
    assert error.value.code == code


def test_big_endian_marker_is_not_accepted():
    record = bytearray(own_record())
    struct.pack_into(">I", record, 68, 1)
    with pytest.raises(CameraProbeError) as error:
        probe_camera(bytes(record))
    assert error.value.code == "CAMERA_NO_MARKER"


@pytest.mark.parametrize("offset", [0, 60])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_before_marker_rejected(offset, value):
    record = bytearray(own_record())
    struct.pack_into("<f", record, offset, value)
    with pytest.raises(CameraProbeError) as error:
        probe_camera(bytes(record) + own_record(flags=1))
    assert error.value.code == "CAMERA_NONFINITE_PREFIX"


def test_marker_and_tail_are_opaque_even_with_nonfinite_or_another_marker():
    terminal = bytearray(own_record(flags=3))
    struct.pack_into("<f", terminal, 0, float("nan"))
    tail = own_record(flags=1, fields={108: 999}) + bytes([255]) * 128
    result = probe_camera(own_record() + bytes(terminal) + tail)
    assert result["prefix_record_count"] == 1 and result["marker_has_other_bits"]
    assert result["opaque_tail"] == {"size": len(tail), "sha256": digest(tail)}
    assert not any(result["reference_range_disagreements"].values())


@pytest.mark.parametrize("offset", list(REFERENCE_MAXIMA))
@pytest.mark.parametrize("delta", [0, 1])
def test_reference_range_boundary_is_observation_not_rejection(offset, delta):
    prefix = own_record(fields={offset: REFERENCE_MAXIMA[offset] + delta})
    result = probe_camera(prefix + own_record(flags=1))
    assert result["reference_range_disagreements"][str(offset)] == delta
    assert result["status"] == "hypothesis_match"


def test_multiple_disagreements_and_uncertain_field_not_inferred():
    fields = {offset: 0xFFFFFFFF for offset in REFERENCE_MAXIMA}
    fields[80] = 0xFFFFFFFF
    result = probe_camera(own_record(fields=fields) * 2 + own_record(flags=1))
    assert result["reference_range_disagreements"] == {str(o): 2 for o in REFERENCE_MAXIMA}


@pytest.fixture
def evidence(tmp_path):
    # These are internally consistent synthetic documents, not a claim of an ISO dump.
    root = tmp_path.resolve() / "private"
    root.mkdir()
    repository = tmp_path.resolve() / "checkout"
    repository.mkdir()
    payloads = [
        own_record(fields={108: 14}) + own_record(flags=1) + b"Z" * 384,
        own_record(flags=1) + b"Y" * 384,
        own_record(),
        b"own unrelated content",
    ]
    source_hash = digest(b"own synthetic source identity")
    source = {
        "id": "iso:" + source_hash,
        "sha256": source_hash,
        "size": 65536,
        "profile": {"id": "own-test-profile", "platform": "ps2"},
    }
    origin = {"image_id": source["id"], "profile_id": source["profile"]["id"]}
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
            "origin": origin,
            "block_offset": 0,
            "entry_index": i,
            "container_offset": 128 + i * 8192,
            "size": len(data),
            "sha256": digest(data),
            "source_name": f"own/sample-{i}." + ("CAM" if i < 3 else "bin"),
        }
        for i, data in enumerate(payloads)
    ]
    catalog = {
        "schema_version": 1,
        "scope": "selected_mfa_entries",
        "tool": {"name": "sh3-asset-catalog", "version": 1},
        "source": source,
        "selection": {"schema_version": 1, "canonical_sha256": "a" * 64},
        "containers": [parent],
        "entries": entries,
        "outside_scope": [],
        "summary": {"entry_count": len(entries), "payload_bytes": sum(map(len, payloads))},
        "capabilities": [],
        "payload_decoding": "not_performed",
    }
    resources = resource_plan(catalog)
    hashes = {"catalog": digest(json.dumps(catalog).encode())}
    files = [{k: item[k] for k in ("id", "file", "size", "sha256")} for item in resources]
    receipt = {
        "schema_version": 1,
        "tool": {"name": "sh3-mfa-extract", "version": 1},
        "status": "verified",
        "catalog_sha256": hashes["catalog"],
        "source": source,
        "selection": catalog["selection"],
        "summary": catalog["summary"],
        "resources": resources,
        "copies": {"copy-a": files, "copy-b": files},
        "exclusions": {"containers": [], "outside_scope_ids": []},
        "capabilities": [],
        "payload_decoding": "not_performed",
    }
    hashes["receipt"] = digest(json.dumps(receipt).encode())
    by_id = {e["id"]: data for e, data in zip(entries, payloads, strict=True)}
    for name in ("copy-a", "copy-b"):
        path = root / name
        path.mkdir()
        for item in resources:
            (path / item["file"]).write_bytes(by_id[item["id"]])
    with VerifiedPrivateReader(root / "copy-a", repository) as reader:
        inventory = collect_candidates(
            reader, catalog, receipt, hashes["catalog"], hashes["receipt"]
        )
    hashes["inventory"] = digest(json.dumps(inventory).encode())
    return {
        "catalog": catalog,
        "receipt": receipt,
        "inventory": inventory,
        "hashes": hashes,
        "root": root,
        "repository": repository,
        "directory": tmp_path.resolve(),
    }


def documents(evidence):
    return {k: evidence[k] for k in ("catalog", "receipt", "inventory", "hashes")}


def run(evidence, copy_name="copy-a"):
    with VerifiedPrivateReader(evidence["root"] / copy_name, evidence["repository"]) as reader:
        return survey.survey_camera(reader, **documents(evidence))


def test_two_copies_repeat_with_unknown_and_false_positive_preserved(evidence):
    result = run(evidence)
    assert run(evidence, "copy-b") == result
    evidence["catalog"]["entries"].reverse()
    evidence["inventory"]["candidates"].reverse()
    assert run(evidence) == result
    assert result["summary"] == {
        "selected_count": 3,
        "hypothesis_match_count": 2,
        "unknown_count": 1,
        "unknown_codes": {"CAMERA_NO_MARKER": 1},
        "prefix_record_count": 1,
        "zero_prefix_count": 1,
        "opaque_tail_sizes": [{"size": 384, "count": 2}],
        "reference_range_disagreements": {"72": 0, "76": 0, "92": 0, "108": 1},
        "files_with_reference_disagreements": 1,
        "identified_count": 0,
    }
    for item in result["entries"]:
        assert item["state"] == "candidate" and item["classification"] == {"type": "unknown"}
        assert item["dependencies"]["status"] == "not_inspected"
    assert result["f02_07_status"] == "pending" and result["capabilities"] == []
    assert result["next_task"] == "F02.07/camera-consumer-eu"
    rendered = json.dumps(result)
    assert "own/sample" not in rendered and "ZZZZ" not in rendered
    assert str(evidence["root"]) not in rendered


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), True),
        (("scope",), "other"),
        (("tool", "version"), True),
        (("tool", "name"), "other"),
        (("evidence", "catalog_sha256"), "b" * 64),
        (("source",), {}),
        (("selection",), {}),
        (("capabilities",), ["camera"]),
        (("f02_07_status",), "complete"),
        (("payload_decoding",), "performed"),
        (("corpus_id",), "other"),
        (("candidates", 0, "size"), True),
        (("candidates", 0, "origin"), {}),
        (("candidates", 0, "state"), "identified"),
        (("candidates", 0, "classification", "type"), "camera"),
        (("candidates", 0, "name_hint", "suffix"), ".cam-bogus"),
        (("candidates", 0, "name_hint", "status"), "verified"),
    ],
)
def test_mixed_inventory_rejected_before_reads(evidence, path, value):
    target = evidence["inventory"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ProfileError) as error:
        survey.survey_camera(None, **documents(evidence))
    assert error.value.code == "CAMERA_EVIDENCE_MISMATCH"


@pytest.mark.parametrize("malformed", [None, [], {}, {"schema_version": 1}])
def test_malformed_inventory_is_typed(evidence, malformed):
    evidence["inventory"] = malformed
    with pytest.raises(ProfileError) as error:
        survey.survey_camera(None, **documents(evidence))
    assert error.value.code == "INVALID_CAMERA_EVIDENCE"


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "foreign_id"])
def test_inventory_requires_exact_resource_set(evidence, mutation):
    values = evidence["inventory"]["candidates"]
    if mutation == "duplicate":
        values.append(values[0])
    elif mutation == "missing":
        values.pop()
    else:
        values[0]["id"] = "asset:" + "f" * 64
    with pytest.raises(ProfileError):
        survey.survey_camera(None, **documents(evidence))


def test_empty_selection_is_not_a_success(evidence):
    for item in evidence["catalog"]["entries"]:
        item["source_name"] = "own/no-hint.bin"
    for item in evidence["inventory"]["candidates"]:
        item["name_hint"]["suffix"] = ".bin"
    with pytest.raises(ProfileError) as error:
        survey.survey_camera(None, **documents(evidence))
    assert error.value.code == "CAMERA_EMPTY_SELECTION"


@pytest.mark.parametrize("fault", ["transport", "short", "text", "final_set"])
def test_reader_failure_aborts_entire_survey(evidence, fault):
    class Reader:
        calls = 0

        def verify_set(self, resources):
            self.calls += 1
            if fault == "final_set" and self.calls == 2:
                raise ProfileError("PRIVATE_SET_MISMATCH", "changed")

        def read_verified(self, item, offset, length):
            if fault == "transport":
                raise ProfileError("PRIVATE_HASH_MISMATCH", "changed")
            if fault == "text":
                return "x" * length
            if fault == "short":
                return b""
            return own_record(flags=1) + bytes(length - 128)

    with pytest.raises(ProfileError) as error:
        survey.survey_camera(Reader(), **documents(evidence))
    assert error.value.code in {"PRIVATE_HASH_MISMATCH", "SIZE_MISMATCH", "PRIVATE_SET_MISMATCH"}


def test_over_budget_retained_unknown_without_read(evidence):
    item = evidence["catalog"]["entries"][0]
    size = MAX_CAMERA_BYTES + 128
    difference = size - item["size"]
    item["size"] = size
    # Shared summary objects in these own fixture documents must stay concordant.
    evidence["catalog"]["summary"]["payload_bytes"] += difference
    for collection in (
        evidence["receipt"]["resources"],
        evidence["receipt"]["copies"]["copy-a"],
        evidence["inventory"]["candidates"],
    ):
        next(i for i in collection if i["id"] == item["id"])["size"] = size

    class Reader:
        def verify_set(self, resources):
            pass

        def read_verified(self, resource, offset, length):
            assert resource["id"] != item["id"]
            return bytes(length)

    result = survey.survey_camera(Reader(), **documents(evidence))
    assert result["summary"]["hypothesis_match_count"] == 0
    assert result["summary"]["unknown_codes"]["CAMERA_BUDGET"] == 1
    assert (
        next(i for i in result["entries"] if i["id"] == item["id"])["result"]["read"]
        == "not_performed"
    )


def cli_args(evidence, output):
    args = []
    for key in ("catalog", "receipt", "inventory"):
        path = evidence["directory"] / (key + ".json")
        raw = json.dumps(evidence[key]).encode()
        path.write_bytes(raw)
        assert digest(raw) == evidence["hashes"][key]
        args.extend(["--" + key, str(path), "--" + key + "-sha256", digest(raw)])
    return args + ["--private-copy", str(evidence["root"] / "copy-a"), "--output", str(output)]


def test_cli_success_new_reports_repeat_and_existing_preserved(evidence, capsys):
    first = evidence["directory"] / "first.json"
    second = evidence["directory"] / "second.json"
    for output in (first, second):
        assert survey.main(cli_args(evidence, output)) == 0
        assert json.loads(capsys.readouterr().out)["identified_count"] == 0
    assert first.read_bytes() == second.read_bytes()
    assert survey.main(cli_args(evidence, first)) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "OUTPUT_EXISTS"


@pytest.mark.parametrize(
    "fault", ["catalog_hash", "receipt_hash", "inventory_hash", "private", "publish"]
)
def test_cli_errors_sanitized_no_success_report(evidence, capsys, monkeypatch, fault):
    output = evidence["directory"] / "report.json"
    args = cli_args(evidence, output)
    if fault.endswith("_hash"):
        path = evidence["directory"] / (fault.removesuffix("_hash") + ".json")
        path.write_bytes(path.read_bytes() + b" ")
    elif fault == "private":
        path = next((evidence["root"] / "copy-a").iterdir())
        path.unlink()
    else:

        def fail(*args):
            raise OSError("private-name-do-not-print")

        monkeypatch.setattr(survey, "publish_report", fail)
    assert survey.main(args) == 1
    text = capsys.readouterr().out
    assert json.loads(text)["status"] == "rejected"
    assert "private-name" not in text and "own/sample" not in text
    assert not output.exists()
