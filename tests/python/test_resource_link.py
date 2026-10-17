"""RL01-RL08: own states/extractions and adverse I/O; no original bytes."""

import hashlib
import json
import os
import struct
import zipfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_asset_catalog import catalog_source as catalog_source
from test_camera_observation import observation as observation
from test_candidates import extracted as extracted
from test_extraction import inputs as inputs
from test_pcsx2_state import CPU, CRC, PC, own_archive, own_internals

from tools.inspectors import pcsx2_state, resource_match, resource_scan_files, state_memory
from tools.inspectors import resource_link as cli
from tools.inspectors.observation_capture import validate_capture
from tools.inspectors.resource_scan_files import VerifiedResourceScanner
from tools.pipeline.private_output import resource_filename
from tools.pipeline.profile import ProfileError

PATTERN = bytes(range(64))
KEY = "a" * 64
ADDRESS = 0x100000


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def state_archive(event, memory, delay=0):
    registers = bytearray(own_internals(pc=event["pc"], delay=delay))
    for r, value in event["registers"].items():
        struct.pack_into("<I", registers, CPU + int(r) * 16, int(value, 16))
    return own_archive(
        [
            (pcsx2_state.VERSION_MEMBER, pcsx2_state.VERSION),
            (pcsx2_state.INTERNALS_MEMBER, bytes(registers)),
            (state_memory.RAM_MEMBER, memory),
        ],
        zipfile.ZIP_DEFLATED,
    )


@pytest.fixture
def memory_fixture():
    event = {"pc": PC, "registers": {"4": f"{ADDRESS:08x}", "31": "00001234"}}
    ram = bytearray(state_memory.RAM_SIZE)
    ram[ADDRESS : ADDRESS + 256] = bytes(range(256))
    return event, bytes(ram)


def test_real_size_member_selects_only_requested_range(memory_fixture, capsys):
    event, ram = memory_fixture
    sample = state_memory.sample_state(state_archive(event, ram), CRC, event, 4, 256)
    assert sample.data == bytes(range(256))
    assert "data=" not in repr(sample) and not capsys.readouterr().out


@pytest.mark.parametrize(
    "address",
    [
        0,
        0xFFFFF,
        0x02000000,
        0x01FFFFC1,
        0x20100000,
        0x30100000,
        0x80100000,
        0xA0100000,
        0x70000000,
        0xFFFFFFFF,
    ],
)
def test_invalid_address_or_alias_rejected(memory_fixture, address):
    event, ram = memory_fixture
    event["registers"]["4"] = f"{address:08x}"
    with pytest.raises(ProfileError, match="hypothesis"):
        state_memory.sample_state(state_archive(event, ram), CRC, event, 4, 64)


@pytest.mark.parametrize("variant", ["pc", "registers", "unselected", "delay", "ram_size", "crc"])
def test_memory_identity_rejections(memory_fixture, variant):
    event, ram = memory_fixture
    if variant == "ram_size":
        ram = ram[:-1]
    raw = state_archive(event, ram, delay=int(variant == "delay"))
    if variant == "pc":
        event["pc"] += 4
    elif variant == "registers":
        event["registers"]["31"] = "00009999"
    with pytest.raises(ProfileError):
        state_memory.sample_state(
            raw, CRC + int(variant == "crc"), event, 6 if variant == "unselected" else 4, 64
        )


@pytest.mark.parametrize(
    "register,size",
    [(True, 64), (0, 64), (32, 64), (4, 0), (4, 65), (4, 64.0), (4, True), (4, 4096)],
)
def test_bad_sample_request_before_zip(register, size):
    with pytest.raises(ProfileError):
        state_memory.sample_state(b"not opened", CRC, {}, register, size)


def test_stream_boundary_overlap_and_duplicate_contexts(monkeypatch):
    monkeypatch.setattr(resource_match, "CHUNK", 73)
    pattern = b"ab" * 32
    raw = b"z" * 71 + pattern + b"ab" * 5 + b"z" * 17 + bytes(range(256))
    patterns = {KEY: pattern, "b" * 64: pattern, "c" * 64: bytes(range(256))}
    sha, hits = resource_match.scan_stream(BytesIO(raw), len(raw), patterns)
    assert sha == digest(raw)
    assert hits[KEY] == [71 + i * 2 for i in range(6)] == hits["b" * 64]
    assert hits["c" * 64] == [162]


