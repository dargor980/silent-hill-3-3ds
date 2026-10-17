"""Test-only synchronized stop points; never imported by production tools."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.pipeline import extract_assets  # noqa: E402
from tools.pipeline.iso9660 import IsoImage  # noqa: E402
from tools.pipeline.private_output import PrivateOutput  # noqa: E402


def checkpoint(phase):
    print(phase, flush=True)
    sys.stdin.buffer.read(1)
    raise RuntimeError("Parent must terminate this synthetic worker at the checkpoint")


def main():
    phase = sys.argv[1]
    if phase not in {"reserved", "payload", "copied", "before_receipt"}:
        raise ValueError("Unknown test checkpoint")
    reserve, transfer = PrivateOutput.reserve, IsoImage.copy_range
    verify, receipt = PrivateOutput.verify, PrivateOutput.receipt

    def stopped_reserve(self, *args):
        result = reserve(self, *args)
        if phase == "reserved":
            checkpoint(phase)
        return result

    class PartialWriter:
        def __init__(self, stream):
            self.stream = stream

        def write(self, data):
            part = data[: max(1, len(data) // 2)]
            self.stream.write(part)
            self.stream.flush()
            checkpoint("payload")

    def stopped_copy(self, path, offset, length, target):
        if phase == "payload" and length:
            target = PartialWriter(target)
        return transfer(self, path, offset, length, target)

    def stopped_verify(self, *args):
        if phase == "copied":
            checkpoint(phase)
        return verify(self, *args)

    def stopped_receipt(self, name, document):
        if phase == "before_receipt" and name == "verified.json":
            checkpoint(phase)
        return receipt(self, name, document)

    PrivateOutput.reserve = stopped_reserve
    IsoImage.copy_range = stopped_copy
    PrivateOutput.verify = stopped_verify
    PrivateOutput.receipt = stopped_receipt
    return extract_assets.main(sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
