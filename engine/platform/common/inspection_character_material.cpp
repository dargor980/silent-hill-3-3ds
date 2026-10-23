#include "sh3/platform/inspection_character_material.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <array>
#include <cerrno>
#include <cstring>

namespace sh3::platform {
namespace {
std::uint32_t word(const std::uint8_t *p) noexcept {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) |
           (std::uint32_t(p[3]) << 24);
}
bool valid_alpha(const std::uint8_t *p, std::size_t size) noexcept {
    for (std::size_t i = 3; i < size; i += 4)
        if (p[i] > 128)
            return false;
    return true;
}
} // namespace
ports::FileError read_character_material(const char *path, CharacterMaterialData &out,
                                         std::uint32_t scm_crc, std::size_t indices, StdioApi api,
                                         std::uint32_t *payload_crc) noexcept {
    using E = ports::FileError;
    if (!path || !*path || indices < 9 || indices > domain::character_index_limit || indices % 3)
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    std::array<std::uint8_t, 32> header{};
    std::array<std::uint8_t, 36> raw_ranges{};
    E result = E::ok;
    const auto loaded = api.read(header.data(), 1, header.size(), file);
    if (api.error(file))
        result = E::read_failed;
    else if (loaded != header.size() || std::memcmp(header.data(), "S3CTv1\0\0", 8) ||
             word(header.data() + 8) != 3 || word(header.data() + 12) != 512 ||
             word(header.data() + 16) != 3 || word(header.data() + 20) != scm_crc ||
             word(header.data() + 24) != 36 + out.pixels.size())
        result = E::invalid_data;
    domain::CharacterMaterials ranges{};
    if (result == E::ok) {
        const auto n = api.read(raw_ranges.data(), 1, raw_ranges.size(), file);
        if (api.error(file))
            result = E::read_failed;
        else if (n != raw_ranges.size())
            result = E::invalid_data;
        else {
            for (std::size_t i = 0; i < 3; ++i) {
                const auto *p = raw_ranges.data() + i * 12;
                ranges[i] = {word(p), word(p + 4), word(p + 8)};
            }
            if (!domain::valid_character_materials(ranges, indices))
                result = E::invalid_data;
        }
    }
    if (result == E::ok) {
        const auto n = api.read(out.pixels.data(), 1, out.pixels.size(), file);
        std::uint8_t extra{};
        const auto trailing = api.read(&extra, 1, 1, file);
        if (api.error(file))
            result = E::read_failed;
        else if (n != out.pixels.size() || trailing)
            result = E::invalid_data;
        else {
            const auto ranges_crc = inspection_crc32(raw_ranges.data(), raw_ranges.size());
            const auto crc = inspection_crc32(out.pixels.data(), out.pixels.size(), ranges_crc);
            if (crc != word(header.data() + 28))
                result = E::verify_failed;
            else if (!valid_alpha(out.pixels.data(), out.pixels.size()))
                result = E::invalid_data;
        }
    }
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    if (result == E::ok) {
        out.ranges = ranges;
        if (payload_crc)
            *payload_crc = word(header.data() + 28);
    }
    return result;
}
bool upload_character_texture(const std::uint8_t *source, std::size_t size,
                              std::uint8_t *destination, std::size_t capacity) noexcept {
    if (!source || !destination || size != character_texture_bytes || capacity != size)
        return false;
    const auto s = reinterpret_cast<std::uintptr_t>(source);
    const auto d = reinterpret_cast<std::uintptr_t>(destination);
    if ((s <= d ? d - s : s - d) < size || !valid_alpha(source, size))
        return false;
    for (std::size_t y = 0; y < 512; ++y)
        for (std::size_t x = 0; x < 512; ++x) {
            const auto morton = (x & 1) | ((y & 1) << 1) | ((x & 2) << 1) | ((y & 2) << 2) |
                                ((x & 4) << 2) | ((y & 4) << 3);
            const auto dst = (((y / 8) * 64 + x / 8) * 64 + morton) * 4;
            const auto src = (y * 512 + x) * 4;
            destination[dst] = (unsigned(source[src + 3]) * 255 + 64) / 128;
            for (unsigned c = 1; c < 4; ++c)
                destination[dst + c] = source[src + 3 - c];
        }
    return true;
}
} // namespace sh3::platform
