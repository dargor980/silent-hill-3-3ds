"""IR-T7e: independent source oracle, controlled faults and publication boundaries."""

import ast
import copy
import errno
import json
import os
import struct
import subprocess
import sys
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Barrier

import pytest
from test_collision_intermediate import corpus as corpus
from test_collision_intermediate import fingerprint, input_config
from test_collision_intermediate import inputs as inputs
from test_collision_intermediate import package as package

from tests import collision_wire_oracle as oracle
from tools.pipeline import collision_intermediate as intermediate
from tools.pipeline import inspection_inputs
from tools.pipeline import prepare_collision_intermediate as preparer
from tools.pipeline import private_texture_output as writer
from tools.pipeline.intermediate_json import decode_json, encode_json
from tools.pipeline.profile import ProfileError


@pytest.fixture(scope="module")
def prepared(inputs):
    return preparer.prepare_files(inputs)


def test_independent_origin_bytes_documents_receipts_and_cpu(prepared, corpus):
    files, report = prepared
    requested = []

    def read(name):
        requested.append(name)
        return corpus[-1][name]

    assert oracle.compare_sources(files, read) == dict(
        captures=30,
        blocks=240,
        raw_bytes=1571670,
        files=242,
        source_reports=3,
        source_receipts=30,
        source_states=30,
    )
    assert len(requested) == len(set(requested)) == 64
    assert report["state"] == "observed_registry"


