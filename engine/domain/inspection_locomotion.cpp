#include "sh3/domain/inspection_locomotion.hpp"

namespace sh3::domain {
const char *locomotion_rig_error(const InspectionLocomotion &m) noexcept {
    if (!valid_locomotion_profile(m.profile) || m.inspection_hz != 25 ||
        m.shared.clip_id || m.shared.increment)
        return "profile";
    if (m.shared.bone_count != 36 || m.shared.sample_count != m.profile.sample_count)
        return "counts";
    constexpr std::array<std::uint16_t, 36> source{0,  1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11,
                                                   12, 13, 14, 15, 16, 17, 21, 24, 25, 26, 27, 30,
                                                   31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42};
    constexpr std::array<std::uint8_t, 36> channels{1, 2, 1, 2, 1, 2, 1, 2, 2, 1, 2, 1,
                                                    2, 2, 2, 1, 2, 2, 2, 1, 1, 1, 2, 1,
                                                    1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1};
    for (std::size_t i = 0; i < source.size(); ++i)
        if (m.source_bones[i] != source[i] || m.channels[i] != channels[i])
            return "bindings";
    return rig_payload_error(m.shared);
}
LocomotionSkeleton locomotion_rig_skeleton(const InspectionLocomotion &m) noexcept {
    return {m.shared.bone_count, m.shared.parents, m.channels};
}
bool InspectionLocomotionReader::read(std::uint32_t clip, std::uint32_t frame, std::uint32_t bone,
                                      LocomotionTransform &out) const noexcept {
    const auto &m = model_.shared;
    if (bone >= m.bone_count || bone >= rig_bones || m.sample_count > rig_samples)
        return false;
    for (const auto &c : model_.profile.active_clips()) {
        if (c.id != clip)
            continue;
        if (frame >= c.count || c.packed_first >= m.sample_count ||
            frame >= m.sample_count - c.packed_first)
            return false;
        const auto &s = m.samples[c.packed_first + frame][bone];
        out = {s.translation, s.rotation};
        return true;
    }
    return false;
}
} // namespace sh3::domain
