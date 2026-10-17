"""C01-C08: own extraction evidence, conservative observations and CLI custody."""

import copy
import hashlib
import json
import os

import pytest
from test_asset_catalog import catalog_source as catalog_source
from test_extraction import inputs as inputs
from test_extraction import run

from tools.inspectors import candidate_inventory as cli
from tools.inspectors import candidates, private_reader
from tools.inspectors.private_reader import MAX_RANGE_BYTES, VerifiedPrivateReader
from tools.pipeline.private_output import resource_filename
from tools.pipeline.profile import ProfileError
from tools.qa.custody import _local_violation


@pytest.fixture
def extracted(inputs):
    inputs.receipt = run(inputs)
    inputs.receipt_path = inputs.root / "run/verified.json"
    inputs.receipt_hash = hashlib.sha256(inputs.receipt_path.read_bytes()).hexdigest()
    inputs.copy = inputs.root / "run/copy-a"
    return inputs


def inspect(extracted, *, copy_name="copy-a"):
    with VerifiedPrivateReader(extracted.root / "run" / copy_name, extracted.repository) as reader:
        return candidates.collect_candidates(
            reader,
            extracted.catalog,
            extracted.receipt,
            extracted.catalog_hash,
            extracted.receipt_hash,
        )


def cli_args(extracted, output):
    return [
        str(value)
        for pair in {
            "catalog": extracted.catalog_path,
            "catalog-sha256": extracted.catalog_hash,
            "receipt": extracted.receipt_path,
            "receipt-sha256": extracted.receipt_hash,
            "private-copy": extracted.copy,
            "output": output,
        }.items()
        for value in ("--" + pair[0], pair[1])
    ]


def test_two_copies_deterministic_with_unknowns_and_exclusions(extracted):
    first = inspect(extracted)
    assert first == inspect(extracted, copy_name="copy-b")
    extracted.catalog["entries"].reverse()
    assert first == inspect(extracted)
    assert first["summary"] == {
        "candidate_count": 5,
        "payload_bytes": 27,
        "empty_count": 1,
        "content_group_count": 1,
        "prefix_group_count": 1,
        "identified_count": 0,
        "unresolved_category_count": 12,
    }
    assert len(first["content_groups"][0]["ids"]) == 2
    assert len(first["exclusions"]["containers"]) == 1
    assert len(first["exclusions"]["outside_scope_ids"]) == 3
    assert {item["category"] for item in first["categories"]} == set(candidates.CATEGORIES)
    assert all(item["ids"] == [] and item["next_task"] for item in first["categories"])
    assert first["capabilities"] == [] and first["f02_07_status"] == "pending"
    assert first["room_pair"]["status"] == "unresolved"
    for item in first["candidates"]:
        assert item["state"] == "candidate" and item["classification"]["type"] == "unknown"
        assert item["dependencies"] == {"status": "not_inspected", "known": []}
        raw = (extracted.copy / resource_filename(item["id"])).read_bytes()
        assert item["observations"]["prefix"]["sha256"] == hashlib.sha256(raw[:64]).hexdigest()
    rendered = json.dumps(first)
    assert "own/same" not in rendered and "ABCD" not in rendered
    assert str(extracted.root) not in rendered


def test_same_prefix_is_not_same_content_or_format(extracted):
    resources = extracted.receipt["resources"]
    large = [item for item in resources if item["size"] > 0]
    # Test grouping separately: equal 64-byte prefix, distinct full hashes and sizes.
    entries = [
        {
            "id": item["id"],
            "size": 65,
            "sha256": str(i) * 64,
            "observations": {"prefix": {"length": 64, "sha256": "a" * 64}},
        }
        for i, item in enumerate(large)
    ]
    assert candidates._groups(entries, prefix=False) == []
    assert len(candidates._groups(entries, prefix=True)[0]["ids"]) == len(large)
    for item in extracted.catalog["entries"]:
        item["source_name"] = "own/looks-like-a-scene.ELF"
    report = inspect(extracted)
    assert all(item["name_hint"]["suffix"] == ".elf" for item in report["candidates"])
    assert report["summary"]["identified_count"] == 0


