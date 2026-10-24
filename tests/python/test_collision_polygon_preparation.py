"""CF-T7c integration with own sources only; no private files or emulator."""

import copy
import errno
import json
import os
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier

import pytest

from tests.collision_polygon_recipe_fixtures import corpus, inputs, pin, wire
from tools.pipeline import collision_polygon_inputs as custody
from tools.pipeline import collision_polygon_output as output
from tools.pipeline import collision_polygon_recipe as recipe
from tools.pipeline import prepare_collision_polygon_intermediate as preparer
from tools.pipeline import private_texture_output as writer
from tools.pipeline.collision_polygon_intermediate import verify_collision_polygon_bundle


@pytest.fixture(scope="module")
def own_corpus():
    return corpus()


@pytest.fixture
def configured(tmp_path, own_corpus, monkeypatch):
    config, anchors = inputs(tmp_path.resolve() / "sources", own_corpus)
    # Test-only injection of own document pins; the CLI has no recipe override.
    monkeypatch.setattr(recipe, "ANCHORS", anchors)
    return config


@pytest.fixture(scope="module")
def package():
    path = Path(__file__).parents[1] / "fixtures/synthetic/collision-polygons-intermediate-v1.json"
    cases = json.loads(path.read_bytes())["cases"]
    files = {k: bytes.fromhex(v["wire_hex"]) for k, v in cases[0]["files"].items()}
    manifest = json.loads(files.pop("manifest.json"))
    return files, {k: v for k, v in manifest.items() if k != "files"}


def test_full_recipe_preserves_rows_links_all_results_and_ab(configured, own_corpus, tmp_path):
    before = copy.deepcopy(configured)
    files, report = preparer.prepare_files(configured)
    other, _ = inputs(tmp_path.resolve() / "second", own_corpus, copy_name="copy-b")
    assert preparer.prepare_files(other) == (files, report)
    assert configured == before
    root = json.loads(files["intermediate.json"])
    assert [r["catalog_entry"] for r in root["resources"]] == own_corpus[0]["catalog"]["entries"]
    assert report["counts"] == dict(resources=285, accepted=2, unsupported=282, rejected=1)
    assert len(files) == 288
    slots = [link["slot"] for r in root["resources"] for link in r["scene_links"]]
    assert slots == [2, *range(8, 37)]
    assert b"/unavailable" not in files["intermediate.json"]
    assert b"copy-a" not in files["intermediate.json"]
    for row in root["resources"]:
        assert files[row["source"]["file"]] == own_corpus[1][row["id"][6:] + ".bin"]


@pytest.mark.parametrize("key", ["catalog", "extraction_receipt", "classification_audit"])
@pytest.mark.parametrize("change", ["size", "sha256", "bytes", "relative", "parent", "extra"])
def test_config_pins_paths_and_keys_before_decode(configured, monkeypatch, key, change):
    def forbidden(*args):
        pytest.fail("decoder reached before external checks")

    monkeypatch.setattr(preparer, "make_collision_polygons", forbidden)
    item = configured[key]
    if change == "size":
        item["size"] = True
    elif change == "sha256":
        item["sha256"] = "0" * 64
    elif change == "bytes":
        path = Path(item["path"])
        path.write_bytes(path.read_bytes() + b" ")
    elif change == "relative":
        item["path"] = "relative.json"
    elif change == "parent":
        item["path"] = str(Path(item["path"]).parent / ".." / "x")
    else:
        item["extra"] = "not allowed"
    with pytest.raises((ValueError, OSError)):
        preparer.prepare_files(configured)


@pytest.mark.parametrize(
    "change", ["corrupt", "empty", "oversize", "missing", "symlink", "fifo", "directory"]
)
def test_every_source_verified_before_decode(configured, monkeypatch, change):
    monkeypatch.setattr(
        preparer, "make_collision_polygons", lambda *args: pytest.fail("decoder reached")
    )
    path = sorted(Path(configured["copy_root"]).iterdir())[-1]
    raw = path.read_bytes()
    path.unlink()
    if change == "corrupt":
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    elif change == "empty":
        path.write_bytes(b"")
    elif change == "oversize":
        path.write_bytes(bytes(65537))
    elif change == "symlink":
        path.symlink_to(sorted(path.parent.iterdir())[0])
    elif change == "fifo":
        os.mkfifo(path)
    elif change == "directory":
        path.mkdir()
    with pytest.raises((ValueError, OSError)):
        preparer.prepare_files(configured)


