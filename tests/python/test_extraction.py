"""X01-X11: synthetic export, filesystem custody and injected failures."""

import errno
import hashlib
import json
import os
from contextlib import contextmanager
from importlib.metadata import version
from io import BytesIO
from types import SimpleNamespace

import pytest
from test_asset_catalog import catalog_source as catalog_source

from tools.inspectors.asset_catalog import collect_assets
from tools.inspectors.asset_selection import load_selection
from tools.pipeline import extract_assets as extract
from tools.pipeline import private_output, transfer
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.private_output import PrivateOutput, required_space, resource_filename
from tools.pipeline.profile import ProfileError
from tools.pipeline.verify import load_profile


@pytest.fixture
def inputs(catalog_source, tmp_path):
    iso, profile_path, selection_path = catalog_source
    digest = hashlib.sha256(iso.read_bytes()).hexdigest()
    profile, selection = load_profile(profile_path), load_selection(selection_path)
    with IsoImage(iso) as source:
        catalog = collect_assets(source, profile, iso.stat().st_size, digest, selection)
    catalog["tool"]["pycdlib"] = version("pycdlib")
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog))
    root, repository = tmp_path.resolve() / "private", tmp_path.resolve() / "checkout"
    root.mkdir()
    repository.mkdir()
    return SimpleNamespace(
        iso=iso,
        profile=profile,
        selection=selection,
        image_hash=digest,
        profile_path=profile_path,
        selection_path=selection_path,
        catalog=catalog,
        catalog_path=catalog_path,
        catalog_hash=hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        root=root,
        repository=repository,
    )


def run(inputs, *, name="run", image_factory=IsoImage):
    with PrivateOutput(inputs.root, inputs.repository, name) as output:
        return extract.extract_pair(
            inputs.iso,
            inputs.profile,
            inputs.image_hash,
            inputs.selection,
            inputs.catalog,
            inputs.catalog_hash,
            output,
            image_factory=image_factory,
        )


def args(inputs, name="run"):
    pairs = {
        "iso": inputs.iso,
        "profile": inputs.profile_path,
        "selection": inputs.selection_path,
        "image-sha256": inputs.image_hash,
        "catalog": inputs.catalog_path,
        "catalog-sha256": inputs.catalog_hash,
        "private-root": inputs.root,
        "run-id": name,
    }
    return [part for name, value in pairs.items() for part in ("--" + name, str(value))]


def assert_failed(inputs, code):
    session = inputs.root / "run"
    assert not (session / "verified.json").exists()
    receipt = json.loads((session / "failed.json").read_text())
    assert receipt["status"] == "failed" and receipt["code"] == code


def test_two_independent_copies_match_raw_iso_and_repeat_session(inputs):
    opened = []

    class CountedImage(IsoImage):
        def __enter__(self):
            opened.append(self)
            return super().__enter__()

    original = inputs.iso.read_bytes()
    result = run(inputs, image_factory=CountedImage)
    assert len(opened) == 2 and opened[0] is not opened[1]
    assert result["status"] == "verified" and result["capabilities"] == []
    assert result["summary"]["entry_count"] == 5
    assert len(result["exclusions"]["containers"]) == 1
    assert len(result["exclusions"]["outside_scope_ids"]) == 3
    assert result["copies"]["copy-a"] == result["copies"]["copy-b"]
    for copy in ("copy-a", "copy-b"):
        for item in inputs.catalog["entries"]:
            path = inputs.root / "run" / copy / resource_filename(item["id"])
            assert (
                path.read_bytes()
                == original[item["iso_offset"] : item["iso_offset"] + item["size"]]
            )
            assert path.stat().st_mode & 0o777 == 0o600
        assert (inputs.root / "run" / copy).stat().st_mode & 0o777 == 0o700
    assert run(inputs, name="repeat") == result
    assert (inputs.root / "run/verified.json").read_bytes() == (
        inputs.root / "repeat/verified.json"
    ).read_bytes()
    assert inputs.iso.read_bytes() == original
    assert b"own/same" not in (inputs.root / "run/verified.json").read_bytes()


