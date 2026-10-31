#include "check.hpp"
#include "sh3/platform/skinning_capture.hpp"
#include <limits>
using namespace sh3;
int main() {
    platform::SkinningCapture capture;
    domain::WorkSample s;
    CHECK(!capture.active() && !capture.complete());
    CHECK(!capture.summarize(0, 1000).count);
    capture.record(s);
    CHECK(capture.count() == 0);
    capture.start();
    s.result = unsigned(ports::RenderResult::presented);
    for (unsigned i = 0; i < 288; ++i) {
        s.frame = i;
        s.begin_tick = i * 20;
        s.end_tick = s.begin_tick + 10;
        s.ticks.fill(i);
        s.gpu_valid = i > 0;
        s.gpu_frame = i - 1;
        s.gpu_ms = i - 1;
        capture.record(s);
    }
    CHECK(capture.active() && capture.count() == 256 && !capture.complete());
    CHECK(capture.first() == 32 && capture.last() == 287 && !capture.failed());
    s.gpu_frame = 999;
    capture.record(s); // Unmatched completion cannot finish.
    CHECK(capture.active());
    s.gpu_frame = 287;
    s.gpu_ms = std::numeric_limits<double>::quiet_NaN();
    capture.record(s);
    CHECK(capture.active());
    s.gpu_ms = -1;
    capture.record(s);
    CHECK(capture.active());
    s.gpu_ms = 287;
    capture.record(s);
    CHECK(capture.complete() && !capture.active());
    for (unsigned metric : {0U, 9U, 12U}) {
        auto r = capture.summarize(metric, 1000);
        CHECK(r.count == 256 && r.median == 159.5 && r.p95 == 275 && r.maximum == 287);
    }
    CHECK(capture.summarize(10, 1000).median == 10);
    CHECK(capture.summarize(11, 1000).count == 255);
    CHECK(capture.summarize(11, 1000).median == 20);
    CHECK(!capture.summarize(13, 1000).count && !capture.summarize(0, 0).count);
    capture.record(s);
    CHECK(capture.count() == 256);
    capture.cancel();
    CHECK(!capture.complete());
    capture.start();
    s = {};
    s.result = unsigned(ports::RenderResult::busy);
    for (unsigned i = 0; i < 288; ++i)
        capture.record(s);
    CHECK(capture.complete() && capture.failed() == 256);
    CHECK(!capture.summarize(12, 1000).count);
    capture.start();
    capture.cancel();
    capture.record(s);
    CHECK(!capture.count());
}
