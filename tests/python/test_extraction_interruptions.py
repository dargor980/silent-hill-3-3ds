"""H04/H05: real SIGKILL at synchronized checkpoints, using only own ISO bytes."""

import json
import selectors
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from test_asset_catalog import catalog_source as catalog_source
from test_extraction import args
from test_extraction import inputs as inputs

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "tests/python/helpers/extraction_worker.py"


@pytest.mark.parametrize("phase", ["reserved", "payload", "copied", "before_receipt"])
def test_kill_leaves_incomplete_session_and_new_session_can_succeed(inputs, phase):
    process = subprocess.Popen(
        [sys.executable, str(WORKER), phase, *args(inputs)],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            assert selector.select(timeout=15), "Worker failed to reach synchronized checkpoint"
            assert process.stdout.readline().strip() == phase
        folder = inputs.root / "run"
        payload = sum(path.stat().st_size for path in (folder / "copy-a").iterdir())
        if phase == "reserved":
            assert payload == 0 and not (folder / "started.json").exists()
        elif phase == "payload":
            assert 0 < payload < 27
        else:
            assert payload == 27
        assert not (folder / "verified.json").exists()
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == -signal.SIGKILL
        assert stdout == stderr == ""
        assert not (folder / "verified.json").exists()
        assert not (folder / "failed.json").exists()  # SIGKILL does not run Python cleanup.
        before = {
            p.relative_to(folder).as_posix(): p.read_bytes()
            for p in folder.rglob("*")
            if p.is_file()
        }
        occupied = subprocess.run(
            [sys.executable, "-m", "tools.pipeline.extract_assets", *args(inputs)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert occupied.returncode == 1
        assert json.loads(occupied.stdout)["code"] == "OUTPUT_EXISTS"
        assert before == {
            p.relative_to(folder).as_posix(): p.read_bytes()
            for p in folder.rglob("*")
            if p.is_file()
        }
        retry = subprocess.run(
            [sys.executable, "-m", "tools.pipeline.extract_assets", *args(inputs, name="retry")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert retry.returncode == 0, retry.stderr
        assert json.loads(retry.stdout)["status"] == "verified"
        receipt = json.loads((inputs.root / "retry/verified.json").read_text())
        assert receipt["copies"]["copy-a"] == receipt["copies"]["copy-b"]
        assert receipt["summary"]["entry_count"] == 5
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
