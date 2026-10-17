#include "sh3/domain/lifecycle.hpp"

namespace sh3::domain {
SessionState Lifecycle::state() const noexcept { return state_; }

void Lifecycle::apply(LifecycleEvent event) noexcept {
    if (state_ == SessionState::stopped) {
        return;
    }
    if (event == LifecycleEvent::quit) {
        state_ = SessionState::stopped;
        return;
    }
    if (event == LifecycleEvent::suspend && state_ != SessionState::suspended) {
        before_suspend_ = state_;
        state_ = SessionState::suspended;
    } else if (event == LifecycleEvent::resume && state_ == SessionState::suspended) {
        state_ = before_suspend_;
    } else if (event == LifecycleEvent::toggle_pause) {
        if (state_ == SessionState::running) {
            state_ = SessionState::paused;
        } else if (state_ == SessionState::paused) {
            state_ = SessionState::running;
        }
    }
}
} // namespace sh3::domain
