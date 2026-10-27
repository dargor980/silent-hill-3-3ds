#pragma once
#include "sh3/domain/animation_pose.hpp"
#include "sh3/domain/locomotion_clock.hpp"
#include <cstddef>

namespace sh3::domain {
inline constexpr std::size_t locomotion_bones = 73;
struct LocomotionTransform {
    Vec3 translation{};
    Quaternion rotation{}; // XYZW, not an implicit identity.
};
using LocomotionLocalPose = std::array<LocomotionTransform, locomotion_bones>;
struct LocomotionSkeleton {
    std::uint32_t bone_count{};
    std::array<int, locomotion_bones> parents{}; // Compact, topological; -1 = root.
    std::array<std::uint8_t, locomotion_bones> channels{}; // Exactly one owner: 1 or 2.
};
// Structural validation; original Heather's source map is authenticated by the converter.
[[nodiscard]] bool valid_locomotion_skeleton(const LocomotionSkeleton &) noexcept;

class LocomotionSampleReader {
  public:
    virtual ~LocomotionSampleReader() = default;
    // Relative frame within clip; compact bone. Reader supplies immutable local TR data.
    [[nodiscard]] virtual bool read(std::uint32_t clip, std::uint32_t frame,
                                    std::uint32_t bone, LocomotionTransform &out) const noexcept = 0;
};
struct LocomotionPoseCache {
    std::uint32_t bone_count{};
    bool last_valid{}, saved_valid{};
    LocomotionLocalPose last_local{}, saved_local{};
};
struct LocomotionPoseScratch {
    LocomotionPoseCache next{};
    std::array<PoseMatrix, locomotion_bones> model{};
};

// Caller-owned staging only: scratch can be partial on error and MUST NOT be published.
// No clock/state/output publication occurs here. Current must not alias scratch.next.
// Use a plan returned by plan_locomotion_update for the same current pose/clock.
[[nodiscard]] LocomotionError stage_locomotion_pose(
    const LocomotionSkeleton &, const LocomotionSampleReader &, const LocomotionPlan &,
    const LocomotionPoseCache &current, LocomotionPoseScratch &scratch) noexcept;
// First sample of a supported clip, both channels, no clock advance.
// Default idle preserves initialization semantics; explicit clip is an inspection restart.
[[nodiscard]] LocomotionError initialize_locomotion_pose(
    const LocomotionSkeleton &, const LocomotionSampleReader &,
    LocomotionPoseScratch &scratch, std::uint32_t initial_clip = 101) noexcept;
} // namespace sh3::domain
