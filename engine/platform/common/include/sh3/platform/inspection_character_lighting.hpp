#pragma once
#include "sh3/domain/character_lighting.hpp"
#include "sh3/platform/stdio_files.hpp"
namespace sh3::platform {
[[nodiscard]] ports::FileError read_character_lighting(const char *, domain::CharacterLighting &,
                                                       const domain::CharacterModel &,
                                                       std::uint32_t scm_crc, std::uint32_t san_crc,
                                                       std::uint32_t sct_crc,
                                                       StdioApi = system_stdio) noexcept;
} // namespace sh3::platform
