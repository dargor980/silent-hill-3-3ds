#include "sh3/application/render_probe.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::application {
RenderProbe::RenderProbe(ports::IRenderScene &renderer, domain::OrbitCamera initial,
                         float minimum_distance) noexcept
    : renderer_(renderer),
      minimum_distance_(std::isfinite(minimum_distance) && minimum_distance >= 0.45F &&
                                minimum_distance <= 3
                            ? minimum_distance
                            : 3.0F) {
    if (!set_camera(initial))
        camera_ = domain::OrbitCamera{};
    initial_camera_ = camera_;
}
bool RenderProbe::set_camera(const domain::OrbitCamera &camera) noexcept {
    if (!domain::valid_camera(camera) || camera.distance < minimum_distance_)
        return false;
    camera_ = camera;
    return true;
}
void RenderProbe::dispatch(domain::LifecycleEvent event) noexcept {
    const auto before = state();
    lifecycle_.apply(event);
    if (before == domain::SessionState::suspended && state() == domain::SessionState::running) {
        awaiting_release_ = true;
    }
}
void RenderProbe::step(const CameraInput &input, float seconds) noexcept {
    if (state() != domain::SessionState::running) {
        return;
    }
    // START remains available while waiting for button release.
    if (input.quit) {
        dispatch(domain::LifecycleEvent::quit);
        return;
    }
    if (awaiting_release_) {
        awaiting_release_ = input.any_held || input.reset || input.orbit != 0 ||
                            input.elevate != 0 || input.zoom != 0;
    } else if (input.reset) {
        camera_ = initial_camera_;
    } else if (std::isfinite(seconds) && seconds > 0 && std::isfinite(input.orbit) &&
               std::isfinite(input.elevate) && std::isfinite(input.zoom)) {
        const float dt = std::min(seconds, 0.1F);
        camera_.yaw =
            std::clamp(camera_.yaw + std::clamp(input.orbit, -1.0F, 1.0F) * dt, -0.55F, 0.55F);
        camera_.elevation =
            std::clamp(camera_.elevation + std::clamp(input.elevate, -1.0F, 1.0F) * dt, 0.1F, 0.8F);
        const float zoom_speed = std::min(3.0F, camera_.distance);
        camera_.distance =
            std::clamp(camera_.distance + std::clamp(input.zoom, -1.0F, 1.0F) * dt * zoom_speed,
                       minimum_distance_, 9.0F);
    }
    result_ = renderer_.present(camera_);
    if (result_ == ports::RenderResult::unavailable ||
        result_ == ports::RenderResult::invalid_camera) {
        dispatch(domain::LifecycleEvent::quit);
    }
}
} // namespace sh3::application
