#include "sh3/platform/inspection_character_world.hpp"
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
ports::FileError read_character_world(const char *path, domain::CharacterWorld &out,
                                      const domain::CharacterModel &model, std::uint32_t scm,
                                      std::uint32_t san, std::uint32_t sct, StdioApi api) noexcept {
    using E = ports::FileError;
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    if (!path || !*path || !domain::valid_character(model))
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    std::array<std::uint8_t, 264> raw{};
    const auto size = api.read(raw.data(), 1, raw.size(), file);
    std::uint8_t extra{};
    const auto trailing = api.read(&extra, 1, 1, file);
    E result = E::ok;
    if (api.error(file))
        result = E::read_failed;
    else if (size != raw.size() || trailing || std::memcmp(raw.data(), "S3CWv1\0\0", 8) ||
             word(raw.data() + 8) != 1 || word(raw.data() + 12) != 3 ||
             word(raw.data() + 16) != scm || word(raw.data() + 20) != san ||
             word(raw.data() + 24) != sct || word(raw.data() + 32) != 224 ||
             word(raw.data() + 260) != 0)
        result = E::invalid_data;
    else if (inspection_crc32(raw.data() + 40, 224) != word(raw.data() + 36))
        result = E::verify_failed;
    domain::CharacterWorld world{};
    if (result == E::ok) {
        world.reference_counter = word(raw.data() + 28);
        world.origin = {number(raw.data() + 40), number(raw.data() + 44), number(raw.data() + 48)};
        world.scale = number(raw.data() + 52);
        std::size_t offset = 56;
        for (auto &instance : world.instances) {
            instance.id = word(raw.data() + offset);
            offset += 4;
            for (auto &v : instance.model) {
                v = number(raw.data() + offset);
                offset += 4;
            }
        }
        if (!domain::valid_character_world(world, model))
            result = E::invalid_data;
    }
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    if (result == E::ok)
        out = world;
    return result;
}
} // namespace sh3::platform
