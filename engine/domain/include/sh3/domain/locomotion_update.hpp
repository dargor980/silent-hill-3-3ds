#pragma once
#include "sh3/domain/locomotion_pose.hpp"
#include <type_traits>

namespace sh3::domain {
// The single published snapshot. Consumers read it only between calls on its owning thread.
// No wire deserialization: initialize through initialize_locomotion, then use update_locomotion.
struct LocomotionState {
    LocomotionClock clock{};
    LocomotionSkeleton skeleton{}; // Owned topology; later changes to the input rig cannot affect it.
    LocomotionPoseCache cache{};
    std::array<PoseMatrix, locomotion_bones> model{};
};
// Persistent caller-owned storage, distinct from state and the reader's immutable sample data.
// Scratch is disposable after error; it is never a renderable/public snapshot.
struct LocomotionWorkspace {
    LocomotionPlan plan{};
    LocomotionPoseScratch pose{};
};
inline constexpr std::size_t locomotion_memory_budget = 32 * 1024;
static_assert(sizeof(LocomotionState) + sizeof(LocomotionWorkspace) <= locomotion_memory_budget,
              "Locomotion state and workspace exceed the 32 KiB budget");
static_assert(std::is_nothrow_copy_assignable_v<LocomotionState>);

// Both functions provide the strong error guarantee: state remains byte-for-byte unchanged
// on any error. Publication is synchronous, not synchronization for concurrent readers.
// Initialization may replace an existing state, but only after its new pose is complete.
// Explicit initial_clip restarts that clip in stable mode at frame zero; no tick consumed.
[[nodiscard]] LocomotionError initialize_locomotion(
    const LocomotionProfile &, const LocomotionSkeleton &, const LocomotionSampleReader &,
    LocomotionState &state, LocomotionWorkspace &workspace,
    std::uint32_t initial_clip = 101) noexcept;
[[nodiscard]] LocomotionError update_locomotion(
    const LocomotionProfile &, const LocomotionSampleReader &, std::optional<std::uint32_t> request,
    std::uint32_t ticks, LocomotionState &state, LocomotionWorkspace &workspace) noexcept;
} // namespace sh3::domain
