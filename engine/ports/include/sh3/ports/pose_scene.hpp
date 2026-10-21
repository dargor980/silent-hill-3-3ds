#pragma once
#include "sh3/domain/animation_pose.hpp"
#include "sh3/ports/render_scene.hpp"

namespace sh3::ports {
class IPoseScene {
  public:
    virtual ~IPoseScene() = default;
    virtual RenderResult present_pose(const domain::OrbitCamera &,
                                      const domain::SkeletonPose &) noexcept = 0;
};
} // namespace sh3::ports
