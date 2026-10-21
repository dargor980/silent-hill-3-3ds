#pragma once
#include "sh3/platform/stdio_files.hpp"
#include <cstddef>
#include <cstdint>

namespace sh3::platform {
inline constexpr std::size_t inspection_width = 256;
inline constexpr std::size_t inspection_bytes = inspection_width * inspection_width * 4;
struct InspectionPixels {
    const std::uint8_t *data;
    std::size_t size;
};
[[nodiscard]] bool valid_inspection_pixels(InspectionPixels pixels) noexcept;
// Buffer is borrowed. On failure its contents must not be used.
[[nodiscard]] ports::FileError read_inspection_texture(const char *path, std::uint8_t *destination,
                                                       std::size_t capacity,
                                                       StdioApi api = system_stdio) noexcept;
// Distinct source/destination buffers, at least inspection_bytes each.
// Convert top-down canonical RGBA to PICA ABGR/Morton without a row flip.
[[nodiscard]] bool upload_inspection_pixels(InspectionPixels source, std::uint8_t *destination,
                                            std::size_t capacity) noexcept;
} // namespace sh3::platform