@pytest.mark.parametrize(
    "change", ["root_extra", "copy_relative", "copy_symlink", "parent_symlink", "huge_config"]
)
def test_config_custody(configured, tmp_path, change):
    if change == "root_extra":
        configured["other"] = None
    elif change == "copy_relative":
        configured["copy_root"] = "copy-a"
    elif change == "copy_symlink":
        link = tmp_path / "link"
        link.symlink_to(configured["copy_root"], target_is_directory=True)
        configured["copy_root"] = str(link)
    elif change == "parent_symlink":
        path = Path(configured["catalog"]["path"])
        link = tmp_path / "link"
        link.symlink_to(path.parent, target_is_directory=True)
        configured["catalog"]["path"] = str(link / path.name)
    else:
        configured["other"] = "x" * 32768
    with pytest.raises((ValueError, OSError)):
        preparer.prepare_files(configured)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_catalog",
        "duplicate_receipt",
        "duplicate_audit",
        "duplicate_copy",
        "missing_selected",
        "id_traversal",
        "file_traversal",
        "container",
        "origin",
        "audit_source",
        "copy_hash",
        "copy_count",
        "oracle",
        "copies_disagree",
        "receipt_status",
        "catalog_binding",
        "audit_status",
        "input_pin",
        "slot",
        "resource_link",
        "capture_hash",
        "capture_flag",
        "capture_room",
        "capture_phase",
    ],
)
def test_recipe_metadata_rejects_before_sources(own_corpus, change):
    docs = copy.deepcopy(own_corpus[0])
    cat, receipt, audit = [
        docs[k] for k in ("catalog", "extraction_receipt", "classification_audit")
    ]
    anchors = {k: pin(wire(d)) for k, d in docs.items()}
    if change.startswith("duplicate_"):
        rows = {
            "duplicate_catalog": cat["entries"],
            "duplicate_receipt": receipt["resources"],
            "duplicate_audit": audit["resources"],
            "duplicate_copy": receipt["copies"]["copy-b"],
        }[change]
        rows.append(rows[0])
    elif change == "missing_selected":
        audit["resources"].pop()
    elif change == "id_traversal":
        cat["entries"][0]["id"] = "asset:../../escape"
    elif change == "file_traversal":
        receipt["resources"][0]["file"] = "../escape"
    elif change == "container":
        receipt["resources"][0]["container_offset"] += 1
    elif change == "origin":
        cat["entries"][0]["origin"]["profile_id"] = "other"
    elif change == "audit_source":
        audit["resources"][0]["source_name"] = "other"
    elif change == "copy_hash":
        receipt["copies"]["copy-b"][0]["sha256"] = "0" * 64
    elif change == "copy_count":
        audit["resources"][0]["copies"].pop()
    elif change == "oracle":
        audit["resources"][0]["copies"][0]["oracle_match"] = False
    elif change == "copies_disagree":
        audit["resources"][0]["copies"][1]["view_sha256"] = "0" * 64
    elif change == "receipt_status":
        receipt["status"] = "partial"
    elif change == "catalog_binding":
        receipt["catalog_sha256"] = "0" * 64
    elif change == "audit_status":
        audit["new_vm_execution"] = True
    elif change == "input_pin":
        audit["input_pins"] = []
    else:
        capture = audit["captures"][0]
        if change == "slot":
            capture["slot"] = True
        elif change == "resource_link":
            capture["resource_id"] = audit["resources"][2]["id"]
        elif change == "capture_hash":
            capture["resource_sha256"] = "0" * 64
        elif change == "capture_flag":
            capture["oracle_match"] = 1
        elif change == "capture_room":
            capture["room"] = 0xEB
        else:
            capture["phase"] = "continuous_post_phase"
    with pytest.raises((ValueError, KeyError)):
        recipe.select(docs, anchors)


