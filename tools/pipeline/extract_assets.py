"""Export the accepted MFA subset twice to an explicit private POSIX destination."""

import argparse
import hashlib
import json
from contextlib import AbstractContextManager
from importlib.metadata import version
from pathlib import Path
from typing import BinaryIO, Protocol

from tools.inspectors.asset_catalog import collect_assets
from tools.inspectors.asset_selection import load_selection
from tools.inspectors.inventory import validate_image_hash
from tools.pipeline.iso9660 import IsoImage
from tools.pipeline.private_output import COPIES, PrivateOutput, resource_filename
from tools.pipeline.profile import ProfileError
from tools.pipeline.verify import load_profile

MAX_CATALOG_BYTES = 128 * 1024 * 1024


class CopyReader(Protocol):
    def copy_range(
        self, path: str, offset: int, length: int, destination: BinaryIO
    ) -> tuple[int, str]:
        """Transfer an exact bounded range or raise a typed failure."""


class OutputStore(Protocol):
    @property
    def reserved(self) -> bool: ...

    def reserve(self, payload_bytes: int, count: int) -> int: ...

    def assert_attached(self) -> None: ...

    def open_resource(self, copy: str, identity: str) -> AbstractContextManager[BinaryIO]: ...

    def verify(self, copy: str, resources: list[dict]) -> list[dict]: ...

    def receipt(self, name: str, document: dict) -> None: ...


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError("INVALID_CATALOG", "Duplicate catalog JSON key")
        result[key] = value
    return result


def _invalid_constant(_: str):
    raise ProfileError("INVALID_CATALOG", "Non-finite catalog JSON number")


def canonical(document: object) -> str:
    return json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def load_catalog(path: Path, expected_hash: str) -> dict:
    validate_image_hash(expected_hash)
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_CATALOG_BYTES + 1)
        if len(raw) > MAX_CATALOG_BYTES:
            raise ProfileError("INVALID_CATALOG", "Catalog exceeds size limit")
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ProfileError("CATALOG_HASH_MISMATCH", "Catalog differs from recorded hash")
        document = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        if not isinstance(document, dict):
            raise ProfileError("INVALID_CATALOG", "Expected catalog object")
        return document
    except ProfileError:
        raise
    except (OSError, ValueError, RecursionError) as error:
        raise ProfileError("CATALOG_READ_ERROR", "Cannot read catalog") from error


def resource_plan(catalog: dict) -> list[dict]:
    parents = {item["id"]: item["path"] for item in catalog["containers"]}
    resources, seen = [], set()
    for entry in catalog["entries"]:
        filename = resource_filename(entry["id"])
        if filename in seen:
            raise ProfileError("DUPLICATE_RESOURCE", "Duplicate output identity")
        seen.add(filename)
        validate_image_hash(entry["sha256"])
        if type(entry["size"]) is not int or not 0 <= entry["size"] <= (1 << 63) - 1:
            raise ProfileError("INVALID_SIZE", "Invalid output size")
        resources.append(
            {
                **{
                    key: entry[key]
                    for key in ("id", "container_id", "container_offset", "size", "sha256")
                },
                "container_path": parents[entry["container_id"]],
                "file": filename,
            }
        )
    if not resources:
        raise ProfileError("EMPTY_EXTRACTION", "No accepted resources to export")
    return sorted(resources, key=lambda item: item["id"])


def copy_resources(reader: CopyReader, output: OutputStore, copy: str, resources: list[dict]):
    for item in resources:
        with output.open_resource(copy, item["id"]) as stream:
            size, digest = reader.copy_range(
                item["container_path"], item["container_offset"], item["size"], stream
            )
            if type(size) is not int or size != item["size"] or digest != item["sha256"]:
                raise ProfileError("COPY_HASH_MISMATCH", "Transferred bytes differ from catalog")


