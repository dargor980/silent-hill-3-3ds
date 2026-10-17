"""CO01-CO08: self-authored captures, snapshots and ISO; no original game data."""

import json
import os
import struct
from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
from pathlib import Path

import pycdlib
import pytest
from test_camera_boundary import boundary_evidence as boundary_evidence
from test_camera_boundary import boundary_fixture, collect_boundary
from test_camera_consumer import OwnDisc, digest, own_elf, own_loop, parsed
from test_camera_consumer import evidence as evidence
from test_camera_pointer import jump, special
from test_camera_pointer import pointer_evidence as pointer_evidence

from tools.inspectors import camera_observation as cli
from tools.inspectors import capture_files
from tools.inspectors.call_boundary import inspect_boundaries
from tools.inspectors.camera_boundary import survey_boundaries
from tools.inspectors.camera_consumer import survey_consumer
from tools.inspectors.camera_pointer import survey_pointers
from tools.inspectors.capture_files import PrivateCaptureReader
from tools.inspectors.observation_capture import validate_capture
from tools.inspectors.observation_plan import make_plan, object_hash, prepare_plan
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError, parse_profile


@pytest.fixture
def observation():
    reader, mapping, sites = boundary_fixture()
    data = bytearray(reader.data)
    struct.pack_into("<I", data, 384, 0x70000000)
    reader, mapping = parsed(bytes(data))
    boundary = {
        "source": {"sha256": "1" * 64},
        "executable": {"sha256": "2" * 64},
        "evidence": {},
        "analysis": inspect_boundaries(reader, mapping, sites),
    }
    catalog = {
        "schema_version": 1,
        "scope": "selected_mfa_entries",
        "source": boundary["source"],
        "capabilities": [],
    }
    hashes = {"boundary": "3" * 64, "boundary_repeat": "3" * 64, "catalog": "4" * 64}

    def read_slot(pc):
        return struct.unpack("<I", reader(mapping.file_offset(pc, 4), 4))[0]

    plan = make_plan(boundary, catalog, hashes, read_slot)
    blobs = {}
    for window in plan["code_ranges"]:
        blobs[window["sha256"]] = reader(window["file_offset"], window["end"] - window["start"])
    own_data = b"own sample"
    blobs[digest(own_data)] = own_data
    environment = {
        "emulator": "own synthetic fixture",
        "version": "own-1",
        "binary_sha256": "5" * 64,
        "bios_sha256": "6" * 64,
        "configuration_sha256": "7" * 64,
        "cpu": "EE",
        "method": "manual-debugger-v1",
    }
    first = plan["boundaries"][0]
    phases = ("before_call", "entry_after_slot", "checkpoint", "return_if_reached")
    points = {p["phase"]: p for p in first["points"]}
    events = []
    for sequence, phase in enumerate(phases, 1):
        point = points[phase]
        values = {str(r): "00000000" for r in point["registers"]}
        values["6"] = "00001234"
        values["4"] = "00000099" if sequence == 1 else "00001234"
        values["31"] = f"{points['return_if_reached']['pc']:08x}"
        events.append(
            {
                "sequence": sequence,
                "session_id": "a" * 32,
                "environment_sha256": object_hash(environment),
                "boundary_id": first["id"],
                "point_id": point["id"],
                "pc": point["pc"],
                "registers": values,
            }
        )
    capture = {
        "schema_version": 1,
        "kind": "sh3-runtime-capture",
        "session_id": "a" * 32,
        "status": "complete",
        "plan_sha256": "8" * 64,
        "image_sha256": "1" * 64,
        "executable_sha256": "2" * 64,
        "catalog_sha256": "4" * 64,
        "environment": environment,
        "outcomes": {first["id"]: "observed"},
        "events": events,
        "code_snapshots": [
            {"range_id": r["id"], "size": r["end"] - r["start"], "sha256": r["sha256"]}
            for r in plan["code_ranges"]
        ],
        "data_samples": [
            {
                "event_sequence": 1,
                "register": 6,
                "address": 0x1234,
                "size": len(own_data),
                "sha256": digest(own_data),
            }
        ],
    }
    return plan, capture, blobs, boundary, catalog, hashes, read_slot


