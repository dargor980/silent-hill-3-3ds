#pragma once
#include "sh3/application/animation_probe.hpp"
#include "sh3/ports/rig_scene.hpp"

namespace sh3::application {
class RigProbe final : private ports::IRenderScene {
  public:
    RigProbe(ports::IRigScene &, const domain::InspectionRig &) noexcept;
    void dispatch(domain::LifecycleEvent) noexcept;
    void step(CameraInput, PlaybackInput, float seconds, bool toggle_face = false) noexcept;
    const RenderProbe &view() const noexcept { return view_; }
    std::uint32_t counter() const noexcept { return counter_; }
    bool paused() const noexcept { return paused_; }
    bool face_view() const noexcept { return face_; }

  private:
    ports::RenderResult present(const domain::OrbitCamera &) noexcept override;
    ports::IRigScene &renderer_;
    const domain::InspectionRig &rig_;
    RenderProbe view_;
    domain::RigPose pose_{};
    std::uint32_t counter_{};
    double remainder_{};
    bool paused_{false}, resumed_{false}, valid_{false}, face_{false};
};
} // namespace sh3::application