def test_short_reads_and_empty_resource():
    class Short(BytesIO):
        def read(self, n):
            return super().read(min(7, n))

    raw = b"own" + PATTERN + b"tail"
    assert resource_match.scan_stream(Short(raw), len(raw), {KEY: PATTERN}) == (
        digest(raw),
        {KEY: [3]},
    )
    assert resource_match.scan_stream(BytesIO(), 0, {}) == (digest(b""), {})


@pytest.mark.parametrize(
    "size,patterns",
    [
        (True, {}),
        (-1, {}),
        (resource_match.MAX_BYTES + 1, {}),
        (0, []),
        (0, {"bad": PATTERN}),
        (0, {KEY: b""}),
        (0, {KEY: b"x" * 64}),
        (0, {KEY: bytearray(PATTERN)}),
        (0, {f"{i:064x}": PATTERN for i in range(11)}),
    ],
)
def test_scan_budgets_before_read(size, patterns):
    class Never:
        def read(self, *_):
            pytest.fail("must validate before reading")

    with pytest.raises(ProfileError):
        resource_match.scan_stream(Never(), size, patterns)


@pytest.mark.parametrize("raw,size", [(b"x", 2), (b"xx", 1)])
def test_scan_truncation_or_trailing(raw, size):
    with pytest.raises(ProfileError):
        resource_match.scan_stream(BytesIO(raw), size, {})


def test_match_cap_rejects_ambiguity():
    pattern = b"ab" * 32
    raw = pattern * 6
    with pytest.raises(ProfileError) as error:
        resource_match.scan_stream(BytesIO(raw), len(raw), {KEY: pattern})
    assert error.value.code == "MATCH_HITS"


@pytest.fixture
def private_resource(tmp_path):
    root = tmp_path / "copy"
    root.mkdir(mode=0o700)
    raw = b"own prefix" + PATTERN
    item = {"id": "asset:" + KEY, "size": len(raw), "sha256": digest(raw)}
    path = root / resource_filename(item["id"])
    path.write_bytes(raw)
    path.chmod(0o600)
    return root, item, path, tmp_path / "repo"


def test_private_scanner_and_final_stability(private_resource):
    root, item, path, repo = private_resource
    with VerifiedResourceScanner(root, repo) as reader:
        assert reader.scan_verified(item, {KEY: PATTERN}) == {KEY: [10]}
    with pytest.raises(ProfileError):
        with VerifiedResourceScanner(root, repo) as reader:
            reader.scan_verified(item, {KEY: PATTERN})
            path.write_bytes(b"late change")


@pytest.mark.parametrize(
    "variant", ["hash", "size", "mode", "dir_mode", "hardlink", "symlink", "fifo", "replaced_dir"]
)
def test_private_scan_rejects(private_resource, variant):
    root, item, path, repo = private_resource
    if variant == "hash":
        item["sha256"] = "f" * 64
    elif variant == "size":
        item["size"] += 1
    elif variant == "mode":
        path.chmod(0o644)
    elif variant == "dir_mode":
        root.chmod(0o755)
    elif variant in ("hardlink", "symlink", "fifo"):
        original = path.with_name("original")
        path.rename(original)
        if variant == "hardlink":
            os.link(original, path)
        elif variant == "symlink":
            path.symlink_to(original)
        else:
            os.mkfifo(path, 0o600)
    with pytest.raises((ProfileError, OSError)):
        with VerifiedResourceScanner(root, repo) as reader:
            if variant == "replaced_dir":
                root.rename(root.with_name("moved"))
                root.mkdir(mode=0o700)
            reader.scan_verified(item, {KEY: PATTERN})


def test_mutation_during_scan(private_resource, monkeypatch):
    root, item, path, repo = private_resource
    original = resource_scan_files.scan_stream

    def changing(*args):
        result = original(*args)
        path.write_bytes(b"changed")
        return result

    monkeypatch.setattr(resource_scan_files, "scan_stream", changing)
    with pytest.raises(ProfileError):
        with VerifiedResourceScanner(root, repo) as reader:
            reader.scan_verified(item, {KEY: PATTERN})


