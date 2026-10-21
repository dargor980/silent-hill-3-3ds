#pragma once
#include <cstddef>
#include <cstdint>

namespace sh3::platform {
inline constexpr std::size_t checker_width = 64;
inline constexpr std::size_t checker_bytes = checker_width * checker_width * 4;
// Caller supplies at least checker_bytes bytes. RGBA8 on PICA is A,B,G,R in memory.
void write_checker_texture(std::uint8_t *destination) noexcept;
[[nodiscard]] std::size_t checker_texel_offset(std::size_t x, std::size_t y) noexcept;
} // namespace sh3::platform