def validate(observation, capture=None, read=None):
    plan, original, blobs, *_ = observation
    return validate_capture(
        plan, "8" * 64, original if capture is None else capture, read or (lambda h, n: blobs[h])
    )


def test_plan_deterministic_with_copy_relation_and_checkpoint(observation):
    plan, _, _, boundary, catalog, hashes, read = observation
    assert make_plan(boundary, catalog, hashes, read) == plan
    assert plan["status"] == "not_performed"
    assert plan["boundaries"][0]["argument_copy"] == {"entry_register": 4, "before_register": 6}
    assert len(plan["boundaries"][0]["points"]) == 4


def test_comparisons_do_not_export_register_values_or_authenticate_execution(observation):
    result = validate(observation)
    assert result["status"] == "validated_observations"
    assert result["comparisons"][0]["entry_copy_comparison"] == "equal"
    assert result["comparisons"][0]["entry_return_comparison"] == "equal"
    assert result["execution_authentication"] == "not_provided"
    assert result["resource_links"] == result["capabilities"] == []
    assert "00001234" not in json.dumps(result) and "registers" not in json.dumps(result)


def test_different_registers_are_observations_not_false_global_guarantees(observation):
    capture = deepcopy(observation[1])
    capture["events"][1]["registers"]["4"] = "00005678"
    result = validate(observation, capture)
    assert result["comparisons"][0]["entry_copy_comparison"] == "different"
    assert result["comparisons"][0]["entry_return_comparison"] == "different"


def test_not_reached_reports_no_observations(observation):
    capture = deepcopy(observation[1])
    capture["outcomes"] = {k: "not_reached" for k in capture["outcomes"]}
    capture["events"] = capture["code_snapshots"] = capture["data_samples"] = []
    result = validate(observation, capture)
    assert result["status"] == "validated_no_observations"
    assert result["comparisons"][0]["entry_return_comparison"] == "not_observed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("kind", "other"),
        ("session_id", "a" * 31),
        ("session_id", []),
        ("status", "incomplete"),
        ("status", "not_performed"),
        ("plan_sha256", "f" * 64),
        ("image_sha256", "f" * 64),
        ("executable_sha256", "f" * 64),
        ("catalog_sha256", "f" * 64),
        ("events", {}),
        ("events", [{}] * 129),
        ("outcomes", {}),
        ("code_snapshots", [{}] * 33),
        ("data_samples", [{}] * 17),
    ],
)
def test_capture_header_and_budgets_rejected(observation, field, value):
    capture = deepcopy(observation[1])
    capture[field] = value
    with pytest.raises(ProfileError):
        validate(observation, capture)


@pytest.mark.parametrize(
    "field,value",
    [
        ("emulator", ""),
        ("version", " " * 128 + "x"),
        ("version", 1),
        ("binary_sha256", "bad"),
        ("bios_sha256", "bad"),
        ("configuration_sha256", "bad"),
        ("cpu", "IOP"),
        ("method", "invented"),
    ],
)
def test_environment_contract(observation, field, value):
    capture = deepcopy(observation[1])
    capture["environment"][field] = value
    with pytest.raises(ProfileError):
        validate(observation, capture)


@pytest.mark.parametrize(
    "field,value",
    [
        ("sequence", True),
        ("sequence", 0),
        ("sequence", 3),
        ("session_id", "b" * 32),
        ("environment_sha256", "b" * 64),
        ("boundary_id", "b" * 64),
        ("boundary_id", []),
        ("point_id", "b" * 64),
        ("point_id", []),
        ("pc", True),
        ("pc", 0),
        ("registers", {}),
    ],
)
def test_event_session_point_order_and_register_contract(observation, field, value):
    capture = deepcopy(observation[1])
    capture["events"][0][field] = value
    with pytest.raises(ProfileError):
        validate(observation, capture)


@pytest.mark.parametrize("value", ["0", "0000000G", "FFFFFFFF", 0, None])
def test_register_values_require_exact_low32_hex(observation, value):
    capture = deepcopy(observation[1])
    capture["events"][0]["registers"]["4"] = value
    with pytest.raises(ProfileError):
        validate(observation, capture)


