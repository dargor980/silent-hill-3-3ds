#include "sh3/domain/locomotion_update.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::domain {
namespace {
using Error = LocomotionError;
bool valid_model(const LocomotionState &state) noexcept {
    for (std::uint32_t i = 0; i < state.skeleton.bone_count; ++i) {
        const auto &matrix = state.model[i];
        for (const auto value : matrix)
            if (!std::isfinite(value))
                return false;
        if (matrix[3] != 0 || matrix[7] != 0 || matrix[11] != 0 || matrix[15] != 1)
            return false;
    }
    return true;
}
void publish(const LocomotionClock &clock, const LocomotionSkeleton &rig,
             const LocomotionPoseScratch &pose, LocomotionState &state) noexcept {
    // All fallible work and reader callbacks have finished. These copies cannot fail.
    // Publish only active matrices; stale workspace slots must never leak into state.
    state.skeleton = rig;
    state.cache = pose.next;
    state.model.fill({});
    std::copy_n(pose.model.begin(), rig.bone_count, state.model.begin());
    state.clock = clock;
}
} // namespace
Error initialize_locomotion(const LocomotionProfile &profile, const LocomotionSkeleton &rig,
                            const LocomotionSampleReader &reader, LocomotionState &state,
                            LocomotionWorkspace &workspace, std::uint32_t initial_clip) noexcept {
    if (!valid_locomotion_profile(profile) || !valid_locomotion_skeleton(rig))
        return Error::invalid_profile;
    const auto error = initialize_locomotion_pose(rig, reader, workspace.pose, initial_clip, profile);
    if (error != Error::ok)
        return error;
    workspace.plan = {};
    workspace.plan.next = initial_locomotion_clock(profile);
    workspace.plan.next.source_id = workspace.plan.next.target_id = initial_clip;
    // Initialization does not consume a tick; the first update still evaluates clip[0].
    publish(workspace.plan.next, rig, workspace.pose, state);
    return Error::ok;
}
Error update_locomotion(const LocomotionProfile &profile, const LocomotionSampleReader &reader,
                        std::optional<std::uint32_t> request, std::uint32_t ticks,
                        LocomotionState &state, LocomotionWorkspace &workspace) noexcept {
    if (!valid_locomotion_profile(profile))
        return Error::invalid_profile;
    if (!valid_locomotion_skeleton(state.skeleton) || !state.cache.last_valid ||
        state.cache.bone_count != state.skeleton.bone_count ||
        state.cache.saved_valid != state.clock.saved_local_valid)
        return Error::invalid_state;
    const auto error = plan_locomotion_update(profile, state.clock, request, ticks, workspace.plan);
    if (error != Error::ok)
        return error;
    const auto pose_error = stage_locomotion_pose(state.skeleton, reader, workspace.plan,
                                                 state.cache, workspace.pose);
    if (pose_error != Error::ok)
        return pose_error;
    if (!valid_model(state))
        return Error::invalid_pose;
    publish(workspace.plan.next, state.skeleton, workspace.pose, state);
    return Error::ok;
}
} // namespace sh3::domain
