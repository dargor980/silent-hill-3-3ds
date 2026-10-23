#pragma once
#include "sh3/domain/character_skinning.hpp"

namespace sh3::domain {
using LightVector = std::array<float, 3>;
using LightColor = std::array<float, 4>;
struct CharacterDirectionalLight {
    LightVector direction{};
    LightColor color{};
};
struct CharacterSpotlight {
    LightVector position{}, direction{};
    LightColor color{}, attenuation{};
};
struct CharacterLightRange {
    std::uint32_t first_vertex{}, vertex_count{}, first_index{}, index_count{};
    LightVector diffuse{}, ambient{};
};
struct CharacterLighting {
    std::uint32_t reference_counter{};
    PoseMatrix model_to_capture{};
    LightColor ambient{};
    std::array<CharacterDirectionalLight, 3> directionals{};
    CharacterSpotlight spot{};
    std::array<CharacterLightRange, 15> ranges{};
};
[[nodiscard]] bool valid_character_lighting(const CharacterLighting &,
                                            const CharacterModel &) noexcept;
// Pure mode-2/type-0x10 equation. No camera, GPU, allocation, or normal normalization.
// Input is post-skinning model space; output is unclamped PS2 RGBA units.
[[nodiscard]] bool shade_character_vertex(const CharacterLighting &, const CharacterLightRange &,
                                          const DeformedVertex &, LightColor &) noexcept;
// Model/profile were validated at load. All buffers are caller-owned and disjoint.
// Failure invalidates this frame; the caller must not submit partially written colors.
[[nodiscard]] bool light_character(const CharacterLighting &, const CharacterModel &,
                                   const DeformedVertex *, std::size_t, LightVector *, std::size_t,
                                   CharacterDrawVertex *, std::size_t) noexcept;
} // namespace sh3::domain
