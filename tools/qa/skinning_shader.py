"""Fail closed on any change to the independently validated HSN v1 SHBIN."""

import hashlib
import sys
from pathlib import Path

SHA256 = "08997532a98f04f44e978e1a17e0906e120897cdd55fc19a4bd21ffdc34e1b6b"


def validate(raw):
    if len(raw) != 408 or hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError("HSN shader differs from the frozen contract; revalidate explicitly")


if __name__ == "__main__":
    validate(Path(sys.argv[1]).read_bytes())
