#pragma once
#include "sh3/domain/animation_pose.hpp"
#include <cstdint>

namespace sh3::domain {
// Bounded native profile, not an EE/VU or collision solver implementation.
inline constexpr float inspection_movement_pi = 3.14159265358979323846F;
inline constexpr float inspection_movement_limit = 1000000.0F;
inline constexpr std::uint32_t inspection_movement_step_ms = 40;
enum class InspectionMotion { idle, walk, run };
enum class InspectionTurn { none, left, right };
struct InspectionMovementIntent {
    InspectionMotion motion{InspectionMotion::idle};
    InspectionTurn turn{InspectionTurn::none};
};
struct InspectionMovementState {
    Vec3 position{};
    float yaw{};
    std::uint32_t ordinal{};
};
struct InspectionMovementPlan {
    InspectionMovementState next{};
    Vec3 displacement{}; // Requested delta, before position rounding or contact.
    PoseMatrix model{}; // Provisional T(position) * Ry(yaw), column major.
};
enum class InspectionMovementError {
    ok, invalid_state, invalid_intent, invalid_ticks, ordinal_exhausted, out_of_bounds
};

// Validates placement and builds T(position) * Ry(yaw), without consuming a tick.
// Used again after contact correction. Error leaves every output byte unchanged.
[[nodiscard]] bool make_inspection_movement_model(Vec3 position, float yaw,
                                                 PoseMatrix &out) noexcept;

// Exactly two PAL ticks, no I/O, allocation, local pose or collision response.
// On error every byte of out is unchanged; current may alias out.next.
// Caller resolves contacts and stages HL before publishing any next state.
[[nodiscard]] InspectionMovementError plan_inspection_movement(
    const InspectionMovementState &current, InspectionMovementIntent intent,
    std::uint32_t ticks, InspectionMovementPlan &out) noexcept;
} // namespace sh3::domain
