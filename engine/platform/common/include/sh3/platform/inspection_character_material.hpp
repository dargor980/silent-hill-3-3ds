#pragma once
#include "sh3/domain/character_skinning.hpp"
#include "sh3/platform/stdio_files.hpp"

namespace sh3::platform {
inline constexpr std::size_t character_texture_width = 512;
inline constexpr std::size_t character_texture_bytes = 512 * 512 * 4;
struct CharacterMaterialData {
    domain::CharacterMaterials ranges{};
    std::array<std::uint8_t, 3 * character_texture_bytes> pixels{};
};
// Caller owns bounded heap storage. On failure pixels must not be consumed.
[[nodiscard]] ports::FileError
read_character_material(const char *, CharacterMaterialData &, std::uint32_t scm_payload_crc,
                        std::size_t indices, StdioApi = system_stdio,
                        std::uint32_t *payload_crc = nullptr) noexcept;
// Original PS2 RGBA -> normalized ABGR/Morton, no row flip; buffers must be disjoint.
[[nodiscard]] bool upload_character_texture(const std::uint8_t *, std::size_t, std::uint8_t *,
                                            std::size_t) noexcept;
} // namespace sh3::platform