@pytest.mark.parametrize(
    "target,path,value",
    [
        ("catalog", ("schema_version",), True),
        ("receipt", ("schema_version",), 2),
        ("catalog", ("scope",), "other"),
        ("catalog", ("tool", "name"), "other"),
        ("receipt", ("tool", "name"), "other"),
        ("receipt", ("tool", "version"), True),
        ("catalog", ("tool", "version"), 2),
        ("receipt", ("capabilities",), ["decoded"]),
        ("catalog", ("payload_decoding",), "performed"),
        ("receipt", ("status",), "started"),
        ("receipt", ("catalog_sha256",), "a" * 64),
        ("receipt", ("source", "profile", "id"), "other"),
        ("receipt", ("selection", "canonical_sha256"), "a" * 64),
        ("receipt", ("summary", "entry_count"), 4),
        ("catalog", ("entries", 0, "origin", "image_id"), "other"),
        ("catalog", ("entries", 0, "block_offset"), True),
        ("catalog", ("entries", 0, "entry_index"), -1),
        ("catalog", ("entries", 0, "id"), "asset:" + "a" * 64),
        ("catalog", ("entries", 0, "container_offset"), 2**63),
        ("catalog", ("entries", 0, "source_name"), None),
        ("receipt", ("resources", 0, "size"), 999),
        ("receipt", ("copies", "copy-b", 0, "sha256"), "a" * 64),
        ("receipt", ("exclusions", "outside_scope_ids"), []),
    ],
)
def test_evidence_conflicts_fail_before_private_reads(extracted, target, path, value):
    document = getattr(extracted, target)
    for key in path[:-1]:
        document = document[key]
    document[path[-1]] = value

    class NoReads:
        def verify_set(self, resources):
            pytest.fail("Malformed evidence reached filesystem")

    with pytest.raises(ProfileError, match="Candidate evidence") as error:
        candidates.collect_candidates(
            NoReads(),
            extracted.catalog,
            extracted.receipt,
            extracted.catalog_hash,
            extracted.receipt_hash,
        )
    assert error.value.code == "CANDIDATE_EVIDENCE_MISMATCH"


@pytest.mark.parametrize("shape", [None, [], {}, {"schema_version": 1, "scope": []}])
def test_malformed_evidence_is_typed(shape):
    with pytest.raises(ProfileError) as error:
        candidates.validate_evidence(shape, {}, "a" * 64)
    assert error.value.code in {"INVALID_CANDIDATE_EVIDENCE", "CANDIDATE_EVIDENCE_MISMATCH"}


def test_catalog_and_receipt_cannot_jointly_claim_wrong_source(extracted):
    for doc in (extracted.catalog, extracted.receipt):
        doc["source"]["id"] = "iso:" + "b" * 64
    with pytest.raises(ProfileError) as error:
        inspect(extracted)
    assert error.value.code == "CANDIDATE_EVIDENCE_MISMATCH"


@pytest.mark.parametrize("operation", ["empty", "duplicate", "parent", "copies", "size_bool"])
def test_reconciled_but_invalid_plan_rejected(extracted, operation):
    if operation == "empty":
        extracted.catalog["entries"] = []
    elif operation == "duplicate":
        extracted.catalog["containers"].append(copy.deepcopy(extracted.catalog["containers"][0]))
    elif operation == "parent":
        parent_id = extracted.catalog["entries"][0]["container_id"]
        next(c for c in extracted.catalog["containers"] if c["id"] == parent_id)["result"][
            "status"
        ] = "unknown"
    elif operation == "copies":
        del extracted.receipt["copies"]["copy-b"]
    else:
        for doc in (extracted.catalog, extracted.receipt):
            doc["summary"]["payload_bytes"] = True
    with pytest.raises(ProfileError) as error:
        inspect(extracted)
    assert error.value.code == "CANDIDATE_EVIDENCE_MISMATCH"


