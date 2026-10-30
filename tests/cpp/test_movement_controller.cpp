#include "check.hpp"
#include "movement_fixture.hpp"
#include <algorithm>
#include <cstring>
#include <new>

namespace {
bool forbid_allocation = false;
}
void *operator new(std::size_t n) {
    if (forbid_allocation)
        std::abort();
    if (auto *p = std::malloc(n ? n : 1))
        return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }

namespace {
using namespace sh3;
using namespace movement_test;
using Controller = application::MovementController;
using Input = application::MovementInput;
using Session = domain::SessionState;
using Event = domain::LifecycleEvent;
using Motion = domain::InspectionMotion;
using Snapshot = application::InspectionActorSnapshot;
using Bytes = std::array<unsigned char, sizeof(Snapshot)>;
constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
Bytes bytes(const Controller &c) {
    Bytes result;
    std::memcpy(result.data(), &c.snapshot(), result.size());
    return result;
}
void release(Controller &c) {
    CHECK(c.step({}, maximum) == 0 && !c.awaiting_release() && c.remainder_us() == 0);
}
Input walk() {
    Input i;
    i.forward = true;
    return i;
}
Input run() {
    auto i = walk();
    i.run = true;
    return i;
}
void stable(Controller &c, Input i) {
    unsigned guard = 0;
    while (c.snapshot().animation.clock.mode != domain::LocomotionMode::stable) {
        CHECK(++guard < 20 && c.step(i, 40000) == 1);
        CHECK(c.result().error == application::InspectionActorError::ok);
    }
}
void timing_and_intents() {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    CHECK(c.ready() && c.state() == Session::running && c.awaiting_release());
    const auto initial = bytes(c);
    // Every held control, including unmapped ones, prevents startup/resume.
    for (auto field : {&Input::forward, &Input::backward, &Input::left, &Input::right, &Input::run,
                       &Input::pause, &Input::advance, &Input::restart, &Input::any_held}) {
        Input i;
        i.*field = true;
        CHECK(c.step(i, maximum) == 0 && c.awaiting_release());
        CHECK(bytes(c) == initial && contacts.calls == 0);
    }
    release(c);
    CHECK(c.step(run(), 39999) == 0 && c.remainder_us() == 39999 &&
          c.pending_motion() == Motion::run);
    CHECK(c.step(run(), 1) == 1 && c.remainder_us() == 0);
    CHECK(c.snapshot().animation.clock.target_id == 109 && c.pending_motion() == Motion::run);
    CHECK(c.snapshot().movement.position.z == spawn.z + 28);
    stable(c, run());
    CHECK(c.snapshot().animation.clock.target_id == 109); // Bridge finishes before selection.
    CHECK(c.step(run(), 40000) == 1 && c.snapshot().animation.clock.target_id == 113);
    CHECK(!c.pending_motion());
    CHECK(c.step(walk(), 0) == 0 && c.pending_motion() == Motion::walk);
    CHECK(c.step({}, 0) == 0 && c.pending_motion() == Motion::idle); // Latest request replaces.
    const auto z = c.snapshot().movement.position.z;
    CHECK(c.step({}, 40000) == 1 && c.snapshot().movement.position.z == z + 70);
    stable(c, {});
    CHECK(c.step({}, 40000) == 1 && c.snapshot().animation.clock.target_id == 101);
    stable(c, {});
    CHECK(!c.pending_motion());
    Input opposed = run();
    opposed.backward = opposed.left = opposed.right = true;
    const auto before = c.snapshot().movement;
    CHECK(c.step(opposed, 40000) == 1);
    CHECK(c.snapshot().movement.position.z == before.position.z &&
          c.snapshot().movement.yaw == before.yaw);
    Input left;
    left.left = true;
    CHECK(c.step(left, 40000) == 1 && c.snapshot().movement.yaw == -.088F);
    Input right;
    right.right = true;
    CHECK(c.step(right, 40000) == 1 && c.snapshot().movement.yaw == 0);

    CHECK(c.step(walk(), 39999) == 0);
    CHECK(c.step(walk(), 120000) == 3 && c.remainder_us() == 39999);
    CHECK(c.step(walk(), 120001) == 3 && c.remainder_us() == 0);
    CHECK(c.step(walk(), 1000000) == 3 && c.remainder_us() == 0);
    const auto slow_start = c.snapshot().movement.ordinal;
    for (unsigned i = 0; i < 100; ++i)
        CHECK(c.step(walk(), 160000) == 3 && c.remainder_us() == 0);
    CHECK(c.snapshot().movement.ordinal == slow_start + 300);
    const auto snapshot = bytes(c);
    for (auto invalid : {std::uint64_t{1000001}, maximum}) {
        CHECK(c.step(run(), invalid) == 0 && c.remainder_us() == 0 && !c.pending_motion());
        CHECK(bytes(c) == snapshot);
    }
    CHECK(c.step(walk(), 1) == 0 && c.remainder_us() == 1);
}
void lifecycle_and_priority() {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    release(c);
    CHECK(c.step(run(), 39999) == 0);
    Input pause;
    pause.pause = pause.restart = pause.advance = true;
    CHECK(c.step(pause, 120000) == 0 && c.state() == Session::paused);
    CHECK(c.snapshot().movement.ordinal == 0 && !c.pending_motion());
    CHECK(c.remainder_us() == 0 && c.awaiting_release());
    release(c);
    const auto before = bytes(c);
    CHECK(c.step(run(), maximum) == 0 && bytes(c) == before && !c.pending_motion());
    Input single = walk();
    single.advance = true;
    CHECK(c.step(single, maximum) == 1 && c.state() == Session::paused && c.remainder_us() == 0);
    const auto position = c.snapshot().movement.position;
    Input reset;
    reset.restart = reset.advance = true;
    CHECK(c.step(reset, maximum) == 0 && c.state() == Session::paused && c.awaiting_release());
    CHECK(c.snapshot().movement.ordinal == 0 && c.snapshot().movement.position.z == spawn.z);
    CHECK(position.z != spawn.z && c.snapshot().animation.clock.target_id == 101);
    release(c);
    c.dispatch(Event::toggle_pause);
    CHECK(c.state() == Session::running && c.awaiting_release());
    release(c);
    CHECK(c.step(single, 120000) == 0 &&
          c.snapshot().movement.ordinal == 0); // R in play consumes time.
    CHECK(c.step(run(), 10000) == 0);
    c.dispatch(Event::suspend);
    CHECK(c.state() == Session::suspended && c.remainder_us() == 0 && !c.pending_motion());
    c.dispatch(Event::suspend);
    c.dispatch(Event::toggle_pause);
    CHECK(c.step(reset, maximum) == 0 && c.state() == Session::suspended);
    c.dispatch(Event::resume);
    CHECK(c.state() == Session::running && c.awaiting_release());
    CHECK(c.step(run(), maximum) == 0 && c.awaiting_release());
    release(c);
    CHECK(c.step({}, 39999) == 0);
    c.dispatch(Event::resume);
    c.dispatch(Event::none);
    CHECK(c.remainder_us() == 39999 && !c.awaiting_release()); // Duplicate resume is inert.
    CHECK(c.step({}, 1) == 1);
    c.dispatch(Event::toggle_pause);
    release(c);
    c.dispatch(Event::suspend);
    c.dispatch(Event::resume);
    CHECK(c.state() == Session::paused && c.awaiting_release());
    release(c);
    const auto terminal = bytes(c);
    c.dispatch(Event::suspend);
    Input quit;
    quit.quit = quit.pause = quit.restart = quit.advance = true;
    CHECK(c.step(quit, maximum) == 0 && c.state() == Session::stopped);
    for (auto event : {Event::resume, Event::toggle_pause, Event::suspend, Event::quit})
        c.dispatch(event);
    CHECK(c.step(single, maximum) == 0 && bytes(c) == terminal && c.state() == Session::stopped);
}
void errors_and_reentry() {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    release(c);
    // Failure on the second step retains the first commit, never the failed second one.
    contacts.fail_at = contacts.calls + 1;
    CHECK(c.step(walk(), 120000) == 1 && c.snapshot().movement.ordinal == 1);
    CHECK(c.state() == Session::paused && c.awaiting_release() && c.remainder_us() == 0);
    CHECK(c.result().error == application::InspectionActorError::contacts_unavailable &&
          !c.pending_motion());
    const auto before = bytes(c);
    CHECK(c.step(walk(), maximum) == 0 && bytes(c) == before);
    release(c);
    Input one = walk();
    one.advance = true;
    reader.fail = true;
    CHECK(c.step(one, 40000) == 0 && bytes(c) == before && c.awaiting_release());
    CHECK(c.result().animation == domain::LocomotionError::sample_unavailable);
    release(c);
    Input reset;
    reset.restart = true;
    CHECK(c.step(reset, 40000) == 0 && bytes(c) == before && c.state() == Session::paused);
    reader.fail = false;
    release(c);
    CHECK(c.step(one, maximum) == 1 && c.snapshot().movement.ordinal == 2);
    CHECK(c.result().error == application::InspectionActorError::ok);
    release(c);
    CHECK(c.step(reset, 1) == 0 && c.snapshot().movement.ordinal == 0);
    release(c);
    c.dispatch(Event::toggle_pause);
    release(c);
    // Callback attempts cannot quit, consume time or reset a partly prepared update.
    auto observer = +[](void *context) {
        auto &app = *static_cast<Controller *>(context);
        const auto old = bytes(app);
        Input quit;
        quit.quit = true;
        CHECK(app.step(quit, maximum) == 0);
        app.dispatch(Event::quit);
        CHECK(bytes(app) == old && app.state() == Session::running);
    };
    reader.observe = contacts.observe = observer;
    reader.context = contacts.context = &c;
    CHECK(c.step(walk(), 40000) == 1 && c.state() == Session::running);
    reader.observe = contacts.observe = nullptr;

    reader.fail = true;
    Controller unavailable(profile, rig(), reader, contacts, spawn, 0);
    CHECK(!unavailable.ready() && unavailable.state() == Session::paused);
    release(unavailable);
    CHECK(unavailable.step(one, 40000) == 0 && !unavailable.ready());
    reader.fail = false;
    release(unavailable);
    CHECK(unavailable.step(reset, 40000) == 0 && unavailable.ready());
    CHECK(unavailable.state() == Session::paused && unavailable.awaiting_release());
}
void same(const Snapshot &a, const Snapshot &b) {
    CHECK(a.movement.position.x == b.movement.position.x &&
          a.movement.position.y == b.movement.position.y &&
          a.movement.position.z == b.movement.position.z && a.movement.yaw == b.movement.yaw &&
          a.movement.ordinal == b.movement.ordinal && a.instance == b.instance);
    const auto &x = a.animation, &y = b.animation;
    CHECK(x.clock.counter == y.clock.counter && x.clock.mode == y.clock.mode &&
          x.clock.blend == y.clock.blend && x.clock.source_id == y.clock.source_id &&
          x.clock.target_id == y.clock.target_id &&
          x.clock.saved_local_valid == y.clock.saved_local_valid && x.model == y.model);
    for (unsigned i = 0; i < 73; ++i) {
        CHECK(x.cache.last_local[i].rotation == y.cache.last_local[i].rotation);
        CHECK(x.cache.saved_local[i].rotation == y.cache.saved_local[i].rotation);
        const auto u = x.cache.last_local[i].translation, v = y.cache.last_local[i].translation;
        const auto s = x.cache.saved_local[i].translation, t = y.cache.saved_local[i].translation;
        CHECK(u.x == v.x && u.y == v.y && u.z == v.z && s.x == t.x && s.y == t.y && s.z == t.z);
    }
}
Snapshot replay(std::array<unsigned, 3> cadence, bool interrupts) {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    release(c);
    unsigned frame = 0;
    for (auto input : {Input{}, walk(), run(), walk(), Input{}}) {
        unsigned remaining = 1200000;
        while (remaining) {
            const auto interval = std::min(cadence[frame++ % cadence.size()], remaining);
            c.step(input, interval);
            remaining -= interval;
        }
        CHECK(c.remainder_us() == 0);
        if (interrupts) {
            const auto old = bytes(c);
            c.dispatch(Event::toggle_pause);
            release(c);
            CHECK(c.step(run(), maximum) == 0);
            c.dispatch(Event::suspend);
            c.dispatch(Event::resume);
            CHECK(c.state() == Session::paused);
            release(c);
            c.dispatch(Event::toggle_pause);
            release(c);
            CHECK(bytes(c) == old);
        }
    }
    CHECK(c.snapshot().movement.ordinal == 150 && c.state() == Session::running);
    return c.snapshot();
}
} // namespace
int main() {
    forbid_allocation = true;
    timing_and_intents();
    lifecycle_and_priority();
    errors_and_reentry();
    const auto reference = replay({40000, 40000, 40000}, false);
    same(reference, replay({16000, 17000, 17000}, false));
    same(reference, replay({1000, 79000, 40000}, true));
    same(reference, replay({120000, 120000, 120000}, true));
    forbid_allocation = false;
    std::printf(
        "MovementController: %zu bytes; fixed ticks, queue, faults and lifecycle replay passed\n",
        sizeof(Controller));
}