def test_cli_success_and_existing_session_preserved(inputs, capsys):
    assert extract.main(args(inputs)) == 0
    assert json.loads(capsys.readouterr().out)["copies"] == 2
    before = (inputs.root / "run/verified.json").read_bytes()
    assert extract.main(args(inputs)) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "OUTPUT_EXISTS"
    assert (inputs.root / "run/verified.json").read_bytes() == before


@pytest.mark.parametrize(
    "change", ["id", "offset", "hash", "size", "boolean", "extra", "missing", "version", "unknown"]
)
def test_changed_catalog_rejected_even_if_file_hash_is_updated(inputs, change):
    entry = inputs.catalog["entries"][0]
    if change == "id":
        entry["id"] = "asset:" + "0" * 64
    elif change == "offset":
        entry["container_offset"] += 1
    elif change == "hash":
        entry["sha256"] = "0" * 64
    elif change == "size":
        entry["size"] += 1
    elif change == "boolean":
        inputs.catalog["schema_version"] = True
    elif change == "extra":
        inputs.catalog["entries"].append(dict(entry))
    elif change == "missing":
        inputs.catalog["entries"].pop()
    elif change == "version":
        inputs.catalog["tool"]["pycdlib"] = "other"
    elif change == "unknown":
        inputs.catalog["summary"]["unknown_container_count"] = 0
    with pytest.raises(ProfileError, match="Catalog differs"):
        run(inputs)
    assert list(inputs.root.iterdir()) == []


@pytest.mark.parametrize(
    "raw", [b"[]", b"null", b"{", b'{"a":1,"a":2}', b'{"x":NaN}', b"\xff", b"[" * 2000]
)
def test_catalog_load_rejects_invalid_json(tmp_path, raw):
    path = tmp_path / "catalog.json"
    path.write_bytes(raw)
    with pytest.raises(ProfileError):
        extract.load_catalog(path, hashlib.sha256(raw).hexdigest())


def test_catalog_load_hash_limit_and_missing(inputs, monkeypatch):
    with pytest.raises(ProfileError) as caught:
        extract.load_catalog(inputs.catalog_path, "b" * 64)
    assert caught.value.code == "CATALOG_HASH_MISMATCH"
    monkeypatch.setattr(extract, "MAX_CATALOG_BYTES", 10)
    with pytest.raises(ProfileError) as caught:
        extract.load_catalog(inputs.catalog_path, inputs.catalog_hash)
    assert caught.value.code == "INVALID_CATALOG"
    with pytest.raises(ProfileError):
        extract.load_catalog(inputs.root / "missing", inputs.catalog_hash)


@pytest.mark.parametrize("change", ["image", "profile", "selection", "catalog", "root"])
def test_cli_bad_inputs_rejected_before_output(inputs, capsys, change):
    if change == "image":
        inputs.iso.write_bytes(b"not an iso")
    if change == "profile":
        inputs.profile_path.write_text("{}")
    if change == "selection":
        inputs.selection_path.write_text("{}")
    if change == "catalog":
        inputs.catalog_path.write_text("{}")
    if change == "root":
        inputs.root.rmdir()
    assert extract.main(args(inputs)) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"
    assert not (inputs.root / "run").exists()


def test_image_hash_mismatch_before_session(inputs):
    inputs.image_hash = "0" * 64
    with pytest.raises(ProfileError) as caught:
        run(inputs)
    assert caught.value.code == "IMAGE_MISMATCH"
    assert list(inputs.root.iterdir()) == []


@pytest.mark.parametrize("name", ["", "../escape", "/absolute", "a/b", "A", "a" * 65])
def test_bad_session_names(inputs, name):
    with pytest.raises(ProfileError):
        PrivateOutput(inputs.root, inputs.repository, name)