@pytest.mark.parametrize("invalid", [b"", "not bytes"])
def test_reader_contract_cannot_publish_short_or_nonbinary_range(extracted, invalid):
    class BadReader:
        def verify_set(self, resources):
            pass

        def read_verified(self, resource, offset, length):
            return invalid

    with pytest.raises(ProfileError) as error:
        candidates.collect_candidates(
            BadReader(),
            extracted.catalog,
            extracted.receipt,
            extracted.catalog_hash,
            extracted.receipt_hash,
        )
    assert error.value.code == "SIZE_MISMATCH"


@pytest.fixture
def private_file(tmp_path):
    root, repo = tmp_path.resolve() / "private", tmp_path.resolve() / "repo"
    root.mkdir()
    repo.mkdir()
    data = b"own fixture data" * 300
    resource = {
        "id": "asset:" + "1" * 64,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    path = root / resource_filename(resource["id"])
    path.write_bytes(data)
    return root, repo, resource, path, data


@pytest.mark.parametrize("offset,length", [(0, 0), (0, 4096), (1, 7), (4800, 0), (4799, 1)])
def test_verified_range_exact_boundaries(private_file, offset, length):
    root, repo, resource, path, data = private_file
    with VerifiedPrivateReader(root, repo) as reader:
        assert reader.read_verified(resource, offset, length) == data[offset : offset + length]
    assert path.read_bytes() == data


@pytest.mark.parametrize(
    "offset,length",
    [(-1, 0), (0, -1), (False, 1), (0, True), (0, MAX_RANGE_BYTES + 1), (4801, 0), (4800, 1)],
)
def test_bad_range_rejected_before_open(private_file, offset, length, monkeypatch):
    root, repo, resource, path, data = private_file
    with VerifiedPrivateReader(root, repo) as reader:
        monkeypatch.setattr(
            reader, "_assert_attached", lambda: pytest.fail("I/O before validation")
        )
        with pytest.raises(ProfileError) as error:
            reader.read_verified(resource, offset, length)
    assert error.value.code == "INVALID_RANGE"


@pytest.mark.parametrize("size", [True, -1, 2**63, "4"])
def test_invalid_resource_size(private_file, size):
    root, repo, resource, *_ = private_file
    resource["size"] = size
    with VerifiedPrivateReader(root, repo) as reader, pytest.raises(ProfileError) as error:
        reader.read_verified(resource, 0, 0)
    assert error.value.code == "INVALID_SIZE"


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("missing", "PRIVATE_READ_ERROR"),
        ("short", "SIZE_MISMATCH"),
        ("long", "SIZE_MISMATCH"),
        ("corrupt", "PRIVATE_HASH_MISMATCH"),
        ("symlink", "PRIVATE_READ_ERROR"),
        ("hardlink", "INVALID_PRIVATE_FILE"),
        ("fifo", "INVALID_PRIVATE_FILE"),
        # fdopen rejects a directory before the stream-level regular-file check.
        ("directory", "PRIVATE_READ_ERROR"),
    ],
)
def test_rejects_private_file_mutations(private_file, mutation, code):
    root, repo, resource, path, data = private_file
    if mutation == "short":
        path.write_bytes(data[:-1])
    elif mutation == "long":
        path.write_bytes(data + b"x")
    elif mutation == "corrupt":
        path.write_bytes(b"x" + data[1:])
    elif mutation == "hardlink":
        os.link(path, root / "another")
    else:
        path.unlink()
        if mutation == "symlink":
            target = repo / "own.bin"
            target.write_bytes(data)
            path.symlink_to(target)
        elif mutation == "fifo":
            os.mkfifo(path)
        elif mutation == "directory":
            path.mkdir()
    with VerifiedPrivateReader(root, repo) as reader, pytest.raises(ProfileError) as error:
        reader.read_verified(resource, 0, 64)
    assert error.value.code == code


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_requires_exact_file_set(private_file, mutation):
    root, repo, resource, path, data = private_file
    resources = [resource]
    if mutation == "missing":
        path.unlink()
    elif mutation == "extra":
        (root / "extra").write_bytes(b"own")
    else:
        resources.append(resource)
    with VerifiedPrivateReader(root, repo) as reader, pytest.raises(ProfileError) as error:
        reader.verify_set(resources)
    assert error.value.code == "PRIVATE_SET_MISMATCH"


