#include "sh3/platform/inspection_locomotion.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <algorithm>
#include <cerrno>
#include <cstring>
#include <limits>
#include <memory>
#include <new>

namespace sh3::platform {
namespace {
using E = ports::FileError;
using Result = LocomotionLoadResult;
using Model = domain::InspectionLocomotion;
std::uint32_t u32(const std::uint8_t *p) noexcept {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) |
           (std::uint32_t(p[3]) << 24);
}
std::uint16_t u16(const std::uint8_t *p) noexcept { return p[0] | (std::uint16_t(p[1]) << 8); }
std::int16_t i16(const std::uint8_t *p) noexcept {
    const auto x = u16(p);
    return x < 32768 ? x : int(x) - 65536;
}
float f32(const std::uint8_t *p) noexcept {
    const auto bits = u32(p);
    float f;
    std::memcpy(&f, &bits, 4);
    return f;
}
Result decode(const std::uint8_t *h, const std::uint8_t *p, Model &model) noexcept {
    auto &m = model.shared;
    m.bone_count = u32(h + 8);
    m.sample_count = u32(h + 12);
    m.helper_count = u32(h + 16);
    m.vertex_count = u32(h + 20);
    m.index_count = u32(h + 24);
    m.material_count = u32(h + 28);
    model.profile = {u32(h + 44), u32(h + 48), u32(h + 52), m.sample_count, u32(h + 36),
                     u32(h + 32), {}};
    model.inspection_hz = u32(h + 40);
    m.center = {f32(p), f32(p + 4), f32(p + 8)};
    m.scale = f32(p + 12);
    p += 16;
    for (unsigned b = 0; b < m.bone_count; ++b, p += 4) {
        const auto parent = u32(p);
        m.parents[b] = parent == 0xffffffffU ? -1 : parent < b ? int(parent) : -2;
    }
    for (unsigned b = 0; b < m.bone_count; ++b, p += 4) {
        model.source_bones[b] = u16(p);
        model.channels[b] = p[2];
        if (p[3])
            return {E::invalid_data, "bindings.reserved"};
    }
    for (unsigned i = 0; i < model.profile.clip_count; ++i) {
        auto &c = model.profile.clips[i]; // Exact profile/count pair checked before allocation.
        c = {u16(p), u16(p + 2), i16(p + 4), u16(p + 6), u16(p + 8), p[10], p[11], u32(p + 12)};
        if (u32(p + 16))
            return {E::invalid_data, "descriptors.reserved"};
        p += 20;
    }
    if (!domain::valid_locomotion_profile(model.profile))
        return {E::invalid_data, "descriptors"};
    for (unsigned f = 0; f < m.sample_count; ++f)
        for (unsigned b = 0; b < m.bone_count; ++b, p += 28)
            m.samples[f][b] = {{f32(p), f32(p + 4), f32(p + 8)},
                               {f32(p + 12), f32(p + 16), f32(p + 20), f32(p + 24)}};
    for (unsigned i = 0; i < m.helper_count; ++i) {
        m.targets[i] = u32(p);
        p += 4;
        for (auto &v : m.helpers[i]) {
            v = f32(p);
            p += 4;
        }
    }
    for (unsigned i = 0; i < m.vertex_count; ++i, p += 28) {
        auto &v = m.vertices[i];
        for (unsigned j = 0; j < 3; ++j) {
            v.position[j] = i16(p + 2 * j);
            v.normal[j] = i16(p + 6 + 2 * j);
            v.weights[j] = u16(p + 16 + 2 * j);
        }
        v.uv = {i16(p + 12), i16(p + 14)};
        v.primary = p[22];
        v.count = p[23];
        v.helpers = {p[24], p[25]};
        if (u16(p + 26))
            return {E::invalid_data, "vertices.reserved"};
    }
    for (unsigned i = 0; i < m.index_count; ++i, p += 2)
        m.indices[i] = u16(p);
    for (unsigned i = 0; i < m.material_count; ++i, p += 28)
        m.materials[i] = {u32(p),      u32(p + 4),  u32(p + 8), u32(p + 12),
                          u32(p + 16), u32(p + 20), u32(p + 24)};
    const auto field = domain::locomotion_rig_error(model);
    return field ? Result{E::invalid_data, field} : Result{};
}
Result load(const char *path, std::unique_ptr<Model> &out, StdioApi api) noexcept {
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    if (!path || !*path)
        return {E::invalid_target, "target"};
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return {errno == ENOENT ? E::missing : E::read_failed, "open"};
    std::array<std::uint8_t, 96> header{};
    const auto count = api.read(header.data(), 1, header.size(), file);
    const auto *h = header.data();
    const auto nb = u32(h + 8), nf = u32(h + 12), nh = u32(h + 16), nv = u32(h + 20),
               ni = u32(h + 24), nm = u32(h + 28), bytes = u32(h + 56);
    Result result;
    const auto *profile = domain::locomotion_profile(u32(h + 44));
    if (api.error(file))
        result = {E::read_failed, "header"};
    else if (count != header.size() || std::memcmp(h, "S3RIv2\0\0", 8))
        result = {E::invalid_data, "header.magic_or_size"};
    else if (nb != 36 || nf > domain::rig_samples || nh > domain::rig_helpers || nv < 3 ||
             nv > domain::rig_vertices || ni < 3 || ni > domain::rig_indices || ni % 3 || nm < 1 ||
             nm > domain::rig_materials)
        result = {E::invalid_data, "counts"};
    else if (!profile || nf != profile->sample_count || u32(h + 32) != profile->clip_count ||
             u32(h + 36) != 2 || u32(h + 40) != 25 ||
             u32(h + 48) != 522 || u32(h + 52) != 525)
        result = {E::invalid_data, "profile"};
    else if (bytes != 16 + 8 * nb + 20 * profile->clip_count + 28 * nb * nf + 68 * nh +
                          28 * nv + 2 * ni + 28 * nm)
        result = {E::invalid_data, "payload.length"};
    else {
        for (unsigned i = 64; i < 96; i += 4)
            if (u32(h + i))
                result = {E::invalid_data, "header.reserved"};
    }
    std::unique_ptr<std::uint8_t[]> raw;
    std::unique_ptr<Model> model;
    if (result.error == E::ok) {
        raw.reset(new (std::nothrow) std::uint8_t[bytes]);
        if (!raw)
            result = {E::read_failed, "allocation.payload"};
    }
    if (result.error == E::ok) {
        const auto n = api.read(raw.get(), 1, bytes, file);
        std::uint8_t extra{};
        const auto tail = api.read(&extra, 1, 1, file);
        if (api.error(file))
            result = {E::read_failed, "payload"};
        else if (n != bytes || tail)
            result = {E::invalid_data, "payload.length"};
        else if (inspection_crc32(raw.get(), bytes) != u32(h + 60))
            result = {E::verify_failed, "payload.crc32"};
    }
    if (result.error == E::ok) {
        model.reset(new (std::nothrow) Model{});
        result = model ? decode(h, raw.get(), *model) : Result{E::read_failed, "allocation.model"};
    }
    if (api.close(file) != 0 && result.error == E::ok)
        result = {E::close_failed, "close"};
    if (result.error == E::ok)
        out = std::move(model);
    return result;
}
bool join(const char *root, const char *name, std::array<char, 512> &path) noexcept {
    if (!root || !*root)
        return false;
    const auto separator = root[std::strlen(root) - 1] == '/' ? "" : "/";
    const auto n = std::snprintf(path.data(), path.size(), "%s%s%s", root, separator, name);
    return n > 0 && static_cast<std::size_t>(n) < path.size();
}
Result texture(const char *path, const domain::RigMaterial &m, std::uint8_t *buffer,
               StdioApi api) noexcept {
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return {errno == ENOENT ? E::missing : E::read_failed, "texture.open", m.texture};
    std::size_t remaining = std::size_t(m.width) * m.height * 4;
    std::uint32_t crc = 0;
    Result result;
    while (remaining) {
        const auto n = std::min<std::size_t>(remaining, 65536);
        const auto count = api.read(buffer, 1, n, file);
        if (api.error(file)) {
            result = {E::read_failed, "texture.read", m.texture};
            break;
        }
        if (count != n) {
            result = {E::invalid_data, "texture.length", m.texture};
            break;
        }
        crc = inspection_crc32(buffer, n, crc);
        remaining -= n;
    }
    if (result.error == E::ok) {
        std::uint8_t extra{};
        const auto tail = api.read(&extra, 1, 1, file);
        if (api.error(file))
            result = {E::read_failed, "texture.tail", m.texture};
        else if (tail)
            result = {E::invalid_data, "texture.length", m.texture};
        else if (crc != m.crc)
            result = {E::verify_failed, "texture.crc32", m.texture};
    }
    if (api.close(file) != 0 && result.error == E::ok)
        result = {E::close_failed, "texture.close", m.texture};
    return result;
}
} // namespace
LocomotionLoadResult read_locomotion_rig(const char *path, Model &out, StdioApi api) noexcept {
    std::unique_ptr<Model> candidate;
    const auto result = load(path, candidate, api);
    if (result.error == E::ok)
        out = *candidate;
    return result;
}
LocomotionLoadResult read_locomotion_bundle(const char *root, Model &out, StdioApi api) noexcept {
    std::array<char, 512> path{};
    if (!join(root, "heather.sri", path))
        return {E::invalid_target, "target"};
    std::unique_ptr<Model> candidate;
    auto result = load(path.data(), candidate, api);
    if (result.error != E::ok)
        return result;
    std::unique_ptr<std::uint8_t[]> buffer(new (std::nothrow) std::uint8_t[65536]);
    if (!buffer)
        return {E::read_failed, "allocation.texture"};
    for (unsigned i = 0; i < candidate->shared.material_count; ++i) {
        std::array<char, 32> name{};
        std::snprintf(name.data(), name.size(), "texture-%02u.rgba", i);
        if (!join(root, name.data(), path))
            return {E::invalid_target, "texture.path", i};
        result = texture(path.data(), candidate->shared.materials[i], buffer.get(), api);
        if (result.error != E::ok)
            return result;
    }
    out = *candidate;
    return {};
}
} // namespace sh3::platform