@pytest.mark.parametrize(
    "variant",
    [
        "missing_return",
        "entry_first",
        "double_before",
        "checkpoint_first",
        "return_first",
        "bad_ra",
        "not_reached_with_events",
    ],
)
def test_invocation_order_and_completion(observation, variant):
    capture = deepcopy(observation[1])
    if variant == "missing_return":
        capture["events"].pop()
    elif variant == "bad_ra":
        capture["events"][1]["registers"]["31"] = "00000000"
    elif variant == "not_reached_with_events":
        capture["outcomes"] = {k: "not_reached" for k in capture["outcomes"]}
    else:
        index = {"entry_first": 1, "double_before": 0, "checkpoint_first": 2, "return_first": 3}[
            variant
        ]
        if variant == "double_before":
            capture["events"][1] = deepcopy(capture["events"][0])
            capture["events"][1]["sequence"] = 2
        else:
            capture["events"][0] = deepcopy(capture["events"][index])
            capture["events"][0]["sequence"] = 1
    with pytest.raises(ProfileError):
        validate(observation, capture)


@pytest.mark.parametrize(
    "variant", ["missing", "duplicate", "foreign", "size", "hash", "bool_size"]
)
def test_code_snapshots_match_exact_required_ranges(observation, variant):
    capture = deepcopy(observation[1])
    items = capture["code_snapshots"]
    if variant == "missing":
        items.pop()
    elif variant == "duplicate":
        items.append(items[0])
    else:
        items[0][
            {"foreign": "range_id", "size": "size", "hash": "sha256", "bool_size": "size"}[variant]
        ] = {"foreign": "f" * 64, "size": 4, "hash": "f" * 64, "bool_size": True}[variant]
    with pytest.raises(ProfileError):
        validate(observation, capture)


@pytest.mark.parametrize(
    "field,value",
    [
        ("event_sequence", 0),
        ("event_sequence", 5),
        ("register", 31),
        ("register", 32),
        ("address", 0),
        ("size", 0),
        ("size", 4097),
        ("size", True),
        ("sha256", "bad"),
    ],
)
def test_data_sample_ranges_and_context(observation, field, value):
    capture = deepcopy(observation[1])
    capture["data_samples"][0][field] = value
    with pytest.raises(ProfileError):
        validate(observation, capture)


def test_data_range_cannot_wrap_32_bits(observation):
    capture = deepcopy(observation[1])
    capture["events"][0]["registers"]["6"] = "ffffffff"
    capture["data_samples"][0]["address"] = (1 << 32) - 1
    with pytest.raises(ProfileError):
        validate(observation, capture)


@pytest.mark.parametrize("blob", [b"wrong", bytearray(b"wrong"), None])
def test_reader_contract_does_not_bypass_hash_check(observation, blob):
    with pytest.raises(ProfileError):
        validate(observation, read=lambda *_: blob)


@pytest.mark.parametrize("target", ["root", "environment", "event", "snapshot", "sample"])
def test_extra_fields_are_rejected(observation, target):
    capture = deepcopy(observation[1])
    item = {
        "root": capture,
        "environment": capture["environment"],
        "event": capture["events"][0],
        "snapshot": capture["code_snapshots"][0],
        "sample": capture["data_samples"][0],
    }[target]
    item["unexpected"] = 1
    with pytest.raises(ProfileError):
        validate(observation, capture)


def write_private(root, name, data):
    path = root / name
    path.write_bytes(data)
    path.chmod(0o600)
    return path