@pytest.mark.parametrize("key", ["classification", "decoder_error", "view_sha256", "counts"])
def test_changed_decoder_outcome_not_published(configured, monkeypatch, key):
    real = recipe.verify_outcomes

    def changed(files, selected, summary):
        if key == "counts":
            summary["classifications"]["accepted"] = 100
        else:
            selected[next(iter(selected))]["copies"][0][key] = "incorrect"
        return real(files, selected, summary)

    monkeypatch.setattr(recipe, "verify_outcomes", changed)
    with pytest.raises(ValueError):
        preparer.prepare_files(configured)


@pytest.mark.parametrize("change", ["modify", "replace", "parent_replace"])
def test_source_recheck_detects_changes(configured, monkeypatch, change):
    real = preparer.make_collision_polygons
    path = sorted(Path(configured["copy_root"]).iterdir())[0]

    def changed(*args):
        result = real(*args)
        if change == "modify":
            raw = path.read_bytes()
            path.write_bytes(b"x" + raw[1:])
        elif change == "replace":
            raw = path.read_bytes()
            path.unlink()
            path.write_bytes(raw)
        else:
            parent = path.parent
            parent.rename(parent.with_name("detached"))
            parent.mkdir()
            for item in parent.with_name("detached").iterdir():
                os.link(item, parent / item.name)
        return result

    monkeypatch.setattr(preparer, "make_collision_polygons", changed)
    with pytest.raises(ValueError):
        preparer.prepare_files(configured)


def test_read_race_checks_open_named_and_parent_identity(tmp_path, monkeypatch):
    parent = tmp_path.resolve() / "read-race"
    parent.mkdir()
    path = parent / "input"
    path.write_bytes(b"own data")
    real = custody._owned_stream

    @contextmanager
    def stream(fd, mode):
        with real(fd, mode) as original:

            class Proxy:
                def fileno(self):
                    return original.fileno()

                def read(self, limit):
                    raw = original.read(limit)
                    parent.rename(parent.with_name("detached"))
                    parent.mkdir()
                    os.link(parent.with_name("detached") / "input", path)
                    return raw

            yield Proxy()

    monkeypatch.setattr(custody, "_owned_stream", stream)
    with pytest.raises(ValueError):
        custody.read_path(path, 64)


def test_writer_and_directory_reader_are_source_independent(package, tmp_path):
    files, report = package
    root = tmp_path.resolve()
    result = output.write_collision_polygon_bundle(root, Path.cwd(), "complete", files, report)
    destination = root / "complete"
    raw, rebuilt = output.read_collision_polygon_bundle(destination)
    assert rebuilt == files and json.loads(raw) == result
    assert raw == (destination / ".manifest.pending.json").read_bytes()
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in destination.iterdir())
    (destination / ".manifest.pending.json").unlink()
    assert output.read_collision_polygon_bundle(destination) == (raw, files)
    before = {p.name: p.read_bytes() for p in destination.iterdir()}
    with pytest.raises(FileExistsError):
        output.write_collision_polygon_bundle(root, Path.cwd(), "complete", files, report)
    assert before == {p.name: p.read_bytes() for p in destination.iterdir()}


