"""Synthetic cases only; no game bytes."""

import struct

import pytest

from tools.inspectors.pcsx2_gs_dump import REG_SIZE, STATE_SIZE, Dump


def fixture(records):
    serial = b"SYNTHETIC"
    header = (
        struct.pack("<9I", 9, STATE_SIZE, 36, len(serial), 123, 0, 0, 36 + len(serial), 0) + serial
    )
    state = struct.pack("<I", 9) + bytes(STATE_SIZE - 4)
    return struct.pack("<II", 0xFFFFFFFF, len(header)) + header + state + bytes(REG_SIZE) + records


def transfer(path, data):
    return b"\0" + struct.pack("<BI", path, len(data)) + data


def tag(loops=1, regs=0xE, nreg=1, flag=0):
    return struct.pack("<QQ", loops | (flag << 58) | (nreg << 60), regs)


def test_interleaved_paths_preserve_partial_packets():
    a, b = bytes(range(16)), bytes(reversed(range(16)))
    data = transfer(2, tag(2) + a) + transfer(1, tag() + b) + b"\1\0" + transfer(2, a)
    packets = list(Dump(fixture(data)).packets())
    assert [(p.path, p.frame, p.payload) for p in packets] == [(1, 0, b), (2, 0, a * 2)]


@pytest.mark.parametrize("flag,payload", [(1, bytes(32)), (2, bytes(16)), (3, bytes(16))])
def test_reglist_padding_and_image(flag, payload):
    data = transfer(3, tag(nreg=3, flag=flag) + payload + tag(0))
    packets = list(Dump(fixture(data)).packets())
    assert len(packets) == 2 and packets[0].payload == payload and packets[1].payload == b""


def test_zero_nreg_means_sixteen_and_packed_primitive_is_preserved():
    low = 1 | (1 << 46) | (60 << 47)
    data = transfer(3, struct.pack("<QQ", low, 0xEEEEEEEEEEEEEEEE) + bytes(256))
    (packet,) = Dump(fixture(data)).packets()
    assert packet.fields == dict(nloop=1, pre=1, prim=60, flag=0, nreg=16, regs=0xEEEEEEEEEEEEEEEE)
    assert len(packet.payload) == 256


@pytest.mark.parametrize(
    "data",
    [
        b"\4",
        b"\0",
        b"\0\2\20\0\0",
        transfer(4, tag()),
        b"\0\2\1\0\0\0\0",
        b"\1\2",
        b"\3",
        b"\2\0\0\0",
        transfer(0, tag()),
        transfer(0, tag() + bytes(16))[:-1],
    ],
)
def test_rejects_malformed_records_or_incomplete_packets(data):
    with pytest.raises(ValueError):
        list(Dump(fixture(data)).packets())


def test_rejects_truncated_header():
    with pytest.raises(ValueError):
        Dump(fixture(b"")[:100])


def test_active_initial_path_requires_explicit_decoder():
    data = bytearray(fixture(b""))
    pos = 8 + 36 + len(b"SYNTHETIC") + STATE_SIZE - 84
    data[pos] = 1
    with pytest.raises(ValueError, match="active"):
        Dump(data)
