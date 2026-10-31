"""Reject incomplete, recursive or oversized compiler stack evidence."""

import pytest

from tests.heather_turns_stack import UNITS, analyze, verify


def test_accounting_and_duplicate_emission():
    result = analyze(["frame\t64\tstatic", "frame\t32\tstatic", "introsort\t48\tstatic"])
    assert result["frame_sum"] == 112
    assert result["sort_recursion_extra"] == 26 * 48
    assert result["total_with_reserve"] == 112 + 26 * 48 + 8192
    assert not result["physical_stack_measured"]


@pytest.mark.parametrize("row", ["f\t1\tdynamic", "f\t-1\tstatic", "f\t8193\tstatic"])
def test_invalid_frame(row):
    with pytest.raises(ValueError, match="Unbounded"):
        analyze([row])


def test_empty_and_total_limit():
    with pytest.raises(ValueError, match="Missing"):
        analyze([])
    with pytest.raises(ValueError, match="exceeded"):
        analyze([f"f{i}\t8192\tstatic" for i in range(4)])
    assert analyze(["f\t16\tdynamic,bounded"])["frame_sum"] == 16


def graph(name="f", child="f"):
    return (
        f'node: {{ title: "{name}" label: "{name} 16 bytes (static)" }}\n'
        f'edge: {{ sourcename: "{name}" targetname: "{child}" }}'
    )


def test_recursion_and_external_calls():
    with pytest.raises(ValueError, match="recursion"):
        analyze(["f\t16\tstatic"], [graph()])
    with pytest.raises(ValueError, match="recursion"):
        analyze(["f\t16\tstatic"], [graph("a", "b"), graph("b", "a")])
    assert analyze(["introsort\t16\tstatic"], [graph("introsort", "introsort")])[
        "direct_graph_checked"
    ]
    result = analyze(["f\t16\tstatic"], [graph("f", "memcpy"), graph("g", "f")])
    assert result["external_calls"] == ["memcpy"]


def test_missing_units(tmp_path):
    with pytest.raises(ValueError, match="Missing production"):
        verify(tmp_path)


def test_verify_requires_all_graphs_and_units(tmp_path):
    paths = []
    for unit in UNITS:
        path = tmp_path / "CMakeFiles/test.dir" / (unit + ".su")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{unit}\t16\tstatic\n")
        paths.append(path)
    assert len(verify(tmp_path)["units"]) == len(UNITS)
    paths[0].with_suffix(".ci").write_text(graph("f", "memcpy"))
    with pytest.raises(ValueError, match="Incomplete GCC"):
        verify(tmp_path)
    with pytest.raises(ValueError, match="Empty GCC"):
        analyze(["f\t16\tstatic"], ["malformed graph"])
