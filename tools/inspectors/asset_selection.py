"""Explicit, identity-bound MFA selection. No format inference or resource I/O."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from tools.inspectors.inventory import validate_image_hash
from tools.inspectors.mfa import layout_descriptor
from tools.pipeline.profile import GameProfile, ProfileError, safe_relative_path

MAX_SELECTION_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class ContainerChoice:
    path: str
    size: int
    sha256: str
    layout: str


@dataclass(frozen=True)
class AssetSelection:
    image_sha256: str
    profile_id: str
    containers: tuple[ContainerChoice, ...]

    def document(self) -> dict:
        return {
            "schema_version": 1,
            "image_sha256": self.image_sha256,
            "profile_id": self.profile_id,
            "containers": [asdict(c) for c in sorted(self.containers, key=lambda c: c.path)],
        }

    def digest(self) -> str:
        canonical = json.dumps(
            self.document(), sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_selection(data: object) -> AssetSelection:
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "image_sha256", "profile_id", "containers"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise ProfileError("INVALID_SELECTION", "Expected selection schema 1 and exact fields")
    validate_image_hash(data["image_sha256"])
    profile_id = data["profile_id"]
    if not isinstance(profile_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", profile_id):
        raise ProfileError("INVALID_SELECTION", "Invalid selection profile ID")
    items = data["containers"]
    if not isinstance(items, list) or not 1 <= len(items) <= 10000:
        raise ProfileError("INVALID_SELECTION", "Expected 1..10000 container choices")
    choices = []
    paths = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256", "layout"}:
            raise ProfileError("INVALID_SELECTION", "Invalid choice fields")
        path = safe_relative_path(item["path"])
        if path.casefold() in paths:
            raise ProfileError("INVALID_SELECTION", "Duplicate or case-ambiguous choice")
        paths.add(path.casefold())
        size = item["size"]
        if type(size) is not int or not 0 <= size <= (1 << 63) - 1:
            raise ProfileError("INVALID_SELECTION", "Invalid choice size")
        validate_image_hash(item["sha256"])
        layout_descriptor(item["layout"])
        choices.append(ContainerChoice(path, size, item["sha256"], item["layout"]))
    return AssetSelection(data["image_sha256"], profile_id, tuple(choices))


def validate_selection(selection: AssetSelection, profile: GameProfile, image_sha256: str) -> None:
    if selection.image_sha256 != image_sha256 or selection.profile_id != profile.profile_id:
        raise ProfileError("SELECTION_MISMATCH", "Selection identity differs from source")
    expected = {f.path: f for f in profile.files if f.path.lower().endswith(".mfa")}
    actual = {c.path: c for c in selection.containers}
    if len(actual) != len(selection.containers) or set(actual) != set(expected):
        raise ProfileError("SELECTION_MISMATCH", "Selection must describe every MFA candidate")
    for path, choice in actual.items():
        item = expected[path]
        if choice.size != item.size or choice.sha256 != item.sha256:
            raise ProfileError("SELECTION_MISMATCH", "Choice identity differs from profile")
        layout_descriptor(choice.layout)


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError("INVALID_SELECTION", "Duplicate JSON key")
        result[key] = value
    return result


def load_selection(path: Path) -> AssetSelection:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_SELECTION_BYTES + 1)
        if len(raw) > MAX_SELECTION_BYTES:
            raise ProfileError("INVALID_SELECTION", "Selection exceeds size limit")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ProfileError("SELECTION_READ_ERROR", "Cannot read selection JSON") from error
    return parse_selection(data)