@pytest.mark.parametrize(
    "fault",
    [
        "write",
        "fsync",
        "readback",
        "pending",
        "link",
        "extra",
        "stale_file",
        "replace_file",
        "replace_dir",
        "pending_symlink",
        "existing_file",
        "open",
    ],
)
def test_failed_publication_has_no_final_manifest(package, tmp_path, monkeypatch, fault):
    files, report = package
    root = tmp_path.resolve()
    destination = root / "attempt"
    first = sorted(files)[0]
    real_write, real_sync, real_link = writer.write_all, os.fsync, os.link
    real_hash, real_open = writer.fingerprint_stream, os.open
    triggered = False
    writes = 0

    def write(stream, raw):
        nonlocal triggered, writes
        writes += 1
        if (fault == "write" and writes == 2) or (fault == "pending" and writes == len(files) + 1):
            triggered = True
            stream.write(raw[:2])
            raise OSError(errno.ENOSPC, "own injected write failure")
        real_write(stream, raw)
        if writes == len(files) + 1 and fault in (
            "extra",
            "stale_file",
            "replace_file",
            "replace_dir",
            "pending_symlink",
        ):
            triggered = True
            if fault == "extra":
                (destination / "unexpected").write_bytes(b"own extra")
            elif fault == "stale_file":
                (destination / first).write_bytes(b"x" + files[first][1:])
            elif fault == "replace_file":
                (destination / first).unlink()
                (destination / first).symlink_to(root / "no-source")
            elif fault == "replace_dir":
                destination.rename(root / "detached")
                destination.mkdir()
            else:
                pending = destination / ".manifest.pending.json"
                pending.unlink()
                pending.symlink_to(destination / first)

    def sync(fd):
        nonlocal triggered
        if fault == "fsync" and not triggered:
            triggered = True
            raise OSError(errno.EIO, "own injected sync failure")
        return real_sync(fd)

    def readback(stream, size):
        nonlocal triggered
        result = real_hash(stream, size)
        if fault == "readback" and not triggered:
            triggered = True
            result["sha256"] = "0" * 64
        return result

    def link(*args, **kwargs):
        nonlocal triggered
        if fault == "link":
            triggered = True
            raise OSError(errno.EIO, "own injected commit failure")
        return real_link(*args, **kwargs)

    def open_file(path, flags, *args, **kwargs):
        nonlocal triggered
        if flags & os.O_CREAT and not triggered and fault in ("open", "existing_file"):
            triggered = True
            if fault == "open":
                raise OSError(errno.EIO, "own injected open failure")
            (destination / path).write_bytes(b"preserve me")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(writer, "write_all", write)
    monkeypatch.setattr(writer.os, "fsync", sync)
    monkeypatch.setattr(writer, "fingerprint_stream", readback)
    monkeypatch.setattr(writer.os, "link", link)
    monkeypatch.setattr(writer.os, "open", open_file)
    with pytest.raises((ValueError, OSError)):
        output.write_collision_polygon_bundle(root, Path.cwd(), "attempt", files, report)
    assert triggered
    assert not list(root.rglob("manifest.json"))
    if fault == "existing_file":
        assert (destination / first).read_bytes() == b"preserve me"


def test_concurrent_same_run_has_one_publisher(package, tmp_path):
    files, report = package
    barrier = Barrier(2)

    def publish():
        barrier.wait(timeout=10)
        try:
            output.write_collision_polygon_bundle(
                tmp_path.resolve(), Path.cwd(), "same", files, report
            )
        except FileExistsError:
            return "existing"
        return "published"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish) for _ in range(2)]
        assert sorted(f.result(timeout=20) for f in futures) == ["existing", "published"]
    assert output.read_collision_polygon_bundle(tmp_path.resolve() / "same")[1] == files


@pytest.mark.parametrize(
    "change",
    [
        "extra",
        "missing",
        "hash",
        "auxiliary",
        "aux_symlink",
        "manifest_missing",
        "manifest_symlink",
        "oversize",
        "fifo",
    ],
)
def test_directory_reader_rejects_incomplete_or_modified(package, tmp_path, change):
    files, report = package
    root = tmp_path.resolve()
    output.write_collision_polygon_bundle(root, Path.cwd(), "bundle", files, report)
    path = root / "bundle"
    first = path / sorted(files)[0]
    if change == "extra":
        (path / "extra").write_bytes(b"extra")
    elif change == "missing":
        first.unlink()
    elif change == "hash":
        first.write_bytes(b"x" + first.read_bytes()[1:])
    elif change in ("auxiliary", "aux_symlink"):
        aux = path / ".manifest.pending.json"
        aux.unlink()
        if change == "aux_symlink":
            aux.symlink_to(path / "manifest.json")
        else:
            aux.write_bytes(b"{}")
    elif change in ("manifest_missing", "manifest_symlink"):
        (path / "manifest.json").unlink()
        if change == "manifest_symlink":
            (path / "manifest.json").symlink_to(path / ".manifest.pending.json")
    elif change == "oversize":
        first.write_bytes(bytes(1024 * 1024 + 1))
    else:
        first.unlink()
        os.mkfifo(first)
    with pytest.raises((ValueError, OSError)):
        output.read_collision_polygon_bundle(path)


