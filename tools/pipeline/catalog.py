"""Pure comparison with explicitly supplied catalog metadata; never fetches URLs."""

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

from tools.pipeline.profile import ProfileError


@dataclass(frozen=True)
class CatalogReference:
    reference_id: str
    source_url: str
    retrieved_on: str
    serial: str
    region: str
    revision: str
    languages: tuple[str, ...]
    image_size: int
    checksums: tuple[tuple[str, str], ...]


def _text(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ProfileError("INVALID_CATALOG", f"Invalid catalog field: {key}")
    return value


def parse_catalog(data: object) -> CatalogReference:
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        raise ProfileError("INVALID_CATALOG", "Missing integer catalog schema_version")
    if data["schema_version"] != 1:
        raise ProfileError("INVALID_CATALOG", "Only catalog schema 1 is supported")
    reference_id = _text(data, "id")
    serial = _text(data, "serial")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", reference_id) or not re.fullmatch(
        r"[A-Z]{4}-\d{5}", serial
    ):
        raise ProfileError("INVALID_CATALOG", "Invalid catalog ID or PS2 serial")
    source_url, retrieved_on = _text(data, "source_url"), _text(data, "retrieved_on")
    try:
        url = urlsplit(source_url)
        date.fromisoformat(retrieved_on)
        if url.scheme != "https" or not url.netloc:
            raise ValueError("Expected an HTTPS metadata reference")
    except ValueError as error:
        raise ProfileError("INVALID_CATALOG", "Invalid catalog URL or retrieval date") from error
    languages = data.get("languages")
    if (
        not isinstance(languages, list)
        or not 1 <= len(languages) <= 32
        or any(
            not isinstance(item, str) or not re.fullmatch(r"[a-z]{2}", item) for item in languages
        )
        or len(set(languages)) != len(languages)
    ):
        raise ProfileError("INVALID_CATALOG", "Expected unique two-letter language codes")
    image = data.get("image")
    if not isinstance(image, dict) or type(image.get("size")) is not int:
        raise ProfileError("INVALID_CATALOG", "Missing catalog image size")
    if not 1 <= image["size"] <= (1 << 63) - 1:
        raise ProfileError("INVALID_CATALOG", "Invalid catalog image size")
    checksums = []
    for algorithm, length in (("sha1", 40), ("md5", 32), ("crc32", 8)):
        digest = image.get(algorithm)
        if not isinstance(digest, str) or not re.fullmatch(f"[0-9a-f]{{{length}}}", digest):
            raise ProfileError("INVALID_CATALOG", f"Invalid catalog {algorithm}")
        checksums.append((algorithm, digest))
    return CatalogReference(
        reference_id,
        source_url,
        retrieved_on,
        serial,
        _text(data, "region"),
        _text(data, "revision"),
        tuple(languages),
        image["size"],
        tuple(checksums),
    )


def match_catalog(reference: CatalogReference, image: dict, boot: dict, region: str) -> None:
    """A filename or serial alone can never match a catalog entry."""
    if image.get("size") != reference.image_size or any(
        image.get(algorithm) != digest for algorithm, digest in reference.checksums
    ):
        raise ProfileError("CATALOG_MISMATCH", "Image size or checksums differ from catalog")
    if (
        boot.get("serial") != reference.serial
        or boot.get("system_cnf_ver") != reference.revision
        or region not in ("unknown", reference.region)
    ):
        raise ProfileError("CATALOG_MISMATCH", "Boot metadata or region differs from catalog")