@pytest.mark.parametrize("location", ["repo", "inside", "ancestor", "link", "relative"])
def test_root_confinement(private_file, location):
    root, repo, resource, path, data = private_file
    if location == "repo":
        root = repo
    elif location == "inside":
        root = repo / "child"
    elif location == "ancestor":
        root = repo.parent
    elif location == "link":
        alias = root.parent / "alias"
        alias.symlink_to(root, target_is_directory=True)
        root = alias
    else:
        root = type(root)("relative-root")
    with pytest.raises(ProfileError):
        with VerifiedPrivateReader(root, repo):
            pytest.fail("Invalid root accepted")


@pytest.mark.parametrize("replacement", ["directory", "file", "in_place", "hardlink"])
def test_changed_during_hash_is_rejected(private_file, monkeypatch, replacement):
    root, repo, resource, path, data = private_file
    original = private_reader.fingerprint_stream

    def changing(stream, expected):
        result = original(stream, expected)
        if replacement == "directory":
            root.rename(root.with_name("old"))
            root.mkdir()
        elif replacement == "file":
            path.unlink()
            path.write_bytes(data)
        elif replacement == "in_place":
            path.write_bytes(b"x" + data[1:])
        else:
            os.link(path, root / "alias")
        return result

    monkeypatch.setattr(private_reader, "fingerprint_stream", changing)
    with VerifiedPrivateReader(root, repo) as reader, pytest.raises(ProfileError) as error:
        reader.read_verified(resource, 0, 64)
    assert error.value.code == "PRIVATE_CHANGED"


def test_changed_directory_before_read(private_file):
    root, repo, resource, *_ = private_file
    with VerifiedPrivateReader(root, repo) as reader:
        root.rename(root.with_name("old"))
        root.mkdir()
        with pytest.raises(ProfileError) as error:
            reader.verify_set([resource])
    assert error.value.code == "PRIVATE_CHANGED"


@pytest.mark.parametrize("operation", ["listdir", "hash", "stat"])
def test_io_errors_are_typed(private_file, monkeypatch, operation):
    root, repo, resource, *_ = private_file

    def fail(*args, **kwargs):
        raise OSError("private-name-and-data-must-not-escape")

    with VerifiedPrivateReader(root, repo) as reader:
        if operation == "listdir":
            monkeypatch.setattr(os, "listdir", fail)
        elif operation == "hash":
            monkeypatch.setattr(private_reader, "fingerprint_stream", fail)
        else:
            monkeypatch.setattr(os, "stat", fail)
        with pytest.raises(ProfileError) as error:
            if operation == "listdir":
                reader.verify_set([resource])
            else:
                reader.read_verified(resource, 0, 64)
    assert error.value.code == "PRIVATE_READ_ERROR"
    assert "private-name" not in str(error.value)


@pytest.mark.parametrize("short", [True, False])
def test_range_handles_short_reads_and_rejects_truncation(private_file, monkeypatch, short):
    root, repo, resource, path, data = private_file
    original = os.fdopen

    class RangeStream:
        def __init__(self, stream):
            self.stream, self.range_mode = stream, False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def seek(self, offset):
            self.range_mode = True
            return self.stream.seek(offset)

        def read(self, length):
            if self.range_mode:
                return self.stream.read(min(length, 7)) if short else b""
            return self.stream.read(length)

    monkeypatch.setattr(os, "fdopen", lambda fd, mode: RangeStream(original(fd, mode)))
    with VerifiedPrivateReader(root, repo) as reader:
        if short:
            assert reader.read_verified(resource, 5, 64) == data[5:69]
        else:
            with pytest.raises(ProfileError) as error:
                reader.read_verified(resource, 5, 64)
            assert error.value.code == "SIZE_MISMATCH"


