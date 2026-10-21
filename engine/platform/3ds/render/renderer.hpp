#pragma once
#include "sh3/platform/inspection_geometry.hpp"
#include "sh3/platform/inspection_texture.hpp"
#include "sh3/ports/render_scene.hpp"
#include <3ds.h>
#include <citro3d.h>

namespace sh3::platform::ctr {
class SceneRenderer final : public ports::IRenderScene, public ports::IDynamicScene {
  public:
    // gfx must outlive this adapter. This executable has one Citro3D owner.
    SceneRenderer() noexcept;
    // Pixels are copied during construction and may be released afterwards.
    explicit SceneRenderer(InspectionPixels pixels) noexcept;
    // Geometry is copied; the diagnostic checker is generated internally.
    explicit SceneRenderer(InspectionMesh mesh) noexcept;
    // Captured glass profile; both inputs are copied, with an own opaque backdrop.
    SceneRenderer(InspectionMesh mesh, InspectionPixels pixels) noexcept;
    ~SceneRenderer() override;
    SceneRenderer(const SceneRenderer &) = delete;
    SceneRenderer &operator=(const SceneRenderer &) = delete;
    [[nodiscard]] bool ready() const noexcept { return ready_; }
    [[nodiscard]] const char *stage() const noexcept { return stage_; }
    [[nodiscard]] ports::RenderResult present(const domain::OrbitCamera &camera) noexcept override;
    [[nodiscard]] ports::RenderResult present_mesh(const domain::OrbitCamera &camera,
        const domain::SceneVertex *vertices, std::size_t count) noexcept override;

  private:
    ports::RenderResult present_frame(const domain::OrbitCamera &, const InspectionMesh *) noexcept;
    void initialize(const InspectionPixels *pixels,
                    const InspectionMesh *geometry = nullptr) noexcept;
    bool citro_ready_{false}, program_ready_{false}, texture_ready_{false}, ready_{false};
    const char *stage_{"CITRO3D"};
    C3D_RenderTarget *target_{nullptr};
    DVLB_s *shader_{nullptr};
    shaderProgram_s program_{};
    C3D_Tex texture_{};
    void *vertices_{nullptr};
    int transform_location_{-1};
    C3D_Mtx projection_{};
    int vertex_count_{60};
    bool material_{false};
    bool mesh_mode_{false};
};
} // namespace sh3::platform::ctr