@pytest.fixture
def link_case(extracted, observation, tmp_path, monkeypatch):
    # Smaller self-authored RAM keeps repeated integration tests cheap.
    monkeypatch.setattr(state_memory, "RAM_SIZE", ADDRESS + 4096)
    plan, capture, blobs, *_ = observation
    plan["source"] = extracted.catalog["source"]
    plan["catalog_sha256"] = extracted.catalog_hash
    capture["image_sha256"] = plan["source"]["sha256"]
    capture["catalog_sha256"] = extracted.catalog_hash
    capture["data_samples"] = []
    root, states = tmp_path / "capture", tmp_path / "states"
    root.mkdir(mode=0o700)
    states.mkdir(mode=0o700)

    def save(path, data):
        path.write_bytes(data)
        path.chmod(0o600)
        return digest(data)

    plan_path = tmp_path / "plan.json"
    plan_hash = save(plan_path, json.dumps(plan).encode())
    capture["plan_sha256"] = plan_hash
    index = {"schema_version": 1, "capture_sha256": "", "expected_crc": CRC, "states": []}
    memory = bytearray(state_memory.RAM_SIZE)
    memory[ADDRESS : ADDRESS + 256] = bytes(range(256))
    for event in capture["events"]:
        for r in ("4", "6"):
            event["registers"][r] = f"{ADDRESS:08x}"
        name = f"own-{event['sequence']}.p2s"
        sha = save(states / name, state_archive(event, bytes(memory)))
        index["states"].append({"sequence": event["sequence"], "name": name, "sha256": sha})
    capture_hash = save(root / "capture.json", json.dumps(capture).encode())
    index["capture_sha256"] = capture_hash
    for key, blob in blobs.items():
        save(root / (key + ".bin"), blob)
    receipt = validate_capture(plan, plan_hash, capture, lambda h, n: blobs[h])
    receipt["capture_sha256"] = capture_hash
    docs = {
        "plan": plan,
        "observation": receipt,
        "observation-repeat": receipt,
        "catalog": extracted.catalog,
        "extraction": extracted.receipt,
        "state-index": index,
    }
    paths, hashes = {}, {}
    for name, document in docs.items():
        paths[name] = tmp_path / (name + ".json")
        hashes[name] = save(paths[name], json.dumps(document).encode())
    args = [
        v for k in cli.INPUTS for v in ("--" + k, str(paths[k]), "--" + k + "-sha256", hashes[k])
    ]
    output = tmp_path / "result.json"
    dirs = [root, states, extracted.root / "run/copy-a", extracted.root / "run/copy-b"]
    args += [
        v
        for k, p in zip(("capture-root", "state-root", "copy-a", "copy-b"), dirs, strict=True)
        for v in ("--" + k, str(p))
    ]
    args += ["--capture-sha256", capture_hash, "--output", str(output)]
    return SimpleNamespace(
        args=args,
        output=output,
        docs=docs,
        hashes=hashes,
        capture_hash=capture_hash,
        dirs=dirs,
        repo=tmp_path / "repo",
        paths=paths,
        capture=capture,
    )


def test_cli_two_runs_identical_and_private_values_absent(link_case, capsys):
    c = link_case
    assert cli.main(c.args) == 0
    report = json.loads(c.output.read_text())
    assert report["status"] == "no_exact_matches"
    assert report["summary"] == {
        "sample_count": 2,
        "searched_count": 2,
        "match_count": 0,
        "resources_per_copy": 5,
        "bytes_per_copy": 27,
        "copies_verified": 2,
    }
    assert report["resource_links"] == report["capabilities"] == []
    assert "registers" not in c.output.read_text() and "address" not in c.output.read_text()
    args = c.args.copy()
    args[-1] = str(c.output.with_name("repeat.json"))
    assert cli.main(args) == 0
    assert c.output.read_bytes() == Path(args[-1]).read_bytes()
    assert cli.main(c.args) == 1
    assert "OUTPUT_EXISTS" in capsys.readouterr().out


