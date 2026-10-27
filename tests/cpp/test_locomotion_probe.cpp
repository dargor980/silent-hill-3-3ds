#include "check.hpp"
#include "sh3/application/locomotion_probe.hpp"
#include <cmath>
#include <cstring>
#include <limits>
#include <new>

namespace {
bool forbid_allocation{};
}
void *operator new(std::size_t n) {
    if (forbid_allocation)
        std::abort();
    if (auto *p = std::malloc(n ? n : 1))
        return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void *operator new(std::size_t n, std::align_val_t a) {
    if (forbid_allocation)
        std::abort();
    void *p = nullptr;
    if (posix_memalign(&p, std::size_t(a), n ? n : 1) == 0)
        return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n, std::align_val_t a) { return ::operator new(n, a); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
void operator delete(void *p, std::align_val_t) noexcept { std::free(p); }
void operator delete[](void *p, std::align_val_t) noexcept { std::free(p); }
void operator delete(void *p, std::size_t, std::align_val_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t, std::align_val_t) noexcept { std::free(p); }

namespace {
using namespace sh3;
using App = application::LocomotionProbe;
using Input = application::LocomotionInput;
using Notice = application::LocomotionNotice;
using Mode = domain::LocomotionMode;
using Error = domain::LocomotionError;
using Event = domain::LifecycleEvent;
using Session = domain::SessionState;
constexpr auto profile = domain::heather_locomotion_profile;
constexpr Input pause{true}, advance{false, true}, restart{false, false, true};
constexpr Input previous{false, false, false, true}, next{false, false, false, false, true};
constexpr float nan = std::numeric_limits<float>::quiet_NaN();
constexpr float inf = std::numeric_limits<float>::infinity();
using Bytes = std::array<unsigned char, sizeof(domain::LocomotionState)>;
Bytes bytes(const domain::LocomotionState &state) {
    Bytes out{};
    std::memcpy(out.data(), &state, sizeof(state));
    return out;
}
domain::LocomotionSkeleton skeleton() {
    domain::LocomotionSkeleton out{};
    out.bone_count = 2;
    out.parents[0] = -1;
    out.parents[1] = 0;
    out.channels[0] = 1;
    out.channels[1] = 2;
    return out;
}
struct Reader final : domain::LocomotionSampleReader {
    mutable unsigned reads{};
    unsigned missing_at = ~0U, invalid_at = ~0U;
    bool read(std::uint32_t clip, std::uint32_t frame, std::uint32_t bone,
              domain::LocomotionTransform &out) const noexcept override {
        CHECK(clip == 101 || clip == 109 || clip == 113);
        CHECK(frame < (clip == 101 ? 10U : 24U) && bone < 2);
        const auto call = reads++;
        if (call == missing_at)
            return false;
        // Linear TR: expected matrices are independently calculable, with both channels.
        out = {{float(clip) + float(frame), float(bone), 0}, {0, 0, 0, 1}};
        if (call == invalid_at)
            out.rotation = {};
        return true;
    }
};
struct Scene final : ports::IRigScene {
    domain::RigPose last{};
    unsigned frames{};
    ports::RenderResult result = ports::RenderResult::presented;
    ports::RenderResult present_pose(const domain::OrbitCamera &,
                                     const domain::RigPose &pose) noexcept override {
        last = pose;
        ++frames;
        return result;
    }
};
struct Fixture {
    Reader reader;
    Scene scene;
    App app{scene, profile, skeleton(), reader};
    void step(Input input = {}, float dt = .04F) { app.step({}, input, dt); }
    void settle() {
        for (unsigned i = 0; app.snapshot().clock.mode != Mode::stable; ++i) {
            CHECK(i < 20);
            step();
        }
    }
    void walk() {
        step(next);
        step();
        settle();
    }
    void run() {
        walk();
        step(next);
        step();
        settle();
    }
};
void near(float actual, float expected) { CHECK(std::abs(actual - expected) < .0001F); }
void presentation_and_time() {
    Fixture f;
    CHECK(f.app.ready() && !f.app.paused() && f.reader.reads == 2);
    const auto original = bytes(f.app.snapshot());
    for (unsigned i = 0; i < 100; ++i)
        f.step({}, 0);
    CHECK(f.reader.reads == 2 && f.scene.frames == 100 && bytes(f.app.snapshot()) == original);
    CHECK(f.scene.last == f.app.snapshot().model);
    near(f.scene.last[0][12], 101);
    near(f.scene.last[1][12], 202);
    near(f.scene.last[1][13], 1);
    f.step(); // Pose is evaluated before advancing, not at the resulting counter.
    CHECK(f.app.snapshot().clock.counter == 614 && f.reader.reads == 6);
    near(f.scene.last[0][12], 101);
    f.step();
    near(f.scene.last[0][12], 101 + 614.F / 4096);

    Fixture long_call, singles;
    long_call.step({}, .03F); // 0.75 remainder.
    CHECK(long_call.app.snapshot().clock.counter == 0);
    for (auto dt : {-1.F, nan, inf, -inf, 0.F})
        long_call.step({}, dt);
    CHECK(long_call.reader.reads == 2);
    long_call.step({}, 100000); // Clamped: 3 full updates, remainder 0.25.
    for (unsigned i = 0; i < 3; ++i)
        singles.step();
    CHECK(long_call.app.snapshot().clock.counter == 1842);
    CHECK(long_call.reader.reads == 14 && long_call.scene.last == singles.scene.last);
    long_call.step({}, .03F);
    CHECK(long_call.app.snapshot().clock.counter == 2456);
    long_call.step(pause);
    const auto before = bytes(long_call.app.snapshot());
    for (unsigned i = 0; i < 100; ++i)
        long_call.step({}, 1000);
    CHECK(bytes(long_call.app.snapshot()) == before);
    long_call.step(advance, 1000);
    CHECK(long_call.app.snapshot().clock.counter == 3070 && long_call.app.paused());
}
void selection_and_cache() {
    Fixture f;
    f.step(previous, 1); // Idle -> run is deliberately unsupported.
    CHECK(f.app.error() == Error::unsupported_transition && !f.app.pending_clip());
    CHECK(!f.app.paused() && f.app.snapshot().clock.counter == 0);
    CHECK(std::strcmp(f.app.notice_text(), "unsupported_transition") == 0);
    f.step();
    CHECK(f.app.snapshot().clock.counter == 614); // Error is latched but does not stop time.
    f.step({false, false, false, true, true}, 1);
    CHECK(f.app.notice() == Notice::selection_conflict && !f.app.pending_clip());
    f.step(next, 1);
    CHECK(f.app.notice() == Notice::queued && f.app.pending_clip() == 109);
    CHECK(f.app.snapshot().clock.target_id == 101 && f.app.snapshot().clock.counter == 614);
    f.step(previous, 1);
    CHECK(f.app.notice() == Notice::selection_pending && f.app.pending_clip() == 109);
    f.step();
    CHECK(f.app.snapshot().clock.mode == Mode::cached && f.app.snapshot().clock.blend == 768);
    CHECK(f.app.snapshot().clock.counter == 0 && f.app.snapshot().cache.saved_valid);
    CHECK(!f.app.pending_clip());
    near(f.app.snapshot().cache.saved_local[0].translation.x, 101);
    near(f.scene.last[0][12], 101 + 8 * 768.F / 4096);
    f.step(next);
    CHECK(f.app.error() == Error::transition_busy && !f.app.pending_clip());
    CHECK(std::strcmp(f.app.notice_text(), "transition_busy") == 0);
    f.step(pause);
    const auto cached = bytes(f.app.snapshot());
    for (unsigned i = 0; i < 100; ++i)
        f.step();
    CHECK(bytes(f.app.snapshot()) == cached);
    f.step(next);
    CHECK(f.app.notice() == Notice::paused);
    f.step(advance, 10000);
    CHECK(f.app.snapshot().clock.blend == 1536 && f.app.paused());
    f.step(pause);
    f.settle();
    CHECK(f.app.snapshot().clock.target_id == 109 && !f.app.snapshot().cache.saved_valid);

    f.step(next);
    f.step();
    CHECK(f.app.snapshot().clock.mode == Mode::phase_blend && f.app.snapshot().clock.blend == 384);
    f.step(pause);
    const auto phase = bytes(f.app.snapshot());
    for (unsigned i = 0; i < 100; ++i)
        f.step();
    CHECK(bytes(f.app.snapshot()) == phase);
    f.step(advance);
    CHECK(f.app.snapshot().clock.blend == 768 && f.app.paused());
    f.step(pause);
    f.settle();
    CHECK(f.app.snapshot().clock.target_id == 113);
    f.step(next); // Cycle wraps from run to idle, a supported cached edge.
    CHECK(f.app.pending_clip() == 101);
    f.step();
    f.settle();
    CHECK(f.app.snapshot().clock.target_id == 101);
}
void catch_up_is_sequential() {
    Fixture batched, sequential;
    for (auto *f : {&batched, &sequential}) {
        f->walk();
        f->step({}, .03F);
        f->step(next, 0);
    }
    // Three complete mode-5 updates must equal three individually presented updates.
    batched.step({}, 1);
    for (unsigned i = 0; i < 3; ++i)
        sequential.step();
    CHECK(batched.app.snapshot().clock.blend == 1152);
    CHECK(batched.app.snapshot().clock.counter == sequential.app.snapshot().clock.counter);
    CHECK(batched.scene.last == sequential.scene.last &&
          batched.reader.reads == sequential.reader.reads);
    // Also cross the cached-mode exit inside a single catch-up call.
    Fixture a, b;
    for (auto *f : {&a, &b}) {
        f->step(next);
        f->step();
        f->step();
        f->step();
        f->step();
        CHECK(f->app.snapshot().clock.blend == 3072);
        f->step({}, .03F);
    }
    a.step({}, 1);
    for (unsigned i = 0; i < 3; ++i)
        b.step();
    CHECK(a.app.snapshot().clock.mode == Mode::stable);
    CHECK(a.scene.last == b.scene.last && a.reader.reads == b.reader.reads);
}
void restart_and_priority() {
    for (unsigned phase = 0; phase < 3; ++phase) {
        Fixture f;
        if (phase > 0) {
            f.step(next);
            f.step();
        }
        if (phase == 2) {
            f.settle();
            f.step(next);
            f.step();
        }
        const auto target = f.app.snapshot().clock.target_id;
        const auto saved = bytes(f.app.snapshot());
        f.step({true, true, true, true, true}, 1); // A wins over all.
        CHECK(f.app.paused() && bytes(f.app.snapshot()) == saved);
        f.step({false, true, true, true, true}, 1); // L wins over R and selections.
        const auto &s = f.app.snapshot();
        CHECK(s.clock.target_id == target && s.clock.source_id == target);
        CHECK(s.clock.counter == 0 && s.clock.blend == 0 && s.clock.mode == Mode::stable);
        CHECK(!s.cache.saved_valid && !s.clock.saved_local_valid && f.app.paused());
        near(f.scene.last[0][12], float(target));
        f.step({false, true, false, true, true}, 1); // R wins over selection, exactly one update.
        CHECK(s.clock.counter == (target == 101 ? 614U : target == 109 ? 3992U : 4454U));
        CHECK(!f.app.pending_clip());
        f.step(pause);
        const auto before = bytes(s);
        f.step(advance, 1); // R while playing ignores both step and elapsed time.
        CHECK(bytes(s) == before);
        f.step(restart, 1);
        CHECK(!f.app.paused() && s.clock.counter == 0);
    }
    for (auto control : {pause, restart}) {
        Fixture f;
        f.step({}, .03F);
        f.step(next);
        f.step(control);
        CHECK(!f.app.pending_clip());
        if (f.app.paused())
            f.step(pause);
        f.step({}, .01F);
        CHECK(f.app.snapshot().clock.counter == 0);
    }
}
void lifecycle_and_camera() {
    for (unsigned phase = 1; phase <= 2; ++phase) {
        Fixture f;
        f.step(next);
        f.step();
        if (phase == 2) {
            f.settle();
            f.step(next);
            f.step();
        }
        const auto before = bytes(f.app.snapshot());
        f.app.dispatch(Event::suspend);
        f.app.dispatch(Event::resume);
        f.step({}, 10000);
        CHECK(bytes(f.app.snapshot()) == before);
        f.step();
        CHECK(f.app.snapshot().clock.blend == (phase == 1 ? 1536U : 768U));
    }
    for (bool paused : {false, true}) {
        Fixture f;
        if (paused)
            f.step(pause);
        else {
            f.step({}, .03F);
            f.step(next);
        }
        const auto before = bytes(f.app.snapshot());
        f.app.dispatch(Event::suspend);
        f.app.dispatch(Event::suspend);
        CHECK(!f.app.pending_clip() && f.app.view().state() == Session::suspended);
        const auto frames = f.scene.frames;
        f.step({true, true, true, true, true}, 500);
        f.app.dispatch(Event::toggle_pause);
        CHECK(bytes(f.app.snapshot()) == before && f.scene.frames == frames);
        f.app.dispatch(Event::resume);
        f.app.dispatch(Event::resume);
        for (unsigned i = 0; i < 100; ++i)
            f.app.step({1, 1, -1, true, false, true}, {true, true, true, true, true}, 500, true);
        CHECK(bytes(f.app.snapshot()) == before && f.app.view().awaiting_release());
        CHECK(!f.app.face_view() && f.app.view().camera().distance == 3);
        f.step({}, 500); // Release frame discards time too.
        CHECK(!f.app.view().awaiting_release() && bytes(f.app.snapshot()) == before);
        CHECK(f.app.paused() == paused);
        f.step({}, .01F);
        CHECK(bytes(f.app.snapshot()) == before); // Pre-suspend remainder was dropped.
        f.app.dispatch(Event::toggle_pause);
        CHECK(f.app.paused() != paused && f.app.view().state() == Session::running);
    }
    Fixture f;
    f.step(pause);
    const auto before = bytes(f.app.snapshot());
    f.app.step({1, 1, 1}, {}, .1F, true);
    CHECK(f.app.face_view() && f.app.view().camera().distance == .65F);
    for (unsigned i = 0; i < 100; ++i)
        f.app.step({0, 0, -1}, {}, .1F);
    CHECK(f.app.view().camera().distance == .45F && bytes(f.app.snapshot()) == before);
    f.app.step({}, {}, 1, true);
    CHECK(!f.app.face_view() && f.app.view().camera().distance == 3);
    f.app.step({}, {}, 0, true);
    f.app.step({1, 1, -1, true}, {}, 1, true); // B wins over SELECT and axes.
    CHECK(!f.app.face_view() && f.app.view().camera().distance == 3);
    for (bool suspended : {false, true}) {
        Fixture stop;
        stop.step(next);
        stop.scene.result = ports::RenderResult::busy;
        if (suspended) {
            stop.app.dispatch(Event::suspend);
            stop.app.dispatch(Event::resume);
        }
        const auto state = bytes(stop.app.snapshot());
        const auto frames = stop.scene.frames;
        stop.app.step({0, 0, 0, false, true}, {true, true, true, true, true}, 1, true);
        CHECK(stop.app.view().state() == Session::stopped && !stop.app.pending_clip());
        stop.app.dispatch(Event::resume);
        stop.app.dispatch(Event::toggle_pause);
        stop.step();
        CHECK(bytes(stop.app.snapshot()) == state && stop.scene.frames == frames);
    }
    Fixture suspended_stop;
    suspended_stop.app.dispatch(Event::suspend);
    suspended_stop.app.step({0, 0, 0, false, true}, {}, 0);
    CHECK(suspended_stop.app.view().state() == Session::stopped);
}
void failures_and_rendering() {
    {
        Fixture f;
        f.step(next);
        f.step();
        f.reader.missing_at = f.reader.reads + 3; // Second of up to three updates fails.
        f.step({}, .03F);
        f.step({}, .1F);
        CHECK(f.app.paused() && f.app.snapshot().clock.blend == 1536);
        near(f.scene.last[0][12], 101 + 8 * 1536.F / 4096);
        CHECK(f.reader.reads == f.reader.missing_at + 1); // No third update/read after error.
        const auto before = bytes(f.app.snapshot());
        f.step(pause);
        f.step({}, .01F);
        CHECK(bytes(f.app.snapshot()) == before); // Catch-up time was discarded on failure.
    }
    for (bool invalid : {false, true}) {
        Fixture f;
        f.step(next);
        f.step();
        const auto before = bytes(f.app.snapshot());
        if (invalid)
            f.reader.invalid_at = f.reader.reads + 1;
        else
            f.reader.missing_at = f.reader.reads + 1; // Late in channel 1, after channel 2.
        f.step({}, .1F);
        CHECK(f.app.paused() && bytes(f.app.snapshot()) == before);
        CHECK(f.app.error() == (invalid ? Error::invalid_pose : Error::sample_unavailable));
        CHECK(f.scene.last == f.app.snapshot().model);
        f.step({}, .1F);
        CHECK(bytes(f.app.snapshot()) == before);
        f.step(advance);
        CHECK(f.app.snapshot().clock.blend == 1536 && f.app.paused());
        const auto state = bytes(f.app.snapshot());
        f.reader.missing_at = f.reader.reads + 1;
        f.step(restart);
        CHECK(bytes(f.app.snapshot()) == state && f.app.paused());
        f.step(restart);
        CHECK(f.app.snapshot().clock.counter == 0 && f.app.snapshot().clock.target_id == 109);
    }
    Scene scene;
    Reader reader;
    reader.missing_at = 1;
    App broken(scene, profile, skeleton(), reader);
    CHECK(!broken.ready() && broken.paused());
    broken.step({}, {}, .1F);
    CHECK(broken.view().state() == Session::stopped && scene.frames == 0);
    auto invalid_profile = profile;
    invalid_profile.id = 2;
    App bad(scene, invalid_profile, skeleton(), reader);
    CHECK(!bad.ready() && std::strcmp(bad.notice_text(), "invalid_profile") == 0);

    Fixture busy;
    busy.scene.result = ports::RenderResult::busy;
    busy.step();
    CHECK(busy.app.snapshot().clock.counter == 614 && busy.app.view().state() == Session::running);
    const auto before = bytes(busy.app.snapshot());
    for (unsigned i = 0; i < 100; ++i)
        busy.step({}, 0);
    CHECK(bytes(busy.app.snapshot()) == before && busy.reader.reads == 6);
    for (auto result : {ports::RenderResult::unavailable, ports::RenderResult::invalid_camera}) {
        Fixture f;
        f.scene.result = result;
        f.step({}, 0);
        CHECK(f.app.view().state() == Session::stopped);
    }
}
} // namespace
int main() {
    forbid_allocation = true;
    presentation_and_time();
    selection_and_cache();
    catch_up_is_sequential();
    restart_and_priority();
    lifecycle_and_camera();
    failures_and_rendering();
    forbid_allocation = false;
    std::puts("Locomotion presenter, fixed updates, controls, failures and lifecycle: OK; no "
              "allocations");
}
