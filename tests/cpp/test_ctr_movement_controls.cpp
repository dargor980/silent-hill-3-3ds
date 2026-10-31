#include "../../engine/platform/3ds/movement_controls.hpp"
#include "check.hpp"
#include "movement_fixture.hpp"
#include <cstring>
#include <utility>

namespace fake {
void (*callback)(APT_HookType, void *){};
void *context{};
aptHookCookie *cookie{};
unsigned hooks{}, unhooks{}, speedups{};
void event(APT_HookType type) {
    CHECK(callback);
    callback(type, context);
}
} // namespace fake
void osSetSpeedupEnable(bool enabled) {
    CHECK(enabled);
    ++fake::speedups;
}
void aptHook(aptHookCookie *cookie, void (*callback)(APT_HookType, void *), void *context) {
    CHECK(!fake::callback);
    fake::cookie = cookie;
    fake::callback = callback;
    fake::context = context;
    ++fake::hooks;
}
void aptUnhook(aptHookCookie *cookie) {
    CHECK(fake::cookie == cookie && fake::callback);
    fake::cookie = nullptr;
    fake::callback = nullptr;
    fake::context = nullptr;
    ++fake::unhooks;
}

namespace {
using namespace sh3;
using namespace movement_test;
using Controller = application::MovementController;
using Controls = platform::ctr::MovementControls;
using Session = domain::SessionState;
constexpr std::uint64_t frequency = SYSCLOCK_ARM11;
constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
std::uint64_t ticks(std::uint64_t microseconds) {
    return (microseconds * frequency + 999999) / 1000000;
}
using Bytes = std::array<unsigned char, sizeof(application::InspectionActorSnapshot)>;
Bytes bytes(const Controller &c) {
    Bytes b;
    std::memcpy(b.data(), &c.snapshot(), b.size());
    return b;
}
void mapping() {
    using Input = application::MovementInput;
    for (const auto &entry : {std::pair{KEY_DUP, &Input::forward},
                              {KEY_DDOWN, &Input::backward},
                              {KEY_DLEFT, &Input::left},
                              {KEY_DRIGHT, &Input::right},
                              {KEY_B, &Input::run}}) {
        const auto held = platform::ctr::movement_input(entry.first, 0);
        const auto down = platform::ctr::movement_input(0, entry.first);
        CHECK(held.*entry.second && !(down.*entry.second) && held.any_held && down.any_held);
    }
    for (const auto &entry : {std::pair{KEY_A, &Input::pause},
                              {KEY_R, &Input::advance},
                              {KEY_L, &Input::restart},
                              {KEY_START, &Input::quit}}) {
        CHECK(platform::ctr::movement_input(0, entry.first).*entry.second);
        CHECK(!(platform::ctr::movement_input(entry.first, 0).*entry.second));
    }
    const auto empty = platform::ctr::movement_input(0, 0);
    CHECK(!empty.any_held && !empty.forward && !empty.run && !empty.quit);
    CHECK(platform::ctr::movement_input(KEY_SELECT | KEY_X | KEY_Y, 0).any_held);
}
void commands_and_hooks() {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    {
        Controls controls(c);
        CHECK(controls.frame(KEY_X, 0, 0) == 0 && c.awaiting_release());
        CHECK(controls.frame(0, 0, frequency * 1000) == 0 && !c.awaiting_release());
        // Establish a regular origin after the deliberately large release interval.
        const auto origin = frequency * 1000;
        CHECK(controls.frame(KEY_DUP, 0, origin + ticks(40000)) == 1);
        CHECK(c.snapshot().animation.clock.target_id == 109);
        const auto before_pause = bytes(c);
        CHECK(controls.frame(KEY_A, KEY_A, origin + ticks(80000)) == 0 &&
              c.state() == Session::paused);
        CHECK(controls.frame(KEY_A, 0, origin + ticks(120000)) == 0 && c.awaiting_release());
        CHECK(controls.frame(0, 0, origin + frequency * 3600) == 0 && !c.awaiting_release());
        CHECK(bytes(c) == before_pause);
        CHECK(controls.frame(0, 0, origin + frequency * 3600 + ticks(100000)) == 0);
        CHECK(controls.frame(0, 0, origin + frequency * 3600 + ticks(200000)) == 0);
        CHECK(controls.frame(KEY_R | KEY_DUP, KEY_R, origin + frequency * 3601) == 0);
        CHECK(controls.frame(KEY_R | KEY_DUP, 0, origin + frequency * 3601 + ticks(100000)) == 1);
        CHECK(c.snapshot().movement.ordinal == 2 && c.state() == Session::paused);
        CHECK(controls.frame(KEY_R, 0, origin + frequency * 3602) == 0);
        CHECK(controls.frame(KEY_L, KEY_L, origin + frequency * 3603) == 0);
        CHECK(c.snapshot().movement.ordinal == 0 && c.state() == Session::paused);
        std::uint64_t now = origin + frequency * 3604;
        CHECK(controls.frame(0, 0, now) == 0 && !c.awaiting_release());
        for (bool paused : {true, false}) {
            if (!paused) {
                CHECK(controls.frame(KEY_A, KEY_A, ++now) == 0);
                CHECK(controls.frame(0, 0, ++now) == 0);
            }
            CHECK(c.state() == (paused ? Session::paused : Session::running));
            for (auto sleep : {APTHOOK_ONSUSPEND, APTHOOK_ONSLEEP}) {
                const auto before = bytes(c);
                fake::event(sleep);
                fake::event(sleep);
                CHECK(c.state() == Session::suspended && c.remainder_us() == 0);
                now += frequency * 3600;
                CHECK(controls.frame(KEY_L, KEY_L, now) == 0);
                fake::event(sleep == APTHOOK_ONSLEEP ? APTHOOK_ONWAKEUP : APTHOOK_ONRESTORE);
                CHECK(c.state() == (paused ? Session::paused : Session::running) &&
                      c.awaiting_release());
                CHECK(controls.frame(KEY_SELECT, 0, ++now) == 0 && c.awaiting_release());
                CHECK(controls.frame(0, 0, ++now) == 0 && !c.awaiting_release());
                CHECK(bytes(c) == before);
            }
        }
        // Duplicate wake and an unmapped APT hook preserve fractional time/baseline.
        const auto base = now;
        CHECK(controls.frame(0, 0, base + ticks(20000)) == 0);
        fake::event(APTHOOK_ONWAKEUP);
        fake::event(static_cast<APT_HookType>(5));
        CHECK(controls.frame(0, 0, base + ticks(40000)) == 1);
        fake::event(APTHOOK_ONEXIT);
        const auto stopped = bytes(c);
        CHECK(c.state() == Session::stopped);
        CHECK(controls.frame(KEY_A | KEY_L, KEY_A | KEY_L, maximum) == 0);
        fake::event(APTHOOK_ONRESTORE);
        CHECK(bytes(c) == stopped && c.state() == Session::stopped);
    }
    CHECK(!fake::callback && fake::hooks == fake::unhooks);
    // START has priority even with the initial release guard and other commands.
    Controller other(profile, rig(), reader, contacts, spawn, 0);
    Controls controls(other);
    CHECK(controls.frame(KEY_START | KEY_A, KEY_START | KEY_A, 0) == 0);
    CHECK(other.state() == Session::stopped && other.snapshot().movement.ordinal == 0);
}
void clock_limits() {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    Controls controls(c);
    CHECK(controls.frame(0, 0, 100) == 0);
    CHECK(controls.frame(KEY_DUP, 0, 100 + ticks(39999)) == 0);
    CHECK(c.remainder_us() == 39999);
    CHECK(controls.frame(KEY_DUP, 0, 0) == 0 && c.remainder_us() == 0); // Backward clock.
    CHECK(controls.frame(KEY_DUP, 0, ticks(40000)) == 1);
    auto previous = ticks(40000);
    CHECK(controls.frame(KEY_DUP, 0, previous + ticks(120001)) == 3 && c.remainder_us() == 0);
    CHECK(controls.frame(KEY_DUP, 0, maximum) == 0 && c.remainder_us() == 0);
    CHECK(controls.frame(KEY_DUP, 0, 0) == 0);
    CHECK(controls.frame(KEY_DUP, 0, ticks(40000)) == 1);
    contacts.fail_at = contacts.calls;
    CHECK(controls.frame(KEY_DUP, 0, ticks(80000)) == 0);
    CHECK(c.state() == Session::paused && c.awaiting_release());
}
void noisy_single_step() {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    Controls controls(c);
    std::uint64_t us = 0;
    const auto sample = [&](u32 held, u32 down, unsigned dt = 20000) {
        us += dt;
        return controls.frame(held, down, ticks(us));
    };
    sample(0, 0);
    sample(KEY_A, KEY_A);
    sample(0, 0);
    for (unsigned i = 0; i < 10; ++i)
        sample(0, 0);
    const auto frozen = bytes(c);
    // Realistic HID edges from a chattering R switch: 20 ms high, 20 ms low.
    for (unsigned i = 0; i < 250; ++i) {
        CHECK(sample(KEY_R, KEY_R) == 0);
        CHECK(sample(0, 0) == 0);
        CHECK(c.state() == Session::paused && bytes(c) == frozen);
    }
    // A deliberate press commits once, even if the SDK repeats its down bit.
    for (unsigned i = 0; i < 10; ++i)
        sample(0, 0);
    unsigned steps = 0;
    for (unsigned i = 0; i < 100; ++i)
        steps += sample(KEY_R, KEY_R);
    CHECK(steps == 1 && c.snapshot().movement.ordinal == 1);
    // Short release bounce must not rearm an already consumed press.
    sample(0, 0);
    for (unsigned i = 0; i < 100; ++i)
        CHECK(sample(KEY_R, KEY_R) == 0);
    for (unsigned i = 0; i < 10; ++i)
        sample(0, 0);
    for (unsigned i = 0; i < 10; ++i)
        steps += sample(KEY_R, i ? 0 : KEY_R);
    CHECK(steps == 2 && c.snapshot().movement.ordinal == 2);
    // Contradictory down-only samples and an unobserved edge cannot authorize a step.
    for (unsigned i = 0; i < 10; ++i)
        CHECK(sample(0, KEY_R) == 0);
    for (unsigned i = 0; i < 10; ++i)
        sample(0, 0);
    for (unsigned i = 0; i < 10; ++i)
        CHECK(sample(KEY_R, 0) == 0);
    // Suspension, restart and clock discontinuity discard a partially qualified press.
    for (unsigned mode = 0; mode < 5; ++mode) {
        for (unsigned i = 0; i < 10; ++i)
            sample(0, 0);
        CHECK(sample(KEY_R, KEY_R) == 0);
        if (mode == 0) {
            fake::event(APTHOOK_ONSUSPEND);
            fake::event(APTHOOK_ONRESTORE);
        } else if (mode == 1)
            sample(KEY_R | KEY_L, KEY_L);
        else if (mode == 2)
            sample(KEY_R, 0, 1000001);
        else if (mode == 3) {
            us = 0;
            sample(KEY_R, 0);
        } else {
            sample(KEY_A | KEY_R, KEY_A);
            sample(0, 0);
            sample(KEY_A | KEY_R, KEY_A);
        }
        const auto old = bytes(c);
        for (unsigned i = 0; i < 10; ++i)
            CHECK(sample(KEY_R, 0) == 0 && bytes(c) == old);
    }
}
void single_step_boundary() {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    Controls controls(c);
    controls.frame(0, 0, 0);
    controls.frame(KEY_A, KEY_A, 1);
    controls.frame(0, 0, 2);
    controls.frame(0, 0, 3);
    // Use integral hardware ticks so the boundary is independent of conversion rounding.
    constexpr auto stable = (frequency * 80 + 999) / 1000;
    controls.frame(0, 0, 3 + stable);
    CHECK(controls.frame(KEY_R, KEY_R, 4 + stable) == 0);
    CHECK(controls.frame(KEY_R, 0, 3 + stable * 2) == 0);
    CHECK(controls.frame(KEY_R, 0, 4 + stable * 2) == 1);
    CHECK(c.snapshot().movement.ordinal == 1 && c.state() == Session::paused);
    CHECK(controls.frame(KEY_R, KEY_R, 5 + stable * 2) == 0);
}
void cadence(unsigned rate) {
    Reader reader;
    Contacts contacts;
    Controller c(profile, rig(), reader, contacts, spawn, 0);
    Controls controls(c);
    CHECK(controls.frame(0, 0, 0) == 0);
    unsigned steps = 0;
    for (unsigned frame = 1; frame <= rate * 2; ++frame)
        steps += controls.frame(KEY_DUP, 0, frequency * frame / rate);
    // Without the carried conversion remainder, 60/143 Hz would lose the last tick.
    CHECK(steps == 50 && c.snapshot().movement.ordinal == 50 && c.remainder_us() == 0);
    CHECK(c.snapshot().movement.position.z == spawn.z + 50 * 28);
}
void turn_cache_lifecycle() {
    for (bool left : {false, true}) {
        for (unsigned phase : {1U, 7U, 8U}) { // Entry cache, stable turn, return cache.
            Reader reader;
            Contacts contacts;
            Controller c(domain::heather_turns_profile, rig(), reader, contacts, spawn, 0);
            application::MovementInput turn;
            turn.left = left;
            turn.right = !left;
            c.step({}, 0);
            for (unsigned i = 0; i < phase; ++i)
                CHECK(c.step(i == 7 ? application::MovementInput{} : turn, 40000) == 1);
            CHECK(c.snapshot().animation.clock.profile_id == 2);
            CHECK(c.snapshot().animation.clock.saved_local_valid == (phase != 7));
            const auto original = bytes(c);
            Controls controls(c, true);
            std::uint64_t now = 0;
            const auto sample = [&](u32 held, u32 down, unsigned dt = 20000) {
                now += ticks(dt);
                return controls.frame(held, down, now);
            };
            CHECK(sample(0, 0) == 0);
            // HOME/tapa while RUNNING and PAUSED, including overlapping reasons.
            for (bool paused : {false, true}) {
                if (paused) {
                    sample(KEY_A, KEY_A);
                    sample(0, 0);
                }
                CHECK(c.state() == (paused ? Session::paused : Session::running));
                for (auto sleep : {APTHOOK_ONSUSPEND, APTHOOK_ONSLEEP}) {
                    fake::event(sleep);
                    CHECK(c.state() == Session::suspended && !c.pending_action() &&
                          !c.remainder_us());
                    sample(KEY_R | KEY_L | KEY_DUP, KEY_R | KEY_L, 10000000);
                    fake::event(sleep == APTHOOK_ONSLEEP ? APTHOOK_ONWAKEUP : APTHOOK_ONRESTORE);
                    CHECK(c.awaiting_release());
                    sample(KEY_R, KEY_R);
                    CHECK(sample(0, 0, 10000000) == 0 && !c.awaiting_release());
                    CHECK(bytes(c) == original);
                }
                fake::event(APTHOOK_ONSUSPEND);
                fake::event(APTHOOK_ONSLEEP);
                fake::event(APTHOOK_ONRESTORE);
                CHECK(c.state() == Session::suspended);
                sample(0, 0, 10000000);
                fake::event(APTHOOK_ONWAKEUP);
                CHECK(sample(0, 0) == 0 && bytes(c) == original);
            }
            CHECK(sample(0, 0, 10000000) == 0 && bytes(c) == original);
            for (unsigned i = 0; i < 10; ++i)
                sample(0, 0);
            const auto held = KEY_R | (left ? KEY_DLEFT : KEY_DRIGHT);
            CHECK(sample(held, KEY_R) == 0);
            unsigned steps = 0;
            for (unsigned i = 0; i < 100; ++i)
                steps += sample(held, KEY_R);
            CHECK(steps == 1 && c.snapshot().movement.ordinal == phase + 1);
            const auto advanced = bytes(c);
            for (unsigned i = 0; i < 100; ++i)
                CHECK(sample(held, 0) == 0 && bytes(c) == advanced);
            sample(0, 0);
            CHECK(sample(0, 0, 10000000) == 0 && bytes(c) == advanced);
            sample(KEY_L, KEY_L);
            CHECK(c.state() == Session::paused && c.awaiting_release());
            CHECK(c.snapshot().movement.ordinal == 0 && c.snapshot().animation.clock.counter == 0);
            CHECK(c.snapshot().animation.clock.profile_id == 2 &&
                  c.snapshot().animation.clock.target_id == 101);
            CHECK(!c.snapshot().animation.clock.saved_local_valid && !c.pending_action());
            sample(0, 0);
            sample(KEY_A, KEY_A);
            sample(0, 0);
            CHECK(sample(left ? KEY_DLEFT : KEY_DRIGHT, 0, 40000) == 1);
            CHECK(c.snapshot().movement.ordinal == 1 &&
                  c.snapshot().animation.clock.target_id == (left ? 108U : 107U));
            sample(KEY_START | KEY_A | KEY_L | KEY_R, KEY_START | KEY_A | KEY_L | KEY_R);
            CHECK(c.state() == Session::stopped && c.snapshot().movement.ordinal == 1);
        }
    }
}
} // namespace
int main() {
    turn_cache_lifecycle();
    noisy_single_step();
    single_step_boundary();
    mapping();
    commands_and_hooks();
    clock_limits();
    cadence(25);
    cadence(60);
    cadence(143);
    CHECK(fake::hooks == fake::unhooks && !fake::callback);
    std::puts("Actual 3DS movement adapter: HID, APT RAII and ARM11 fractional clock passed");
}
