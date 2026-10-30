#include "check.hpp"
#include "movement_fixture.hpp"
#include "sh3/application/room_loop.hpp"
#include "sh3/platform/room_movement_contacts.hpp"
#include <cstring>
#include <new>

namespace {
bool forbid{};
}
void *operator new(std::size_t n) {
    if (forbid)
        std::abort();
    if (auto *p = std::malloc(n ? n : 1))
        return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
#if defined(__cpp_sized_deallocation)
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
#endif
using namespace sh3;
using namespace movement_test;
using Loop = application::RoomLoop;
using Fault = application::RoomFault;
using S = domain::SessionState;
using E = domain::LifecycleEvent;
using Input = application::MovementInput;
using R = ports::RenderResult;
struct View final : ports::IRoomView {
    R result{R::presented};
    unsigned calls{};
    domain::RigPose pose{};
    domain::PoseMatrix instance{};
    Loop *reentry{};
    R present(const domain::RigPose &p, const domain::PoseMatrix &m) noexcept override {
        ++calls;
        pose = p;
        instance = m;
        if (reentry) {
            Input q;
            q.quit = true;
            CHECK(reentry->step(q, 120000) == 0);
            reentry->dispatch(E::quit);
        }
        return result;
    }
};
auto bytes(const Loop &a) {
    std::array<unsigned char, sizeof(application::InspectionActorSnapshot)> out{};
    std::memcpy(out.data(), &a.snapshot(), out.size());
    return out;
}
Input walk() {
    Input i;
    i.forward = true;
    return i;
}
Input reset() {
    Input i;
    i.restart = true;
    return i;
}
void release(Loop &a) {
    a.step({}, 10000000);
    CHECK(!a.awaiting_release());
}
void faults() {
    Reader reader;
    Contacts contacts;
    View view;
    Loop a(profile, rig(), reader, contacts, view, spawn, 0);
    CHECK(a.ready() && contacts.calls == 1);
    release(a);
    CHECK(a.step(walk(), 40000) == 1 && view.instance == a.snapshot().instance);
    CHECK(view.pose == a.snapshot().animation.model);
    contacts.fail_at = contacts.calls + 1;
    CHECK(a.step(walk(), 120000) == 1 && a.snapshot().movement.ordinal == 2);
    CHECK(a.fault() == Fault::simulation && a.state() == S::paused && a.awaiting_release());
    auto old = bytes(a);
    release(a);
    a.dispatch(E::toggle_pause);
    CHECK(a.state() == S::paused);
    Input pause;
    pause.pause = true;
    CHECK(a.step(pause, 120000) == 0 && bytes(a) == old);
    reader.fail = true;
    a.step(reset(), 0);
    CHECK(bytes(a) == old && a.awaiting_release());
    reader.fail = false;
    release(a);
    a.step(reset(), 0);
    CHECK(a.fault() == Fault::none && a.state() == S::paused);
    CHECK(a.snapshot().movement.ordinal == 0 && a.snapshot().animation.clock.target_id == 101);
    release(a);
    a.step(pause, 0);
    release(a);
    view.result = R::busy;
    CHECK(a.step(walk(), 40000) == 1 && a.state() == S::running);
    view.result = R::unavailable;
    a.step({}, 0);
    CHECK(a.fault() == Fault::render && a.state() == S::paused);
    old = bytes(a);
    auto calls = view.calls;
    release(a);
    a.step(walk(), 120000);
    CHECK(view.calls == calls && bytes(a) == old);
    view.result = R::invalid_camera;
    a.step(reset(), 0);
    CHECK(a.fault() == Fault::render);
    view.result = R::presented;
    release(a);
    a.step(reset(), 0);
    CHECK(a.fault() == Fault::none);
    release(a);
    a.step(pause, 0);
    release(a);
    view.reentry = &a;
    CHECK(a.step(walk(), 40000) == 1 && a.state() == S::running);
    view.reentry = nullptr;
    contacts.fail_at = contacts.calls;
    old = bytes(a);
    a.step(reset(), 0);
    CHECK(a.fault() == Fault::spawn && bytes(a) == old && a.awaiting_release());
    release(a);
    a.step(reset(), 0);
    CHECK(a.fault() == Fault::none);
    a.dispatch(E::suspend);
    calls = view.calls;
    a.step(reset(), 120000);
    CHECK(view.calls == calls);
    Input quit;
    quit.quit = true;
    a.step(quit, 0);
    a.dispatch(E::resume);
    CHECK(a.state() == S::stopped);
    a.step(walk(), 40000);
    CHECK(view.calls == calls);
    contacts.fail_at = contacts.calls;
    Loop invalid(profile, rig(), reader, contacts, view, spawn, 0);
    CHECK(!invalid.ready() && invalid.fault() == Fault::spawn);
    release(invalid);
    invalid.step(reset(), 0);
    CHECK(invalid.ready());
    reader.fail = true;
    Loop bad_reader(profile, rig(), reader, contacts, view, spawn, 0);
    CHECK(!bad_reader.ready());
    reader.fail = false;
    release(bad_reader);
    bad_reader.step(reset(), 0);
    CHECK(bad_reader.ready());
}
application::InspectionActorSnapshot replay(unsigned cadence, bool interrupts) {
    Reader reader;
    View view;
    platform::RoomMovementContacts contacts;
    domain::RoomContactBox wall{-1000, 1000, 600, 650};
    domain::RoomContactInput input;
    input.floor_y = -7;
    input.floor = {-2000, 2000, -2000, 2000};
    input.blockers = &wall;
    input.blocker_count = 1;
    CHECK(contacts.prepare(input) == domain::RoomContactError::ok);
    Loop a(profile, rig(), reader, contacts, view, spawn, 0);
    release(a);
    for (unsigned segment = 0; segment < 5; ++segment) {
        auto in = walk();
        in.run = segment == 1;
        in.left = segment == 3;
        unsigned remaining = 1200000;
        while (remaining) {
            auto dt = std::min(cadence, remaining);
            a.step(in, dt);
            remaining -= dt;
        }
        if (interrupts) {
            const auto before = bytes(a);
            a.dispatch(E::toggle_pause);
            release(a);
            a.dispatch(E::suspend);
            a.dispatch(E::resume);
            CHECK(a.state() == S::paused);
            CHECK(bytes(a) == before);
            a.step(walk(), 9999999);
            CHECK(a.awaiting_release());
            release(a);
            a.dispatch(E::toggle_pause);
            release(a);
        }
    }
    CHECK(a.snapshot().movement.ordinal == 150 && a.fault() == Fault::none);
    CHECK(a.snapshot().movement.position.z < 424); // swept wall expanded by 176, closed boundary
    return a.snapshot();
}
int main() {
    forbid = true;
    faults();
    const auto a = replay(40000, false);
    for (auto rate : {1000U, 16000U, 79000U, 120000U}) {
        const auto b = replay(rate, true);
        CHECK(a.instance == b.instance && a.animation.model == b.animation.model);
        CHECK(a.animation.clock.counter == b.animation.clock.counter &&
              a.movement.ordinal == b.movement.ordinal);
    }
    forbid = false;
    std::printf("RoomLoop: %zu bytes; fault recovery, lifecycle, render and swept replay PASS\n",
                sizeof(Loop));
}
