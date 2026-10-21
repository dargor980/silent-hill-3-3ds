#pragma once
#include "sh3/domain/render_scene.hpp"
#include <array>
#include <cstdint>

namespace sh3::domain {
using Quaternion = std::array<float, 4>;
using PoseMatrix = std::array<float, 16>;
using SkeletonPose = std::array<PoseMatrix, 3>;
struct InspectionClip {
    std::array<int, 3> parents{-1, -1, 1};
    Vec3 center{};
    float scale{1};
    std::array<Vec3, 3> translations{};
    std::array<std::array<Quaternion, 3>, 24> rotations{};
};
inline constexpr std::uint32_t clip_period = 24 * 4096;
inline constexpr std::uint32_t clip_increment = 3686;
using SkeletonMesh = std::array<SceneVertex, 120>;
[[nodiscard]] bool valid_clip(const InspectionClip &) noexcept;
// Callers validate the immutable clip once. Counter is always bounded internally.
[[nodiscard]] SkeletonPose evaluate_pose(const InspectionClip &, std::uint32_t counter) noexcept;
[[nodiscard]] SkeletonMesh skeleton_mesh(const InspectionClip &, const SkeletonPose &) noexcept;
} // namespace sh3::domain
