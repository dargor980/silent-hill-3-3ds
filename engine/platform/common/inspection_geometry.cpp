#include "sh3/platform/inspection_geometry.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <array>
#include <cerrno>
#include <cmath>
#include <cstring>
#include <limits>
#include <type_traits>

namespace sh3::platform {
namespace {
std::uint32_t u32(const std::uint8_t *p) noexcept {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) |
           (std::uint32_t(p[3]) << 24);
}
bool bounded(float value, float limit) noexcept {
    return std::isfinite(value) && std::abs(value) <= limit;
}
bool count_valid(std::size_t count) noexcept {
    return count >= 3 && count <= inspection_max_vertices && count % 3 == 0;
}
} // namespace
bool valid_inspection_mesh(InspectionMesh mesh) noexcept {
    if (!mesh.data || !count_valid(mesh.count))
        return false;
    for (std::size_t i = 0; i < mesh.count; ++i) {
        const auto &v = mesh.data[i];
        if (!bounded(v.position.x, 4) || !bounded(v.position.y, 4) || !bounded(v.position.z, 4) ||
            !bounded(v.u, 2) || !bounded(v.v, 2) || !bounded(v.color.x, 1) || v.color.x < 0 ||
            !bounded(v.color.y, 1) || v.color.y < 0 || !bounded(v.color.z, 1) || v.color.z < 0)
            return false;
    }
    for (std::size_t i = 0; i < mesh.count; i += 3) {
        const auto a = mesh.data[i].position, b = mesh.data[i + 1].position,
                   c = mesh.data[i + 2].position;
        // Double avoids underflow/overflow while checking finite float32 input.
        const double x = double(b.x) - a.x, y = double(b.y) - a.y, z = double(b.z) - a.z;
        const double u = double(c.x) - a.x, v = double(c.y) - a.y, w = double(c.z) - a.z;
        if (y * w == z * v && z * u == x * w && x * v == y * u)
            return false;
    }
    return true;
}
ports::FileError read_inspection_geometry(const char *path, domain::SceneVertex *destination,
                                          std::size_t capacity, std::size_t &count,
                                          StdioApi api) noexcept {
    using E = ports::FileError;
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    static_assert(sizeof(domain::SceneVertex) == 32);
    static_assert(std::is_trivially_copyable_v<domain::SceneVertex>);
    count = 0;
    if (!path || !*path || !destination || capacity < 3 || capacity > inspection_max_vertices)
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    std::array<std::uint8_t, 24> header{};
    E result = E::ok;
    const auto header_read = api.read(header.data(), 1, header.size(), file);
    const auto vertices = u32(header.data() + 8);
    const auto bytes = std::size_t(vertices) * 32;
    if (api.error(file)) {
        result = E::read_failed;
    } else if (header_read != header.size() || std::memcmp(header.data(), "S3GMv1\0\0", 8) ||
               !count_valid(vertices) || vertices > capacity || u32(header.data() + 12) != 32 ||
               u32(header.data() + 16) != bytes) {
        result = E::invalid_data;
    } else {
        // Raw object representation is not read as floats until after explicit LE decoding.
        auto *raw = reinterpret_cast<std::uint8_t *>(destination);
        const auto loaded = api.read(raw, 1, bytes, file);
        std::uint8_t extra{};
        const auto trailer = api.read(&extra, 1, 1, file);
        if (api.error(file)) {
            result = E::read_failed;
        } else if (loaded != bytes || trailer != 0) {
            result = E::invalid_data;
        } else if (inspection_crc32(raw, bytes) != u32(header.data() + 20)) {
            result = E::verify_failed;
        } else {
            for (std::size_t i = 0; i < vertices; ++i) {
                std::array<float, 8> values{};
                for (std::size_t j = 0; j < values.size(); ++j) {
                    const auto word = u32(raw + i * 32 + j * 4);
                    std::memcpy(&values[j], &word, 4);
                }
                destination[i] = {{values[0], values[1], values[2]},
                                  values[3],
                                  values[4],
                                  {values[5], values[6], values[7]}};
            }
            if (!valid_inspection_mesh({destination, vertices}))
                result = E::invalid_data;
        }
    }
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    if (result == E::ok)
        count = vertices;
    return result;
}
} // namespace sh3::platform
