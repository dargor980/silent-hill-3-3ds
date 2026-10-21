#pragma once
#include "sh3/application/render_probe.hpp"
#include "sh3/domain/animation_pose.hpp"
#include "sh3/ports/pose_scene.hpp"

namespace sh3::application {
struct PlaybackInput {
    bool pause{false}, advance{false}, restart{false};
};
class AnimationProbe final : private ports::IRenderScene {
  public:
    // Validated immutable clip and renderer must outlive the application.
    AnimationProbe(ports::IPoseScene &renderer, const domain::InspectionClip &clip) noexcept;
    void dispatch(domain::LifecycleEvent event) noexcept;
    void step(CameraInput input, PlaybackInput playback, float seconds) noexcept;
    [[nodiscard]] const RenderProbe &view() const noexcept { return view_; }
    [[nodiscard]] std::uint32_t counter() const noexcept { return counter_; }
    [[nodiscard]] bool paused() const noexcept { return paused_; }

  private:
    ports::RenderResult present(const domain::OrbitCamera &) noexcept override;
    ports::IPoseScene &renderer_;
    const domain::InspectionClip &clip_;
    RenderProbe view_;
    std::uint32_t counter_{0};
    double remainder_{0};
    bool paused_{false}, resumed_{false}, valid_{false};
};
} // namespace sh3::application
