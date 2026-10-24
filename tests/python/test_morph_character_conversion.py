"""Pinned synthetic ISO -> morph/material bundles, including exclusive writes."""

import hashlib
import json
from io import BytesIO

import pycdlib
import pytest
from test_mfa import sector
from test_morph_materials import textured_morph

from tools.pipeline import decode_morph_character as coordinator
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.profile import ProfileError


@pytest.fixture
def selection(tmp_path):
    mdl, _, _ = textured_morph()
    animation = b"independent ANM identity; decoded in another pipeline"
    offset = (len(mdl) + 2047) // 2048 * 2048
    payload = mdl + bytes(offset - len(mdl)) + animation + bytes(2048 - len(animation))
    archive = (
        sector(
            ("model", "animation"),
            data_size=len(payload),
            ranges=[(0, len(mdl)), (offset, len(animation))],
        )
        + payload
    )
    disc = pycdlib.PyCdlib()
    disc.new(interchange_level=3)
    disc.add_fp(BytesIO(archive), len(archive), iso_path="/OWN.MFA;1")
    path = tmp_path / "own.iso"
    disc.write(str(path))
    disc.close()

    def sha(b):
        return hashlib.sha256(b).hexdigest()

    document = dict(
        schema_version=1,
        image_size=path.stat().st_size,
        image_sha256=sha(path.read_bytes()),
        container=dict(path="OWN.MFA", size=len(archive), sha256=sha(archive), layout="d8"),
        model=dict(ordinal=1, size=len(mdl), sha256=sha(mdl)),
        animation=dict(ordinal=2, size=len(animation), sha256=sha(animation)),
    )
    selected = tmp_path / "selection.json"
    selected.write_text(json.dumps(document))
    root = tmp_path / "private"
    root.mkdir()
    args = [
        "--iso",
        str(path),
        "--selection",
        str(selected),
        "--selection-sha256",
        sha(selected.read_bytes()),
        "--private-root",
        str(root),
        "--run-id",
        "first",
    ]
    return path, document, root, args


def test_conversion_is_deterministic_and_preserves_all_geometry(selection, tmp_path):
    path, document, root, _ = selection
    with IsoImage(path) as reader:
        files, report = coordinator.decode_selected(reader, document)
    with IsoImage(path) as reader:
        again = coordinator.decode_selected(reader, document)
    assert again == (files, report)
    geometry = json.loads(files["geometry.json"])
    assert geometry["targets"][0]["position_deltas"] == [[1, -2, 3, 2], [4, 5, -6, 0]]
    assert report["summary"]["morph_targets"] == 1 and report["capabilities"] == []
    assert len(files["texture-0.rgba"]) == 128 * 128 * 4
    assert len(files["image-0-selector-7.bin"]) == 16 * 4
    repository = tmp_path / "repo"
    repository.mkdir()
    a = coordinator.write_morph_bundle(root, repository, "a", files, report)
    b = coordinator.write_morph_bundle(root, repository, "b", files, report)
    assert a == b
    for name, data in files.items():
        assert (root / "a" / name).read_bytes() == data == (root / "b" / name).read_bytes()
    with pytest.raises(FileExistsError):
        coordinator.write_morph_bundle(root, repository, "a", files, report)
    with pytest.raises(ProfileError) as rejected:
        coordinator.write_morph_bundle(
            root, repository, "extra", {**files, "../escape": b"x"}, report
        )
    assert rejected.value.code == "PX_OUTPUT_SET"


def test_cli_success_and_occupied_destination(selection, capsys):
    _, _, root, args = selection
    assert coordinator.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["morph_targets"] == 1 and (root / "first/manifest.json").is_file()
    assert coordinator.main(args) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "HI_IO_ERROR"


def test_cli_rejects_wrong_identity_without_creating_output(selection, capsys):
    _, _, root, args = selection
    args[args.index("--selection-sha256") + 1] = "0" * 64
    assert coordinator.main(args) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "rejected"
    assert list(root.iterdir()) == []


@pytest.mark.parametrize(
    "document",
    [
        None,
        {},
        {"selectors": [], "textures": [0]},
        {"selectors": [[0, 1]], "textures": [0]},
        {"selectors": [[False, True, 4, 5]], "textures": [0]},
        {"selectors": [None], "textures": [0]},
        {"selectors": [list(range(8))], "textures": []},
    ],
)
def test_writer_rejects_bad_output_contract(tmp_path, document):
    with pytest.raises(ValueError, match="HI_OUTPUT_SET"):
        coordinator.write_morph_bundle(
            tmp_path, tmp_path / "repo", "x", {"materials.json": json.dumps(document).encode()}, {}
        )


def test_writer_rejects_malformed_json(tmp_path):
    with pytest.raises(ValueError, match="HI_OUTPUT_SET"):
        coordinator.write_morph_bundle(
            tmp_path, tmp_path / "repo", "x", {"materials.json": b"{"}, {}
        )