@pytest.mark.parametrize("relationship", ["same", "ancestor", "child"])
def test_private_root_cannot_be_related_to_repository(inputs, relationship):
    root = {
        "same": inputs.repository,
        "ancestor": inputs.repository.parent,
        "child": inputs.repository / "sub",
    }[relationship]
    with pytest.raises(ProfileError) as caught:
        PrivateOutput(root, inputs.repository, "run")
    assert caught.value.code == "PRIVATE_DATA_IN_REPO"


@pytest.mark.parametrize("kind", ["root", "parent", "traversal", "relative", "file", "missing"])
def test_root_must_be_absolute_existing_directory_without_links(inputs, kind):
    parent = inputs.root.parent
    if kind == "root":
        path = parent / "link"
        path.symlink_to(inputs.root, target_is_directory=True)
    elif kind == "parent":
        (parent / "link").symlink_to(parent, target_is_directory=True)
        path = parent / "link/private"
    elif kind == "traversal":
        path = inputs.root / "../private"
    elif kind == "relative":
        path = type(inputs.root)("relative-private")
    elif kind == "file":
        path = inputs.iso
    else:
        path = parent / "missing"
    with pytest.raises((OSError, ProfileError)):
        with PrivateOutput(path, inputs.repository, "run"):
            pytest.fail("Invalid root accepted")


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_existing_session_never_overwritten(inputs, kind):
    path = inputs.root / "run"
    if kind == "directory":
        path.mkdir()
    elif kind == "file":
        path.write_text("keep")
    else:
        path.symlink_to(inputs.iso)
    with pytest.raises(ProfileError) as caught:
        run(inputs)
    assert caught.value.code == "OUTPUT_EXISTS"
    assert path.exists()


def test_budget_and_insufficient_space(inputs, monkeypatch):
    assert required_space(1562367840, 1740) == 3465717408
    monkeypatch.setattr(os, "fstatvfs", lambda fd: SimpleNamespace(f_bavail=1, f_frsize=4096))
    with pytest.raises(ProfileError) as caught:
        run(inputs)
    assert caught.value.code == "INSUFFICIENT_SPACE"
    assert list(inputs.root.iterdir()) == []


@pytest.mark.parametrize("total,count", [(-1, 1), (True, 1), (0, 0), (0, True), (0, -1)])
def test_invalid_budgets(total, count):
    with pytest.raises(ProfileError):
        required_space(total, count)


@pytest.mark.parametrize("identity", ["../escape", "asset:" + "A" * 64, "asset:" + "f" * 63, None])
def test_output_id_is_not_a_path(identity):
    with pytest.raises(ProfileError):
        resource_filename(identity)


def test_stream_transfer_short_reads_short_writes_and_no_neighbor_bytes():
    class ShortReader(BytesIO):
        def read(self, length):
            return super().read(min(length, 3))

    class ShortWriter(BytesIO):
        def write(self, data):
            return super().write(data[:2])

    source, target = ShortReader(b"own-data-neighbor"), ShortWriter()
    assert transfer.copy_exact(source, target, 8) == (8, hashlib.sha256(b"own-data").hexdigest())
    assert source.tell() == 8 and target.getvalue() == b"own-data"
    assert transfer.copy_exact(source, target, 0) == (0, hashlib.sha256(b"").hexdigest())
    assert source.tell() == 8


def test_stream_transfer_chunk_budget(monkeypatch):
    class Reader(BytesIO):
        def read(self, length):
            assert length <= 1024 * 1024
            return super().read(length)

    raw = b"x" * (1024 * 1024 + 3)
    target = BytesIO()
    assert transfer.copy_exact(Reader(raw + b"next"), target, len(raw))[0] == len(raw)
    assert target.getvalue() == raw


@pytest.mark.parametrize("length", [-1, True, 1.5, 1 << 63])
def test_stream_transfer_invalid_size(length):
    with pytest.raises(ProfileError):
        transfer.copy_exact(BytesIO(), BytesIO(), length)


