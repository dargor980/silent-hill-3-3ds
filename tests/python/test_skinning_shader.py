import json
import runpy
import sys
from pathlib import Path

import pytest

from tools.qa.skinning_shader import validate

ROOT = Path(__file__).resolve().parents[2]


def test_shader_gate_and_cli(tmp_path, monkeypatch):
    data = bytes.fromhex(
        json.loads((ROOT / "tests/fixtures/synthetic/heather-skinning-native-v1.json").read_text())[
            "shader_hex"
        ]
    )
    validate(data)
    for altered in (data[:-1], data + b"\0", b"\0" + data[1:]):
        with pytest.raises(ValueError, match="frozen contract"):
            validate(altered)
    path = tmp_path / "own.shbin"
    path.write_bytes(data)
    monkeypatch.setattr(sys, "argv", ["skinning_shader.py", str(path)])
    runpy.run_path(str(ROOT / "tools/qa/skinning_shader.py"), run_name="__main__")
