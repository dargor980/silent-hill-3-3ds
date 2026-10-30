#include "sh3/platform/inspection_crc32.hpp"
#include <array>

namespace sh3::platform {
namespace {
constexpr auto make_table() noexcept {
    std::array<std::uint32_t, 256> table{};
    for (unsigned i = 0; i < table.size(); ++i) {
        auto crc = std::uint32_t(i);
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1) ? 0xEDB88320U : 0U);
        table[i] = crc;
    }
    return table;
}
constexpr auto table = make_table(); // 1 KiB read-only; no heap or runtime initialization.
} // namespace
std::uint32_t inspection_crc32(const std::uint8_t *data, std::size_t size,
                               std::uint32_t previous) noexcept {
    std::uint32_t crc = ~previous;
    for (std::size_t i = 0; i < size; ++i)
        crc = (crc >> 8) ^ table[(crc ^ data[i]) & 0xFF];
    return crc ^ 0xFFFFFFFF;
}
} // namespace sh3::platform
