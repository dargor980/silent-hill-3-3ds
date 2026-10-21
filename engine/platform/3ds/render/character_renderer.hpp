#pragma once
#include "sh3/domain/character_skinning.hpp"
#include "sh3/ports/render_scene.hpp"
#include <3ds.h>
#include <citro3d.h>

namespace sh3::platform::ctr {
class CharacterRenderer final {
  public:
    explicit CharacterRenderer(std::size_t count) noexcept;
    ~CharacterRenderer();
    CharacterRenderer(const CharacterRenderer &) = delete;
    CharacterRenderer &operator=(const CharacterRenderer &) = delete;
    bool ready() const noexcept { return ready_; }
    const char *stage() const noexcept { return stage_; }
    ports::RenderResult present(const domain::OrbitCamera &, const domain::CharacterDrawVertex *,
                                std::size_t) noexcept;

  private:
    bool citro_{false}, program_ready_{false}, ready_{false};
    const char *stage_{"COUNT"};
    C3D_RenderTarget *target_{nullptr};
    DVLB_s *shader_{nullptr};
    shaderProgram_s program_{};
    void *vertices_{nullptr};
    int uniform_{-1};
    std::size_t count_{};
    C3D_Mtx projection_{};
};
} // namespace sh3::platform::ctr
