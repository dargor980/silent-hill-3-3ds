"""Independent asymmetric oracles for the static MAP coordinate contract."""

import json
import struct
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tools.pipeline.decoders.ps2_map_geometry import decode_shape, encode_vertices
from tools.pipeline.geometry_transform import MapAffine, inspection_basis, material_uv

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/synthetic/geometry-conventions-v1.json"
IDENTITY = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


@pytest.fixture
def example():
    return json.loads(FIXTURE.read_text())


def normal(a, b, c):
    ab = [b[i] - a[i] for i in range(3)]
    ac = [c[i] - a[i] for i in range(3)]
    return (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )


def volume6(points):
    a, b, c, d = points
    n = normal(a, b, c)
    return sum(n[i] * (d[i] - a[i]) for i in range(3))


def test_asymmetric_strip_preserves_world_units_orientation_and_original_words(example):
    raw = b"".join(
        struct.pack("<8h", *p, 17, *uv, -29, 31)
        for p, uv in zip(example["local_positions"], example["uv_words"], strict=True)
    )
    geometry = decode_shape(raw, 4)
    assert encode_vertices(geometry.vertices) == raw
    assert geometry.triangles == tuple(map(tuple, example["expected_triangles"]))
    model = MapAffine(example["model_columns"])
    world = [model.transform_point(v.position) for v in geometry.vertices]
    adapted = [inspection_basis(p) for p in world]
    assert world == list(map(tuple, example["expected_world"]))
    assert adapted == list(map(tuple, example["expected_basis"]))
    assert [material_uv(v.uv_words) for v in geometry.vertices] == list(
        map(tuple, example["expected_uv"])
    )
    assert volume6(example["local_positions"]) == example["expected_local_volume6"]
    assert volume6(world) == example["expected_world_volume6"]
    assert volume6(adapted) == example["expected_world_volume6"]
    assert normal(*world[:3]) == tuple(example["expected_first_world_normal"])
    assert normal(*adapted[:3]) == tuple(example["expected_first_basis_normal"])
    # The old OBJ/checker view has a distinct, explicitly named UV convention.
    for vertex, uv in zip(geometry.vertices, example["expected_uv"], strict=True):
        assert vertex.uv_reference == (uv[0], 1 - uv[1])


@pytest.mark.parametrize(
    "mistake",
    ["transpose", "double_model", "basis_first", "reflection", "winding", "flip_v", "mask_u"],
)
def test_fixture_detects_wrong_conventions(example, mistake):
    """Deliberately wrong alternatives must disagree with the fixed numeric oracle."""
    model = example["model_columns"]
    points = example["local_positions"]
    expected = example["expected_basis"]
    if mistake == "transpose":
        # Wrong row-major affine application; deliberately do not use production math.
        observed = [
            [sum(model[r * 4 + c] * (*p, 1)[c] for c in range(4)) for r in range(3)] for p in points
        ]
        assert observed != example["expected_world"]
    elif mistake == "double_model":
        observed = [MapAffine(model).transform_point(p) for p in example["expected_world"]]
        assert observed != list(map(tuple, example["expected_world"]))
    elif mistake == "basis_first":
        observed = [MapAffine(model).transform_point(inspection_basis(p)) for p in points]
        assert observed != list(map(tuple, expected))
    elif mistake == "reflection":
        observed = [(x, -y, z) for x, y, z in example["expected_world"]]
        assert observed != list(map(tuple, expected))
        assert volume6(observed) == -example["expected_world_volume6"]
    elif mistake == "winding":
        a, b, c = expected[:3]
        assert normal(a, c, b) != tuple(example["expected_first_basis_normal"])
    elif mistake == "flip_v":
        observed = [(u / 32768, 1 - v / 32768) for u, v in example["uv_words"]]
        assert all(p != tuple(q) for p, q in zip(observed, example["expected_uv"], strict=True))
    else:
        observed = [((u & ~1) / 32768, v / 32768) for u, v in example["uv_words"]]
        assert observed[0] != tuple(example["expected_uv"][0])
        assert observed[1] != tuple(example["expected_uv"][1])


def test_model_snapshots_input_and_is_immutable():
    columns = list(IDENTITY)
    model = MapAffine(columns)
    columns[0] = float("nan")
    assert model.transform_point((1, -2, 3)) == (1, -2, 3)
    with pytest.raises(FrozenInstanceError):
        model.columns = IDENTITY


@pytest.mark.parametrize("bad", [None, {}, "matrix", [], [0] * 15, [0] * 17])
def test_rejects_malformed_model(bad):
    with pytest.raises(ValueError):
        MapAffine(bad)


@pytest.mark.parametrize(
    ("index", "value"),
    [
        (0, True),
        (0, "1"),
        (0, float("nan")),
        (0, float("inf")),
        (0, -float("inf")),
        (0, 10**400),
        (0, 1_000_001),
        (12, -1_000_001),
        (3, 1),
        (7, 1),
        (11, 1),
        (15, 0),
        (0, 0),
        (0, -1),
        (0, 1e-8),
    ],
)
def test_rejects_unsupported_affine_model(index, value):
    model = list(IDENTITY)
    model[index] = value
    with pytest.raises(ValueError):
        MapAffine(model)


def test_accepts_documented_model_bounds():
    model = MapAffine((1e-7, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1e6, -1e6, 1e6, 1))
    assert model.transform_point((0, 0, 0)) == (1e6, -1e6, 1e6)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "point",
        [1, 2],
        [1, 2, 3, 4],
        [True, 0, 0],
        [0, float("nan"), 0],
        [0, 0, "3"],
        [10**400, 0, 0],
    ],
)
def test_rejects_malformed_points(bad):
    with pytest.raises(ValueError):
        MapAffine(IDENTITY).transform_point(bad)
    with pytest.raises(ValueError):
        inspection_basis(bad)


def test_rejects_nonfinite_result():
    model = list(IDENTITY)
    model[0] = 1e6
    with pytest.raises(ValueError):
        MapAffine(model).transform_point((1e308, 0, 0))


@pytest.mark.parametrize(
    "bad", [None, {}, "uv", [], [0], [0, 0, 0], [True, 0], [0, 1.0], [-32769, 0], [0, 32768]]
)
def test_rejects_uv_that_are_not_original_i16_words(bad):
    with pytest.raises(ValueError):
        material_uv(bad)


def test_signed_uv_endpoints_are_preserved():
    assert material_uv((-32768, 32767)) == (-1, 32767 / 32768)
