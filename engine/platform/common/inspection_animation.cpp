#include "sh3/platform/inspection_animation.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <array>
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
    auto w = word(p);
    float f;
    std::memcpy(&f, &w, 4);
    return f;
}
} // namespace
ports::FileError read_inspection_animation(const char *path, domain::InspectionClip &out,
                                           StdioApi api, std::uint32_t *payload_crc) noexcept {
    using E = ports::FileError;
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    if (!path || !*path)
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    std::array<std::uint8_t, 1248> raw{};
    const auto loaded = api.read(raw.data(), 1, raw.size(), file);
    std::uint8_t extra{};
    const auto trailer = api.read(&extra, 1, 1, file);
    E result = E::ok;
    if (api.error(file))
        result = E::read_failed;
    else if (loaded != raw.size() || trailer || std::memcmp(raw.data(), "S3ANv1\0\0", 8) ||
             word(raw.data() + 8) != 3 || word(raw.data() + 12) != 24 ||
             word(raw.data() + 16) != 0x1449 || word(raw.data() + 20) != domain::clip_increment ||
             word(raw.data() + 24) != 1216)
        result = E::invalid_data;
    else if (inspection_crc32(raw.data() + 32, 1216) != word(raw.data() + 28))
        result = E::verify_failed;
    domain::InspectionClip clip{};
    if (result == E::ok) {
        for (int i = 0; i < 3; ++i) {
            const auto p = word(raw.data() + 32 + 4 * i);
            clip.parents[i] = p == 0xFFFFFFFFU ? -1 : p <= 2 ? int(p) : -2;
        }
        clip.center = {number(raw.data() + 44), number(raw.data() + 48), number(raw.data() + 52)};
        clip.scale = number(raw.data() + 56);
        std::size_t offset = 60;
        for (auto &t : clip.translations) {
            t = {number(raw.data() + offset), number(raw.data() + offset + 4),
                 number(raw.data() + offset + 8)};
            offset += 12;
        }
        for (auto &frame : clip.rotations)
            for (auto &q : frame)
                for (auto &v : q) {
                    v = number(raw.data() + offset);
                    offset += 4;
                }
        if (!domain::valid_clip(clip))
            result = E::invalid_data;
    }
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    if (result == E::ok) {
        out = clip;
        if (payload_crc)
            *payload_crc = word(raw.data() + 28);
    }
    return result;
}
} // namespace sh3::platform