@pytest.mark.parametrize("data", [b"", b"too-long", None])
def test_stream_transfer_invalid_read(data):
    with pytest.raises(ProfileError):
        transfer.copy_exact(SimpleNamespace(read=lambda limit: data), BytesIO(), 4)


@pytest.mark.parametrize("written", [None, 0, -1, 5, True])
def test_stream_transfer_invalid_write_progress(written):
    with pytest.raises(ProfileError):
        transfer.copy_exact(BytesIO(b"abcd"), SimpleNamespace(write=lambda data: written), 4)


@pytest.mark.parametrize("failure_at", [1, 3, 6, 10])
def test_copy_io_failure_retains_partial_but_never_verifies_pair(inputs, monkeypatch, failure_at):
    original, calls = IsoImage.copy_range, 0

    def failing(self, path, offset, length, target):
        nonlocal calls
        calls += 1
        if calls == failure_at:
            target.write(b"partial")
            raise OSError(errno.ENOSPC, "synthetic full disk")
        return original(self, path, offset, length, target)

    monkeypatch.setattr(IsoImage, "copy_range", failing)
    with pytest.raises(ProfileError):
        run(inputs)
    assert_failed(inputs, "OUTPUT_IO_ERROR")
    assert any((inputs.root / "run/copy-a").iterdir())


@pytest.mark.parametrize("returned", [(0, "0" * 64), (True, "0" * 64)])
def test_copy_port_contract_mismatch(inputs, monkeypatch, returned):
    monkeypatch.setattr(IsoImage, "copy_range", lambda *args: returned)
    with pytest.raises(ProfileError):
        run(inputs)
    assert_failed(inputs, "COPY_HASH_MISMATCH")


def test_closed_source_stability_required_before_copy_receipt(inputs):
    class Unstable(IsoImage):
        def __exit__(self, *args):
            stat = self.path.stat()
            os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000))
            return super().__exit__(*args)

    with pytest.raises(ProfileError):
        run(inputs, image_factory=Unstable)
    assert_failed(inputs, "INPUT_CHANGED")
    assert not (inputs.root / "run/copy-a.json").exists()


@pytest.mark.parametrize("name", ["started.json", "copy-a.json", "copy-b.json", "verified.json"])
def test_receipt_error_never_reports_pair_success(inputs, monkeypatch, name):
    original = PrivateOutput.receipt

    def failing(self, filename, document):
        if filename == name:
            raise OSError(errno.ENOSPC, "synthetic metadata full")
        return original(self, filename, document)

    monkeypatch.setattr(PrivateOutput, "receipt", failing)
    with pytest.raises(ProfileError):
        run(inputs)
    assert_failed(inputs, "OUTPUT_IO_ERROR")


def test_failure_receipt_can_also_fail_without_masking_original(inputs, monkeypatch):
    def unavailable(*args):
        raise OSError(errno.ENOSPC, "synthetic full disk")

    monkeypatch.setattr(PrivateOutput, "receipt", unavailable)
    with pytest.raises(ProfileError) as caught:
        run(inputs)
    assert caught.value.code == "OUTPUT_IO_ERROR"
    assert not (inputs.root / "run/verified.json").exists()


@pytest.mark.parametrize(
    "corruption", ["missing", "extra", "same_size", "truncated", "symlink", "hardlink", "fifo"]
)
def test_reread_rejects_corrupt_or_replaced_outputs(inputs, monkeypatch, corruption):
    original, changed = PrivateOutput.verify, False

    def corrupt(self, copy, resources):
        nonlocal changed
        if not changed:
            changed = True
            folder = inputs.root / "run" / copy
            item = next(r for r in resources if r["size"])
            path = folder / item["file"]
            if corruption == "extra":
                (folder / "extra").write_bytes(b"x")
            elif corruption == "same_size":
                path.write_bytes(b"?" * item["size"])
            elif corruption == "truncated":
                path.write_bytes(b"")
            else:
                path.unlink()
                if corruption == "symlink":
                    path.symlink_to(inputs.iso)
                elif corruption == "hardlink":
                    os.link(inputs.iso, path)
                elif corruption == "fifo":
                    os.mkfifo(path)
        return original(self, copy, resources)

    monkeypatch.setattr(PrivateOutput, "verify", corrupt)
    with pytest.raises(ProfileError):
        run(inputs)
    assert not (inputs.root / "run/verified.json").exists()


