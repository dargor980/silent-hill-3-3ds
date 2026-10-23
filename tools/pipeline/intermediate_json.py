"""Bounded project-canonical JSON, retaining all finite JSON values and types."""

import json
import math

MAX_BYTES = 8 * 1024 * 1024
MAX_NODES = 500_000
MAX_DEPTH = 32
MAX_STRING = 65_536


def validate_tree(value):
    remaining = MAX_NODES
    text_bytes = 0

    def visit(item, depth):
        nonlocal remaining, text_bytes
        remaining -= 1
        if remaining < 0 or depth > MAX_DEPTH:
            raise ValueError("Intermediate tree budget exceeded")
        kind = type(item)
        if kind is dict:
            for key, child in item.items():
                if type(key) is not str or len(key) > 256:
                    raise ValueError("Invalid intermediate key")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif kind is list:
            for child in item:
                visit(child, depth + 1)
        elif kind is str:
            if len(item) > MAX_STRING:
                raise ValueError("Intermediate string budget exceeded")
            text_bytes += len(item.encode("utf-8", errors="strict"))
            if text_bytes > MAX_BYTES:
                raise ValueError("Intermediate text budget exceeded")
        elif kind is int:
            if not -(1 << 63) <= item < 1 << 64:
                raise ValueError("Intermediate integer out of range")
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("Nonfinite intermediate number")
        elif item is not None and kind is not bool:
            raise ValueError("Unsupported intermediate value")

    visit(value, 0)


def encode_json(value):
    validate_tree(value)
    raw = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()
    if len(raw) > MAX_BYTES:
        raise ValueError("Intermediate byte budget exceeded")
    return raw


def decode_json(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("Invalid intermediate input size")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate intermediate key")
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError("Nonfinite intermediate literal")

    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    except RecursionError as error:
        raise ValueError("Intermediate tree budget exceeded") from error
    validate_tree(result)
    return result
