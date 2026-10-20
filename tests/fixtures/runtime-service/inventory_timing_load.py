"""One optional CPU load child, in the supervisor's owned process group."""

import hashlib
import json
import os
import signal
import subprocess
import sys
import time


def load():
    active = True

    def stop(_signal, _frame):
        nonlocal active
        active = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    block = bytes(4 * 1024 * 1024)
    start = time.monotonic()
    print("IT_LOAD_START " + json.dumps(dict(pid=os.getpid(), buffer_bytes=len(block))), flush=True)
    iterations = 0
    while active and time.monotonic() - start < 95:
        hashlib.sha256(block).digest()
        iterations += 1
    print(
        "IT_LOAD_STOP "
        + json.dumps(
            dict(pid=os.getpid(), iterations=iterations, elapsed_seconds=time.monotonic() - start)
        ),
        flush=True,
    )


def main():
    child = None
    try:
        if sys.argv[1] == "loaded":
            child = subprocess.Popen(
                [sys.executable, __file__, "--load"], stdout=subprocess.PIPE, text=True
            )
            first = child.stdout.readline()
            if not first.startswith("IT_LOAD_START "):
                raise RuntimeError("load child did not start")
            print(first, end="", flush=True)
        elif sys.argv[1] != "idle":
            raise ValueError("unknown condition")
        return subprocess.call(sys.argv[2:])
    finally:
        if child:
            child.terminate()
            remaining, _ = child.communicate(timeout=5)
            print(remaining, end="", flush=True)
            if child.returncode != 0 or not remaining.startswith("IT_LOAD_STOP "):
                raise RuntimeError("load child did not stop cleanly")


if __name__ == "__main__":
    if sys.argv[1:] == ["--load"]:
        load()
    else:
        sys.exit(main())