def test_manifest_and_aggregate_budgets_before_mkdir(package, tmp_path, monkeypatch):
    files, report = package
    for key, limit in (("MANIFEST_LIMIT", 1), ("TOTAL_LIMIT", 1)):
        with monkeypatch.context() as patch:
            patch.setattr(output, key, limit)
            with pytest.raises(ValueError):
                output.write_collision_polygon_bundle(
                    tmp_path.resolve(), Path.cwd(), "bad", files, report
                )
            assert not (tmp_path / "bad").exists()


def test_cli_success_and_sources_rechecked_before_commit(configured, tmp_path, monkeypatch, capsys):
    args = [
        "--inputs",
        str(Path(configured["copy_root"]).parent / "inputs.json"),
        "--private-root",
        str(tmp_path.resolve()),
        "--run-id",
        "ready",
    ]
    real = writer.os.link

    def commit(source, target, **kwargs):
        assert target == "manifest.json"
        path = tmp_path.resolve() / "ready"
        assert not (path / target).exists()
        raw = (path / source).read_bytes()
        files = {p.name: p.read_bytes() for p in path.iterdir() if p.name != source}
        assert verify_collision_polygon_bundle(raw, files) == files
        return real(source, target, **kwargs)

    monkeypatch.setattr(writer.os, "link", commit)
    assert preparer.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "prepared"
    assert preparer.main(args) == 1
    message = capsys.readouterr().out
    assert json.loads(message)["status"] == "rejected"
    assert str(tmp_path) not in message


@pytest.mark.parametrize("changed", ["config", "source"])
def test_cli_rechecks_sources_after_writes(configured, tmp_path, monkeypatch, changed):
    config_path = Path(configured["copy_root"]).parent / "inputs.json"
    source = (
        config_path if changed == "config" else sorted(Path(configured["copy_root"]).iterdir())[0]
    )
    real_write = writer.write_all
    triggered = False

    def write(stream, raw):
        nonlocal triggered
        real_write(stream, raw)
        if not triggered:
            triggered = True
            source.write_bytes(source.read_bytes() + b" ")

    monkeypatch.setattr(writer, "write_all", write)
    assert (
        preparer.main(
            [
                "--inputs",
                str(config_path),
                "--private-root",
                str(tmp_path.resolve()),
                "--run-id",
                "stale",
            ]
        )
        == 1
    )
    assert triggered
    assert not (tmp_path / "stale" / "manifest.json").exists()


def test_repeat_read_and_named_replacement(tmp_path, monkeypatch):
    path = tmp_path.resolve() / "repeat"
    path.write_bytes(b"own source")
    guard = custody.PinnedInputs()
    expected = pin(path.read_bytes())
    assert guard.read(path, 100, expected) == guard.read(path, 100, expected)
    real = custody._owned_stream

    @contextmanager
    def stream(fd, mode):
        with real(fd, mode) as original:

            class Proxy:
                def fileno(self):
                    return original.fileno()

                def read(self, limit):
                    raw = original.read(limit)
                    path.unlink()
                    path.write_bytes(raw)
                    return raw

            yield Proxy()

    monkeypatch.setattr(custody, "_owned_stream", stream)
    with pytest.raises(ValueError):
        guard.read(path, 100, expected)


@pytest.mark.parametrize("change", ["repo", "run", "root_symlink", "unsafe_name", "bad_report"])
def test_writer_rejects_destination_and_inventory_before_writing(package, tmp_path, change):
    files, report = copy.deepcopy(package)
    root, repository, run = tmp_path.resolve(), Path.cwd(), "bad"
    if change == "repo":
        repository = root
    elif change == "run":
        run = "../bad"
    elif change == "root_symlink":
        link = root / "link"
        link.symlink_to(root, target_is_directory=True)
        root = link
    elif change == "unsafe_name":
        files["../escape"] = b"own input"
    else:
        report["scene_link_rechecked"] = True
    with pytest.raises((OSError, ValueError)):
        output.write_collision_polygon_bundle(root, repository, run, files, report)
    assert not list(tmp_path.rglob("manifest.json"))


