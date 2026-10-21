#include "sh3/platform/checker_texture.hpp"

namespace sh3::platform {
std::size_t checker_texel_offset(std::size_t x, std::size_t y) noexcept {
    const auto morton = (x & 1) | ((y & 1) << 1) | ((x & 2) << 1) | ((y & 2) << 2) |
                        ((x & 4) << 2) | ((y & 4) << 3);
    return (((y / 8) * (checker_width / 8) + x / 8) * 64 + morton) * 4;
}
void write_checker_texture(std::uint8_t *destination) noexcept {
    for (std::size_t y = 0; y < checker_width; ++y) {
        for (std::size_t x = 0; x < checker_width; ++x) {
            const auto offset = checker_texel_offset(x, y);
            const auto shade = static_cast<std::uint8_t>(((x / 8 + y / 8) % 2) ? 100 : 240);
            destination[offset] = 255;
            destination[offset + 1] = shade;
            destination[offset + 2] = shade;
            destination[offset + 3] = shade;
            // Red corner marker makes texture orientation visible.
            if (x < 8 && y < 8) {
                destination[offset + 1] = 40;
                destination[offset + 2] = 40;
                destination[offset + 3] = 255;
            }
        }
    }
}
} // namespace sh3::platform
