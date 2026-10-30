"""Fail-closed controls for the compiler-report memory gate."""

import pytest

from tests.room_contacts_stack import verify


def reports(path, count=128, kind="static"):
    (path / "room_contacts.cpp.su").write_text(f"core\t{count}\t{kind}\n")
    (path / "room_movement_contacts.cpp.su").write_text("adapter\t16\tstatic\n")


def graphs(path, callee="memcpy"):
    (path / "room_contacts.cpp.ci").write_text(
        'node: { title: "core" label: "core\\n128 bytes (static)" }\n'
        f'edge: {{ sourcename: "core" targetname: "{callee}" }}\n'
    )
    (path / "room_movement_contacts.cpp.ci").write_text(
        'node: { title: "prepare" label: "RoomMovementContacts::prepare(\\n16 bytes (static)" }\n'
        'node: { title: "resolve" label: "RoomMovementContacts::resolve(\\n16 bytes (static)" }\n'
        'edge: { sourcename: "prepare" targetname: "core" }\n'
        'edge: { sourcename: "resolve" targetname: "core" }\n'
    )


@pytest.mark.parametrize("with_graph", [False, True])
def test_counts_frames_and_leaf_reserve(tmp_path, with_graph):
    reports(tmp_path)
    if with_graph:
        graphs(tmp_path)
    result = verify(tmp_path)
    assert result["conservative_stack"] == 272
    assert result["conservative_total"] == 848
    assert result["gcc_graph_checked"] is with_graph


@pytest.mark.parametrize("count,kind", [(2500, "static"), (-1, "static"), (10, "dynamic")])
def test_rejects_oversized_or_unbounded_frames(tmp_path, count, kind):
    reports(tmp_path, count, kind)
    with pytest.raises(ValueError):
        verify(tmp_path)


@pytest.mark.parametrize("problem", ["missing", "empty", "duplicate"])
def test_rejects_incomplete_or_ambiguous_reports(tmp_path, problem):
    reports(tmp_path)
    if problem == "missing":
        (tmp_path / "room_contacts.cpp.su").unlink()
    elif problem == "empty":
        (tmp_path / "room_contacts.cpp.su").write_text("")
    else:
        (tmp_path / "room_contacts.su").write_text("duplicate\t16\tstatic\n")
    with pytest.raises(ValueError):
        verify(tmp_path)


@pytest.mark.parametrize("callee", ["core", "malloc", "indirect"])
def test_rejects_recursion_or_unaccounted_calls(tmp_path, callee):
    reports(tmp_path)
    graphs(tmp_path, callee)
    with pytest.raises(ValueError):
        verify(tmp_path)


def test_requires_both_graphs(tmp_path):
    reports(tmp_path)
    graphs(tmp_path)
    (tmp_path / "room_movement_contacts.cpp.ci").unlink()
    with pytest.raises(ValueError):
        verify(tmp_path)
