#pragma once
#include "sh3/domain/inspection_movement.hpp"

namespace sh3::application {
// Animation intent is independent of the current world turn. During a retained
// blend they may point in opposite directions. Movement is derived, never supplied twice.
enum class InspectionAction { idle, walk, run, turn_right, turn_left };
struct InspectionActionIntent {
    InspectionAction action{InspectionAction::idle};
    domain::InspectionTurn turn{domain::InspectionTurn::none};
};
constexpr domain::InspectionMotion action_motion(InspectionAction action) noexcept {
    switch (action) {
    case InspectionAction::idle:
    case InspectionAction::turn_right:
    case InspectionAction::turn_left:
        return domain::InspectionMotion::idle;
    case InspectionAction::walk:
        return domain::InspectionMotion::walk;
    case InspectionAction::run:
        return domain::InspectionMotion::run;
    }
    return static_cast<domain::InspectionMotion>(-1); // Movement validation rejects it.
}
constexpr std::uint32_t action_clip(InspectionAction action) noexcept {
    switch (action) {
    case InspectionAction::idle:
        return 101;
    case InspectionAction::walk:
        return 109;
    case InspectionAction::run:
        return 113;
    case InspectionAction::turn_right:
        return 107;
    case InspectionAction::turn_left:
        return 108;
    }
    return 0;
}
} // namespace sh3::application
