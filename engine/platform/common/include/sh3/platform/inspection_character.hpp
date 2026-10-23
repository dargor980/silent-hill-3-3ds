#pragma once
#include "sh3/domain/character_skinning.hpp"
#include "sh3/platform/stdio_files.hpp"
namespace sh3::platform {
// Only publishes a complete validated model; temporary allocation is limited to load time.
[[nodiscard]] ports::FileError read_inspection_character(const char *, domain::CharacterModel &,
                                                         StdioApi = system_stdio,
                                                         std::uint32_t *payload_crc = nullptr) noexcept;
} // namespace sh3::platform
