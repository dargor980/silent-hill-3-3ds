#include "sh3/domain/inspection_movement.hpp"
#include <cmath>
#include <limits>

namespace sh3::domain {
namespace {
static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
bool bounded(float value) noexcept {
    return std::isfinite(value) && std::abs(value) <= inspection_movement_limit;
}
bool valid_position(Vec3 p) noexcept {
    return bounded(p.x) && bounded(p.y) && bounded(p.z);
}
bool valid_placement(Vec3 p, float yaw) noexcept {
    return valid_position(p) && std::isfinite(yaw) &&
           yaw >= -inspection_movement_pi && yaw < inspection_movement_pi;
}
PoseMatrix model(Vec3 p, float yaw) noexcept {
    const auto c = std::cos(yaw);
    const auto s = std::sin(yaw);
    return {c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, p.x, p.y, p.z, 1};
}
} // namespace

bool make_inspection_movement_model(Vec3 position, float yaw, PoseMatrix &out) noexcept {
    if (!valid_placement(position, yaw))
        return false;
    out = model(position, yaw);
    return true;
}

InspectionMovementError plan_inspection_movement(
    const InspectionMovementState &current, InspectionMovementIntent intent,
    std::uint32_t ticks, InspectionMovementPlan &out) noexcept {
    using Error = InspectionMovementError;
    constexpr auto pi = inspection_movement_pi;
    if (!valid_placement(current.position, current.yaw))
        return Error::invalid_state;
    float distance = 0;
    switch (intent.motion) {
    case InspectionMotion::idle: break;
    case InspectionMotion::walk: distance = 28; break;
    case InspectionMotion::run: distance = 70; break;
    default: return Error::invalid_intent;
    }
    float turn = 0;
    switch (intent.turn) {
    case InspectionTurn::none: break;
    case InspectionTurn::left: turn = -0.088F; break;
    case InspectionTurn::right: turn = 0.088F; break;
    default: return Error::invalid_intent;
    }
    if (ticks != 2)
        return Error::invalid_ticks;
    if (current.ordinal == std::numeric_limits<std::uint32_t>::max())
        return Error::ordinal_exhausted;

    InspectionMovementPlan staged{};
    staged.next = current;
    if (distance != 0) {
        staged.displacement = {std::sin(current.yaw) * distance, 0,
                               std::cos(current.yaw) * distance};
        staged.next.position.x += staged.displacement.x;
        staged.next.position.z += staged.displacement.z;
    }
    if (!valid_position(staged.next.position))
        return Error::out_of_bounds;
    auto &yaw = staged.next.yaw;
    yaw += turn;
    if (yaw >= pi)
        yaw -= 2 * pi;
    else if (yaw < -pi)
        yaw += 2 * pi;
    ++staged.next.ordinal;
    staged.model = model(staged.next.position, yaw);
    out = staged;
    return Error::ok;
}
} // namespace sh3::domain
