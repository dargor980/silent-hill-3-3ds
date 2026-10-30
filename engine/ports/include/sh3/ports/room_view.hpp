#pragma once
#include "sh3/domain/inspection_rig.hpp"
#include "sh3/ports/render_scene.hpp"

namespace sh3::ports {
class IRoomView {
  public:
    virtual ~IRoomView() = default;
    // Borrow the last complete pose/instance. Never mutate simulation or retain these references.
    virtual RenderResult present(const domain::RigPose &, const domain::PoseMatrix &) noexcept = 0;
};
} // namespace sh3::ports