def test_oracle_is_independent_and_uses_only_stdlib():
    tree = ast.parse(Path(oracle.__file__).read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.partition(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imports.add(node.module.partition(".")[0])
        assert not isinstance(node, ast.Call) or not (
            isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "__import__")
        )
    assert imports <= {"hashlib", "json", "math", "zipfile", "io"}


def test_common_decoder_fault_is_detected(package, corpus, monkeypatch):
    original = intermediate.decode_registry

    def corrupt(ranges):
        result = original(ranges)
        result["actors"][-1]["status"] ^= 1  # No reference target points to this actor.
        return result

    monkeypatch.setattr(intermediate, "decode_registry", corrupt)
    root = decode_json(package["intermediate.json"])
    for capture in root["captures"]:
        capture["observations"]["actors"][-1]["status"] ^= 1
    # Import and export agree on the injected bug; the independent oracle must not.
    faulty = intermediate.export_collision(encode_json(root), corpus[3])
    assert intermediate.export_collision(faulty["intermediate.json"], corpus[3]) == faulty
    with pytest.raises(AssertionError, match="JSON value"):
        oracle.inspect_package(faulty)


@pytest.mark.parametrize(
    "loss",
    [
        "inactive_actor",
        "inactive_character",
        "event_storage",
        "unknown_document",
        "unknown_receipt",
    ],
)
def test_rehashed_loss_is_detected_against_original_sources(package, corpus, loss):
    root, blobs = decode_json(package["intermediate.json"]), dict(corpus[3])
    if loss in ("unknown_document", "unknown_receipt"):
        if loss == "unknown_document":
            del root["documents"]["collision_reference"]["unknown"]
        else:
            del root["captures"][0]["receipt"]["opaque"]
    else:
        name, offset = {
            "inactive_actor": ("actors.bin", -1),
            "inactive_character": ("character.bin", 0x2300),
            "event_storage": ("events.bin", 0),
        }[loss]
        filename = "capture-02-" + name
        raw = bytearray(blobs[filename])
        raw[offset] ^= 1
        blobs[filename] = bytes(raw)
        next(e for e in root["captures"][0]["ranges"] if e["file"] == filename)["sha256"] = (
            fingerprint(bytes(raw))["sha256"]
        )
    altered = intermediate.export_collision(encode_json(root), blobs)
    oracle.inspect_package(altered)  # Local consistency cannot authenticate source history.
    with pytest.raises(AssertionError):
        oracle.compare_sources(altered, corpus[-1].__getitem__)


@pytest.mark.parametrize(
    "mutation",
    [
        "view",
        "type",
        "negative_zero",
        "manifest_hash",
        "manifest_claim",
        "extra",
        "short",
        "duplicate_json",
    ],
)
def test_oracle_negative_controls(package, prepared, corpus, mutation):
    files = dict(package)
    report = copy.deepcopy(prepared[1])
    report["files"] = [dict(file=k, **fingerprint(v)) for k, v in sorted(files.items())]
    if mutation == "view":
        view = decode_json(files["collision-observations.json"])
        view["captures"][0]["observations"]["character"]["selector"] = 0
        files["collision-observations.json"] = encode_json(view)
    elif mutation in ("type", "negative_zero"):
        root = decode_json(files["intermediate.json"])
        root["documents"]["collision_reference"]["unknown"][
            "negative_zero" if mutation == "negative_zero" else "flag"
        ] = 0.0 if mutation == "negative_zero" else 1
        files["intermediate.json"] = encode_json(root)
        with pytest.raises(AssertionError, match="JSON (float|type)"):
            oracle.compare_sources(files, corpus[-1].__getitem__)
        return
    elif mutation == "manifest_hash":
        report["files"][0]["sha256"] = "0" * 64
    elif mutation == "manifest_claim":
        report["collision_response_verified"] = True
    elif mutation == "extra":
        files["unexpected"] = b"x"
    elif mutation == "short":
        files["capture-02-actors.bin"] = files["capture-02-actors.bin"][:-1]
    else:
        files["intermediate.json"] = b'{"schema_version":1,' + files["intermediate.json"][1:]
    with pytest.raises(AssertionError):
        oracle.inspect_package(files, report)


def test_standalone_oracle_remains_effective_under_optimized_python(tmp_path, package):
    directory = tmp_path / "package"
    directory.mkdir()
    for name, raw in package.items():
        (directory / name).write_bytes(raw)
    code = """
import sys
from pathlib import Path
from tests.collision_wire_oracle import inspect_package
files={p.name:p.read_bytes() for p in Path(sys.argv[1]).iterdir()}
inspect_package(files)
files['capture-02-actors.bin']=b'x'
try:
    inspect_package(files)
except AssertionError:
    print('independent checks active')
else:
    raise SystemExit(3)
"""
    result = subprocess.run(
        [sys.executable, "-O", "-c", code, str(directory)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and result.stderr == ""
    assert result.stdout.strip() == "independent checks active"


@pytest.mark.parametrize(
    "variant", ["empty", "short", "same_size_change", "directory", "fifo", "symlink", "oversized"]
)
def test_pinned_source_io_failures_do_not_publish(inputs, tmp_path, monkeypatch, capsys, variant):
    config = copy.deepcopy(inputs)
    original = Path(config["captures"][0]["state"]["path"])
    bad = tmp_path / "state.p2s"
    if variant == "directory":
        bad.mkdir()
    elif variant == "fifo":
        os.mkfifo(bad)
    elif variant == "symlink":
        bad.symlink_to(original)
    elif variant == "oversized":
        with bad.open("wb") as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
    else:
        raw = original.read_bytes()
        bad.write_bytes(
            b""
            if variant == "empty"
            else raw[:-1]
            if variant == "short"
            else raw[:-1] + bytes([raw[-1] ^ 1])
        )
    config["captures"][0]["state"]["path"] = str(bad)
    config_path = tmp_path / "inputs.json"
    config_path.write_bytes(encode_json(config))
    monkeypatch.setattr(
        preparer,
        "write_collision_intermediate_bundle",
        lambda *a: pytest.fail("Invalid input reached publication"),
    )
    assert (
        preparer.main(
            ["--inputs", str(config_path), "--private-root", str(tmp_path), "--run-id", "rejected"]
        )
        == 1
    )
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "rejected" and set(output) == {"status", "error_type"}
    assert not (tmp_path / "rejected").exists()


def repin_state(inputs, directory, raw):
    config = copy.deepcopy(inputs)
    state = directory / "state.p2s"
    state.write_bytes(raw)
    config["captures"][0]["state"] = dict(path=str(state), **fingerprint(raw))
    inventory = json.loads(Path(config["inventory"]["path"]).read_bytes())
    inventory["samples"][0].update(state_size=len(raw), state_sha256=fingerprint(raw)["sha256"])
    raw_inventory = encode_json(inventory)
    inventory_path = directory / "inventory.json"
    inventory_path.write_bytes(raw_inventory)
    config["inventory"] = dict(path=str(inventory_path), **fingerprint(raw_inventory))
    return config


@pytest.mark.parametrize(
    "variant",
    [
        "missing_ram",
        "duplicate_ram",
        "zip_tail",
        "broken_deflate",
        "encrypted",
        "oversized_internals",
        "zip64",
    ],
)
def test_container_failures_after_repinning_still_reject(inputs, tmp_path, monkeypatch, variant):
    raw = Path(inputs["captures"][0]["state"]["path"]).read_bytes()
    with zipfile.ZipFile(BytesIO(raw)) as z:
        members = [(n, z.read(n)) for n in z.namelist()]
    if variant == "zip_tail":
        raw += b"x"
    elif variant == "broken_deflate":
        data = bytearray(raw)
        offset = 30 + int.from_bytes(data[26:28], "little")
        data[offset] ^= 255
        raw = bytes(data)
    elif variant == "encrypted":
        data = bytearray(raw)
        struct.pack_into("<H", data, 6, 1)
        raw = bytes(data)
    else:
        stream = BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, value in members:
                if variant == "missing_ram" and name == "eeMemory.bin":
                    continue
                if variant == "oversized_internals" and name == "PCSX2 Internal Structures.dat":
                    value = bytes(4 * 1024 * 1024 + 1)
                if variant == "zip64":
                    with z.open(name, "w", force_zip64=True) as out:
                        out.write(value)
                else:
                    z.writestr(name, value)
            if variant == "duplicate_ram":
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    z.writestr("eeMemory.bin", b"duplicate")
        raw = stream.getvalue()
    config = repin_state(inputs, tmp_path, raw)
    monkeypatch.setattr(
        preparer, "make_collision", lambda *a: pytest.fail("Invalid state reached codec")
    )
    with pytest.raises(ValueError):
        preparer.prepare_files(config)


@pytest.mark.parametrize(
    "raw",
    [
        b"{",
        b'{"reports":{},"reports":{}}',
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b"[]",
        b"null",
        b" " * 32769,
    ],
)
def test_cli_json_rejections(raw, tmp_path, capsys):
    config = tmp_path / "config.json"
    config.write_bytes(raw)
    assert (
        preparer.main(
            ["--inputs", str(config), "--private-root", str(tmp_path), "--run-id", "bad-json"]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"
    assert not (tmp_path / "bad-json").exists()


@pytest.mark.parametrize(
    "fault",
    [
        "open",
        "write",
        "fsync",
        "readback",
        "extra_entry",
        "rename",
        "pending",
        "link",
        "existing_file",
    ],
)
def test_publication_faults_never_commit_manifest(prepared, tmp_path, monkeypatch, fault):
    files, report = prepared
    root = tmp_path / "private"
    root.mkdir()
    destination = root / "attempt"
    saved = root / "detached"
    real_open, real_write, real_fsync, real_hash, real_link = (
        os.open,
        writer.write_all,
        os.fsync,
        writer.fingerprint_stream,
        os.link,
    )
    written, triggered = 0, False

    def open_file(path, flags, *args, **kwargs):
        nonlocal triggered
        if flags & os.O_CREAT and not triggered and fault in ("open", "existing_file"):
            triggered = True
            if fault == "open":
                raise OSError(errno.EIO, "own injected open failure")
            (destination / str(path)).write_bytes(b"existing own file")
        return real_open(path, flags, *args, **kwargs)

    def write(stream, data):
        nonlocal written, triggered
        written += 1
        if fault == "write" and written == 3:
            triggered = True
            stream.write(data[:2])
            raise OSError(errno.ENOSPC, "own injected capacity failure")
        if fault == "pending" and written == 243:
            triggered = True
            raise OSError(errno.EIO, "own injected manifest failure")
        return real_write(stream, data)

    def sync(fd):
        nonlocal triggered
        if fault == "fsync" and not triggered:
            triggered = True
            raise OSError(errno.EIO, "own injected sync failure")
        return real_fsync(fd)

    def reread(stream, size):
        nonlocal triggered
        result = real_hash(stream, size)
        if not triggered:
            if fault == "readback":
                triggered = True
                result["sha256"] = "0" * 64
            elif fault == "extra_entry":
                triggered = True
                (destination / "unexpected").write_bytes(b"own extra file")
            elif fault == "rename":
                triggered = True
                destination.rename(saved)
                destination.mkdir()
        return result

    def link(*args, **kwargs):
        nonlocal triggered
        if fault == "link":
            triggered = True
            raise OSError(errno.EIO, "own injected link failure")
        return real_link(*args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(writer.os, "open", open_file)
        m.setattr(writer, "write_all", write)
        m.setattr(writer.os, "fsync", sync)
        m.setattr(writer, "fingerprint_stream", reread)
        m.setattr(writer.os, "link", link)
        with pytest.raises((OSError, ProfileError)):
            writer.write_collision_intermediate_bundle(root, Path.cwd(), "attempt", files, report)
    assert triggered
    assert not list(root.rglob("manifest.json"))
    if fault == "existing_file":
        assert (destination / sorted(files)[0]).read_bytes() == b"existing own file"
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(FileExistsError):
        writer.write_collision_intermediate_bundle(root, Path.cwd(), "attempt", files, report)
    assert before == {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def test_manifest_published_only_after_all_content_is_read_back(prepared, tmp_path, monkeypatch):
    files, report = prepared
    destination = tmp_path / "complete"
    real_link, real_hash = os.link, writer.fingerprint_stream
    hashes = []

    def reread(stream, size):
        result = real_hash(stream, size)
        hashes.append(result["sha256"])
        return result

    def publish(source, target, **kwargs):
        assert source == ".manifest.pending.json" and target == "manifest.json"
        assert len(hashes) == 243
        assert not (destination / "manifest.json").exists()
        disk_files = {k: (destination / k).read_bytes() for k in files}
        pending = json.loads((destination / source).read_bytes())
        oracle.inspect_package(disk_files, pending)
        assert disk_files == files
        return real_link(source, target, **kwargs)

    monkeypatch.setattr(writer, "fingerprint_stream", reread)
    monkeypatch.setattr(writer.os, "link", publish)
    writer.write_collision_intermediate_bundle(tmp_path, Path.cwd(), "complete", files, report)
    assert (destination / "manifest.json").read_bytes() == (
        destination / ".manifest.pending.json"
    ).read_bytes()


def test_concurrent_same_id_has_exactly_one_publisher(prepared, tmp_path):
    files, report = prepared
    barrier = Barrier(2)

    def publish():
        barrier.wait(timeout=10)
        try:
            writer.write_collision_intermediate_bundle(
                tmp_path, Path.cwd(), "concurrent", files, report
            )
        except FileExistsError:
            return "existing"
        return "published"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish) for _ in range(2)]
        assert sorted(f.result(timeout=20) for f in futures) == ["existing", "published"]
    directory = tmp_path / "concurrent"
    oracle.inspect_package(
        {k: (directory / k).read_bytes() for k in files},
        json.loads((directory / "manifest.json").read_bytes()),
    )


def test_source_free_rebuild_and_independent_check_after_removal(tmp_path, corpus, monkeypatch):
    config = input_config(tmp_path / "sources", corpus)
    files, report = preparer.prepare_files(config)
    writer.write_collision_intermediate_bundle(tmp_path, Path.cwd(), "kept", files, report)
    # Detach sources so all configured paths disappear; the source-free APIs must do no reads.
    (tmp_path / "sources").rename(tmp_path / "inaccessible-sources")
    directory = tmp_path / "kept"
    raw = (directory / "intermediate.json").read_bytes()
    blobs = {k: (directory / k).read_bytes() for k in intermediate.BLOB_NAMES}
    monkeypatch.setattr(
        inspection_inputs,
        "bounded_read",
        lambda *a: pytest.fail("Source I/O during reconstruction"),
    )
    rebuilt = intermediate.export_collision(raw, blobs)
    assert rebuilt == files
    oracle.inspect_package(rebuilt, json.loads((directory / "manifest.json").read_bytes()))


def test_ci_gates_all_collision_modules_and_lints_independent_oracle():
    workflow = Path(".github/workflows/ci.yml").read_text()
    lines = workflow.splitlines()
    gates = [
        line
        for line in lines
        if "tools.qa.coverage_gate build/python-coverage.json --files" in line
        and "tools/pipeline/collision_registry.py" in line
    ]
    assert len(gates) == 1
    assert set(gates[0].split("--files", 1)[1].split()) == {
        "tools/pipeline/collision_registry.py",
        "tools/pipeline/collision_evidence.py",
        "tools/pipeline/collision_intermediate.py",
        "tools/pipeline/prepare_collision_intermediate.py",
        "tools/pipeline/decoders/ps2_cld_polygons.py",
        "tools/pipeline/collision_polygon_intermediate.py",
        "tools/pipeline/collision_polygon_inputs.py",
        "tools/pipeline/collision_polygon_recipe.py",
        "tools/pipeline/collision_polygon_output.py",
        "tools/pipeline/prepare_collision_polygon_intermediate.py",
    }
    for command in ("ruff check", "ruff format --check"):
        for helper in (
            "tests/collision_wire_oracle.py",
            "tests/cld_polygon_wire_oracle.py",
            "tests/cld_polygon_fixtures.py",
            "tests/collision_polygon_recipe_fixtures.py",
            "tests/collision_polygon_package_fixtures.py",
            "tests/collision_polygon_package_oracle.py",
        ):
            assert any(command in line and helper in line for line in lines)
