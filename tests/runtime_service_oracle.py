"""Local launcher/parent for the real service with explicitly synthetic CPU ports."""

import os
import socket
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    binary, mode = sys.argv[1:]
    with tempfile.TemporaryDirectory(prefix="sh3rt-", dir="/tmp") as directory:
        endpoint = str(Path(directory) / "io.sock")
        env = {
            key: value for key, value in os.environ.items() if not key.startswith("SH3_RUNTIME_")
        }
        env.update(
            SH3_RUNTIME_ENDPOINT=endpoint,
            SH3_RUNTIME_MANIFEST=str(Path(directory) / "absent.lm"),
            SH3_RUNTIME_TRIGGER="paused"
            if mode in {"cancel_wait", "ui_wait", "ui_vm_wait", "paused"}
            else "immediate",
            SH3_RUNTIME_POLICY="03" * 32,
            SH3_RUNTIME_MANIFEST_SHA256="04" * 32,
            SH3_RUNTIME_PLATFORM="05" * 32,
        )
        if mode == "disabled":
            del env["SH3_RUNTIME_ENDPOINT"]
        elif mode == "bad_hash":
            env["SH3_RUNTIME_POLICY"] = "Z" * 64
        elif mode == "zero_hash":
            env["SH3_RUNTIME_POLICY"] = "0" * 64
        elif mode == "bad_trigger":
            env["SH3_RUNTIME_TRIGGER"] = "remote"
        elif mode == "relative":
            env["SH3_RUNTIME_MANIFEST"] = "relative.lm"
        elif mode == "missing_field":
            del env["SH3_RUNTIME_PLATFORM"]
        elif mode == "long_endpoint":
            env["SH3_RUNTIME_ENDPOINT"] = "/" + "x" * 110
        connected = mode in {
            "queue_null",
            "queue_rejected",
            "late_callback",
            "missing_manifest",
            "paused",
            "disconnect",
            "cancel_session",
            "ui_session",
            "ui_finished",
            "ui_vm_session",
        }
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            if mode != "connect_failure":
                server.bind(endpoint)
                server.listen(1)
                server.settimeout(8)
            child = subprocess.Popen(
                [binary, mode], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            prefix = ""
            try:
                if connected:
                    connection, _ = server.accept()
                    with connection:
                        if mode in {"missing_manifest", "paused", "ui_finished"}:
                            connection.sendall(b"SH3PDQ02" + b"\x01" * 16 + struct.pack("<Q", 1))
                        if mode == "disconnect":
                            prefix = child.stdout.readline()
                            assert prefix == "RT_CPU_READY\n", prefix
                            connection.shutdown(socket.SHUT_RDWR)
                        output, _ = child.communicate(timeout=10)
                else:
                    output, _ = child.communicate(timeout=10)
                output = prefix + output
                print(output, end="")
                assert child.returncode == 0, (mode, child.returncode)
                if connected or mode in {"cancel_wait", "ui_wait", "ui_vm_wait", "connect_failure"}:
                    lines = [line for line in output.splitlines() if line.startswith("SH3_RT_END ")]
                    assert len(lines) == 1, output
                    values = dict(item.split("=", 1) for item in lines[0].split()[1:])
                    assert (
                        values["clean"] == "1"
                        and values["replies"] == "0"
                        and values["admitted"] == "0"
                    )
                    expected = {
                        "queue_null": "9",
                        "queue_rejected": "9",
                        "late_callback": "6",
                        "missing_manifest": "1",
                        "paused": "1",
                        "disconnect": "4",
                        "cancel_session": "6",
                        "cancel_wait": "6",
                        "ui_wait": "6",
                        "ui_session": "6",
                        "ui_finished": "1",
                        "ui_vm_wait": "6",
                        "ui_vm_session": "6",
                        "connect_failure": "4",
                    }
                    assert values["reason"] == expected[mode], (mode, values)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)


if __name__ == "__main__":
    main()
