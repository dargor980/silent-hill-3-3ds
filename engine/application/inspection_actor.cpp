#include "sh3/application/inspection_actor.hpp"
#include <limits>

namespace sh3::application {
namespace {
using Error = InspectionActorError;
using AnimationError = domain::LocomotionError;
class CallScope final {
  public:
    explicit CallScope(bool &busy) noexcept : busy_(busy) { busy_ = true; }
    ~CallScope() { busy_ = false; }

  private:
    bool &busy_;
};
InspectionActorResult animation_failure(AnimationError error) noexcept {
    return {Error::animation_rejected, domain::InspectionMovementError::ok, error};
}
} // namespace

InspectionActor::InspectionActor(const domain::LocomotionProfile &profile,
                                 const domain::LocomotionSkeleton &skeleton,
                                 const domain::LocomotionSampleReader &reader,
                                 const ports::IMovementContacts &contacts) noexcept
    : profile_(profile), skeleton_(skeleton), reader_(reader), contacts_(contacts) {}

InspectionActorResult InspectionActor::reset(domain::Vec3 position, float yaw) noexcept {
    if (busy_)
        return {Error::busy};
    const CallScope scope(busy_);
    domain::WorkInterval interval(trace_, domain::WorkPhase::animation_pose);
    if (!domain::make_inspection_movement_model(position, yaw, staged_.instance))
        return {Error::invalid_placement};
    const auto error =
        domain::initialize_locomotion(profile_, skeleton_, reader_, staged_.animation, workspace_);
    if (error != AnimationError::ok)
        return animation_failure(error);
    staged_.movement = {position, yaw, 0};
    state_ = staged_;
    ready_ = true;
    return {};
}

InspectionActorResult InspectionActor::step(domain::InspectionMovementIntent intent,
                                            std::uint32_t ticks) noexcept {
    // Compatibility entry point: idle plus yaw still selects idle, even for a turn-capable rig.
    const auto clip = intent.motion == domain::InspectionMotion::idle   ? 101U
                      : intent.motion == domain::InspectionMotion::walk ? 109U
                                                                        : 113U;
    return step_with_clip(intent, clip, ticks);
}
InspectionActorResult InspectionActor::step_action(InspectionActionIntent intent,
                                                   std::uint32_t ticks) noexcept {
    return step_with_clip({action_motion(intent.action), intent.turn}, action_clip(intent.action),
                          ticks);
}
InspectionActorResult InspectionActor::step_with_clip(domain::InspectionMovementIntent intent,
                                                      std::uint32_t clip,
                                                      std::uint32_t ticks) noexcept {
    if (busy_)
        return {Error::busy};
    if (!ready_)
        return {Error::not_initialized};
    const CallScope scope(busy_);
    domain::WorkInterval interval(trace_, domain::WorkPhase::movement_contacts);
    domain::InspectionMovementPlan movement;
    const auto error = domain::plan_inspection_movement(state_.movement, intent, ticks, movement);
    if (error != domain::InspectionMovementError::ok)
        return {Error::movement_rejected, error};
    // Movement and action validation precede selection and contact callbacks.
    interval.next(domain::WorkPhase::animation_pose);
    const auto selection = domain::plan_locomotion_update(profile_, state_.animation.clock, clip,
                                                          ticks, workspace_.plan);
    if (selection != AnimationError::ok)
        return animation_failure(selection);
    interval.next(domain::WorkPhase::movement_contacts);
    const auto nan = std::numeric_limits<float>::quiet_NaN();
    domain::Vec3 accepted{nan, nan, nan};
    const ports::MovementContactQuery query{state_.movement.position, movement.next.position,
                                            movement.next.ordinal};
    switch (contacts_.resolve(query, accepted)) {
    case ports::MovementContactStatus::unavailable:
        return {Error::contacts_unavailable};
    case ports::MovementContactStatus::unsupported:
        return {Error::contacts_unsupported};
    case ports::MovementContactStatus::accepted:
        break;
    default:
        return {Error::invalid_contact};
    }
    if (!domain::make_inspection_movement_model(accepted, movement.next.yaw, staged_.instance))
        return {Error::invalid_contact};
    staged_.movement = movement.next;
    staged_.movement.position = accepted;
    interval.next(domain::WorkPhase::animation_pose);
    staged_.animation = state_.animation;
    const auto animation =
        domain::update_locomotion(profile_, reader_, clip, ticks, staged_.animation, workspace_);
    if (animation != AnimationError::ok)
        return animation_failure(animation);
    state_ = staged_;
    return {};
}
} // namespace sh3::application
