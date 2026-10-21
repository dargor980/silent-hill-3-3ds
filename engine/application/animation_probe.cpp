#include "sh3/application/animation_probe.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::application {
AnimationProbe::AnimationProbe(ports::IPoseScene &renderer,
                               const domain::InspectionClip &clip) noexcept
    : renderer_(renderer), clip_(clip), view_(*this, {0.35F, 0.35F, 4.0F}),
      valid_(domain::valid_clip(clip)) {}
void AnimationProbe::dispatch(domain::LifecycleEvent event) noexcept {
    const auto previous = view_.state();
    view_.dispatch(event);
    if (previous == domain::SessionState::suspended &&
        view_.state() == domain::SessionState::running)
        resumed_ = true;
}
void AnimationProbe::step(CameraInput input, PlaybackInput playback, float seconds) noexcept {
    input.any_held = input.any_held || playback.pause || playback.advance || playback.restart;
    const bool eligible = view_.state() == domain::SessionState::running && !input.quit &&
                          !view_.awaiting_release() && !resumed_;
    if (eligible) {
        if (playback.pause) {
            paused_ = !paused_;
            remainder_ = 0;
        }
        if (playback.restart) {
            counter_ = 0;
            remainder_ = 0;
        } else if (paused_ && playback.advance)
            counter_ = (counter_ + domain::clip_increment) % domain::clip_period;
        else if (!paused_ && !playback.pause && std::isfinite(seconds) && seconds > 0) {
            remainder_ += std::min(double(seconds), 0.1) * 25;
            const auto ticks = static_cast<unsigned>(remainder_ + 1e-7);
            remainder_ = std::max(0.0, remainder_ - ticks);
            counter_ = (counter_ + ticks * domain::clip_increment) % domain::clip_period;
        }
    }
    view_.step(input, resumed_ ? 0 : seconds);
    if (view_.state() == domain::SessionState::running)
        resumed_ = false;
}
ports::RenderResult AnimationProbe::present(const domain::OrbitCamera &camera) noexcept {
    if (!valid_)
        return ports::RenderResult::unavailable;
    return renderer_.present_pose(camera, domain::evaluate_pose(clip_, counter_));
}
} // namespace sh3::application
