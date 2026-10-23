"""Synthetic SHBIN regressions for a failure that SDK doubles cannot execute."""

import struct

import pytest

from tools.qa.pica_shader_outputs import main, validate_shader

CODE = 40
DESCRIPTORS = 80
DVLE = 144
OUTPUTS = 208


def put(data, offset, value):
    struct.pack_into("<I", data, offset, value)


@pytest.fixture
def shader():
    data = bytearray(232)
    data[0:4], data[12:16], data[DVLE : DVLE + 4] = b"DVLB", b"DVLP", b"DVLE"
    for offset, value in {
        4: 1,
        8: DVLE,
        20: CODE - 12,
        24: 10,
        28: DESCRIPTORS - 12,
        32: 8,
        DVLE + 12: 10,
        DVLE + 40: OUTPUTS - DVLE,
        DVLE + 44: 3,
    }.items():
        put(data, offset, value)
    # The masks are in PICA instruction order: W is bit 0, X is bit 3.
    for index, mask in enumerate([8, 4, 2, 1, 14, 15, 12, 3]):
        put(data, DESCRIPTORS + index * 8, mask)
    words = [
        0x08020000,  # DP4 o0.x
        0x08021001,  # DP4 o0.y
        0x08022002,  # DP4 o0.z
        0x08023003,  # DP4 o0.w
        0x4C201004,  # MOV o1.xyz
        0x4C27F003,  # MOV o1.w
        0x4C402005,  # MOV o2.xyzw
        0x4E002005,  # MOV r0: scratch is not an output
        0x88000000,  # END
        0x84000000,  # trailing NOP
    ]
    for index, word in enumerate(words):
        put(data, CODE + index * 4, word)
    for index, semantic in enumerate((0, 2, 3)):
        struct.pack_into("<HHI", data, OUTPUTS + index * 8, semantic, index, 15)
    return data


def test_complete_output(shader):
    assert validate_shader(bytes(shader)) == {
        "instructions": 10,
        "output_registers": 3,
        "components": 12,
    }


@pytest.mark.parametrize("descriptor,missing", [(6, "z"), (7, "x")])
def test_partial_output_matching_physical_failure(shader, descriptor, missing):
    put(shader, CODE + 6 * 4, 0x4C402000 | descriptor)
    with pytest.raises(ValueError, match=rf"o2\.{missing}: expected one write, found 0"):
        validate_shader(bytes(shader))


def test_duplicate_component(shader):
    put(shader, CODE + 5 * 4, 0x4C201005)  # color XYZW after XYZ
    with pytest.raises(ValueError, match=r"o1.x: expected one write, found 2"):
        validate_shader(bytes(shader))


@pytest.mark.parametrize("length", [0, 4, 8, 12, 20, 40, 80, 144, 208, 231])
def test_truncated(shader, length):
    with pytest.raises(ValueError, match="truncated"):
        validate_shader(bytes(shader[:length]))


@pytest.mark.parametrize(
    "offset,value,message",
    [
        (0, 0, "one DVLE"),
        (4, 2, "one DVLE"),
        (12, 0, "signature"),
        (DVLE, 0, "signature"),
        (DVLE + 4, 0x10000, "vertex shader"),
        (24, 513, "count"),
        (32, 0, "count"),
        (DVLE + 8, 10, "entrypoint"),
        (DVLE + 12, 11, "entrypoint"),
        (DVLE + 44, 0, "position, color and UV"),
        (OUTPUTS, 1, "semantic"),
        (OUTPUTS + 8, 0x10000, "semantic"),
        (OUTPUTS + 4, 3, "full output"),
        (OUTPUTS + 8, 2, "full output"),
        (OUTPUTS + 8, 0x30002, "full output"),
        (CODE + 9 * 4, 0x4E002005, "after END"),
        (CODE + 6 * 4, 0x90000000, "unsupported instruction"),
        (CODE + 6 * 4, 0x4C40207F, "descriptor outside"),
        (CODE + 6 * 4, 0x4C602005, "undeclared output"),
        (CODE + 8 * 4, 0x84000000, "missing END"),
    ],
)
def test_invalid_program(shader, offset, value, message):
    put(shader, offset, value)
    with pytest.raises(ValueError, match=message):
        validate_shader(bytes(shader))


def test_cli(shader, tmp_path, capsys):
    path = tmp_path / "test.shbin"
    assert main([str(path)]) == 1
    path.write_bytes(shader)
    assert main([str(path)]) == 0
    assert "12 components once" in capsys.readouterr().out
    put(shader, CODE + 6 * 4, 0x4C402006)
    path.write_bytes(shader)
    assert main([str(path)]) == 1
    assert "o2.z" in capsys.readouterr().out
