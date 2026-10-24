#include "sh3/application/rig_probe.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::application {
RigProbe::RigProbe(ports::IRigScene &renderer, const domain::InspectionRig &clip) noexcept
    : renderer_(renderer), rig_(clip), view_(*this, {0.35F, 0.35F, 3.0F}, 0.45F),
      valid_(domain::valid_rig(clip)) {}
void RigProbe::dispatch(domain::LifecycleEvent event) noexcept {
    const auto previous = view_.state();
    view_.dispatch(event);
    if (previous == domain::SessionState::suspended &&
        view_.state() == domain::SessionState::running)
        resumed_ = true;
}
void RigProbe::step(CameraInput input, PlaybackInput playback, float seconds,
                    bool toggle_face) noexcept {
    input.any_held =
        input.any_held || playback.pause || playback.advance || playback.restart || toggle_face;
    const bool eligible = view_.state() == domain::SessionState::running && !input.quit &&
                          !view_.awaiting_release() && !resumed_;
    if (eligible && valid_) {
        if (input.reset)
            face_ = false;
        else if (toggle_face) {
            face_ = !face_;
            const domain::OrbitCamera preset =
                face_ ? domain::OrbitCamera{0.0F, 0.1F, 0.65F, {0.0F, 1.32F, -1.98F}}
                      : domain::OrbitCamera{0.35F, 0.35F, 3.0F};
            (void)view_.set_camera(preset);
            // A preset wins over simultaneous held camera directions this frame.
            input.orbit = input.elevate = input.zoom = 0;
        }
        if (playback.pause) {
            paused_ = !paused_;
            remainder_ = 0;
        }
        if (playback.restart) {
            counter_ = 0;
            remainder_ = 0;
        } else if (paused_ && playback.advance)
            counter_ = (counter_ + rig_.increment) % (rig_.sample_count * 4096);
        else if (!paused_ && !playback.pause && std::isfinite(seconds) && seconds > 0) {
            remainder_ += std::min(double(seconds), 0.1) * 25;
            const auto ticks = static_cast<unsigned>(remainder_ + 1e-7);
            remainder_ = std::max(0.0, remainder_ - ticks);
            counter_ = (counter_ + ticks * rig_.increment) % (rig_.sample_count * 4096);
        }
    }
    view_.step(input, resumed_ ? 0 : seconds);
    if (view_.state() == domain::SessionState::running)
        resumed_ = false;
}
ports::RenderResult RigProbe::present(const domain::OrbitCamera &camera) noexcept {
    if (!valid_)
        return ports::RenderResult::unavailable;
    domain::evaluate_rig(rig_, counter_, pose_);
    return renderer_.present_pose(camera, pose_);
}
} // namespace sh3::application
