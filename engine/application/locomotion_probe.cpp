#include "sh3/application/locomotion_probe.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::application {
using Error = domain::LocomotionError;
using Event = domain::LifecycleEvent;
using Session = domain::SessionState;
LocomotionProbe::LocomotionProbe(ports::IRigScene &renderer,
                                 const domain::LocomotionProfile &profile,
                                 const domain::LocomotionSkeleton &skeleton,
                                 const domain::LocomotionSampleReader &reader) noexcept
    : renderer_(renderer), profile_(profile), reader_(reader),
      view_(*this, {0.35F, 0.35F, 3.0F}, 0.45F) {
    const auto result =
        domain::initialize_locomotion(profile_, skeleton, reader_, state_, workspace_);
    valid_ = result == Error::ok;
    if (!valid_)
        set_error(result);
}
void LocomotionProbe::clear_pending() noexcept {
    pending_.reset();
    remainder_ = 0;
    if (notice_ == LocomotionNotice::queued)
        notice_ = LocomotionNotice::ready;
}
void LocomotionProbe::toggle_pause() noexcept {
    paused_ = !paused_;
    clear_pending();
    notice_ = LocomotionNotice::ready;
    error_ = Error::ok;
}
void LocomotionProbe::dispatch(Event event) noexcept {
    if (event == Event::toggle_pause) {
        // Playback pause leaves the camera and rendering alive.
        if (valid_ && view_.state() == Session::running && !view_.awaiting_release())
            toggle_pause();
        return;
    }
    if (event == Event::suspend || event == Event::quit)
        clear_pending();
    view_.dispatch(event);
}
void LocomotionProbe::set_error(Error error) noexcept {
    error_ = error;
    notice_ = LocomotionNotice::core_error;
    // Request errors are recoverable on a later no-request tick. Data/state failures pause.
    if (error != Error::unknown_clip && error != Error::transition_busy &&
        error != Error::unsupported_transition)
        paused_ = true;
}
bool LocomotionProbe::update() noexcept {
    const auto request = pending_;
    pending_.reset();
    const auto result =
        domain::update_locomotion(profile_, reader_, request, profile_.ticks, state_, workspace_);
    if (result != Error::ok) {
        clear_pending();
        set_error(result);
        return false;
    }
    if (notice_ == LocomotionNotice::queued)
        notice_ = LocomotionNotice::ready;
    return true;
}
void LocomotionProbe::playback(LocomotionInput input, float seconds) noexcept {
    // Each higher-priority action consumes this call, including its elapsed time.
    if (input.pause) {
        toggle_pause();
    } else if (input.restart) {
        clear_pending();
        const auto result = domain::initialize_locomotion(
            profile_, state_.skeleton, reader_, state_, workspace_, state_.clock.target_id);
        if (result != Error::ok)
            set_error(result);
        else {
            notice_ = LocomotionNotice::ready;
            error_ = Error::ok;
        }
    } else if (input.advance) {
        // R while playing consumes the event but does not change the clock.
        if (paused_) {
            clear_pending();
            notice_ = LocomotionNotice::ready;
            error_ = Error::ok;
            (void)update();
        }
    } else if (input.previous_clip || input.next_clip) {
        error_ = Error::ok;
        if (paused_)
            notice_ = LocomotionNotice::paused;
        else if (input.previous_clip && input.next_clip)
            notice_ = LocomotionNotice::selection_conflict;
        else if (pending_)
            notice_ = LocomotionNotice::selection_pending;
        else {
            std::size_t index = 0;
            while (profile_.clips[index].id != state_.clock.target_id)
                ++index; // Valid published state and fixed authenticated profile.
            index = (index + (input.next_clip ? 1 : profile_.clip_count - 1)) % profile_.clip_count;
            const auto clip = profile_.clips[index].id;
            // Reject invalid edges now, without sampling or publishing a pose.
            const auto result = domain::plan_locomotion_update(profile_, state_.clock, clip,
                                                               profile_.ticks, workspace_.plan);
            if (result != Error::ok)
                set_error(result);
            else {
                pending_ = clip;
                notice_ = LocomotionNotice::queued;
            }
        }
    } else if (!paused_ && std::isfinite(seconds) && seconds > 0) {
        remainder_ += std::min(double(seconds), 0.1) * 25;
        const auto count = static_cast<unsigned>(remainder_ + 1e-7);
        remainder_ = std::max(0.0, remainder_ - count);
        // At most three complete updates, each publishing cache, clock and matrices.
        for (unsigned i = 0; i < count; ++i)
            if (!update())
                break;
    }
}
void LocomotionProbe::step(CameraInput input, LocomotionInput controls, float seconds,
                           bool toggle_face) noexcept {
    if (input.quit) {
        dispatch(Event::quit);
        return;
    }
    input.any_held = input.any_held || controls.pause || controls.advance || controls.restart ||
                     controls.previous_clip || controls.next_clip || toggle_face;
    const bool eligible = view_.state() == Session::running && !view_.awaiting_release();
    if (eligible && valid_) {
        if (input.reset)
            face_ = false;
        else if (toggle_face) {
            face_ = !face_;
            const domain::OrbitCamera preset =
                face_ ? domain::OrbitCamera{0.0F, 0.1F, 0.65F, {0.0F, 1.32F, -1.98F}}
                      : domain::OrbitCamera{0.35F, 0.35F, 3.0F};
            (void)view_.set_camera(preset);
            input.orbit = input.elevate = input.zoom = 0;
        }
        playback(controls, seconds);
    }
    view_.step(input, seconds);
    if (view_.state() == Session::stopped)
        clear_pending();
}
ports::RenderResult LocomotionProbe::present(const domain::OrbitCamera &camera) noexcept {
    return valid_ ? renderer_.present_pose(camera, state_.model) : ports::RenderResult::unavailable;
}
const char *LocomotionProbe::notice_text() const noexcept {
    switch (notice_) {
    case LocomotionNotice::ready:
        return "Animation ready";
    case LocomotionNotice::queued:
        return "Clip queued for next update";
    case LocomotionNotice::paused:
        return "paused: resume before selection";
    case LocomotionNotice::selection_conflict:
        return "Conflicting clip buttons";
    case LocomotionNotice::selection_pending:
        return "A clip is already pending";
    case LocomotionNotice::core_error:
        break;
    }
    switch (error_) {
    case Error::ok:
        return "Animation ready";
    case Error::invalid_profile:
        return "invalid_profile";
    case Error::invalid_state:
        return "invalid_state";
    case Error::invalid_ticks:
        return "invalid_ticks";
    case Error::unknown_clip:
        return "unknown_clip";
    case Error::transition_busy:
        return "transition_busy";
    case Error::unsupported_transition:
        return "unsupported_transition";
    case Error::sample_unavailable:
        return "sample_unavailable";
    case Error::invalid_pose:
        return "invalid_pose";
    }
    return "invalid_state";
}
} // namespace sh3::application
