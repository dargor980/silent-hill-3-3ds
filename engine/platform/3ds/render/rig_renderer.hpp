#pragma once
#include "sh3/platform/inspection_rig.hpp"
#include "sh3/ports/rig_scene.hpp"
#include <3ds.h>
#include <citro3d.h>

namespace sh3::platform::ctr {
class RigRenderer final {
  public:
    RigRenderer(const domain::InspectionRig &, ports::IRigTextures &) noexcept;
    ~RigRenderer();
    RigRenderer(const RigRenderer &) = delete;
    RigRenderer &operator=(const RigRenderer &) = delete;
    bool ready() const noexcept { return ready_; }
    const char *stage() const noexcept { return stage_; }
    ports::RenderResult present(const domain::OrbitCamera &, const domain::CharacterDrawVertex *,
                                std::size_t) noexcept;

  private:
    const domain::InspectionRig &model_;
    bool citro_{false}, program_ready_{false}, ready_{false};
    const char *stage_{"MODEL"};
    C3D_RenderTarget *target_{nullptr};
    DVLB_s *shader_{nullptr};
    shaderProgram_s program_{};
    void *vertices_{nullptr};
    int uniform_{-1};
    std::size_t count_{};
    C3D_Mtx projection_{};
    std::array<C3D_Tex, domain::rig_materials> textures_{};
    std::size_t texture_count_{};
};
} // namespace sh3::platform::ctr
