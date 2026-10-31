"""HS adds the planner and GPU adapter to the conservative HG stack inventory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.heather_turns_stack import UNITS, verify  # noqa: E402

if __name__ == "__main__":
    verify(
        sys.argv[1],
        UNITS | {"engine/domain/skinning_plan.cpp", "engine/platform/3ds/render/skinning_gpu.cpp"},
    )
