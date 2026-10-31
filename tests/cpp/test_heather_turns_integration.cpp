#include "check.hpp"
#include "movement_fixture.hpp"
#include "sh3/application/room_loop.hpp"
#include "sh3/platform/room_movement_contacts.hpp"
#include <cmath>
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

namespace {
using namespace sh3;
using Action = application::InspectionAction;
using Actor = application::InspectionActor;
using Controller = application::MovementController;
using Input = application::MovementInput;
using Turn = domain::InspectionTurn;
using Error = application::InspectionActorError;
using AE = domain::LocomotionError;
using S = domain::SessionState;
constexpr auto profile = domain::heather_turns_profile;
using Snapshot = application::InspectionActorSnapshot;
template <class T> auto bytes(const T &a) {
    std::array<unsigned char, sizeof(Snapshot)> b{};
    std::memcpy(b.data(), &a.snapshot(), b.size());
    return b;
}
Action action(unsigned id) {
    switch (id) {
    case 101:
        return Action::idle;
    case 109:
        return Action::walk;
    case 113:
        return Action::run;
    case 107:
        return Action::turn_right;
    case 108:
        return Action::turn_left;
    default:
        std::abort();
    }
}
Input input(unsigned id, int yaw = 0) {
    Input i;
    i.forward = id == 109 || id == 113;
    i.run = id == 113;
    i.right = yaw > 0 || (!yaw && id == 107);
    i.left = yaw < 0 || (!yaw && id == 108);
    return i;
}
struct Watch {
    Actor *actor{};
    std::array<unsigned char, sizeof(Snapshot)> before{};
    mutable unsigned calls{};
    void check() const {
        if (!actor)
            return;
        ++calls;
        CHECK(bytes(*actor) == before);
        CHECK(actor->step_action({}, 2).error == Error::busy);
        CHECK(actor->reset({}, 0).error == Error::busy);
        CHECK(bytes(*actor) == before);
    }
};
struct Reader final : domain::LocomotionSampleReader {
    Watch *watch{};
    mutable unsigned calls{};
    unsigned fail_at{}, fault{};
    bool read(std::uint32_t clip, std::uint32_t frame, std::uint32_t bone,
              domain::LocomotionTransform &out) const noexcept override {
        ++calls;
        if (watch)
            watch->check();
        if (calls == fail_at && fault == 0)
            return false;
        const auto angle = float(frame + bone) / 80;
        out = {{float(clip) / 16 + float(frame) / 8, float(bone) + 2, -4},
               {0, 0, std::sin(angle), std::cos(angle)}};
        if (calls == fail_at) {
            if (fault == 1)
                out.translation.x = std::numeric_limits<float>::quiet_NaN();
            if (fault == 2)
                out.rotation = {};
        }
        return true;
    }
};
struct Contacts final : ports::IMovementContacts {
    Watch *watch{};
    unsigned fault{};
    mutable unsigned calls{};
    ports::MovementContactStatus resolve(const ports::MovementContactQuery &q,
                                         domain::Vec3 &out) const noexcept override {
        ++calls;
        if (watch)
            watch->check();
        using C = ports::MovementContactStatus;
        if (fault == 1)
            return C::unavailable;
        if (fault == 2)
            return C::unsupported;
        if (fault == 3)
            return C::accepted; // Intentionally leaves the sentinel untouched.
        if (fault == 4) {
            out = q.requested;
            out.z = INFINITY;
            return C::accepted;
        }
        if (fault == 5)
            return static_cast<C>(99);
        out = q.requested;
        return C::accepted;
    }
};
void setup(Actor &a, unsigned source, unsigned target, unsigned phase) {
    CHECK(a.reset(movement_test::spawn, 0).error == Error::ok);
    if (source != 101)
        for (unsigned i = 0; i < 8; ++i)
            CHECK(a.step_action({action(source), Turn::right}, 2).error == Error::ok);
    else
        for (unsigned i = 0; i < 3; ++i)
            CHECK(a.step_action({}, 2).error == Error::ok);
    for (unsigned i = 0; i < phase; ++i)
        CHECK(a.step_action({action(target), Turn::left}, 2).error == Error::ok);
}
unsigned failures{}, retries{};
void atomicity() {
    for (const auto &pair : {std::pair{101U, 107U}, {101U, 108U}, {107U, 101U}, {108U, 101U}}) {
        for (unsigned phase : {0U, 1U, pair.first == 101 ? 5U : 8U}) {
            Reader reader;
            Contacts contacts;
            Actor a(profile, movement_test::rig(), reader, contacts);
            setup(a, pair.first, pair.second, phase);
            reader.calls = 0;
            CHECK(a.step_action({action(pair.second), Turn::left}, 2).error == Error::ok);
            const auto reads = reader.calls;
            const auto expected = bytes(a);
            CHECK(reads >= 2);
            for (unsigned kind = 0; kind < 3; ++kind) {
                for (unsigned call = 1; call <= reads; ++call) {
                    setup(a, pair.first, pair.second, phase);
                    Watch w{&a, bytes(a)};
                    reader.watch = contacts.watch = &w;
                    reader.calls = 0;
                    reader.fail_at = call;
                    reader.fault = kind;
                    const auto result = a.step_action({action(pair.second), Turn::left}, 2);
                    CHECK(result.error == Error::animation_rejected);
                    CHECK(result.animation ==
                          (kind == 0 ? AE::sample_unavailable : AE::invalid_pose));
                    CHECK(bytes(a) == w.before && w.calls > 0);
                    ++failures;
                    reader.watch = nullptr;
                    contacts.watch = nullptr;
                    reader.fail_at = 0;
                    CHECK(a.step_action({action(pair.second), Turn::left}, 2).error == Error::ok);
                    CHECK(bytes(a) == expected);
                    ++retries;
                }
            }
            for (unsigned fault = 1; fault <= 5; ++fault) {
                setup(a, pair.first, pair.second, phase);
                Watch w{&a, bytes(a)};
                reader.watch = contacts.watch = &w;
                contacts.fault = fault;
                reader.calls = 0;
                const auto result = a.step_action({action(pair.second), Turn::left}, 2);
                CHECK(result.error == (fault == 1   ? Error::contacts_unavailable
                                       : fault == 2 ? Error::contacts_unsupported
                                                    : Error::invalid_contact));
                CHECK(bytes(a) == w.before && reader.calls == 0);
                ++failures;
                reader.watch = contacts.watch = nullptr;
                contacts.fault = 0;
                CHECK(a.step_action({action(pair.second), Turn::left}, 2).error == Error::ok);
                CHECK(bytes(a) == expected);
                ++retries;
            }
        }
    }
    Reader r;
    Contacts c;
    Actor a(profile, movement_test::rig(), r, c);
    CHECK(a.step_action({}, 2).error == Error::not_initialized);
    CHECK(a.reset({}, 0).error == Error::ok);
    const auto old = bytes(a);
    for (int bad : {-1, 5, 999}) {
        CHECK(a.step_action({static_cast<Action>(bad), Turn::none}, 2).movement ==
              domain::InspectionMovementError::invalid_intent);
        CHECK(bytes(a) == old && c.calls == 0);
    }
    CHECK(a.step_action({Action::turn_right, static_cast<Turn>(99)}, 2).error ==
          Error::movement_rejected);
    CHECK(a.step_action({Action::turn_right, Turn::none}, 1).error == Error::movement_rejected);
    CHECK(a.step_action({Action::run, Turn::none}, 2).animation == AE::unsupported_transition);
    CHECK(c.calls == 0 && bytes(a) == old);
    CHECK(a.step_action({Action::turn_right, Turn::none}, 2).error == Error::ok);
    const auto blended = bytes(a);
    CHECK(a.step_action({Action::turn_left, Turn::none}, 2).animation == AE::transition_busy);
    CHECK(bytes(a) == blended && c.calls == 1);
    r.calls = 0;
    r.fail_at = 2;
    CHECK(a.reset({}, 0).animation == AE::sample_unavailable && bytes(a) == blended);
    r.fail_at = 0;
    CHECK(a.reset({}, 0).error == Error::ok && a.snapshot().animation.clock.profile_id == 2);
    CHECK(!a.snapshot().animation.clock.saved_local_valid && a.snapshot().movement.ordinal == 0);
    Actor legacy(domain::heather_locomotion_profile, movement_test::rig(), r, c);
    CHECK(legacy.reset({}, 0).error == Error::ok);
    CHECK(legacy.step_action({Action::turn_left, Turn::none}, 2).animation == AE::unknown_clip);
    CHECK(legacy.step({domain::InspectionMotion::idle, Turn::left}, 2).error == Error::ok);
    CHECK(legacy.snapshot().animation.clock.target_id == 101);
}
struct View final : ports::IRoomView {
    ports::RenderResult result{ports::RenderResult::presented};
    domain::RigPose pose{};
    domain::PoseMatrix instance{};
    ports::RenderResult present(const domain::RigPose &p,
                                const domain::PoseMatrix &m) noexcept override {
        pose = p;
        instance = m;
        return result;
    }
};
void room() {
    Reader r;
    View v;
    platform::RoomMovementContacts contacts;
    domain::RoomContactInput geometry;
    domain::RoomContactBox wall{-1000, 1000, 600, 650};
    geometry.floor_y = -7;
    geometry.floor = {-2000, 2000, -2000, 2000};
    geometry.blockers = &wall;
    geometry.blocker_count = 1;
    CHECK(contacts.prepare(geometry) == domain::RoomContactError::ok);
    application::RoomLoop loop(profile, movement_test::rig(), r, contacts, v, movement_test::spawn,
                               0);
    CHECK(loop.ready());
    loop.step({}, 0);
    for (unsigned i = 0; i < 20; ++i)
        CHECK(loop.step(input(109), 40000) == 1);
    const auto blocked = loop.snapshot().movement.position;
    CHECK(blocked.z < 424 && blocked.z >= 396);
    CHECK(loop.step(input(109), 40000) == 1 && loop.snapshot().movement.position.z == blocked.z);
    for (unsigned i = 0; i < 20; ++i)
        CHECK(loop.step(input(107), 40000) == 1);
    CHECK(loop.snapshot().animation.clock.target_id == 107);
    CHECK(loop.snapshot().movement.position.z == blocked.z &&
          loop.snapshot().movement.position.x == blocked.x);
    CHECK(v.pose == loop.snapshot().animation.model && v.instance == loop.snapshot().instance);
    CHECK(v.instance[12] == blocked.x && v.instance[14] == blocked.z);
    CHECK(v.pose[0][12] != blocked.x); // World placement is separate and applied once.
    const auto old = bytes(loop);
    r.calls = 0;
    r.fail_at = 2;
    CHECK(loop.step(input(108), 40000) == 0 && bytes(loop) == old);
    CHECK(loop.state() == S::paused && loop.fault() == application::RoomFault::simulation);
    loop.step({}, 10000000);
    Input restart;
    restart.restart = true;
    r.calls = 0;
    CHECK(loop.step(restart, 0) == 0 && bytes(loop) == old); // Failed reset is also atomic.
    r.fail_at = 0;
    loop.step({}, 0);
    loop.step(restart, 0);
    CHECK(loop.fault() == application::RoomFault::none && loop.snapshot().movement.ordinal == 0);
    CHECK(loop.snapshot().animation.clock.profile_id == 2 &&
          loop.snapshot().animation.clock.counter == 0);
    loop.step({}, 0);
    loop.dispatch(domain::LifecycleEvent::toggle_pause);
    loop.step({}, 0);
    CHECK(loop.step(input(108), 40000) == 1);
    v.result = ports::RenderResult::unavailable;
    loop.step({}, 0);
    CHECK(loop.state() == S::paused && loop.fault() == application::RoomFault::render);
    const auto rendered = bytes(loop);
    loop.step({}, 0);
    loop.step(input(107), 120000);
    CHECK(bytes(loop) == rendered);
    v.result = ports::RenderResult::presented;
    loop.step(restart, 0);
    CHECK(loop.fault() == application::RoomFault::none && loop.snapshot().movement.ordinal == 0);
    // A failure in update 2 or 3 retains the preceding full publications.
    for (unsigned committed : {1U, 2U}) {
        movement_test::Contacts failing;
        Reader reader;
        Controller c(profile, movement_test::rig(), reader, failing, {}, 0);
        c.step({}, 0);
        failing.fail_at = committed;
        CHECK(c.step(input(107), 120000) == committed);
        CHECK(c.snapshot().movement.ordinal == committed && c.state() == S::paused);
        CHECK(!c.pending_action() && !c.remainder_us() && c.awaiting_release());
    }
    Reader reader;
    Contacts clear;
    Controller c(profile, movement_test::rig(), reader, clear, {}, 0);
    c.step({}, 0);
    CHECK(c.step(input(107), 1) == 0 && c.pending_action() == Action::turn_right);
    CHECK(c.step(input(108), 1) == 0 && c.pending_action() == Action::turn_left);
    CHECK(c.step({}, 0) == 0 && !c.pending_action());
    CHECK(c.step(input(107), 39998) == 1);
    const auto snapshot = bytes(c);
    CHECK(c.step(input(108), 0) == 0 && c.pending_action() == Action::turn_left);
    CHECK(c.step(input(113), 0) == 0 && c.pending_action() == Action::run);
    CHECK(c.step(input(107), 0) == 0 && !c.pending_action());
    CHECK(c.step({}, 0) == 0 && c.pending_action() == Action::idle);
    CHECK(bytes(c) == snapshot);
    for (unsigned i = 0; i < 5; ++i)
        CHECK(c.step({}, 40000) == 1);
    CHECK(c.snapshot().animation.clock.target_id == 107);
    CHECK(c.step({}, 40000) == 1 && c.snapshot().animation.clock.target_id == 101);
}
void emit(const Controller &c, float previous_yaw) {
    const auto &s = c.snapshot();
    const auto &k = s.animation.clock;
    std::printf("%u %u %u %u %u %u %u %.9g %.9g %.9g %u\n", k.target_id, k.source_id, k.target_id,
                unsigned(k.mode), k.counter, k.blend,
                c.pending_action() ? application::action_clip(*c.pending_action()) : 0,
                double(s.movement.yaw - previous_yaw), double(s.movement.position.x),
                double(s.movement.position.z), s.movement.ordinal);
}
int protocol() {
    char command;
    while (std::scanf(" %c", &command) == 1) {
        Reader r;
        Contacts contacts;
        Controller c(profile, movement_test::rig(), r, contacts, {}, 0);
        c.step({}, 0);
        if (command == 'I') {
            unsigned mask;
            CHECK(std::scanf("%u", &mask) == 1);
            Input i{bool(mask & 1), bool(mask & 2), bool(mask & 4), bool(mask & 8),
                    bool(mask & 16)};
            CHECK(c.step(i, 0) == 0);
            auto pending = c.pending_action();
            std::printf("%u ", pending ? application::action_clip(*pending) : 101);
            CHECK(c.step(i, 40000) == 1);
            emit(c, 0);
        } else if (command == 'R') {
            unsigned n;
            CHECK(std::scanf("%u", &n) == 1);
            for (unsigned i = 0; i < n; ++i) {
                unsigned goal;
                int yaw;
                CHECK(std::scanf("%u%d", &goal, &yaw) == 2);
                const auto before = c.snapshot().movement.yaw;
                CHECK(c.step(input(goal, yaw), 40000) == 1);
                emit(c, before);
            }
        } else if (command == 'H') {
            unsigned source, goal;
            CHECK(std::scanf("%u%u", &source, &goal) == 2);
            for (unsigned i = 0;
                 i < 60 && (c.snapshot().animation.clock.target_id != source ||
                            c.snapshot().animation.clock.mode != domain::LocomotionMode::stable);
                 ++i)
                CHECK(c.step(input(source), 40000) == 1);
            CHECK(c.snapshot().animation.clock.target_id == source);
            auto previous = source;
            for (unsigned i = 0;
                 i < 60 && (c.snapshot().animation.clock.target_id != goal ||
                            c.snapshot().animation.clock.mode != domain::LocomotionMode::stable);
                 ++i) {
                CHECK(c.step(input(goal), 40000) == 1);
                auto target = c.snapshot().animation.clock.target_id;
                if (target != previous)
                    std::printf("%u ", target);
                previous = target;
            }
            CHECK(c.snapshot().animation.clock.target_id == goal &&
                  c.snapshot().animation.clock.mode == domain::LocomotionMode::stable);
            std::puts("0");
        } else
            return 2;
    }
    return 0;
}
} // namespace
int main(int argc, char **) {
    if (argc > 1)
        return protocol();
    forbid = true;
    atomicity();
    room();
    forbid = false;
    std::printf("HG integration: %u atomic failures, %u retries; contacts, room, zero allocations "
                "PASS; actor %zu/controller %zu/loop %zu\n",
                failures, retries, sizeof(Actor), sizeof(Controller),
                sizeof(application::RoomLoop));
}
