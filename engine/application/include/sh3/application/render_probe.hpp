#pragma once
#include "sh3/domain/lifecycle.hpp"
#include "sh3/ports/render_scene.hpp"

namespace sh3::application {
struct CameraInput {
    float orbit{0}, elevate{0}, zoom{0};
    bool reset{false}, quit{false}, any_held{false};
};
class RenderProbe final {
  public:
    explicit RenderProbe(ports::IRenderScene &renderer, domain::OrbitCamera initial = {},
                         float minimum_distance = 3.0F) noexcept;
    [[nodiscard]] bool set_camera(const domain::OrbitCamera &) noexcept;
    void dispatch(domain::LifecycleEvent event) noexcept;
    void step(const CameraInput &input, float seconds) noexcept;
    [[nodiscard]] const domain::OrbitCamera &camera() const noexcept { return camera_; }
    [[nodiscard]] domain::SessionState state() const noexcept { return lifecycle_.state(); }
    [[nodiscard]] ports::RenderResult result() const noexcept { return result_; }
    [[nodiscard]] bool awaiting_release() const noexcept { return awaiting_release_; }

  private:
    ports::IRenderScene &renderer_;
    domain::Lifecycle lifecycle_;
    domain::OrbitCamera camera_;
    domain::OrbitCamera initial_camera_;
    float minimum_distance_;
    ports::RenderResult result_{ports::RenderResult::busy};
    bool awaiting_release_{false};
};
} // namespace sh3::application
