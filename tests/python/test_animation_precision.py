"""Own endpoint vectors; independent exact-rational accumulation controls."""

import math
import struct
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

from tools.qa.animation_precision import reconstruct_quaternion_f32


def floor_positive_f32(value):
    """Quantize a rational using an integer significand, without float casts."""
    if value == 0:
        return value
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    unit = Fraction(2) ** exponent
    if unit > value:
        exponent -= 1
    quantum = Fraction(2) ** (exponent - 23)
    return (value // quantum) * quantum


def rational_reference(words):
    squares = [floor_positive_f32(Fraction(w * w, 32768**2)) for w in words]
    total = floor_positive_f32(floor_positive_f32(squares[0] + squares[1]) + squares[2])
    radicand = max(Fraction(0), 1 - total)
    with localcontext() as context:
        context.prec = 70
        root = (Decimal(radicand.numerator) / Decimal(radicand.denominator)).sqrt()
    return struct.unpack("<f", struct.pack("<f", float(root)))[0]


@pytest.mark.parametrize(
    "words,w_hex",
    [
        ((0, 0, 0), "0000803f"),
        ((16384, 0, 0), "d7b35d3f"),
        ((32760, 500, 300), "11a0563c"),
        ((23170, 23170, 0), "89d6d13b"),
        ((32767, 256, 0), "00000000"),
        ((-32768, 0, 0), "00000000"),
    ],
)
def test_literal_endpoints_and_independent_rational_reference(words, w_hex):
    result = reconstruct_quaternion_f32(words, negative_w=False)
    assert result[:3] == tuple(w / 32768 for w in words)
    assert struct.pack("<f", result[3]).hex() == w_hex
    assert result[3] == rational_reference(words)
    negative = reconstruct_quaternion_f32(list(words), negative_w=True)
    assert negative[:3] == result[:3]
    assert negative[3] == -result[3] and math.copysign(1, negative[3]) == -1


def test_precision_control_distinguishes_double_endpoints():
    words = (32760, 500, 300)
    w = reconstruct_quaternion_f32(words, negative_w=False)[3]
    mathematical = math.sqrt(1 - sum((v / 32768) ** 2 for v in words))
    assert abs(w - mathematical) > 1e-6


@pytest.mark.parametrize("words", [(20001, 15001, 10001), (30001, 9999, 1), (18001, -18003, 18005)])
def test_rounding_up_in_host_arithmetic_is_removed(words):
    q = reconstruct_quaternion_f32(words, negative_w=False)
    assert q[3] == rational_reference(words)


@pytest.mark.parametrize(
    "words",
    [
        None,
        "123",
        b"123",
        (),
        (1, 2),
        (1, 2, 3, 4),
        (True, 0, 0),
        (0.0, 0, 0),
        (-32769, 0, 0),
        (32768, 0, 0),
    ],
)
def test_malformed_words_rejected(words):
    with pytest.raises(ValueError, match="i16"):
        reconstruct_quaternion_f32(words, negative_w=False)


@pytest.mark.parametrize("sign", [0, 1, None, "negative"])
def test_sign_must_be_boolean(sign):
    with pytest.raises(ValueError, match="boolean"):
        reconstruct_quaternion_f32((0, 0, 0), negative_w=sign)


def test_large_nonunit_input_is_outside_profile():
    with pytest.raises(ValueError, match="norm"):
        reconstruct_quaternion_f32((32767, 32767, 32767), negative_w=False)
