#include "movement_controls.hpp"
#include <limits>

namespace sh3::platform::ctr {
application::MovementInput movement_input(u32 held, u32 down) noexcept {
    return {bool(held & KEY_DUP),    bool(held & KEY_DDOWN), bool(held & KEY_DLEFT),
            bool(held & KEY_DRIGHT), bool(held & KEY_B),     bool(down & KEY_A),
            bool(down & KEY_R),      bool(down & KEY_L),     bool(down & KEY_START),
            bool(held | down)};
}
MovementControls::MovementControls(application::IMovementSession &controller,
                                   bool fast_cpu) noexcept
    : controller_(controller), fast_cpu_(fast_cpu) {
    aptHook(&cookie_, hook, this);
}
MovementControls::~MovementControls() { aptUnhook(&cookie_); }
void MovementControls::hook(APT_HookType type, void *context) noexcept {
    auto &self = *static_cast<MovementControls *>(context);
    using Event = domain::LifecycleEvent;
    Event event = Event::none;
    const auto reasons = self.suspended_;
    switch (type) {
    case APTHOOK_ONSUSPEND:
        self.suspended_ |= 1;
        break;
    case APTHOOK_ONSLEEP:
        self.suspended_ |= 2;
        break;
    case APTHOOK_ONRESTORE:
        self.suspended_ &= ~1U;
        break;
    case APTHOOK_ONWAKEUP:
        self.suspended_ &= ~2U;
        break;
    case APTHOOK_ONEXIT:
        event = Event::quit;
        break;
    default:
        return;
    }
    if (!reasons && self.suspended_)
        event = Event::suspend;
    else if (reasons && !self.suspended_) {
        if (self.fast_cpu_)
            osSetSpeedupEnable(true);
        event = Event::resume;
    }
    const auto before = self.controller_.state();
    self.controller_.dispatch(event);
    if (self.controller_.state() != before) {
        self.baseline_ = false;
        self.fraction_ = 0;
        self.r_seen_ = false;
    }
}
bool MovementControls::single_step(u32 held, u32 down, std::uint64_t now, bool enabled) noexcept {
    constexpr auto stable_ticks = (SYSCLOCK_ARM11 * 80 + 999) / 1000;
    const bool level = held & KEY_R;
    if (!enabled || ((down & KEY_R) && !level)) {
        r_seen_ = false;
        return false;
    }
    if (!r_seen_ || now < r_previous_ || now - r_previous_ > SYSCLOCK_ARM11) {
        r_seen_ = true;
        r_held_ = level;
        r_armed_ = r_pending_ = false;
        r_previous_ = r_changed_ = now;
        return false;
    }
    r_previous_ = now;
    if (level != r_held_) {
        r_pending_ = level && r_armed_ && (down & KEY_R);
        r_armed_ = false;
        r_held_ = level;
        r_changed_ = now;
    }
    if (now - r_changed_ < stable_ticks)
        return false;
    if (!level)
        r_armed_ = true;
    if (!r_pending_)
        return false;
    r_pending_ = false;
    return true;
}
unsigned MovementControls::frame(u32 held, u32 down, std::uint64_t now) noexcept {
    auto input = movement_input(held, down);
    const bool paused = controller_.state() == domain::SessionState::paused;
    const bool advance = single_step(held, down, now,
                                     paused && !controller_.awaiting_release() && !input.pause &&
                                         !input.restart && !input.quit);
    if (paused)
        input.advance = advance;
    constexpr std::uint64_t frequency = SYSCLOCK_ARM11;
    constexpr std::uint64_t million = 1000000;
    const bool interrupted = controller_.state() != domain::SessionState::running ||
                             controller_.awaiting_release() || input.pause || input.advance ||
                             input.restart || input.quit;
    std::uint64_t elapsed = 0;
    if (interrupted || !baseline_) {
        fraction_ = 0;
    } else if (now < previous_ || now - previous_ > frequency) {
        elapsed = std::numeric_limits<std::uint64_t>::max();
        fraction_ = 0;
    } else {
        const auto numerator = (now - previous_) * million + fraction_;
        elapsed = numerator / frequency;
        fraction_ = elapsed > application::movement_max_interval_us ? 0 : numerator % frequency;
    }
    previous_ = now;
    baseline_ = true;
    const auto committed = controller_.step(input, elapsed);
    if (controller_.state() != domain::SessionState::running || controller_.awaiting_release())
        fraction_ = 0;
    return committed;
}
} // namespace sh3::platform::ctr
