#pragma once
#include "sh3/domain/character_skinning.hpp"

namespace sh3::domain {
inline constexpr std::size_t character_instance_limit = 3;
struct CharacterInstance {
    std::uint32_t id{};
    PoseMatrix model{};
};
struct CharacterWorld {
    Vec3 origin{};
    float scale{};
    std::uint32_t reference_counter{};
    std::array<CharacterInstance, character_instance_limit> instances{};
};
using WorldPosition = std::array<float, 4>;
[[nodiscard]] bool valid_character_world(const CharacterWorld &, const CharacterModel &) noexcept;
// Validated immutable instance; result is original units relative to the common origin.
[[nodiscard]] WorldPosition rebase_character_position(const CharacterInstance &, Vec3,
                                                      const WorldPosition &) noexcept;
[[nodiscard]] bool place_character(const CharacterWorld &, const CharacterModel &,
                                   const DeformedVertex *, std::size_t, WorldPosition *,
                                   std::size_t, CharacterDrawVertex *, std::size_t) noexcept;
} // namespace sh3::domain
