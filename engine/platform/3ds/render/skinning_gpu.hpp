#pragma once
#include "sh3/domain/skinning_plan.hpp"
#include <citro3d.h>
#include <memory>

namespace sh3::platform::ctr {
// Caller owns the C3D context and synchronizes its target before destruction.
class SkinningGpu final {
  public:
    SkinningGpu(const domain::InspectionRig &, std::size_t budget) noexcept;
    ~SkinningGpu();
    SkinningGpu(const SkinningGpu &) = delete;
    SkinningGpu &operator=(const SkinningGpu &) = delete;
    bool ready() const noexcept { return ready_; }
    const char *stage() const noexcept { return stage_; }
    std::size_t bytes() const noexcept { return bytes_; }
    const domain::SkinCounts &counts() const noexcept { return counts_; }
    bool prepare(const domain::RigPalette &, const domain::PoseMatrix &) noexcept;
    void draw(const C3D_Mtx &, C3D_Tex *) noexcept;

  private:
    bool ready_{}, program_ready_{};
    const char *stage_{"HS_WORKSPACE"};
    std::size_t bytes_{};
    domain::SkinCounts counts_{};
    std::unique_ptr<domain::SkinBatch[]> batches_;
    domain::SkinRows scratch_{}, rows_{};
    void *vertices_{}, *indices_{};
    DVLB_s *shader_{};
    shaderProgram_s program_{};
    C3D_AttrInfo attributes_{};
    C3D_BufInfo buffer_{};
};
} // namespace sh3::platform::ctr
