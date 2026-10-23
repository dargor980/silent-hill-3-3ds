#pragma once
#include "sh3/domain/animation_pose.hpp"
#include <cstddef>

namespace sh3::domain {
inline constexpr std::size_t character_vertex_limit = 2048, character_index_limit = 4608;
struct CharacterVertex {
    std::array<std::int16_t, 3> position{}, normal{};
    std::array<std::int16_t, 2> uv{};
    std::array<std::uint16_t, 3> weights{};
    std::uint8_t primary{}, count{1};
    std::array<std::uint8_t, 2> helpers{255, 255};
};
struct CharacterModel {
    Vec3 center{};
    float scale{1};
    std::array<std::uint32_t, 3> targets{};
    std::array<PoseMatrix, 3> helpers{};
    std::array<CharacterVertex, character_vertex_limit> vertices{};
    std::array<std::uint16_t, character_index_limit> indices{};
    std::size_t vertex_count{}, index_count{};
};
struct DeformedVertex {
    std::array<float, 4> position{};
    std::array<float, 3> normal{};
};
struct CharacterDrawVertex {
    std::array<float, 4> position{};
    Vec3 color{};
    std::array<float, 2> uv{};
};
struct CharacterMaterialRange {
    std::uint32_t first{}, count{}, texture{};
};
using CharacterMaterials = std::array<CharacterMaterialRange, 3>;
[[nodiscard]] bool valid_character_materials(const CharacterMaterials &, std::size_t) noexcept;
using CharacterPalette = std::array<PoseMatrix, 6>;
[[nodiscard]] bool valid_character(const CharacterModel &) noexcept;
// Immutable model is validated at load. Output storage is caller-owned, with no allocation.
[[nodiscard]] CharacterPalette character_palette(const CharacterModel &,
                                                 const SkeletonPose &) noexcept;
[[nodiscard]] DeformedVertex deform_character_vertex(const CharacterVertex &,
                                                     const CharacterPalette &) noexcept;
[[nodiscard]] bool character_draw(const CharacterModel &, const SkeletonPose &, DeformedVertex *,
                                  std::size_t, CharacterDrawVertex *, std::size_t,
                                  bool neutral_light = false) noexcept;
[[nodiscard]] bool valid_character_draw(const CharacterDrawVertex *, std::size_t) noexcept;
} // namespace sh3::domain
