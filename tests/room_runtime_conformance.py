"""Host integration uses an invented 31-shape MAP, 32 blockers and original-format SRI2."""

import re
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.python.helpers.heather_room_scene_fixture import pin, scene_inputs  # noqa: E402
from tools.pipeline import heather_room_contacts as contact  # noqa: E402
from tools.pipeline import heather_room_scene as scene  # noqa: E402
from tools.pipeline import prepare_heather_room_scene as preparation  # noqa: E402
from tools.pipeline.prepare_heather_room_runtime import runtime_descriptor  # noqa: E402


def main(executable):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        paths, _, a, b, ref = scene_inputs(root / "inputs")
        contact.PROFILE_PIN = pin(paths["profile"].read_bytes())
        scene.REFERENCE_SHA = preparation.REFERENCE_SHA = pin(ref.read_bytes())["sha256"]
        packages, _ = preparation.prepare(paths, a, b, ref)
        files = packages["copy-a"]
        out = root / "runtime"
        out.mkdir()
        for name, raw in {**files, "scene.srr": runtime_descriptor(files)}.items():
            (out / name).write_bytes(raw)
        subprocess.run([executable, str(out)], check=True)
        # Exercise the real reader/renderer with all nine slots, hidden forms and
        # opaque -> blend -> cutout -> opaque in source order (invented pixels).
        raw = files["map.srm"]
        ns, nv = struct.unpack_from("<2I", raw, 8)
        shapes = list(struct.iter_unpack("<4I", raw[32 : 32 + ns * 16]))
        descriptors = b"".join(
            struct.pack("<6I", *s, 0 if s[3] else i % 9, int(i not in (3, 11, 23)))
            for i, s in enumerate(shapes)
        )
        pixels = bytes((53, 101, 177, 255)) * (512 * 512)
        crc = zlib.crc32(pixels)
        materials = b"".join(struct.pack("<4I", 512, 512, crc, (4, 6, 5)[i % 3]) for i in range(9))
        payload = descriptors + materials + raw[32 + ns * 16 :]
        original = (
            struct.pack(
                "<8s6I",
                b"S3RMv2\0\0",
                ns,
                nv,
                len(payload),
                zlib.crc32(payload),
                zlib.crc32(files["glass.rgba"]),
                2,
            )
            + payload
        )
        (out / "map.srm").write_bytes(original)
        descriptor = bytearray(runtime_descriptor(files))
        struct.pack_into("<I", descriptor, 16, zlib.crc32(original))
        (out / "scene.srr").write_bytes(descriptor)
        for i in range(9):
            (out / f"room-texture-{i:02}.rgba").write_bytes(pixels)
        subprocess.run([executable, str(out)], check=True)
        trace = subprocess.run(
            [executable, str(out), "--pause-trace"], check=True, capture_output=True, text=True
        ).stdout
        for hz in (25, 60, 143):
            block = trace.split(f"PAUSE_TRACE_BEGIN {hz}\n", 1)[1].split(
                f"PAUSE_TRACE_END {hz}\n", 1
            )[0]
            paused = [s for s in block.split("\x1b[1;1H") if "\nPAUSED" in s]
            readings = [
                tuple(map(int, re.search(r"Step: (\d+)  Clip: (\d+)  Q12: (\d+)", s).groups()))
                for s in paused
            ]
            reset_at = readings.index((0, 101, 0))
            after_reset = readings[reset_at:]
            first_step = next(i for i, r in enumerate(after_reset) if r[0] == 1)
            # At least 10 seconds of actual HUD publications with no simulation progress.
            assert first_step >= 35, (hz, first_step)
            assert all(r == (0, 101, 0) for r in after_reset[:first_step]), (hz, after_reset)
            assert all(r == after_reset[first_step] for r in after_reset[first_step:]), hz
            raw = [int(re.search(r"R presses: (\d+)", s).group(1)) for s in paused[reset_at:]]
            accepted = [int(re.search(r"R steps: (\d+)", s).group(1)) for s in paused[reset_at:]]
            assert raw[first_step - 1] >= hz * 2, (hz, raw)
            assert set(accepted[:first_step]) == {0} and set(accepted[first_step:]) == {1}, hz
        print("Room pause HUD: neutral 10s, noisy R, reset, one R and held R PASS at 25/60/143 Hz")


if __name__ == "__main__":
    main(sys.argv[1])
