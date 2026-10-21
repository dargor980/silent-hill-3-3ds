#pragma once
#include <cstddef>
#include "sh3/domain/render_scene.hpp"

namespace sh3::ports {
enum class RenderResult { presented, busy, invalid_camera, unavailable };
class IRenderScene {
  public:
    virtual ~IRenderScene() = default;
    // One immutable scene, one camera. No retained reference to the argument.
    [[nodiscard]] virtual RenderResult present(const domain::OrbitCamera &camera) noexcept = 0;
};
class IDynamicScene {
  public:
    virtual ~IDynamicScene() = default;
    // The mesh is borrowed only for this call; implementations synchronize GPU ownership.
    virtual RenderResult present_mesh(const domain::OrbitCamera &, const domain::SceneVertex *,
                                      std::size_t count) noexcept = 0;
};
} // namespace sh3::ports