@pytest.mark.parametrize(
    "variant",
    [
        "observation",
        "capture_identity",
        "sequence",
        "state_hash",
        "name",
        "register",
        "copy",
        "catalog",
    ],
)
def test_invalid_evidence_no_success_report(link_case, variant, capsys):
    c = link_case
    if variant == "observation":
        c.docs["observation-repeat"] = {**c.docs["observation-repeat"], "event_count": 0}
        key = "observation-repeat"
    elif variant == "catalog":
        c.docs["catalog"]["entries"][0]["size"] += 1
        key = "catalog"
    elif variant == "copy":
        c.args[c.args.index("--copy-b") + 1] = str(c.dirs[2])
        key = None
    else:
        key = "state-index"
        item = c.docs[key]["states"][0]
        if variant == "capture_identity":
            c.docs[key]["capture_sha256"] = "f" * 64
        elif variant == "sequence":
            item["sequence"] = True
        elif variant == "state_hash":
            item["sha256"] = "f" * 64
        elif variant == "name":
            item["name"] = "../own.p2s"
        else:
            source = c.dirs[1] / c.docs[key]["states"][1]["name"]
            dest = c.dirs[1] / item["name"]
            dest.write_bytes(source.read_bytes())
            item["sha256"] = digest(dest.read_bytes())
    if key:
        raw = json.dumps(c.docs[key]).encode()
        c.paths[key].write_bytes(raw)
        c.args[c.args.index("--" + key + "-sha256") + 1] = digest(raw)
    assert cli.main(c.args) == 1 and not c.output.exists()
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"


def test_late_scanner_close_failure_no_report(link_case, monkeypatch):
    original = VerifiedResourceScanner.__exit__

    def fail(self, *args):
        original(self, *args)
        raise OSError("own close failure")

    monkeypatch.setattr(VerifiedResourceScanner, "__exit__", fail)
    assert cli.main(link_case.args) == 1
    assert not link_case.output.exists()


def test_global_match_cap():
    class OwnReader:
        def verify_set(self, resources):
            pass

        def assert_stable(self):
            pass

        def scan_verified(self, resource, patterns):
            return {KEY: list(range(100))}

    resources = [{"id": "own-" + str(n), "size": 256, "sha256": "b" * 64} for n in range(2)]
    with pytest.raises(ProfileError):
        cli.scan_catalog(OwnReader(), resources, {KEY: PATTERN})


def test_ram_crc_is_checked_even_outside_sample(memory_fixture):
    event, ram = memory_fixture
    registers = bytearray(own_internals())
    struct.pack_into("<I", registers, CPU + 4 * 16, ADDRESS)
    struct.pack_into("<I", registers, CPU + 31 * 16, 0x1234)
    raw = bytearray(
        own_archive(
            [
                (pcsx2_state.VERSION_MEMBER, pcsx2_state.VERSION),
                (pcsx2_state.INTERNALS_MEMBER, bytes(registers)),
                (state_memory.RAM_MEMBER, ram),
            ]
        )
    )
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        info = archive.getinfo(state_memory.RAM_MEMBER)
        offset = info.header_offset + 30 + len(info.filename)
    raw[offset + len(ram) - 1] ^= 1
    with pytest.raises(ProfileError) as error:
        state_memory.sample_state(bytes(raw), CRC, event, 4, 64)
    assert error.value.code == "STATE_ZIP"


def test_selection_keeps_uniform_samples_and_both_b_phases(observation):
    plan, capture, *_ = observation
    plan["boundaries"][0]["argument_copy"] = None
    index = {
        "schema_version": 1,
        "capture_sha256": "f" * 64,
        "expected_crc": CRC,
        "states": [
            {"sequence": e["sequence"], "name": f"{e['sequence']}.p2s", "sha256": "a" * 64}
            for e in capture["events"]
        ],
    }

    def state(item):
        event = capture["events"][item["sequence"] - 1]
        return SimpleNamespace(registers_at=lambda *args: event["registers"])

    samples, patterns = cli.select_samples(
        plan, capture, index, state, lambda item, e, r, n: b"x" * n
    )
    assert len(samples) == 4 and not patterns
    assert {s["status"] for s in samples} == {"non_discriminating"}


