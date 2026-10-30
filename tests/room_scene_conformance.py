"""Public CI uses only invented MAP/SRI2 bytes and a separate scalar oracle."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.python.helpers.heather_room_scene_fixture import pin, scene_inputs  # noqa: E402
from tests.room_scene_oracle import check  # noqa: E402
from tools.pipeline import heather_room_contacts as contact  # noqa: E402
from tools.pipeline import heather_room_scene as scene  # noqa: E402
from tools.pipeline import prepare_heather_room_scene as preparation  # noqa: E402


def main(executable):
    with tempfile.TemporaryDirectory() as folder:
        paths, _, a, b, ref = scene_inputs(Path(folder) / "inputs")
        # Only this synthetic test process changes pins; production CLI has no bypass.
        contact.PROFILE_PIN = pin(paths["profile"].read_bytes())
        scene.REFERENCE_SHA = preparation.REFERENCE_SHA = pin(ref.read_bytes())["sha256"]
        files, _ = preparation.prepare(paths, a, b, ref)
        requests = [
            (sample, position, yaw)
            for sample in (0, 10, 34, 57)
            for position, yaw in (
                ([100275, 0, 140000], 0),
                ([100230, 0, 139850], 1.5707963),
                ([100320, 0, 140400], -2.4),
            )
        ]
        result, _, _ = check(Path(executable).resolve(), files["copy-a"], a, requests)
        print(f"Shared room independent native/oracle: {result['frames']} frames, 31 shapes PASS")


if __name__ == "__main__":
    main(sys.argv[1])
