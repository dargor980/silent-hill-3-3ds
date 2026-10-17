"""OR01-OR08: own resources, changed return registers and bounded comparisons."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_asset_catalog import catalog_source as catalog_source
from test_camera_observation import observation as observation
from test_candidates import extracted as extracted
from test_extraction import inputs as inputs
from test_pcsx2_state import CRC, PC
from test_resource_link import ADDRESS, digest, state_archive
from test_resource_link import link_case as link_case

from tools.inspectors import origin_memory, resource_link
from tools.inspectors import resource_origin as cli
from tools.inspectors.observation_capture import validate_capture
from tools.inspectors.origin_compare import compare_ranges
from tools.inspectors.origin_memory import EntryBase, entry_base, preserved_range
from tools.pipeline.extract_assets import resource_plan
from tools.pipeline.private_output import resource_filename
from tools.pipeline.profile import ProfileError


@pytest.fixture
def own_memory(monkeypatch):
    monkeypatch.setattr(origin_memory, "RAM_SIZE", ADDRESS + 8192)
    event = {
        "pc": PC,
        "registers": {"4": f"{ADDRESS:08x}", "31": "00001234"},
        "session_id": "a" * 32,
        "environment_sha256": "b" * 64,
        "sequence": 2,
    }
    memory = bytearray(origin_memory.RAM_SIZE)
    memory[ADDRESS : ADDRESS + 4096] = bytes(range(256)) * 16
    return event, memory


def test_preserves_base_when_return_register_changes(own_memory):
    event, memory = own_memory
    base = entry_base(state_archive(event, bytes(memory)), CRC, event, 4)
    returned = deepcopy(event)
    returned["sequence"] = 3
    returned["registers"]["4"] = f"{ADDRESS + 4096:08x}"
    memory[ADDRESS + 92] ^= 1
    result = preserved_range(state_archive(returned, bytes(memory)), CRC, returned, base, 1536)
    assert result.data == bytes(memory[ADDRESS : ADDRESS + 1536])
    assert "address" not in repr(base) and "data" not in repr(result)


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", "c" * 32),
        ("environment_sha256", "c" * 64),
        ("sequence", 1),
        ("sequence", True),
    ],
)
def test_cross_state_identity_rejected_before_zip(own_memory, field, value):
    event, memory = own_memory
    base = entry_base(state_archive(event, bytes(memory)), CRC, event, 4)
    event[field] = value
    with pytest.raises(ProfileError) as error:
        preserved_range(b"must not read", CRC, event, base, 1536)
    assert error.value.code == "ORIGIN_SESSION"


@pytest.mark.parametrize("size", [0, -1, 4097, True, 1.0])
def test_range_budgets_before_zip(own_memory, size):
    event, _ = own_memory
    base = EntryBase(ADDRESS, event["session_id"], event["environment_sha256"], 2)
    with pytest.raises(ProfileError):
        preserved_range(b"must not read", CRC, event, base, size)


@pytest.mark.parametrize("register", [0, 32, True, 4.0, 16])
def test_unavailable_anchor_register(own_memory, register):
    event, memory = own_memory
    with pytest.raises(ProfileError):
        entry_base(state_archive(event, bytes(memory)), CRC, event, register)


@pytest.mark.parametrize(
    "address", [0, ADDRESS - 1, 0x20100000, 0x30100000, 0x80100000, 0xA0100000, 0x70000000]
)
def test_anchor_rejects_aliases_and_low_memory(own_memory, address):
    event, memory = own_memory
    event["registers"]["4"] = f"{address:08x}"
    with pytest.raises(ProfileError):
        entry_base(state_archive(event, bytes(memory)), CRC, event, 4)


@pytest.mark.parametrize("variant", ["pc", "gpr", "delay", "crc", "size", "cross_end"])
def test_target_must_match_state_and_range(own_memory, variant):
    event, memory = own_memory
    base = entry_base(state_archive(event, bytes(memory)), CRC, event, 4)
    if variant == "size":
        memory = memory[:-1]
    if variant == "cross_end":
        base = EntryBase(
            origin_memory.RAM_SIZE - 100, base.session, base.environment, base.sequence
        )
    raw = state_archive(event, bytes(memory), delay=int(variant == "delay"))
    if variant == "pc":
        event["pc"] += 4
    if variant == "gpr":
        event["registers"]["31"] = "ffffffff"
    with pytest.raises(ProfileError):
        preserved_range(raw, CRC + int(variant == "crc"), event, base, 1536)


def test_compare_full_boundaries_and_fragmentation():
    left, right = bytes(4096), bytearray(4096)
    right[0:2] = b"ab"
    right[92:94] = b"cd"
    right[-1] = 1
    result = compare_ranges(left, bytes(right))
    assert result["different_bytes"] == 5
    assert result["difference_ranges"] == [
        {"start": 0, "end": 2},
        {"start": 92, "end": 94},
        {"start": 4095, "end": 4096},
    ]
    assert result["reference_sha256"] == digest(left)
    assert compare_ranges(left, left)["equal"]
    alternating = bytes([0, 1]) * 2048
    assert len(compare_ranges(left, alternating)["difference_ranges"]) == 2048


@pytest.mark.parametrize(
    "a,b",
    [(b"", b""), (b"a", b"ab"), (b"x" * 4097, b"x" * 4097), (bytearray(b"a"), b"a"), (b"a", None)],
)
def test_compare_invalid_shapes(a, b):
    with pytest.raises(ProfileError):
        compare_ranges(a, b)


@pytest.mark.parametrize("length", [1, 4096])
def test_supported_range_endpoints(own_memory, length):
    event, memory = own_memory
    raw = state_archive(event, bytes(memory))
    base = entry_base(raw, CRC, event, 4)
    assert preserved_range(raw, CRC, event, base, length).data == bytes(
        memory[ADDRESS : ADDRESS + length]
    )


@pytest.fixture
def origin_case(link_case, monkeypatch):
    c = link_case
    monkeypatch.setattr(origin_memory, "RAM_SIZE", ADDRESS + 4096)
    candidate = bytes(range(256)) + bytes(1280)
    catalog, extraction = c.docs["catalog"], c.docs["extraction"]
    entry = catalog["entries"][0]
    previous_size = entry["size"]
    entry.update(size=len(candidate), sha256=digest(candidate))
    parent = next(p for p in catalog["containers"] if p["id"] == entry["container_id"])
    parent["size"] = max(parent["size"], entry["container_offset"] + len(candidate))
    catalog["summary"]["payload_bytes"] += len(candidate) - previous_size
    resources = resource_plan(catalog)
    extraction.update(resources=resources, summary=deepcopy(catalog["summary"]))
    extraction["copies"] = {
        copy: [{k: r[k] for k in ("id", "file", "size", "sha256")} for r in resources]
        for copy in ("copy-a", "copy-b")
    }
    for root in c.dirs[2:]:
        (root / resource_filename(entry["id"])).write_bytes(candidate)
    catalog_hash = digest(json.dumps(catalog).encode())
    extraction["catalog_sha256"] = catalog_hash
    c.docs["plan"]["catalog_sha256"] = catalog_hash
    plan_hash = digest(json.dumps(c.docs["plan"]).encode())
    memory = bytearray(origin_memory.RAM_SIZE)
    memory[ADDRESS : ADDRESS + len(candidate)] = candidate
    for event, item in zip(c.capture["events"], c.docs["state-index"]["states"], strict=True):
        if event["sequence"] == 4:
            event["registers"]["4"] = f"{ADDRESS + 2048:08x}"
            memory[ADDRESS + 92] ^= 1
        raw = state_archive(event, bytes(memory))
        (c.dirs[1] / item["name"]).write_bytes(raw)
        item["sha256"] = digest(raw)
    c.capture.update(plan_sha256=plan_hash, catalog_sha256=catalog_hash)
    raw = json.dumps(c.capture).encode()
    (c.dirs[0] / "capture.json").write_bytes(raw)
    c.capture_hash = digest(raw)
    c.docs["state-index"]["capture_sha256"] = c.capture_hash
    receipt = validate_capture(
        c.docs["plan"], plan_hash, c.capture, lambda h, n: (c.dirs[0] / (h + ".bin")).read_bytes()
    )
    receipt["capture_sha256"] = c.capture_hash
    c.docs["observation"] = c.docs["observation-repeat"] = receipt
    for name, doc in c.docs.items():
        raw = json.dumps(doc).encode()
        c.paths[name].write_bytes(raw)
        c.args[c.args.index("--" + name + "-sha256") + 1] = digest(raw)
    c.args[c.args.index("--capture-sha256") + 1] = c.capture_hash
    assert resource_link.main(c.args) == 0
    link_path = c.output
    link_hash = digest(link_path.read_bytes())
    c.link = json.loads(link_path.read_text())
    c.request = {
        "schema_version": 1,
        "session_id": c.capture["session_id"],
        "capture_sha256": c.capture_hash,
        "link_sha256": link_hash,
        "resource_id": entry["id"],
        "source_event_sequence": 2,
        "base_register": 4,
        "target_event_sequences": [2, 3, 4],
    }
    c.request_path = c.output.with_name("origin-plan.json")
    c.request_path.write_text(json.dumps(c.request))
    c.args += [
        "--link",
        str(link_path),
        "--link-sha256",
        link_hash,
        "--link-repeat",
        str(link_path),
        "--link-repeat-sha256",
        link_hash,
        "--origin-plan",
        str(c.request_path),
        "--origin-plan-sha256",
        digest(c.request_path.read_bytes()),
    ]
    c.output = c.output.with_name("origin.json")
    c.args[c.args.index("--output") + 1] = str(c.output)
    return c


def test_two_real_cli_chains_identical_and_no_false_origin(origin_case, capsys):
    c = origin_case
    assert cli.main(c.args) == 0
    report = json.loads(c.output.read_text())
    assert report["comparisons"][0]["against_resource"]["equal"]
    assert report["comparisons"][-1]["against_resource"]["different_bytes"] == 1
    assert report["first_observed_change"] == {
        "after_event_sequence": 3,
        "by_event_sequence": 4,
        "difference_ranges": [{"start": 92, "end": 93}],
    }
    assert not report["mapping_verified"] and report["origin_status"] == "pending"
    assert report["resource_links"] == report["capabilities"] == []
    assert all(
        s not in c.output.read_text() for s in ("00100000", "registers", "address", str(c.dirs[0]))
    )
    args = c.args.copy()
    repeated = c.output.with_name("origin-repeat.json")
    args[args.index("--output") + 1] = str(repeated)
    assert cli.main(args) == 0 and repeated.read_bytes() == c.output.read_bytes()
    assert cli.main(c.args) == 1 and "OUTPUT_EXISTS" in capsys.readouterr().out


def test_equal_endpoints_do_not_claim_no_writes_or_origin(origin_case):
    c = origin_case
    c.request["target_event_sequences"] = [2, 3]
    c.request_path.write_text(json.dumps(c.request))
    c.args[c.args.index("--origin-plan-sha256") + 1] = digest(c.request_path.read_bytes())
    assert cli.main(c.args) == 0
    report = json.loads(c.output.read_text())
    assert report["first_observed_change"] is None
    assert report["origin_status"] == "pending" and not report["mapping_verified"]


@pytest.mark.parametrize("variant", ["size", "offset", "length", "no_source"])
def test_candidate_requires_bounded_full_resource_and_source_hit(origin_case, variant):
    c = origin_case
    link = deepcopy(c.link)
    if variant == "size":
        for match in link["matches"]:
            match["resource_size"] = 4097
    elif variant == "offset":
        for match in link["matches"]:
            match["resource_offset"] = 1
    else:
        for sample in link["samples"]:
            sample["length" if variant == "length" else "event_sequence"] = 64
    with pytest.raises(ProfileError):
        cli.validate_origin_plan(
            c.request,
            c.capture,
            c.docs["plan"],
            link,
            {"link": c.request["link_sha256"]},
            c.capture_hash,
        )


def test_unequal_receipt_hashes_stop_before_io():
    with pytest.raises(ProfileError):
        cli.collect_origin_report(
            {},
            {"link": "a" * 64, "link-repeat": "b" * 64},
            None,
            None,
            None,
            None,
            None,
            None,
        )


def test_late_capture_close_prevents_publication(origin_case, monkeypatch):
    class FailingCapture(cli.PrivateCaptureReader):
        def __exit__(self, *args):
            super().__exit__(*args)
            raise OSError("private close error")

    monkeypatch.setattr(cli, "PrivateCaptureReader", FailingCapture)
    assert cli.main(origin_case.args) == 1 and not origin_case.output.exists()


def test_late_candidate_mutation_prevents_publication(origin_case, monkeypatch):
    c = origin_case
    original = cli.preserved_range

    def mutate(*args):
        result = original(*args)
        path = c.dirs[2] / resource_filename(c.request["resource_id"])
        path.write_bytes(b"private late change")
        return result

    monkeypatch.setattr(cli, "preserved_range", mutate)
    assert cli.main(c.args) == 1 and not c.output.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", "f" * 32),
        ("capture_sha256", "f" * 64),
        ("link_sha256", "f" * 64),
        ("schema_version", True),
        ("source_event_sequence", True),
        ("source_event_sequence", 1),
        ("base_register", 6),
        ("base_register", True),
        ("target_event_sequences", [2]),
        ("target_event_sequences", [2, 2]),
        ("target_event_sequences", [2, 1]),
        ("target_event_sequences", [2, True]),
        ("target_event_sequences", [2, 99]),
        ("resource_id", "asset:" + "f" * 64),
    ],
)
def test_plan_rejects_wrong_identity_anchor_order_and_candidate(origin_case, field, value):
    c = origin_case
    request = {**c.request, field: value}
    with pytest.raises(ProfileError):
        cli.validate_origin_plan(
            request,
            c.capture,
            c.docs["plan"],
            c.link,
            {"link": c.request["link_sha256"]},
            c.capture_hash,
        )


@pytest.mark.parametrize(
    "variant",
    [
        "hash",
        "repeat",
        "forged_link",
        "late_close",
        "copy_disagreement",
        "source_state_changed",
        "write_failure",
    ],
)
def test_cli_failure_does_not_publish(origin_case, variant, monkeypatch, capsys):
    c = origin_case
    capsys.readouterr()
    if variant == "hash":
        c.args[c.args.index("--origin-plan-sha256") + 1] = "f" * 64
    elif variant == "repeat":
        monkeypatch.setattr(cli, "collect_link_report", lambda *a: {})
    elif variant == "forged_link":
        path = Path(c.args[c.args.index("--link") + 1])
        path.write_text("{}")
        for flag in ("--link-sha256", "--link-repeat-sha256"):
            c.args[c.args.index(flag) + 1] = digest(path.read_bytes())
    elif variant == "late_close":
        original = cli.OriginResourceReader.__exit__

        def fail(self, *args):
            original(self, *args)
            raise OSError("private detail")

        monkeypatch.setattr(cli.OriginResourceReader, "__exit__", fail)
    elif variant == "copy_disagreement":
        original = cli.OriginResourceReader.candidate

        def changed(self, resource):
            result = original(self, resource)
            return bytes(len(result)) if self.root == c.dirs[3] else result

        monkeypatch.setattr(cli.OriginResourceReader, "candidate", changed)
    elif variant == "source_state_changed":
        original = cli.preserved_range

        def mutate(*args):
            result = original(*args)
            path = c.dirs[1] / c.docs["state-index"]["states"][1]["name"]
            path.write_bytes(b"private changed state")
            return result

        monkeypatch.setattr(cli, "preserved_range", mutate)
    else:

        def fail(*args):
            raise OSError("private detail")

        monkeypatch.setattr(cli, "publish_report", fail)
    assert cli.main(c.args) == 1 and not c.output.exists()
    assert "private detail" not in capsys.readouterr().out
