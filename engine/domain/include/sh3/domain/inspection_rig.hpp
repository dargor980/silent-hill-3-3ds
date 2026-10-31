#pragma once
#include "sh3/domain/character_skinning.hpp"

namespace sh3::domain {
inline constexpr std::size_t sri1_samples = 64;
inline constexpr std::size_t rig_bones = 73, rig_samples = 80, rig_helpers = 128,
                             rig_vertices = 8192, rig_indices = 18000, rig_materials = 16;
struct RigSample {
    Vec3 translation{};
    Quaternion rotation{};
};
struct RigMaterial {
    std::uint32_t first{}, count{}, texture{}, width{}, height{}, blend{}, crc{};
};
struct InspectionRig {
    std::uint32_t bone_count{}, sample_count{}, helper_count{}, vertex_count{}, index_count{},
        material_count{}, clip_id{}, increment{};
    Vec3 center{};
    float scale{1};
    std::array<int, rig_bones> parents{};
    std::array<std::array<RigSample, rig_bones>, rig_samples> samples{};
    std::array<std::uint32_t, rig_helpers> targets{};
    std::array<PoseMatrix, rig_helpers> helpers{};
    std::array<CharacterVertex, rig_vertices> vertices{};
    std::array<std::uint16_t, rig_indices> indices{};
    std::array<RigMaterial, rig_materials> materials{};
};
using RigPose = std::array<PoseMatrix, rig_bones>;
using RigPalette = std::array<PoseMatrix, rig_bones + rig_helpers>;
struct RigTriangle {
    float depth;
    std::uint32_t ordinal;
};
using RigSortOrder = std::array<RigTriangle, rig_indices / 3>;
struct RigVertexScratch {
    std::array<float, 4> position{}; // Original model space, including deficient Q12 W.
    CharacterDrawVertex draw{};     // Inspection space, prepared once per unique vertex.
};
[[nodiscard]] bool valid_rig(const InspectionRig &) noexcept;
// Shared geometry/sample validation, excluding SRI1's single-clip timing.
// nullptr means valid; otherwise a static field name, with no allocation.
[[nodiscard]] const char *rig_payload_error(const InspectionRig &) noexcept;
// Validate immutable input once. Storage and scratch space belong to the caller.
void evaluate_rig(const InspectionRig &, std::uint32_t counter, RigPose &) noexcept;
void rig_palette(const InspectionRig &, const RigPose &, RigPalette &) noexcept;
[[nodiscard]] bool rig_draw(const InspectionRig &, const RigPose &, const OrbitCamera &,
                            RigPalette &, RigSortOrder &, RigVertexScratch *, std::size_t,
                            CharacterDrawVertex *, std::size_t) noexcept;
[[nodiscard]] bool valid_rig_draw(const CharacterDrawVertex *, std::size_t) noexcept;
} // namespace sh3::domain
