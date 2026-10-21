#pragma once
#include <cstddef>
#include <cstdint>

namespace sh3::platform {
std::uint32_t inspection_crc32(const std::uint8_t *data, std::size_t size) noexcept;
} // namespace sh3::platform
