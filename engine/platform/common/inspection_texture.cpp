#include "sh3/platform/inspection_texture.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <array>
#include <cerrno>
#include <cstring>

namespace sh3::platform {
bool valid_inspection_pixels(InspectionPixels pixels) noexcept {
    return pixels.data != nullptr && pixels.size == inspection_bytes;
}
ports::FileError read_inspection_texture(const char *path, std::uint8_t *destination,
                                         std::size_t capacity, StdioApi api) noexcept {
    using E = ports::FileError;
    if (path == nullptr || *path == '\0' || destination == nullptr ||
        capacity != inspection_bytes) {
        return E::invalid_target;
    }
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file) {
        return errno == ENOENT ? E::missing : E::read_failed;
    }
    std::array<std::uint8_t, 24> header{};
    const auto u32 = [&](std::size_t offset) {
        return std::uint32_t(header[offset]) | (std::uint32_t(header[offset + 1]) << 8) |
               (std::uint32_t(header[offset + 2]) << 16) |
               (std::uint32_t(header[offset + 3]) << 24);
    };
    E result = E::ok;
    const auto count = api.read(header.data(), 1, header.size(), file);
    if (api.error(file)) {
        result = E::read_failed;
    } else if (count != header.size() || std::memcmp(header.data(), "S3TXv1\0\0", 8) != 0 ||
               u32(8) != 0x01000100 || u32(12) != 1 || u32(16) != inspection_bytes) {
        result = E::invalid_data;
    } else {
        const auto read = api.read(destination, 1, inspection_bytes, file);
        std::uint8_t extra{};
        const auto trailer = api.read(&extra, 1, 1, file);
        if (api.error(file)) {
            result = E::read_failed;
        } else if (read != inspection_bytes || trailer != 0) {
            result = E::invalid_data;
        } else if (inspection_crc32(destination, inspection_bytes) != u32(20)) {
            result = E::verify_failed;
        }
    }
    if (api.close(file) != 0 && result == E::ok) {
        result = E::close_failed;
    }
    return result;
}
bool upload_inspection_pixels(InspectionPixels source, std::uint8_t *destination,
                              std::size_t capacity) noexcept {
    if (!valid_inspection_pixels(source) || destination == nullptr ||
        capacity != inspection_bytes || destination == source.data) {
        return false;
    }
    for (std::size_t y = 0; y < inspection_width; ++y) {
        const auto gpu_y = y;
        for (std::size_t x = 0; x < inspection_width; ++x) {
            const auto morton = (x & 1) | ((gpu_y & 1) << 1) | ((x & 2) << 1) | ((gpu_y & 2) << 2) |
                                ((x & 4) << 2) | ((gpu_y & 4) << 3);
            const auto target = (((gpu_y / 8) * (inspection_width / 8) + x / 8) * 64 + morton) * 4;
            const auto origin = (y * inspection_width + x) * 4;
            for (std::size_t channel = 0; channel < 4; ++channel) {
                destination[target + channel] = source.data[origin + 3 - channel];
            }
        }
    }
    return true;
}
} // namespace sh3::platform