@pytest.mark.parametrize("primary", [False, True])
def test_close_failure_attempted_once_preserves_primary(private_file, monkeypatch, primary):
    root, repo, *_ = private_file
    reader = VerifiedPrivateReader(root, repo).__enter__()
    descriptor = reader.descriptor
    original, calls = os.close, []

    def close(fd):
        calls.append(fd)
        original(fd)
        raise OSError("close failure")

    monkeypatch.setattr(os, "close", close)
    error = RuntimeError("primary") if primary else None
    if primary:
        reader.__exit__(RuntimeError, error, None)
        assert "attempted once" in error.__notes__[0]
    else:
        with pytest.raises(ProfileError):
            reader.__exit__(None, None, None)
    assert calls == [descriptor] and reader.descriptor is None


def test_cli_repeats_new_metadata_only(extracted, tmp_path, capsys):
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    for output in (first, second):
        assert cli.main(cli_args(extracted, output)) == 0
        result = json.loads(capsys.readouterr().out)
        assert result["candidate_count"] == 5 and result["f02_07_status"] == "pending"
    assert first.read_bytes() == second.read_bytes()
    assert first.stat().st_mode & 0o777 == 0o600
    staging = first.with_name(".first.json.pending.json")
    assert staging.read_bytes() == first.read_bytes()
    assert _local_violation(type(staging)("reports/local") / staging.name, "file", True) is None
    assert cli.main(cli_args(extracted, first)) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "OUTPUT_EXISTS"


@pytest.mark.parametrize("kind", ["catalog", "receipt", "payload", "symlink_output", "publish"])
def test_cli_failure_has_no_payload_names_or_success(
    extracted, tmp_path, capsys, monkeypatch, kind
):
    output = tmp_path / "report.json"
    if kind in ("catalog", "receipt"):
        path = getattr(extracted, kind + "_path")
        path.write_bytes(path.read_bytes() + b" ")
    elif kind == "payload":
        item = next(i for i in extracted.receipt["resources"] if i["size"] > 0)
        (extracted.copy / item["file"]).write_bytes(b"broken")
    elif kind == "symlink_output":
        output.symlink_to(tmp_path / "absent")
    else:

        def fail(*args):
            raise OSError("private-name-and-payload")

        monkeypatch.setattr(cli, "publish_report", fail)
    assert cli.main(cli_args(extracted, output)) == 1
    printed = capsys.readouterr().out
    assert json.loads(printed)["status"] == "rejected"
    assert "own/" not in printed and "private-name" not in printed
    assert not output.exists()


@pytest.mark.parametrize("operation", ["write", "fsync", "link"])
def test_failed_publication_retains_only_staging(tmp_path, monkeypatch, operation):
    output = tmp_path.resolve() / "report.json"

    def fail(*args, **kwargs):
        raise OSError("injected")

    if operation == "write":
        monkeypatch.setattr(cli, "write_all", fail)
    else:
        monkeypatch.setattr(os, operation, fail)
    with pytest.raises(OSError):
        cli.publish_report(output, {"own": "metadata"})
    assert not output.exists()
    assert output.with_name(".report.json.pending.json").exists()


def test_publication_does_not_overwrite_or_follow_parent(tmp_path):
    output = tmp_path.resolve() / "report.json"
    output.write_text("old")
    with pytest.raises(FileExistsError):
        cli.publish_report(output, {"new": "metadata"})
    assert output.read_text() == "old"
    alias = tmp_path.resolve() / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(OSError):
        cli.publish_report(alias / "new.json", {})
