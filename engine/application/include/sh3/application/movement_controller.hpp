#pragma once
#include "sh3/application/inspection_actor.hpp"
#include "sh3/domain/lifecycle.hpp"
#include <optional>

namespace sh3::application {
struct MovementInput {
    bool forward{}, backward{}, left{}, right{}, run{}; // Held controls.
    bool pause{}, advance{}, restart{}, quit{};         // Press edges.
    bool any_held{}; // Includes controls not yet mapped to movement.
};
inline constexpr std::uint32_t movement_step_us = 40000;
inline constexpr std::uint32_t movement_max_interval_us = 120000;
inline constexpr std::uint32_t movement_discontinuity_us = 1000000;

// Narrow HID/APT boundary, shared by the controller and the composed room loop.
class IMovementSession {
  public:
    virtual ~IMovementSession() = default;
    virtual unsigned step(MovementInput, std::uint64_t elapsed_us) noexcept = 0;
    virtual void dispatch(domain::LifecycleEvent) noexcept = 0;
    virtual domain::SessionState state() const noexcept = 0;
    virtual bool awaiting_release() const noexcept = 0;
};

// Fixed inspection cadence. Owns simulation; rendering may only observe snapshot().
// Single owner thread. Reentrant calls from callbacks have no effects.
class MovementController final : public IMovementSession {
  public:
    MovementController(const domain::LocomotionProfile &, const domain::LocomotionSkeleton &,
                       const domain::LocomotionSampleReader &, const ports::IMovementContacts &,
                       domain::Vec3 validated_spawn, float yaw) noexcept;
    // Input is held throughout the supplied interval. Returns committed updates (0..3).
    unsigned step(MovementInput, std::uint64_t elapsed_us) noexcept override;
    void dispatch(domain::LifecycleEvent) noexcept override;
    const InspectionActorSnapshot &snapshot() const noexcept { return actor_.snapshot(); }
    bool ready() const noexcept { return actor_.ready(); }
    domain::SessionState state() const noexcept override { return lifecycle_.state(); }
    bool awaiting_release() const noexcept override { return awaiting_release_; }
    std::uint32_t remainder_us() const noexcept { return remainder_us_; }
    std::optional<InspectionAction> pending_action() const noexcept { return pending_; }
    // Legacy diagnostic view; pending_action retains the full direction for profile 2.
    std::optional<domain::InspectionMotion> pending_motion() const noexcept {
        return pending_ ? std::optional<domain::InspectionMotion>{action_motion(*pending_)}
                        : std::nullopt;
    }
    InspectionActorResult result() const noexcept { return result_; }
    void trace(domain::WorkTrace *value) noexcept { actor_.trace(value); }
    // External presentation/spawn failures discard timing and require release without changing
    // pose.
    void pause_on_fault() noexcept;

  private:
    void clear_timing() noexcept;
    void apply_event(domain::LifecycleEvent) noexcept;
    void fail() noexcept;
    bool update(InspectionActionIntent desired) noexcept;
    InspectionActor actor_;
    domain::Lifecycle lifecycle_{};
    const domain::Vec3 spawn_;
    const float yaw_;
    std::uint32_t remainder_us_{};
    std::optional<InspectionAction> pending_{};
    InspectionActorResult result_{};
    const bool turns_;
    bool awaiting_release_{true}, busy_{};
};
static_assert(sizeof(MovementController) <= 32 * 1024);
} // namespace sh3::application
