#include "sh3/platform/room_scene.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <array>
#include <cerrno>
#include <cmath>
#include <cstring>
#include <memory>
#include <new>

namespace sh3::platform {
namespace {
std::uint32_t word(const std::uint8_t *p) noexcept {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) |
           (std::uint32_t(p[3]) << 24);
}
float number(const std::uint8_t *p) noexcept {
    const auto u = word(p);
    float f;
    std::memcpy(&f, &u, 4);
    return f;
}
} // namespace
ports::FileError read_room_map(const char *path, domain::RoomMap &out, StdioApi api) noexcept {
    using E = ports::FileError;
    if (!path || !*path)
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    std::array<std::uint8_t, 32> header{};
    const auto count = api.read(header.data(), 1, header.size(), file);
    const auto ns = word(header.data() + 8), nv = word(header.data() + 12),
               bytes = word(header.data() + 16);
    const auto version = word(header.data() + 28);
    const bool original = version == 2;
    const unsigned stride = original ? 24 : 16;
    E result = E::ok;
    if (api.error(file))
        result = E::read_failed;
    else if (count != 32 || std::memcmp(header.data(), original ? "S3RMv2\0\0" : "S3RMv1\0\0", 8) ||
             !ns || ns > domain::room_shapes || !nv || nv > domain::room_vertices || nv % 3 ||
             bytes != ns * stride + (original ? domain::room_materials * 16 : 0) + nv * 36 ||
             (version != 1 && version != 2))
        result = E::invalid_data;
    std::unique_ptr<std::uint8_t[]> raw;
    std::unique_ptr<domain::RoomMap> map;
    if (result == E::ok) {
        raw.reset(new (std::nothrow) std::uint8_t[bytes]);
        map.reset(new (std::nothrow) domain::RoomMap{});
        if (!raw || !map)
            result = E::read_failed;
    }
    if (result == E::ok) {
        const auto n = api.read(raw.get(), 1, bytes, file);
        std::uint8_t extra{};
        const auto tail = api.read(&extra, 1, 1, file);
        if (api.error(file))
            result = E::read_failed;
        else if (n != bytes || tail)
            result = E::invalid_data;
        else if (inspection_crc32(raw.get(), bytes) != word(header.data() + 20))
            result = E::verify_failed;
    }
    if (result == E::ok) {
        map->shape_count = ns;
        map->vertex_count = nv;
        map->glass_crc = word(header.data() + 24);
        auto *p = raw.get();
        for (unsigned i = 0; i < ns; ++i, p += stride)
            map->shapes[i] = {word(p),
                              word(p + 4),
                              word(p + 8),
                              word(p + 12),
                              original ? word(p + 16) : 0,
                              original ? word(p + 20) : 1};
        map->material_count = original ? domain::room_materials : 0;
        for (unsigned i = 0; i < map->material_count; ++i, p += 16)
            map->materials[i] = {word(p), word(p + 4), word(p + 8),
                                 static_cast<domain::RoomPass>(word(p + 12))};
        const domain::PoseMatrix model{1,
                                       0,
                                       0,
                                       0,
                                       0,
                                       1,
                                       0,
                                       0,
                                       0,
                                       0,
                                       1,
                                       0,
                                       domain::room_origin.x,
                                       domain::room_origin.y,
                                       domain::room_origin.z,
                                       1};
        for (unsigned i = 0; i < nv; ++i, p += 36) {
            std::array<float, 4> local{number(p), number(p + 4), number(p + 8), number(p + 12)};
            if (local[3] != 1)
                result = E::invalid_data;
            for (unsigned j = 0; j < 3; ++j)
                if (!std::isfinite(local[j]) || std::abs(local[j]) > 32768)
                    result = E::invalid_data;
            map->vertices[i] = {domain::room_position(model, local),
                                {number(p + 16), number(p + 20), number(p + 24)},
                                {number(p + 28), number(p + 32)}};
        }
        if (!domain::valid_room_map(*map))
            result = E::invalid_data;
    }
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    if (result == E::ok)
        out = *map;
    return result;
}
bool upload_room_texture(const std::uint8_t *source, std::size_t size, std::uint8_t *destination,
                         std::size_t capacity) noexcept {
    constexpr std::size_t width = 512, bytes = width * width * 4;
    if (!source || !destination || source == destination || size != bytes || capacity != bytes)
        return false;
    for (std::size_t y = 0; y < width; ++y)
        for (std::size_t x = 0; x < width; ++x) {
            const auto morton = (x & 1) | ((y & 1) << 1) | ((x & 2) << 1) | ((y & 2) << 2) |
                                ((x & 4) << 2) | ((y & 4) << 3);
            const auto target = (((y / 8) * (width / 8) + x / 8) * 64 + morton) * 4;
            const auto origin = (y * width + x) * 4;
            for (std::size_t c = 0; c < 4; ++c)
                destination[target + c] = source[origin + 3 - c];
        }
    return true;
}
} // namespace sh3::platform
