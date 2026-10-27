#pragma once
#include "sh3/application/render_probe.hpp"
#include "sh3/domain/locomotion_update.hpp"
#include "sh3/ports/rig_scene.hpp"

namespace sh3::application {
// Edge-triggered controls. CameraInput::any_held carries all held hardware buttons.
struct LocomotionInput {
    bool pause{}, advance{}, restart{}, previous_clip{}, next_clip{};
};
enum class LocomotionNotice {
    ready,
    queued,
    paused,
    selection_conflict,
    selection_pending,
    core_error
};

// One owning thread, immutable reader lifetime >= probe lifetime. No allocation per update.
// Rendering consumes only a completely published snapshot; it cannot advance animation.
class LocomotionProbe final : private ports::IRenderScene {
  public:
    LocomotionProbe(ports::IRigScene &, const domain::LocomotionProfile &,
                    const domain::LocomotionSkeleton &,
                    const domain::LocomotionSampleReader &) noexcept;
    void dispatch(domain::LifecycleEvent) noexcept;
    void step(CameraInput, LocomotionInput, float seconds, bool toggle_face = false) noexcept;
    const RenderProbe &view() const noexcept { return view_; }
    const domain::LocomotionState &snapshot() const noexcept { return state_; }
    std::optional<std::uint32_t> pending_clip() const noexcept { return pending_; }
    LocomotionNotice notice() const noexcept { return notice_; }
    domain::LocomotionError error() const noexcept { return error_; }
    const char *notice_text() const noexcept;
    bool ready() const noexcept { return valid_; }
    bool paused() const noexcept { return paused_; }
    bool face_view() const noexcept { return face_; }

  private:
    ports::RenderResult present(const domain::OrbitCamera &) noexcept override;
    void toggle_pause() noexcept;
    void clear_pending() noexcept;
    void set_error(domain::LocomotionError) noexcept;
    bool update() noexcept;
    void playback(LocomotionInput, float seconds) noexcept;
    ports::IRigScene &renderer_;
    const domain::LocomotionProfile profile_;
    const domain::LocomotionSampleReader &reader_;
    RenderProbe view_;
    domain::LocomotionState state_{};
    domain::LocomotionWorkspace workspace_{};
    std::optional<std::uint32_t> pending_{};
    double remainder_{};
    LocomotionNotice notice_{LocomotionNotice::ready};
    domain::LocomotionError error_{domain::LocomotionError::ok};
    bool valid_{}, paused_{}, face_{};
};
static_assert(sizeof(LocomotionProbe) <= domain::locomotion_memory_budget);
} // namespace sh3::application
