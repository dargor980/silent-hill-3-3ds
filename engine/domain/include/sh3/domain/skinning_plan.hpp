#pragma once
#include "sh3/domain/room_scene.hpp"

namespace sh3::domain {
inline constexpr std::size_t skinning_capacity = 30;
struct SkinVertex {
    std::array<float, 4> position{}, weights{}, rows{}, uv{};
};
static_assert(sizeof(SkinVertex) == 64 && alignof(SkinVertex) == 4);
static_assert(offsetof(SkinVertex, weights) == 16 && offsetof(SkinVertex, rows) == 32 &&
              offsetof(SkinVertex, uv) == 48);
struct SkinBatch {
    std::uint32_t first{}, count{}, material{}, matrix_count{};
    std::array<std::uint16_t, skinning_capacity> slots{};
};
struct SkinCounts {
    std::size_t vertices{}, indices{}, batches{};
    std::size_t bytes() const noexcept;
};
// Allocate outside the frame. No per-call heap or large automatic remapping array.
struct SkinPlanWorkspace {
    std::array<std::uint16_t, rig_vertices> remap{};
    std::array<bool, rig_bones + rig_helpers> used{}, next{};
    SkinBatch batch{};
};
struct SkinStorage {
    SkinVertex *vertices{};
    std::uint16_t *indices{};
    SkinBatch *batches{};
    SkinCounts capacity{};
};
// Immutable validated input, distinct caller-owned storage/workspace. Count and
// fill use the same deterministic traversal. Failure preserves storage and out.
[[nodiscard]] bool skin_plan(const InspectionRig &, SkinPlanWorkspace &, SkinCounts &out,
                             const SkinStorage * = nullptr,
                             std::size_t matrix_capacity = skinning_capacity) noexcept;
// Exposed for the frozen HSN byte vectors. Does not widen SRI validation.
[[nodiscard]] bool skin_vertex(const CharacterVertex &, const std::uint16_t *slots,
                               std::size_t count, SkinVertex &) noexcept;
using SkinMatrixRows = std::array<std::array<float, 4>, 3>;
using SkinRows = std::array<SkinMatrixRows, rig_bones + rig_helpers>;
// Input palette/instance has passed PreparedRoomScene::frame. Builds every row
// before publishing, preserving prior rows on failure; scratch must be distinct.
[[nodiscard]] bool skin_rows(const RigPalette &, const PoseMatrix &, SkinRows &scratch,
                             SkinRows &out) noexcept;
} // namespace sh3::domain
