#include "sh3/platform/inspection_crc32.hpp"

namespace sh3::platform {
std::uint32_t inspection_crc32(const std::uint8_t *data, std::size_t size) noexcept {
    std::uint32_t crc = 0xFFFFFFFF;
    for (std::size_t i = 0; i < size; ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8; ++bit) {
            crc = (crc >> 1) ^ ((crc & 1) ? 0xEDB88320U : 0U);
        }
    }
    return crc ^ 0xFFFFFFFF;
}
} // namespace sh3::platform
