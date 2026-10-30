#include "sh3/application/movement_controller.hpp"

namespace sh3::application {
namespace {
using Session = domain::SessionState;
using Event = domain::LifecycleEvent;
using Motion = domain::InspectionMotion;
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
domain::InspectionMovementIntent intent(MovementInput i) noexcept {
    const auto motion =
        i.forward && !i.backward ? (i.run ? Motion::run : Motion::walk) : Motion::idle;
    const auto turn = i.left == i.right ? Turn::none : i.left ? Turn::left : Turn::right;
    return {motion, turn};
}
Motion active_motion(const domain::LocomotionClock &clock) noexcept {
    return clock.target_id == 109   ? Motion::walk
           : clock.target_id == 113 ? Motion::run
                                    : Motion::idle;
}
} // namespace

MovementController::MovementController(const domain::LocomotionProfile &profile,
                                       const domain::LocomotionSkeleton &rig,
                                       const domain::LocomotionSampleReader &reader,
                                       const ports::IMovementContacts &contacts, domain::Vec3 spawn,
                                       float yaw) noexcept
    : actor_(profile, rig, reader, contacts), spawn_(spawn), yaw_(yaw) {
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
bool MovementController::update(domain::InspectionMovementIntent desired) noexcept {
    const auto &clock = snapshot().animation.clock;
    const auto current = active_motion(clock);
    auto applied = desired;
    if (clock.mode != domain::LocomotionMode::stable)
        applied.motion = current;
    else if (current == Motion::idle && desired.motion == Motion::run)
        applied.motion = Motion::walk; // Explicit native bridge; HL still rejects idle -> run.
    result_ = actor_.step(applied, 2);
    if (result_.error != InspectionActorError::ok) {
        fail();
        return false;
    }
    pending_ = desired.motion == active_motion(snapshot().animation.clock)
                   ? std::nullopt
                   : std::optional<Motion>{desired.motion};
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
        return state() == Session::paused && update(intent(input)) ? 1 : 0;
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
    const auto desired = intent(input);
    pending_ = desired.motion == active_motion(snapshot().animation.clock)
                   ? std::nullopt
                   : std::optional<Motion>{desired.motion};
    const auto total = remainder_us_ + elapsed_us;
    const auto count = static_cast<unsigned>(total / movement_step_us);
    remainder_us_ = static_cast<std::uint32_t>(total % movement_step_us);
    unsigned committed = 0;
    while (committed < count && update(desired))
        ++committed;
    return committed;
}
} // namespace sh3::application
