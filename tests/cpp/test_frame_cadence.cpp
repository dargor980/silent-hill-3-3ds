#include "check.hpp"
#include "sh3/platform/frame_cadence.hpp"
#include <cmath>

int main() {
    sh3::platform::FrameCadence cadence(1000);
    cadence.record(100, true);
    CHECK(!cadence.fps()); // The first submission only anchors the measurement.
    for (unsigned i = 1; i <= 20; ++i)
        cadence.record(100 + i * 50, true);
    CHECK(cadence.fps() && std::abs(*cadence.fps() - 20) < 1e-9);
    for (unsigned i = 1; i <= 20; ++i)
        cadence.record(1100 + i * 50, i % 2 == 0);
    CHECK(std::abs(*cadence.fps() - 10) < 1e-9); // Busy draws consume elapsed time.
    cadence.record(3100, false);
    CHECK(*cadence.fps() == 0);
    cadence.reset(); // Sleeping time must never be reported as rendering cost.
    CHECK(!cadence.fps());
    cadence.record(100000, true);
    cadence.record(102000, true);
    CHECK(*cadence.fps() == .5);
    cadence.record(5, true); // A clock reversal starts a fresh window.
    CHECK(!cadence.fps());
    cadence.record(1005, true);
    CHECK(*cadence.fps() == 1);
    sh3::platform::FrameCadence invalid(0);
    invalid.record(0, true);
    invalid.record(1000, true);
    CHECK(!invalid.fps());
}
