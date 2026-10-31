#include "sh3/application/movement_controller.hpp"

namespace sh3::application {
namespace {
using Session = domain::SessionState;
using Event = domain::LifecycleEvent;
using Action = InspectionAction;
using Turn = domain::InspectionTurn;
class CallScope final {
  public:
    explicit CallScope(bool &busy) noexcept : busy_(busy) { busy_ = true; }
    ~CallScope() { busy_ = false; }

  private:
    bool &busy_;
};
bool held(MovementInput i) noexcept {
    return i.any_held || i.forward || i.backward || i.left || i.right || i.run || i.pause ||
           i.advance || i.restart || i.quit;
}
InspectionActionIntent intent(MovementInput i, bool turns) noexcept {
    const auto turn = i.left == i.right ? Turn::none : i.left ? Turn::left : Turn::right;
    const auto action = i.forward && !i.backward       ? (i.run ? Action::run : Action::walk)
                        : !turns || turn == Turn::none ? Action::idle
                        : turn == Turn::right          ? Action::turn_right
                                                       : Action::turn_left;
    return {action, turn};
}
Action active_action(const domain::LocomotionClock &clock) noexcept {
    switch (clock.target_id) {
    case 109:
        return Action::walk;
    case 113:
        return Action::run;
    case 107:
        return Action::turn_right;
    case 108:
        return Action::turn_left;
    default:
        return Action::idle;
    }
}
Action next_action(Action current, Action desired) noexcept {
    if (current == desired)
        return current;
    if (current == Action::idle)
        return desired == Action::run ? Action::walk : desired;
    if ((current == Action::walk && desired == Action::run) ||
        (current == Action::run && desired == Action::walk))
        return desired;
    return Action::idle; // All remaining paths go through idle, one arc at a time.
}
} // namespace

MovementController::MovementController(const domain::LocomotionProfile &profile,
                                       const domain::LocomotionSkeleton &rig,
                                       const domain::LocomotionSampleReader &reader,
                                       const ports::IMovementContacts &contacts, domain::Vec3 spawn,
                                       float yaw) noexcept
    : actor_(profile, rig, reader, contacts), spawn_(spawn), yaw_(yaw), turns_(profile.id == 2) {
    result_ = actor_.reset(spawn_, yaw_);
    if (result_.error != InspectionActorError::ok)
        fail();
}
void MovementController::clear_timing() noexcept {
    remainder_us_ = 0;
    pending_.reset();
}
void MovementController::fail() noexcept {
    clear_timing();
    if (state() == Session::running)
        lifecycle_.apply(Event::toggle_pause);
    awaiting_release_ = true;
}
void MovementController::pause_on_fault() noexcept {
    if (busy_ || state() == Session::stopped)
        return;
    const CallScope scope(busy_);
    fail();
}
void MovementController::apply_event(Event event) noexcept {
    const auto before = state();
    lifecycle_.apply(event);
    if (state() != before) {
        clear_timing();
        awaiting_release_ = true;
    }
}
void MovementController::dispatch(Event event) noexcept {
    if (busy_)
        return;
    const CallScope scope(busy_);
    apply_event(event);
}
bool MovementController::update(InspectionActionIntent desired) noexcept {
    const auto &clock = snapshot().animation.clock;
    const auto current = active_action(clock);
    auto applied = desired;
    if (clock.mode != domain::LocomotionMode::stable)
        applied.action = current;
    else
        applied.action = next_action(current, desired.action);
    result_ = actor_.step_action(applied, 2);
    if (result_.error != InspectionActorError::ok) {
        fail();
        return false;
    }
    pending_ = desired.action == active_action(snapshot().animation.clock)
                   ? std::nullopt
                   : std::optional<Action>{desired.action};
    return true;
}
unsigned MovementController::step(MovementInput input, std::uint64_t elapsed_us) noexcept {
    if (busy_)
        return 0;
    const CallScope scope(busy_);
    if (input.quit) {
        apply_event(Event::quit);
        return 0;
    }
    if (state() == Session::stopped || state() == Session::suspended)
        return 0;
    if (awaiting_release_) {
        clear_timing();
        awaiting_release_ = held(input);
        return 0; // The neutral release sample also discards its elapsed time.
    }
    if (input.pause) {
        apply_event(Event::toggle_pause);
        return 0;
    }
    if (input.restart) {
        clear_timing();
        awaiting_release_ = true;
        result_ = actor_.reset(spawn_, yaw_);
        if (result_.error != InspectionActorError::ok)
            fail();
        return 0;
    }
    if (input.advance) {
        clear_timing();
        return state() == Session::paused && update(intent(input, turns_)) ? 1 : 0;
    }
    if (state() == Session::paused) {
        clear_timing();
        return 0;
    }
    if (elapsed_us > movement_discontinuity_us) {
        clear_timing();
        return 0;
    }
    if (elapsed_us > movement_max_interval_us) {
        // A slow renderer must not starve simulation indefinitely. Bound catch-up
        // to three fixed updates and discard excess debt; lifecycle gaps still reset.
        clear_timing();
        elapsed_us = movement_max_interval_us;
    }
    const auto desired = intent(input, turns_);
    pending_ = desired.action == active_action(snapshot().animation.clock)
                   ? std::nullopt
                   : std::optional<Action>{desired.action};
    const auto total = remainder_us_ + elapsed_us;
    const auto count = static_cast<unsigned>(total / movement_step_us);
    remainder_us_ = static_cast<std::uint32_t>(total % movement_step_us);
    unsigned committed = 0;
    while (committed < count && update(desired))
        ++committed;
    return committed;
}
} // namespace sh3::application