def extract_pair(
    iso_path: Path,
    profile,
    image_hash: str,
    selection,
    catalog: dict,
    catalog_hash: str,
    output: OutputStore,
    *,
    image_factory=IsoImage,
) -> dict:
    """Output is already open; source factories permit deterministic failure injection."""
    base = {"schema_version": 1, "catalog_sha256": catalog_hash}
    try:
        for copy in COPIES:
            with image_factory(iso_path) as source:
                size, digest = source.image_identity()
                if digest != image_hash:
                    raise ProfileError("IMAGE_MISMATCH", "Image differs from expected source")
                current = collect_assets(source, profile, size, digest, selection)
                current["tool"]["pycdlib"] = version("pycdlib")
                if canonical(current) != canonical(catalog):
                    raise ProfileError("CATALOG_MISMATCH", "Catalog differs from current source")
                resources = resource_plan(current)
                if copy == COPIES[0]:
                    budget = output.reserve(sum(item["size"] for item in resources), len(resources))
                    base.update(
                        tool={
                            "name": "sh3-mfa-extract",
                            "version": 1,
                            "pycdlib": version("pycdlib"),
                        },
                        source=current["source"],
                        selection=current["selection"],
                        resources=resources,
                        summary=current["summary"],
                        required_free_bytes=budget,
                        exclusions={
                            "containers": [
                                {"id": c["id"], "code": c["result"]["code"]}
                                for c in current["containers"]
                                if c["result"]["status"] == "unknown"
                            ],
                            "outside_scope_ids": [e["id"] for e in current["outside_scope"]],
                        },
                        payload_decoding="not_performed",
                        capabilities=[],
                    )
                    output.receipt("started.json", {**base, "status": "started"})
                output.assert_attached()
                copy_resources(source, output, copy, resources)
                inventory = output.verify(copy, resources)
            # The input has closed with its stability check before publishing copy success.
            output.assert_attached()
            output.receipt(
                copy + ".json",
                {**base, "status": "copy_verified", "copy": copy, "files": inventory},
            )
        inventories = {copy: output.verify(copy, resources) for copy in COPIES}
        if inventories[COPIES[0]] != inventories[COPIES[1]]:
            raise ProfileError("COPIES_DIFFER", "Output inventories differ")
        output.assert_attached()
        result = {**base, "status": "verified", "copies": inventories}
        output.receipt("verified.json", result)
        return result
    except (ProfileError, OSError) as error:
        failure = (
            error
            if isinstance(error, ProfileError)
            else ProfileError("OUTPUT_IO_ERROR", "Private output I/O failed")
        )
        if output.reserved:
            try:
                output.receipt("failed.json", {**base, "status": "failed", "code": failure.code})
            except (OSError, ProfileError):
                pass  # No success receipt; callers still receive the original failure.
        if failure is error:
            raise
        raise failure from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("iso", "profile", "selection", "catalog", "private-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("image-sha256", "catalog-sha256", "run-id"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    result, cleanup_warning = None, {}
    try:
        validate_image_hash(args.image_sha256)
        catalog = load_catalog(args.catalog, args.catalog_sha256)
        profile, selection = load_profile(args.profile), load_selection(args.selection)
        with PrivateOutput(
            args.private_root, Path(__file__).resolve().parents[2], args.run_id
        ) as output:
            result = extract_pair(
                args.iso,
                profile,
                args.image_sha256,
                selection,
                catalog,
                args.catalog_sha256,
                output,
            )
    except (ProfileError, OSError) as error:
        if result is not None and isinstance(error, OSError):
            # extract_pair returned only after publishing verified.json. Cleanup cannot
            # undo that commit; report its warning without claiming the copy was rejected.
            cleanup_warning = {"cleanup_warning": "OUTPUT_CLOSE_ERROR"}
        else:
            code = error.code if isinstance(error, ProfileError) else "OUTPUT_IO_ERROR"
            print(json.dumps({"status": "rejected", "code": code}))
            return 1
    print(
        json.dumps(
            {
                "status": "verified",
                "copies": 2,
                **result["summary"],
                "payload_decoding": "not_performed",
                **cleanup_warning,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