@pytest.mark.parametrize("target", ["root", "session", "copy"])
def test_directory_replacement_is_detected_without_following_link(inputs, monkeypatch, target):
    original, changed = PrivateOutput.assert_attached, False

    def replace(self):
        nonlocal changed
        if not changed:
            changed = True
            path = {
                "root": inputs.root,
                "session": inputs.root / "run",
                "copy": inputs.root / "run/copy-a",
            }[target]
            saved = path.with_name(path.name + "-saved")
            path.rename(saved)
            path.mkdir()
        return original(self)

    monkeypatch.setattr(PrivateOutput, "assert_attached", replace)
    with pytest.raises(ProfileError) as caught:
        run(inputs)
    assert caught.value.code == "OUTPUT_CHANGED"
    assert not (inputs.root / "run/verified.json").exists()


def test_final_second_reread_detects_late_corruption(inputs, monkeypatch):
    original = PrivateOutput.receipt

    def corrupt_after_b(self, name, document):
        original(self, name, document)
        if name == "copy-b.json":
            item = next(r for r in document["resources"] if r["size"])
            (inputs.root / "run/copy-a" / item["file"]).write_bytes(b"?" * item["size"])

    monkeypatch.setattr(PrivateOutput, "receipt", corrupt_after_b)
    with pytest.raises(ProfileError):
        run(inputs)
    assert_failed(inputs, "OUTPUT_HASH_MISMATCH")


def test_receipt_publication_is_atomic_and_exclusive(inputs, monkeypatch):
    with PrivateOutput(inputs.root, inputs.repository, "run") as output:
        output.reserve(0, 1)
        original = private_output.write_all

        def partial(stream, data):
            stream.write(data[:5])
            raise OSError(errno.ENOSPC, "synthetic")

        monkeypatch.setattr(private_output, "write_all", partial)
        with pytest.raises(OSError):
            output.receipt("verified.json", {"status": "verified"})
        assert not (inputs.root / "run/verified.json").exists()
        monkeypatch.setattr(private_output, "write_all", original)
        output.receipt("started.json", {"status": "started"})
        with pytest.raises(FileExistsError):
            output.receipt("started.json", {})
        with pytest.raises(ProfileError):
            output.receipt("../escape", {})
        assert json.loads((inputs.root / "run/started.json").read_text()) == {"status": "started"}


def test_resource_creation_does_not_overwrite_existing_file(inputs):
    identity = "asset:" + "a" * 64
    with PrivateOutput(inputs.root, inputs.repository, "run") as output:
        output.reserve(4, 1)
        with output.open_resource("copy-a", identity) as target:
            target.write(b"keep")
        with pytest.raises(FileExistsError):
            with output.open_resource("copy-a", identity):
                pytest.fail("clobbered")
    assert (inputs.root / "run/copy-a" / resource_filename(identity)).read_bytes() == b"keep"


@pytest.mark.parametrize("offset,length", [(-1, 1), (0, -1), (True, 1), (0, True), (8192, 1)])
def test_iso_copy_ranges_confined(inputs, offset, length):
    with IsoImage(inputs.iso) as source:
        with pytest.raises(ProfileError):
            source.copy_range("B0.MFA", offset, length, BytesIO())


