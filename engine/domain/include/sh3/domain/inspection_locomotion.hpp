#pragma once
#include "sh3/domain/inspection_rig.hpp"
#include "sh3/domain/locomotion_pose.hpp"

namespace sh3::domain {
// SRI2 owns fixed-capacity storage. Single-clip timing stays zero so valid_rig
// rejects it: evaluate_rig MUST NOT be used on the concatenated sample block.
// Geometry rendering can reuse rig_palette/rig_draw with a locomotion pose.
struct InspectionLocomotion {
    InspectionRig shared{};
    LocomotionProfile profile{};
    std::uint32_t inspection_hz{};
    std::array<std::uint16_t, rig_bones> source_bones{};
    std::array<std::uint8_t, rig_bones> channels{};
};
[[nodiscard]] const char *locomotion_rig_error(const InspectionLocomotion &) noexcept;
[[nodiscard]] LocomotionSkeleton locomotion_rig_skeleton(const InspectionLocomotion &) noexcept;

// The caller retains a validated, immutable model for this view's lifetime.
class InspectionLocomotionReader final : public LocomotionSampleReader {
  public:
    explicit InspectionLocomotionReader(const InspectionLocomotion &model) noexcept
        : model_(model) {}
    [[nodiscard]] bool read(std::uint32_t clip, std::uint32_t relative_frame, std::uint32_t bone,
                            LocomotionTransform &) const noexcept override;

  private:
    const InspectionLocomotion &model_;
};
} // namespace sh3::domain
