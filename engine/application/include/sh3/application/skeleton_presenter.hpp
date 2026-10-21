#pragma once
#include "sh3/ports/pose_scene.hpp"

namespace sh3::application {
class SkeletonPresenter final : public ports::IPoseScene {
  public:
    SkeletonPresenter(ports::IDynamicScene &renderer, const domain::InspectionClip &clip) noexcept
        : renderer_(renderer), clip_(clip) {}
    ports::RenderResult present_pose(const domain::OrbitCamera &camera,
                                     const domain::SkeletonPose &pose) noexcept override {
        const auto mesh = domain::skeleton_mesh(clip_, pose);
        return renderer_.present_mesh(camera, mesh.data(), mesh.size());
    }

  private:
    ports::IDynamicScene &renderer_;
    const domain::InspectionClip &clip_;
};
} // namespace sh3::application
