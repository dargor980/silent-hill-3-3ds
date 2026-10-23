#include "sh3/platform/inspection_character_lighting.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <cerrno>
#include <cstring>
#include <limits>

namespace sh3::platform {
namespace {
std::uint32_t word(const std::uint8_t *p) noexcept {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) |
           (std::uint32_t(p[3]) << 24);
}
float number(const std::uint8_t *p) noexcept {
    const auto w = word(p);
    float f;
    std::memcpy(&f, &w, 4);
    return f;
}
} // namespace
ports::FileError read_character_lighting(const char *path, domain::CharacterLighting &out,
                                         const domain::CharacterModel &model, std::uint32_t scm,
                                         std::uint32_t san, std::uint32_t sct,
                                         StdioApi api) noexcept {
    using E = ports::FileError;
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    if (!path || !*path || !domain::valid_character(model))
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    std::array<std::uint8_t, 872> raw{};
    const auto size = api.read(raw.data(), 1, raw.size(), file);
    std::uint8_t extra{};
    const auto trailing = api.read(&extra, 1, 1, file);
    E result = E::ok;
    if (api.error(file))
        result = E::read_failed;
    else if (size != raw.size() || trailing || std::memcmp(raw.data(), "S3CLv1\0\0", 8) ||
             word(raw.data() + 8) != 1 || word(raw.data() + 12) != 15 ||
             word(raw.data() + 16) != 3 || word(raw.data() + 20) != scm ||
             word(raw.data() + 24) != san || word(raw.data() + 28) != sct ||
             word(raw.data() + 32) != model.vertex_count ||
             word(raw.data() + 36) != model.index_count || word(raw.data() + 40) != 824)
        result = E::invalid_data;
    else if (inspection_crc32(raw.data() + 48, 824) != word(raw.data() + 44))
        result = E::verify_failed;
    domain::CharacterLighting light{};
    if (result == E::ok) {
        light.reference_counter = word(raw.data() + 48);
        std::size_t offset = 52;
        auto read = [&](auto &values) {
            for (auto &v : values) {
                v = number(raw.data() + offset);
                offset += 4;
            }
        };
        read(light.model_to_capture);
        read(light.ambient);
        for (auto &d : light.directionals) {
            read(d.direction);
            read(d.color);
        }
        read(light.spot.position);
        read(light.spot.direction);
        read(light.spot.color);
        read(light.spot.attenuation);
        for (auto &r : light.ranges) {
            r.first_vertex = word(raw.data() + offset);
            r.vertex_count = word(raw.data() + offset + 4);
            r.first_index = word(raw.data() + offset + 8);
            r.index_count = word(raw.data() + offset + 12);
            offset += 16;
            read(r.diffuse);
            read(r.ambient);
        }
        if (!domain::valid_character_lighting(light, model))
            result = E::invalid_data;
    }
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    if (result == E::ok)
        out = light;
    return result;
}
} // namespace sh3::platform
