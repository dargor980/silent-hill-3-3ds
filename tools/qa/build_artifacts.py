"""Check the complete synthetic 3DS build before retaining it as an artifact."""

import argparse
import json
import re
from pathlib import Path

from tools.debug.bundle import fingerprint, validate_id, verify

FILES = (
    "sh3_diagnostic.3dsx",
    "sh3_diagnostic.elf",
    "sh3_diagnostic.smdh",
    "probe.txt",
    "build-id.txt",
    "debug-bundle.json",
    "SHA256SUMS",
    "toolchain-packages.txt",
)
CHECKSUM_FILES = FILES[:4]
RECEIPT = "artifact-check.json"


def check(directory: Path, probe: Path, sdk_image: Path) -> dict:
    """Validate fixed inputs; this does not execute or certify the binaries."""
    entries = {name: fingerprint(directory / name) for name in FILES}
    for name, limit in (
        ("build-id.txt", 13),
        ("debug-bundle.json", 4096),
        ("SHA256SUMS", 4096),
        ("toolchain-packages.txt", 1048576),
    ):
        if entries[name]["bytes"] > limit:
            raise ValueError(f"METADATA_TOO_LARGE: {name}")
    build_text = (directory / "build-id.txt").read_text(encoding="utf-8")
    build_id = build_text.removesuffix("\n")
    validate_id(build_id)
    if build_text != build_id + "\n":
        raise ValueError("INVALID_BUILD_ID_FILE")
    verify(directory, directory / "debug-bundle.json", build_id)

    # Minimal format checks complement, but do not replace, the real compiler.
    for name, magic in (
        ("sh3_diagnostic.3dsx", b"3DSX"),
        ("sh3_diagnostic.elf", b"\x7fELF\x01\x01"),
        ("sh3_diagnostic.smdh", b"SMDH"),
    ):
        with (directory / name).open("rb") as stream:
            if stream.read(len(magic)) != magic:
                raise ValueError(f"INVALID_HEADER: {name}")
    with (directory / "sh3_diagnostic.elf").open("rb") as stream:
        stream.seek(18)
        if stream.read(2) != b"\x28\x00":
            raise ValueError("ELF_NOT_ARM")
    if entries["sh3_diagnostic.smdh"]["bytes"] != 14016:
        raise ValueError("INVALID_SMDH_SIZE")
    if entries["probe.txt"] != fingerprint(probe):
        raise ValueError("FIXTURE_MISMATCH")
    expected_checksums = "".join(
        f"{entries[name]['sha256']}  build/3ds/{name}\n" for name in CHECKSUM_FILES
    )
    if (directory / "SHA256SUMS").read_text(encoding="utf-8") != expected_checksums:
        raise ValueError("CHECKSUMS_MISMATCH")
    # The expected image is supplied by the caller, never read from bundle paths.
    if fingerprint(sdk_image)["bytes"] > 256:
        raise ValueError("INVALID_SDK_IMAGE")
    sdk = sdk_image.read_text(encoding="utf-8").removesuffix("\n")
    if not re.fullmatch(r"devkitpro/devkitarm@sha256:[0-9a-f]{64}", sdk):
        raise ValueError("INVALID_SDK_IMAGE")
    return {"schema_version": 1, "build_id": build_id, "expected_sdk_image": sdk, "files": entries}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--sdk-image", required=True, type=Path)
    parser.add_argument(
        "--record", action="store_true", help="Create a new receipt; never overwrite"
    )
    args = parser.parse_args(argv)
    try:
        document = check(args.directory, args.probe, args.sdk_image)
        if args.record:
            with (args.directory / RECEIPT).open("x", encoding="utf-8") as output:
                output.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
        else:
            receipt = args.directory / RECEIPT
            if fingerprint(receipt)["bytes"] > 8192:
                raise ValueError("INVALID_RECEIPT_SIZE")
            if (
                receipt.read_text(encoding="utf-8")
                != json.dumps(document, indent=2, sort_keys=True) + "\n"
            ):
                raise ValueError("RECEIPT_MISMATCH")
    except (OSError, ValueError) as error:
        print(f"build-artifacts: FAIL ({error})")
        return 1
    print(f"build-artifacts: PASS build={document['build_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