@pytest.fixture
def private_capture(observation, tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    for sha, data in observation[2].items():
        write_private(root, sha + ".bin", data)
    raw = json.dumps(observation[1]).encode()
    write_private(root, "capture.json", raw)
    return root, digest(raw), tmp_path / "repo"


def test_private_capture_matches_memory_and_detects_late_file_change(observation, private_capture):
    root, sha, repo = private_capture
    with PrivateCaptureReader(root, repo) as reader:
        assert validate_capture(
            observation[0], "8" * 64, reader.document(sha), reader.blob
        ) == validate(observation)
    with pytest.raises(ProfileError, match="changed"):
        with PrivateCaptureReader(root, repo) as reader:
            reader.document(sha)
            (root / "capture.json").write_text("changed")


@pytest.mark.parametrize("variant", ["inside", "same", "ancestor"])
def test_capture_must_be_external(tmp_path, variant):
    repo = tmp_path / "repo"
    root = {"inside": repo / "nested", "same": repo, "ancestor": tmp_path}[variant]
    with pytest.raises(ProfileError):
        PrivateCaptureReader(root, repo)


@pytest.mark.parametrize(
    "variant",
    ["symlink", "parent_symlink", "hardlink", "fifo", "permissions", "size", "hash", "empty"],
)
def test_private_reader_rejects_invalid_file(private_capture, tmp_path, variant):
    root, sha, repo = private_capture
    path = root / "capture.json"
    if variant in ("symlink", "hardlink", "fifo"):
        moved = root / "original"
        path.rename(moved)
        if variant == "symlink":
            path.symlink_to(moved)
        elif variant == "hardlink":
            os.link(moved, path)
        else:
            os.mkfifo(path, 0o600)
    elif variant == "parent_symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(root)
        root = alias
    elif variant == "permissions":
        path.chmod(0o644)
    elif variant == "size":
        path.write_bytes(b"x" * (capture_files.MAX_JSON + 1))
    elif variant == "hash":
        sha = "f" * 64
    else:
        path.write_bytes(b"")
    with pytest.raises((ProfileError, OSError)):
        with PrivateCaptureReader(root, repo) as reader:
            reader.document(sha)


@pytest.mark.parametrize("raw", [b"[]", b'{"a":1,"a":2}', b'{"a":NaN}', b"{", b"\xff", b"[" * 2000])
def test_json_duplicate_nonfinite_invalid_and_deep_are_rejected(private_capture, raw):
    root, _, repo = private_capture
    write_private(root, "capture.json", raw)
    with pytest.raises(ProfileError):
        with PrivateCaptureReader(root, repo) as reader:
            reader.document(digest(raw))


@pytest.mark.parametrize(
    "name,size,limit",
    [
        ("../escape", 1, 4),
        ("capture.json", True, 4),
        ("capture.json", 5, 4),
        ("capture.json", 1, 0),
        ("capture.json", 1, True),
    ],
)
def test_invalid_private_read_arguments(private_capture, name, size, limit):
    root, sha, repo = private_capture
    with PrivateCaptureReader(root, repo) as reader:
        with pytest.raises(ProfileError):
            reader.read(name, sha, size, limit)


def test_directory_replacement_detected(private_capture):
    root, sha, repo = private_capture
    with pytest.raises(ProfileError):
        with PrivateCaptureReader(root, repo) as reader:
            reader.document(sha)
            root.rename(root.with_name("moved"))
            root.mkdir()


def test_exception_closes_owned_descriptor_once(private_capture, monkeypatch):
    root, _, repo = private_capture
    reader = PrivateCaptureReader(root, repo).__enter__()
    fd = reader.fd
    original = os.close
    closed = []

    def close(number):
        closed.append(number)
        original(number)
        if number == fd:
            raise OSError("close failed after releasing")

    monkeypatch.setattr(capture_files.os, "close", close)
    error = ProfileError("OWN", "synthetic")
    reader.__exit__(ProfileError, error, None)
    assert closed.count(fd) == 1 and reader.fd is None and error.__notes__


def test_mutation_during_read_is_rejected(private_capture, monkeypatch):
    root, sha, repo = private_capture
    original = capture_files._owned_stream

    @contextmanager
    def mutate(fd, mode):
        with original(fd, mode) as stream:

            class Changed:
                def fileno(self):
                    return stream.fileno()

                def read(self, count):
                    data = stream.read(count)
                    (root / "capture.json").write_bytes(b"changed during read")
                    return data

            yield Changed()

    monkeypatch.setattr(capture_files, "_owned_stream", mutate)
    with pytest.raises(ProfileError, match="changed during read"):
        with PrivateCaptureReader(root, repo) as reader:
            reader.document(sha)


@pytest.fixture
def plan_evidence(boundary_evidence, tmp_path):
    boundary = collect_boundary(boundary_evidence)
    bp = tmp_path / "boundary.json"
    bp.write_text(json.dumps(boundary))
    catalog = {
        "schema_version": 1,
        "scope": "selected_mfa_entries",
        "source": boundary["source"],
        "capabilities": [],
    }
    cp = tmp_path / "catalog.json"
    cp.write_text(json.dumps(catalog))
    args = boundary_evidence[-1] + [
        "--boundary",
        str(bp),
        "--boundary-sha256",
        digest(bp.read_bytes()),
        "--boundary-repeat",
        str(bp),
        "--boundary-repeat-sha256",
        digest(bp.read_bytes()),
        "--catalog",
        str(cp),
        "--catalog-sha256",
        digest(cp.read_bytes()),
    ]
    documents, hashes = {}, {"image": args[args.index("--image-sha256") + 1]}
    for name, flag in cli.INPUTS.items():
        documents[name] = json.loads(Path(args[args.index("--" + flag) + 1]).read_text())
        hashes[name] = args[args.index("--" + flag + "-sha256") + 1]
    files = boundary_evidence[0][0][0]
    return args, documents, hashes, files


def collect_plan(plan_evidence, documents=None, hashes=None):
    _, original, oldhash, files = plan_evidence
    docs = original if documents is None else documents
    return prepare_plan(
        OwnDisc(files),
        parse_profile(docs["profile"]),
        docs,
        docs["probe"]["source"]["size"],
        oldhash if hashes is None else hashes,
    )


def test_full_chain_memory_iso_two_cli_plans_and_exclusive_output(plan_evidence, tmp_path):
    args, docs, hashes, _ = plan_evidence
    expected = collect_plan(plan_evidence)
    with IsoImage(Path(args[args.index("--iso") + 1])) as image:
        assert (
            prepare_plan(
                image, parse_profile(docs["profile"]), docs, docs["probe"]["source"]["size"], hashes
            )
            == expected
        )
    paths = [tmp_path / "a.json", tmp_path / "b.json"]
    for path in paths:
        assert cli.main(["plan", *args, "--output", str(path)]) == 0
    assert paths[0].read_bytes() == paths[1].read_bytes()
    assert json.loads(paths[0].read_text()) == expected
    assert cli.main(["plan", *args, "--output", str(paths[0])]) == 1


@pytest.mark.parametrize(
    "mutation", ["repeat", "version", "site", "catalog_source", "catalog_scope", "bool_version"]
)
def test_full_evidence_reconciliation(plan_evidence, mutation):
    docs = deepcopy(plan_evidence[1])
    if mutation == "repeat":
        docs["boundary_repeat"] = {}
    elif mutation == "version":
        docs["boundary"]["schema_version"] = True
        docs["boundary_repeat"] = docs["boundary"]
    elif mutation == "site":
        docs["boundary"]["analysis"]["boundaries"] = [{"fake": True}]
        docs["boundary_repeat"] = docs["boundary"]
    elif mutation == "catalog_source":
        docs["catalog"]["source"] = {}
    elif mutation == "catalog_scope":
        docs["catalog"]["scope"] = "other"
    else:
        docs["catalog"]["schema_version"] = True
    with pytest.raises(ProfileError):
        collect_plan(plan_evidence, documents=docs)


def test_repeat_byte_identity_required(plan_evidence):
    hashes = dict(plan_evidence[2])
    hashes["boundary_repeat"] = "f" * 64
    with pytest.raises(ProfileError):
        collect_plan(plan_evidence, hashes=hashes)


@pytest.mark.parametrize("flag", ["image", *cli.INPUTS.values()])
def test_cli_hash_mismatch_never_publishes(plan_evidence, tmp_path, flag):
    args = list(plan_evidence[0])
    args[args.index("--" + flag + "-sha256") + 1] = "f" * 64
    out = tmp_path / "failed.json"
    assert cli.main(["plan", *args, "--output", str(out)]) == 1 and not out.exists()


def test_plan_budgets_and_unknown_boundary(observation):
    _, _, _, boundary, catalog, hashes, read = observation
    bad = deepcopy(boundary)
    bad["analysis"]["boundaries"] *= 17
    with pytest.raises(ProfileError):
        make_plan(bad, catalog, hashes, read)
    bad = deepcopy(boundary)
    bad["analysis"]["boundaries"][0]["status"] = "unsupported_transfer"
    with pytest.raises(ProfileError):
        make_plan(bad, catalog, hashes, read)


def test_outside_window_points_are_explicitly_deferred(observation):
    _, _, _, boundary, catalog, hashes, read = observation
    bad = deepcopy(boundary)
    bad["analysis"]["boundaries"][0]["callee"]["boundaries"] = [{"kind": "outside_window", "pc": 0}]
    plan = make_plan(bad, catalog, hashes, read)
    assert plan["boundaries"][0]["deferred_points"] == [{"kind": "outside_window", "pc": 0}]


def test_validate_cli_requires_explicit_capture_inputs(plan_evidence, tmp_path):
    out = tmp_path / "failed.json"
    assert cli.main(["validate", *plan_evidence[0], "--output", str(out)]) == 1
    assert not out.exists()


@pytest.fixture
def rich_plan_evidence(plan_evidence, tmp_path):
    _, original, _, oldfiles = plan_evidence
    files, docs = dict(oldfiles), deepcopy(original)
    payload = bytearray(256)
    payload[32:56] = own_loop()
    struct.pack_into("<I", payload, 24, jump(0x1080, call=True))
    struct.pack_into("<I", payload, 128, special(8, rs=31))
    files["SLES_000.01"] = own_elf(bytes(payload))
    image_path = tmp_path / "rich.iso"
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident="OWN")
    for name, data in files.items():
        iso.add_fp(BytesIO(data), len(data), iso_path=f"/{name};1")
    iso.write(str(image_path))
    iso.close()
    hashes = {"image": digest(image_path.read_bytes())}
    docs["profile"]["files"] = [
        {"path": p, "size": len(data), "sha256": digest(data)} for p, data in files.items()
    ]
    docs["probe"]["source"].update(
        id="iso:" + hashes["image"], sha256=hashes["image"], size=image_path.stat().st_size
    )
    args = ["--iso", str(image_path), "--image-sha256", hashes["image"]]

    def save(name):
        path = tmp_path / ("rich-" + name + ".json")
        path.write_text(json.dumps(docs[name]))
        hashes[name] = digest(path.read_bytes())
        flag = cli.INPUTS[name]
        args.extend(["--" + flag, str(path), "--" + flag + "-sha256", hashes[name]])

    save("profile")
    save("probe")
    reader, profile, size = (
        OwnDisc(files),
        parse_profile(docs["profile"]),
        image_path.stat().st_size,
    )
    docs["consumer"] = survey_consumer(
        reader, profile, docs["probe"], size, hashes["image"], hashes["profile"], hashes["probe"]
    )
    save("consumer")
    docs["pointer"] = survey_pointers(
        reader,
        profile,
        docs["probe"],
        docs["consumer"],
        size,
        hashes["image"],
        hashes["profile"],
        hashes["probe"],
        hashes["consumer"],
    )
    docs["repeat"] = docs["pointer"]
    save("pointer")
    save("repeat")
    docs["boundary"] = survey_boundaries(
        reader,
        profile,
        docs["probe"],
        docs["consumer"],
        docs["pointer"],
        docs["repeat"],
        size,
        hashes,
    )
    docs["boundary_repeat"] = docs["boundary"]
    save("boundary")
    save("boundary_repeat")
    docs["catalog"]["source"] = docs["boundary"]["source"]
    save("catalog")
    return args, docs, hashes, files


