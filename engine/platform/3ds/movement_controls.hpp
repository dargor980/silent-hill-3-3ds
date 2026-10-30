#pragma once
#include "sh3/application/movement_controller.hpp"
#include <3ds.h>

namespace sh3::platform::ctr {
[[nodiscard]] application::MovementInput movement_input(u32 held, u32 down) noexcept;
// The scene loop supplies one HID sample and svcGetSystemTick() per frame.
// Register only one instance per controller. Controller outlives this hook owner.
class MovementControls final {
  public:
    explicit MovementControls(application::IMovementSession &, bool fast_cpu = false) noexcept;
    ~MovementControls();
    MovementControls(const MovementControls &) = delete;
    MovementControls &operator=(const MovementControls &) = delete;
    unsigned frame(u32 held, u32 down, std::uint64_t now) noexcept;

  private:
    static void hook(APT_HookType, void *) noexcept;
    bool single_step(u32 held, u32 down, std::uint64_t now, bool enabled) noexcept;
    application::IMovementSession &controller_;
    aptHookCookie cookie_{};
    std::uint64_t previous_{}, fraction_{};
    bool baseline_{};
    const bool fast_cpu_{};
    unsigned suspended_{}; // HOME and lid are independent, possibly overlapping reasons.
    // R needs 80 ms continuously released to arm, then 80 ms held to commit once.
    // These clocks never feed simulation time and are reset at lifecycle/command barriers.
    std::uint64_t r_previous_{}, r_changed_{};
    bool r_seen_{}, r_held_{}, r_armed_{}, r_pending_{};
};
static_assert(sizeof(application::MovementController) + sizeof(MovementControls) <= 32 * 1024);
} // namespace sh3::platform::ctr
