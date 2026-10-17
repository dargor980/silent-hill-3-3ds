#include "check.hpp"
#include "sh3/platform/bounded_log.hpp"
#include <limits>

int main() {
    using S = sh3::domain::SessionState;
    sh3::platform::BoundedLog log;
    CHECK(log.size() == 0);
    CHECK(!log.at(0).has_value());
    log.record(S::paused);
    CHECK(log.at(0) == S::paused);
    // RF14.02: saturation retains exactly the latest 32 events in chronological order.
    for (std::size_t i = 0; i < 10001; ++i) {
        log.record(i % 2 == 0 ? S::running : S::paused);
    }
    CHECK(log.size() == log.capacity);
    for (std::size_t i = 0; i < log.capacity; ++i) {
        CHECK(log.at(i) == (i % 2 == 0 ? S::paused : S::running));
    }
    CHECK(!log.at(log.capacity).has_value());
    CHECK(!log.at(std::numeric_limits<std::size_t>::max()).has_value());
}