@pytest.fixture
def validation_args(rich_plan_evidence, tmp_path):
    args, _, _, files = rich_plan_evidence
    plan_path = tmp_path / "rich-plan.json"
    assert cli.main(["plan", *args, "--output", str(plan_path)]) == 0
    plan = json.loads(plan_path.read_text())
    assert len(plan["boundaries"]) == 1
    env = {
        "emulator": "own",
        "version": "1",
        "binary_sha256": "a" * 64,
        "bios_sha256": "b" * 64,
        "configuration_sha256": "c" * 64,
        "cpu": "EE",
        "method": "manual-debugger-v1",
    }
    b = plan["boundaries"][0]
    points = [p for p in b["points"] if p["phase"] != "checkpoint"]
    events = []
    for seq, p in enumerate(points, 1):
        registers = {str(r): "00001234" for r in p["registers"]}
        registers["31"] = f"{points[2]['pc']:08x}"
        events.append(
            {
                "sequence": seq,
                "session_id": "a" * 32,
                "environment_sha256": object_hash(env),
                "boundary_id": b["id"],
                "point_id": p["id"],
                "pc": p["pc"],
                "registers": registers,
            }
        )
    capture = {
        "schema_version": 1,
        "kind": "sh3-runtime-capture",
        "session_id": "a" * 32,
        "status": "complete",
        "plan_sha256": digest(plan_path.read_bytes()),
        "image_sha256": plan["source"]["sha256"],
        "executable_sha256": plan["executable"]["sha256"],
        "catalog_sha256": plan["catalog_sha256"],
        "environment": env,
        "outcomes": {b["id"]: "observed"},
        "events": events,
        "code_snapshots": [
            {"range_id": r["id"], "size": r["end"] - r["start"], "sha256": r["sha256"]}
            for r in plan["code_ranges"]
        ],
        "data_samples": [],
    }
    private = tmp_path / "rich-private"
    private.mkdir(mode=0o700)
    for r in plan["code_ranges"]:
        write_private(
            private,
            r["sha256"] + ".bin",
            files["SLES_000.01"][r["file_offset"] : r["file_offset"] + r["end"] - r["start"]],
        )
    raw = json.dumps(capture).encode()
    write_private(private, "capture.json", raw)
    return [
        "validate",
        *args,
        "--plan",
        str(plan_path),
        "--plan-sha256",
        digest(plan_path.read_bytes()),
        "--private-root",
        str(private),
        "--capture-sha256",
        digest(raw),
    ]