def make_positive_case(c):
    catalog, extraction = c.docs["catalog"], c.docs["extraction"]
    entry = catalog["entries"][0]
    raw = b"own prefix!" + bytes(range(256)) + b"tail"
    old_size = entry["size"]
    entry.update(size=len(raw), sha256=digest(raw))
    parent = next(p for p in catalog["containers"] if p["id"] == entry["container_id"])
    parent["size"] = max(parent["size"], entry["container_offset"] + len(raw))
    catalog["summary"]["payload_bytes"] += len(raw) - old_size
    from tools.pipeline.extract_assets import resource_plan

    resources = resource_plan(catalog)
    extraction["resources"] = resources
    extraction["summary"] = deepcopy(catalog["summary"])
    extraction["copies"] = {
        copy: [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in resources]
        for copy in ("copy-a", "copy-b")
    }
    for directory in c.dirs[2:]:
        (directory / resource_filename(entry["id"])).write_bytes(raw)
    catalog_hash = digest(json.dumps(catalog).encode())
    extraction["catalog_sha256"] = catalog_hash
    c.docs["plan"]["catalog_sha256"] = catalog_hash
    plan_hash = digest(json.dumps(c.docs["plan"]).encode())
    c.capture.update(plan_sha256=plan_hash, catalog_sha256=catalog_hash)
    capture_raw = json.dumps(c.capture).encode()
    (c.dirs[0] / "capture.json").write_bytes(capture_raw)
    c.capture_hash = digest(capture_raw)
    c.docs["state-index"]["capture_sha256"] = c.capture_hash
    receipt = validate_capture(
        c.docs["plan"], plan_hash, c.capture, lambda h, n: (c.dirs[0] / (h + ".bin")).read_bytes()
    )
    receipt["capture_sha256"] = c.capture_hash
    c.docs["observation"] = c.docs["observation-repeat"] = receipt
    for name, document in c.docs.items():
        raw = json.dumps(document).encode()
        c.paths[name].write_bytes(raw)
        c.args[c.args.index("--" + name + "-sha256") + 1] = digest(raw)
    c.args[c.args.index("--capture-sha256") + 1] = c.capture_hash
    return entry["id"]


def test_positive_matches_remain_candidates(link_case):
    identity = make_positive_case(link_case)
    assert cli.main(link_case.args) == 0
    report = json.loads(link_case.output.read_text())
    assert report["status"] == "candidate_matches"
    assert len(report["matches"]) == 2
    assert {m["resource_id"] for m in report["matches"]} == {identity}
    assert {m["resource_offset"] for m in report["matches"]} == {11}
    assert report["resource_links"] == report["capabilities"] == []


def test_copy_disagreement_prevents_publication(link_case, monkeypatch, capsys):
    make_positive_case(link_case)
    original = VerifiedResourceScanner.scan_verified

    def changed(self, *args):
        result = original(self, *args)
        if self.root == link_case.dirs[3]:
            for positions in result.values():
                if positions:
                    positions[0] += 1
        return result

    monkeypatch.setattr(VerifiedResourceScanner, "scan_verified", changed)
    assert cli.main(link_case.args) == 1 and not link_case.output.exists()
    assert "MATCH_COPIES" in capsys.readouterr().out


def test_all_uniform_is_not_a_negative_search(link_case, monkeypatch):
    original = cli.select_samples

    def uniform(*args):
        samples, _ = original(*args)
        for sample in samples:
            sample["status"] = "non_discriminating"
        return samples, {}

    monkeypatch.setattr(cli, "select_samples", uniform)
    assert cli.main(link_case.args) == 0
    report = json.loads(link_case.output.read_text())
    assert report["status"] == "no_discriminating_samples"
    assert report["summary"]["searched_count"] == 0


def test_extra_file_added_after_scan_is_rejected_at_close(private_resource):
    root, item, _, repo = private_resource
    with pytest.raises(ProfileError):
        with VerifiedResourceScanner(root, repo) as reader:
            reader.verify_set([item])
            reader.scan_verified(item, {KEY: PATTERN})
            (root / "added.bin").write_bytes(b"own extra")
