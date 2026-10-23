#include "sh3/platform/inspection_character.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <array>
#include <cerrno>
#include <cstring>
#include <limits>
#include <memory>
#include <new>

namespace sh3::platform {
namespace {
std::uint32_t word(const std::uint8_t *p) noexcept {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) |
           (std::uint32_t(p[3]) << 24);
}
std::uint16_t half(const std::uint8_t *p) noexcept { return p[0] | (std::uint16_t(p[1]) << 8); }
std::int16_t signed_half(const std::uint8_t *p) noexcept {
    const auto n = half(p);
    return n < 32768 ? n : int(n) - 65536;
}
float number(const std::uint8_t *p) noexcept {
    const auto w = word(p);
    float f;
    std::memcpy(&f, &w, 4);
    return f;
}
} // namespace
ports::FileError read_inspection_character(const char *path, domain::CharacterModel &out,
                                           StdioApi api, std::uint32_t *payload_crc) noexcept {
    using E = ports::FileError;
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    if (!path || !*path)
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    std::array<std::uint8_t, 32> header{};
    const auto loaded = api.read(header.data(), 1, header.size(), file);
    const auto nv = word(header.data() + 8), ni = word(header.data() + 12),
               bytes = word(header.data() + 24);
    E result = E::ok;
    if (api.error(file))
        result = E::read_failed;
    else if (loaded != header.size() || std::memcmp(header.data(), "S3CMv1\0\0", 8) || nv < 3 ||
             nv > domain::character_vertex_limit || ni < 3 || ni > domain::character_index_limit ||
             ni % 3 || word(header.data() + 16) != 3 || word(header.data() + 20) != 28 ||
             bytes != 220 + nv * 28 + ni * 2)
        result = E::invalid_data;
    std::unique_ptr<std::uint8_t[]> raw;
    std::unique_ptr<domain::CharacterModel> model;
    if (result == E::ok) {
        raw.reset(new (std::nothrow) std::uint8_t[bytes]);
        model.reset(new (std::nothrow) domain::CharacterModel{});
        if (!raw || !model)
            result = E::read_failed;
    }
    if (result == E::ok) {
        const auto size = api.read(raw.get(), 1, bytes, file);
        std::uint8_t extra{};
        const auto trailing = api.read(&extra, 1, 1, file);
        if (api.error(file))
            result = E::read_failed;
        else if (size != bytes || trailing)
            result = E::invalid_data;
        else if (inspection_crc32(raw.get(), bytes) != word(header.data() + 28))
            result = E::verify_failed;
    }
    if (result == E::ok) {
        auto *p = raw.get();
        model->center = {number(p), number(p + 4), number(p + 8)};
        model->scale = number(p + 12);
        for (unsigned i = 0; i < 3; ++i)
            model->targets[i] = word(p + 16 + 4 * i);
        p += 28;
        for (auto &h : model->helpers)
            for (auto &v : h) {
                v = number(p);
                p += 4;
            }
        model->vertex_count = nv;
        model->index_count = ni;
        for (unsigned i = 0; i < nv; ++i, p += 28) {
            auto &v = model->vertices[i];
            for (unsigned j = 0; j < 3; ++j) {
                v.position[j] = signed_half(p + 2 * j);
                v.normal[j] = signed_half(p + 6 + 2 * j);
                v.weights[j] = half(p + 16 + 2 * j);
            }
            v.uv = {signed_half(p + 12), signed_half(p + 14)};
            v.primary = p[22];
            v.count = p[23];
            v.helpers = {p[24], p[25]};
            if (half(p + 26))
                result = E::invalid_data;
        }
        for (unsigned i = 0; i < ni; ++i, p += 2)
            model->indices[i] = half(p);
        if (!domain::valid_character(*model))
            result = E::invalid_data;
    }
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    if (result == E::ok) {
        out = *model;
        if (payload_crc)
            *payload_crc = word(header.data() + 28);
    }
    return result;
}
} // namespace sh3::platform
