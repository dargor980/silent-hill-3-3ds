#pragma once
#include "sh3/domain/inspection_movement.hpp"
#include "sh3/domain/locomotion_update.hpp"
#include "sh3/ports/movement_contacts.hpp"

namespace sh3::application {
struct InspectionActorSnapshot {
    domain::InspectionMovementState movement{};
    domain::LocomotionState animation{}; // Model space; no world translation here.
    domain::PoseMatrix instance{}; // Apply once, after the local pose.
};
enum class InspectionActorError {
    ok, busy, not_initialized, invalid_placement, movement_rejected,
    contacts_unavailable, contacts_unsupported, invalid_contact, animation_rejected
};
struct InspectionActorResult {
    InspectionActorError error{InspectionActorError::ok};
    domain::InspectionMovementError movement{domain::InspectionMovementError::ok};
    domain::LocomotionError animation{domain::LocomotionError::ok};
};

// Single owner thread. Reader and contacts outlive the actor; neither may mutate its inputs.
// All callbacks observe only the previous published snapshot. Failures never change it.
class InspectionActor final {
  public:
    InspectionActor(const domain::LocomotionProfile &, const domain::LocomotionSkeleton &,
                    const domain::LocomotionSampleReader &, const ports::IMovementContacts &) noexcept;
    InspectionActor(const InspectionActor &) = delete;
    InspectionActor &operator=(const InspectionActor &) = delete;

    // Explicit scene-validated spawn/restart, idle frame 0, ordinal 0, no contact query.
    [[nodiscard]] InspectionActorResult reset(domain::Vec3 position, float yaw) noexcept;
    [[nodiscard]] InspectionActorResult step(domain::InspectionMovementIntent,
                                             std::uint32_t ticks) noexcept;
    [[nodiscard]] bool ready() const noexcept { return ready_; }
    // Renderable only when ready(); otherwise the initial zero snapshot is diagnostic data.
    [[nodiscard]] const InspectionActorSnapshot &snapshot() const noexcept { return state_; }

  private:
    const domain::LocomotionProfile profile_;
    const domain::LocomotionSkeleton skeleton_;
    const domain::LocomotionSampleReader &reader_;
    const ports::IMovementContacts &contacts_;
    InspectionActorSnapshot state_{}, staged_{};
    domain::LocomotionWorkspace workspace_{};
    bool ready_{}, busy_{};
};
static_assert(std::is_nothrow_copy_assignable_v<InspectionActorSnapshot>);
static_assert(sizeof(InspectionActor) <= 32 * 1024, "Inspection actor exceeds 32 KiB");
} // namespace sh3::application