def test_iso_copy_io_error_typed_and_single_open(inputs, monkeypatch):
    with IsoImage(inputs.iso) as source:
        original, opened = type(source.iso).open_file_from_iso, []

        @contextmanager
        def counted(self, **kwargs):
            opened.append(kwargs)
            with original(self, **kwargs) as stream:
                yield stream

        monkeypatch.setattr(type(source.iso), "open_file_from_iso", counted)
        target = BytesIO()
        assert source.copy_range("B0.MFA", 6176, 3, target) == (
            3,
            hashlib.sha256(b"XYZ").hexdigest(),
        )
        assert len(opened) == 1 and target.getvalue() == b"XYZ"

        def badwrite(data):
            raise OSError(errno.ENOSPC, "synthetic")

        with pytest.raises(ProfileError) as caught:
            source.copy_range("B0.MFA", 6176, 3, SimpleNamespace(write=badwrite))
        assert caught.value.code == "COPY_IO_ERROR"


def test_invalid_resource_plan(inputs):
    import copy

    base = inputs.catalog
    for change, code in [
        ("duplicate", "DUPLICATE_RESOURCE"),
        ("empty", "EMPTY_EXTRACTION"),
        ("size", "INVALID_SIZE"),
    ]:
        doc = copy.deepcopy(base)
        if change == "duplicate":
            doc["entries"].append(doc["entries"][0])
        if change == "empty":
            doc["entries"] = []
        if change == "size":
            doc["entries"][0]["size"] = True
        with pytest.raises(ProfileError) as caught:
            extract.resource_plan(doc)
        assert caught.value.code == code


def test_second_copy_revalidates_current_catalog(inputs):
    opened = 0

    class ChangedSecond(IsoImage):
        def image_identity(self):
            nonlocal opened
            opened += 1
            size, digest = super().image_identity()
            return size, "0" * 64 if opened == 2 else digest

    with pytest.raises(ProfileError):
        run(inputs, image_factory=ChangedSecond)
    assert_failed(inputs, "IMAGE_MISMATCH")
    assert (inputs.root / "run/copy-a.json").exists()
    assert list((inputs.root / "run/copy-b").iterdir()) == []


def test_mismatched_verification_port_never_publishes_success(inputs, monkeypatch):
    original, calls = PrivateOutput.verify, 0

    def wrong(self, copy, resources):
        nonlocal calls
        calls += 1
        inventory = original(self, copy, resources)
        if calls == 4:
            inventory[0]["sha256"] = "0" * 64
        return inventory

    monkeypatch.setattr(PrivateOutput, "verify", wrong)
    with pytest.raises(ProfileError):
        run(inputs)
    assert_failed(inputs, "COPIES_DIFFER")


def test_resource_change_during_reread_rejected(inputs, monkeypatch):
    original, changed = private_output.fingerprint_stream, False

    def mutate(stream, size):
        nonlocal changed
        result = original(stream, size)
        if not changed:
            changed = True
            before = os.fstat(stream.fileno())
            os.utime(stream.fileno(), ns=(before.st_atime_ns, before.st_mtime_ns + 1000000))
        return result

    monkeypatch.setattr(private_output, "fingerprint_stream", mutate)
    with pytest.raises(ProfileError):
        run(inputs)
    assert_failed(inputs, "OUTPUT_CHANGED")


def test_session_created_concurrently_is_not_overwritten(inputs):
    with PrivateOutput(inputs.root, inputs.repository, "run") as output:
        (inputs.root / "run").mkdir()
        (inputs.root / "run/keep").write_text("keep")
        with pytest.raises(FileExistsError):
            output.reserve(0, 1)
        assert not output.reserved
    assert (inputs.root / "run/keep").read_text() == "keep"


def test_enter_failure_closes_root_descriptor(inputs, monkeypatch):
    original = os.stat

    def denied(path, *args, **kwargs):
        if path == "run" and "dir_fd" in kwargs:
            raise PermissionError("synthetic")
        return original(path, *args, **kwargs)

    output = PrivateOutput(inputs.root, inputs.repository, "run")
    monkeypatch.setattr(os, "stat", denied)
    with pytest.raises(PermissionError):
        output.__enter__()
    assert output.root_fd is None
