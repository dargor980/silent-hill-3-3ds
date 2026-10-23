"""Bounded immutable asset inventory checks shared by intermediate import/export."""

import hashlib


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fields(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError("Unexpected intermediate fields")


def digest(value):
    if (
        type(value) is not str
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("Invalid intermediate SHA-256")
    return value


def inventory(manifest, limits, exact=()):
    entries = manifest["files"]
    if type(entries) is not list or len(entries) != len(limits):
        raise ValueError("Unexpected intermediate inventory")
    result = {}
    for entry in entries:
        if type(entry) is not dict:
            raise ValueError("Invalid inventory entry")
        name, size = entry["file"], entry["size"]
        if (
            type(name) is not str
            or name not in limits
            or name in result
            or type(size) is not int
            or not 0 < size <= limits[name]
            or (name in exact and size != limits[name])
        ):
            raise ValueError("Invalid inventory name or size")
        digest(entry["sha256"])
        result[name] = entry
    return result


def verify_file(raw, entry):
    if type(raw) is not bytes or len(raw) != entry["size"] or sha(raw) != digest(entry["sha256"]):
        raise ValueError("Intermediate asset differs")
    return raw