def test_nonempty_full_chain_validation_receipt_and_repeat(validation_args, tmp_path):
    paths = [tmp_path / "receipt-a.json", tmp_path / "receipt-b.json"]
    for path in paths:
        assert cli.main([*validation_args, "--output", str(path)]) == 0
    assert paths[0].read_bytes() == paths[1].read_bytes()
    receipt = json.loads(paths[0].read_text())
    assert receipt["event_count"] == 3 and receipt["status"] == "validated_observations"
    assert receipt["comparisons"][0]["entry_copy_comparison"] == "not_applicable"


@pytest.mark.parametrize("variant", ["plan", "capture", "private_close", "iso_close", "output"])
def test_validation_late_errors_never_publish(
    validation_args, tmp_path, monkeypatch, variant, capsys
):
    args = list(validation_args)
    if variant == "plan":
        path = Path(args[args.index("--plan") + 1])
        doc = json.loads(path.read_text())
        doc["status"] = "forged"
        path.write_text(json.dumps(doc))
        args[args.index("--plan-sha256") + 1] = digest(path.read_bytes())
    elif variant == "capture":
        args[args.index("--capture-sha256") + 1] = "f" * 64
    elif variant in ("private_close", "iso_close"):
        base = PrivateCaptureReader if variant == "private_close" else IsoImage

        class Changed(base):
            def __exit__(self, *a):
                super().__exit__(*a)
                raise ProfileError("OWN_CHANGED", "private detail")

        monkeypatch.setattr(
            cli, "PrivateCaptureReader" if variant == "private_close" else "IsoImage", Changed
        )
    else:

        def fail(*_):
            raise OSError("private detail")

        monkeypatch.setattr(cli, "publish_report", fail)
    out = tmp_path / "failed.json"
    assert cli.main([*args, "--output", str(out)]) == 1 and not out.exists()
    assert "private detail" not in capsys.readouterr().out
