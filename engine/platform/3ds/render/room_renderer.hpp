#pragma once
#include "sh3/platform/room_runtime.hpp"
#include "sh3/ports/room_view.hpp"
#include <citro3d.h>

namespace sh3::platform::ctr {
class SkinningGpu;
enum class SkinningMode { cpu, hybrid };
class RoomRenderer final : public ports::IRoomView {
  public:
    RoomRenderer(const domain::RoomMap &, const domain::InspectionRig &, ports::IRigTextures &,
                 SkinningMode = SkinningMode::cpu, std::size_t diagnostic_bytes = 0) noexcept;
    ~RoomRenderer();
    RoomRenderer(const RoomRenderer &) = delete;
    RoomRenderer &operator=(const RoomRenderer &) = delete;
    bool ready() const noexcept { return ready_; }
    const char *stage() const noexcept { return stage_; }
    std::size_t accounted_bytes() const noexcept { return bytes_; }
    double prepare_ms() const noexcept { return prepare_ms_; }
    double submit_ms() const noexcept { return submit_ms_; }
    SkinningMode skinning_mode() const noexcept {
        return gpu_ ? SkinningMode::hybrid : SkinningMode::cpu;
    }
    const char *skinning_status() const noexcept { return skinning_status_; }
    void trace(domain::WorkTrace *value) noexcept { trace_ = value; }
    ports::RenderResult present(const domain::RigPose &,
                                const domain::PoseMatrix &) noexcept override;

  private:
    domain::PreparedRoomScene scene_;
    std::unique_ptr<SkinningGpu> gpu_;
    const char *skinning_status_{"CPU_SELECTED"};
    domain::WorkTrace *trace_{};
    std::uint64_t pending_frame_{};
    bool pending_sample_{};
    double prepare_ms_{}, submit_ms_{};
    std::unique_ptr<domain::RoomFrame> frame_;
    std::unique_ptr<domain::RoomWorkspace> workspace_;
    bool citro_{}, program_ready_{}, ready_{};
    const char *stage_{"ROOM_BUDGET"};
    C3D_RenderTarget *target_{};
    DVLB_s *shader_{};
    shaderProgram_s program_{};
    void *static_vertices_{}, *dynamic_vertices_{};
    C3D_BufInfo static_buffer_{}, dynamic_buffer_{};
    C3D_AttrInfo cpu_attributes_{};
    C3D_Mtx projection_{};
    int uniform_{-1};
    std::array<C3D_Tex, domain::rig_materials + 1 + domain::room_materials> textures_{};
    std::size_t texture_count_{}, bytes_{};
};
} // namespace sh3::platform::ctr
