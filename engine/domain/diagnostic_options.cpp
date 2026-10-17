#include "sh3/domain/diagnostic_options.hpp"

namespace sh3::domain {
namespace {
std::uint32_t checksum(const std::uint8_t *bytes) noexcept {
    std::uint32_t hash = 2166136261U;
    for (std::size_t i = 0; i < 12; ++i) {
        hash = (hash ^ bytes[i]) * 16777619U;
    }
    return hash;
}
void store32(std::uint8_t *bytes, std::uint32_t value) noexcept {
    for (unsigned i = 0; i < 4; ++i) {
        bytes[i] = static_cast<std::uint8_t>(value >> (i * 8));
    }
}
std::uint32_t load32(const std::uint8_t *bytes) noexcept {
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) {
        value |= std::uint32_t{bytes[i]} << (i * 8);
    }
    return value;
}
} // namespace
OptionsBytes encode_options(OptionsRecord record) noexcept {
    OptionsBytes bytes{'S', '3', 'O',
                       'P', 1,   static_cast<std::uint8_t>(record.options.tone_enabled)};
    store32(bytes.data() + 8, record.generation);
    store32(bytes.data() + 12, checksum(bytes.data()));
    return bytes;
}
bool decode_options(const std::uint8_t *bytes, std::size_t size, OptionsRecord &output) noexcept {
    if (bytes == nullptr || size != 16) {
        return false;
    }
    if (bytes[0] != 'S' || bytes[1] != '3' || bytes[2] != 'O' || bytes[3] != 'P' || bytes[4] != 1 ||
        bytes[5] > 1 || bytes[6] != 0 || bytes[7] != 0 || load32(bytes + 8) == 0 ||
        load32(bytes + 12) != checksum(bytes)) {
        return false;
    }
    output = {{bytes[5] == 1}, load32(bytes + 8)};
    return true;
}
} // namespace sh3::domain
