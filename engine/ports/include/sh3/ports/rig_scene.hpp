#pragma once
#include "sh3/domain/inspection_rig.hpp"
#include "sh3/ports/render_scene.hpp"

namespace sh3::ports {
class IRigScene {
  public:
    virtual ~IRigScene() = default;
    virtual RenderResult present_pose(const domain::OrbitCamera &,
                                      const domain::RigPose &) noexcept = 0;
};
class IRigTextures {
  public:
    virtual ~IRigTextures() = default;
    virtual bool read(const domain::RigMaterial &, std::uint8_t *, std::size_t) noexcept = 0;
};
} // namespace sh3::ports
