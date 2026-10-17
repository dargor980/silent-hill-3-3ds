"""Bounded name diagnostics; codec success never selects an original encoding."""

from tools.pipeline.profile import ProfileError

CODEC_CANDIDATES = ("utf-8", "shift_jis", "cp932")


def name_diagnostics(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > 1024:
        raise ProfileError("NAME_DIAGNOSTIC_LIMIT", "Expected at most 1024 name bytes")
    codecs = {}
    for codec in CODEC_CANDIDATES:
        try:
            decoded = raw.decode(codec, errors="strict")
        except UnicodeDecodeError:
            codecs[codec] = {"decodes": False, "round_trip": False}
        else:
            codecs[codec] = {
                "decodes": True,
                "round_trip": decoded.encode(codec, errors="strict") == raw,
            }
    return {
        "reason": "unsupported_name_bytes",
        "name_bytes": len(raw),
        "non_ascii_bytes": sum(byte > 127 for byte in raw),
        "control_bytes": sum(byte < 32 or byte == 127 for byte in raw),
        "codec_candidates": codecs,
        "encoding": "unresolved",
    }