@pytest.mark.parametrize(
    "change", ["count", "total", "manifest_size", "entry_after_read", "directory_after_read"]
)
def test_reader_budgets_and_snapshot_consistency(package, tmp_path, monkeypatch, change):
    files, report = package
    root = tmp_path.resolve()
    output.write_collision_polygon_bundle(root, Path.cwd(), "reader", files, report)
    path = root / "reader"
    if change == "count":
        for i in range(572):
            (path / f"extra-{i}").write_bytes(b"x")
    elif change == "total":
        with (path / "large").open("wb") as stream:
            stream.truncate(40 * 1024 * 1024 + 1)
    elif change == "manifest_size":
        (path / "manifest.json").write_bytes(bytes(256 * 1024 + 1))
    else:
        real = output.verify_collision_polygon_bundle

        def changed(*args):
            result = real(*args)
            if change == "entry_after_read":
                entry = path / sorted(files)[0]
                raw = entry.read_bytes()
                entry.unlink()
                entry.write_bytes(raw)
            else:
                path.rename(root / "detached-reader")
                path.mkdir()
            return result

        monkeypatch.setattr(output, "verify_collision_polygon_bundle", changed)
    with pytest.raises((ValueError, OSError)):
        output.read_collision_polygon_bundle(path)


def test_reader_reapplies_aggregate_budget_before_allocating_grown_file(
    package, tmp_path, monkeypatch
):
    files, report = package
    root = tmp_path.resolve()
    output.write_collision_polygon_bundle(root, Path.cwd(), "growth", files, report)
    path = root / "growth"
    real_read = output.read_at
    first, last = sorted(files)[0], sorted(files)[-1]
    triggered = False

    def read(directory, name, limit):
        nonlocal triggered
        if name == first:
            triggered = True
            (path / last).write_bytes(files[last] + b"x")
        if name == last:
            assert limit == len(files[last])
        return real_read(directory, name, limit)

    monkeypatch.setattr(output, "read_at", read)
    monkeypatch.setattr(output, "TOTAL_LIMIT", sum(map(len, files.values())))
    monkeypatch.setattr(
        output, "verify_collision_polygon_bundle", lambda *args: pytest.fail("allocated excess")
    )
    with pytest.raises(ValueError):
        output.read_collision_polygon_bundle(path)
    assert triggered


@pytest.mark.parametrize("optimized", [False, True])
def test_subprocess_pipeline_and_source_free_read(configured, tmp_path, optimized):
    # Pins are replaced only inside this synthetic test process, never by CLI options.
    script = """
import json, pathlib, runpy, sys
from tools.pipeline import collision_polygon_recipe as recipe
from tools.pipeline import prepare_collision_polygon_intermediate as prepare
from tools.pipeline.collision_polygon_output import read_collision_polygon_bundle
config_path, root = map(pathlib.Path, sys.argv[1:])
config = json.loads(config_path.read_bytes())
recipe.ANCHORS = {k:{f:config[k][f] for f in ('size','sha256')} for k in recipe.ANCHORS}
manifest = prepare.prepare_and_write(config_path, root, pathlib.Path.cwd(), 'subprocess')
raw, before = read_collision_polygon_bundle(root/'subprocess')
config_path.parent.rename(root/'detached-sources')
if read_collision_polygon_bundle(root/'subprocess') != (raw,before):
    raise RuntimeError('source-free rebuild differs')
if manifest['counts'] != dict(resources=285,accepted=2,unsupported=282,rejected=1):
    raise RuntimeError('counts differ')
# Exercise the actual __main__ rejection route; it must emit no original path.
sys.argv = ['prepare', '--inputs', str(config_path), '--private-root', str(root),
            '--run-id', 'absent']
sys.modules.pop('tools.pipeline.prepare_collision_polygon_intermediate')
try:
    runpy.run_module('tools.pipeline.prepare_collision_polygon_intermediate', run_name='__main__')
except SystemExit as error:
    if error.code != 1: raise
else:
    raise RuntimeError('missing inputs accepted')
if (root/'absent').exists(): raise RuntimeError('partial output from missing config')
print('source-free-pass')
"""
    command = [
        sys.executable,
        *(["-O"] if optimized else []),
        "-c",
        script,
        str(Path(configured["copy_root"]).parent / "inputs.json"),
        str(tmp_path.resolve()),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    assert result.stdout.splitlines()[-1] == "source-free-pass"
    assert str(tmp_path) not in result.stdout + result.stderr
