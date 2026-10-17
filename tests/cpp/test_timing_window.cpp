#include "check.hpp"
#include "sh3/platform/timing_window.hpp"
#include <limits>

int main() {
    using namespace sh3::platform;
    CHECK(elapsed_ticks(10, 10) == 0);
    CHECK(elapsed_ticks(10, 30) == 20);
    CHECK(!elapsed_ticks(30, 10));
    CHECK(!elapsed_ticks(std::numeric_limits<std::uint64_t>::max(), 0));
    TimingWindow window;
    CHECK(window.size() == 0 && window.at(0) == nullptr);
    auto summary = window.summarize(&FrameTimings::begin_wait);
    CHECK(!summary.p95 && !summary.maximum && summary.valid == 0 && summary.invalid == 0);
    for (std::size_t i = 0; i < TimingWindow::warmup_attempts; ++i) {
        window.record({10000, {}, {}, false});
        CHECK(window.size() == 0);
    }
    CHECK(window.warmup_remaining() == 0 && window.rejected() == 60);
    // Nonmonotonic order and an isolated large outlier distinguish p95 from max/mean.
    for (std::uint64_t i = 20; i > 0; --i) {
        window.record({i == 20 ? 9999 : i, 0, {}, true});
    }
    summary = window.summarize(&FrameTimings::begin_wait);
    CHECK(summary.valid == 20 && summary.invalid == 0);
    CHECK(summary.p95 == 19 && summary.maximum == 9999);
    CHECK(window.summarize(&FrameTimings::draw_submit).p95 == 0);
    CHECK(window.summarize(&FrameTimings::audio_poll).invalid == 20);
    CHECK(!window.summarize(&FrameTimings::audio_poll).p95);
    window.record({{}, {}, {}, false});
    summary = window.summarize(&FrameTimings::begin_wait);
    CHECK(summary.valid == 20 && summary.invalid == 1 && summary.p95 == 19);
    CHECK(window.rejected() == 61);
    for (std::uint64_t i = 0; i < 10000; ++i) {
        window.record({i, {}, 7, true});
    }
    CHECK(window.size() == 120);
    CHECK(window.at(0)->begin_wait == 9880);
    CHECK(window.at(119)->begin_wait == 9999);
    CHECK(window.at(120) == nullptr);
    CHECK(window.at(std::numeric_limits<std::size_t>::max()) == nullptr);
    summary = window.summarize(&FrameTimings::begin_wait);
    CHECK(summary.valid == 120 && summary.invalid == 0 && summary.p95 == 9993);
    CHECK(summary.maximum == 9999);
    window.reset();
    CHECK(window.size() == 0 && window.rejected() == 0 && window.warmup_remaining() == 60);
    CHECK(window.at(0) == nullptr && !window.summarize(&FrameTimings::begin_wait).p95);
    for (std::size_t i = 0; i < 61; ++i) {
        window.record({{}, 2, {}, true});
    }
    CHECK(window.summarize(&FrameTimings::draw_submit).p95 == 2);
    CHECK(window.summarize(&FrameTimings::begin_wait).invalid == 1);
}
