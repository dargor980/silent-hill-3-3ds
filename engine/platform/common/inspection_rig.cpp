#include "sh3/platform/inspection_rig.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <algorithm>
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
    const auto v = half(p);
    return v < 32768 ? v : int(v) - 65536;
}
float number(const std::uint8_t *p) noexcept {
    const auto w = word(p);
    float f;
    std::memcpy(&f, &w, 4);
    return f;
}
bool dimension(std::uint32_t n) noexcept { return n == 128 || n == 256 || n == 512 || n == 1024; }
std::size_t pixel_bytes(const domain::RigMaterial &r) noexcept {
    return dimension(r.width) && dimension(r.height) ? std::size_t(r.width) * r.height * 4 : 0;
}
} // namespace
ports::FileError read_inspection_rig(const char *path, domain::InspectionRig &out,
                                     StdioApi api) noexcept {
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    using E = ports::FileError;
    if (!path || !*path)
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    std::array<std::uint8_t, 64> header{};
    const auto loaded = api.read(header.data(), 1, 64, file);
    const auto nb = word(header.data() + 8), nf = word(header.data() + 12),
               nh = word(header.data() + 16), nv = word(header.data() + 20),
               ni = word(header.data() + 24), nm = word(header.data() + 28),
               bytes = word(header.data() + 40);
    E result = E::ok;
    if (api.error(file))
        result = E::read_failed;
    else if (loaded != 64 || std::memcmp(header.data(), "S3RIv1\0\0", 8) || nb < 1 ||
             nb > domain::rig_bones || nf < 2 || nf > domain::sri1_samples ||
             nh > domain::rig_helpers || nv < 3 || nv > domain::rig_vertices || ni < 3 ||
             ni > domain::rig_indices || ni % 3 || nm < 1 || nm > domain::rig_materials ||
             word(header.data() + 48) || word(header.data() + 52) || word(header.data() + 56) ||
             word(header.data() + 60) ||
             bytes != 16 + nb * 4 + nb * nf * 28 + nh * 68 + nv * 28 + ni * 2 + nm * 28)
        result = E::invalid_data;
    std::unique_ptr<std::uint8_t[]> raw;
    std::unique_ptr<domain::InspectionRig> rig;
    if (result == E::ok) {
        raw.reset(new (std::nothrow) std::uint8_t[bytes]);
        rig.reset(new (std::nothrow) domain::InspectionRig{});
        if (!raw || !rig)
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
        else if (inspection_crc32(raw.get(), bytes) != word(header.data() + 44))
            result = E::verify_failed;
    }
    if (result == E::ok) {
        auto &m = *rig;
        auto *p = raw.get();
        m.bone_count = nb;
        m.sample_count = nf;
        m.helper_count = nh;
        m.vertex_count = nv;
        m.index_count = ni;
        m.material_count = nm;
        m.clip_id = word(header.data() + 32);
        m.increment = word(header.data() + 36);
        m.center = {number(p), number(p + 4), number(p + 8)};
        m.scale = number(p + 12);
        p += 16;
        for (unsigned i = 0; i < nb; ++i, p += 4) {
            const auto v = word(p);
            m.parents[i] = v == 0xffffffffU ? -1 : v < nb ? int(v) : -2;
        }
        for (unsigned f = 0; f < nf; ++f)
            for (unsigned i = 0; i < nb; ++i, p += 28) {
                m.samples[f][i] = {
                    {number(p), number(p + 4), number(p + 8)},
                    {number(p + 12), number(p + 16), number(p + 20), number(p + 24)}};
            }
        for (unsigned i = 0; i < nh; ++i) {
            m.targets[i] = word(p);
            p += 4;
            for (auto &v : m.helpers[i]) {
                v = number(p);
                p += 4;
            }
        }
        for (unsigned i = 0; i < nv; ++i, p += 28) {
            auto &v = m.vertices[i];
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
            m.indices[i] = half(p);
        for (unsigned i = 0; i < nm; ++i, p += 28)
            m.materials[i] = {word(p),      word(p + 4),  word(p + 8), word(p + 12),
                              word(p + 16), word(p + 20), word(p + 24)};
        if (!domain::valid_rig(m))
            result = E::invalid_data;
    }
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    if (result == E::ok)
        out = *rig;
    return result;
}
ports::FileError read_rig_texture(const char *path, const domain::RigMaterial &r, std::uint8_t *out,
                                  std::size_t capacity, StdioApi api) noexcept {
    using E = ports::FileError;
    const auto bytes = pixel_bytes(r);
    if (!path || !*path || !out || !bytes || capacity < bytes)
        return E::invalid_target;
    errno = 0;
    auto *file = api.open(path, "rb");
    if (!file)
        return errno == ENOENT ? E::missing : E::read_failed;
    const auto count = api.read(out, 1, bytes, file);
    std::uint8_t extra{};
    const auto tail = api.read(&extra, 1, 1, file);
    E result = E::ok;
    if (api.error(file))
        result = E::read_failed;
    else if (count != bytes || tail)
        result = E::invalid_data;
    else if (inspection_crc32(out, bytes) != r.crc)
        result = E::verify_failed;
    if (api.close(file) != 0 && result == E::ok)
        result = E::close_failed;
    return result;
}
bool upload_rig_texture(const domain::RigMaterial &r, const std::uint8_t *source, std::size_t size,
                        std::uint8_t *target, std::size_t capacity) noexcept {
    const auto bytes = pixel_bytes(r);
    if (!source || !target || source == target || !bytes || size != bytes || capacity < bytes)
        return false;
    for (std::size_t y = 0; y < r.height; ++y)
        for (std::size_t x = 0; x < r.width; ++x) {
            const auto morton = (x & 1) | ((y & 1) << 1) | ((x & 2) << 1) | ((y & 2) << 2) |
                                ((x & 4) << 2) | ((y & 4) << 3);
            const auto dst = (((y / 8) * (r.width / 8) + x / 8) * 64 + morton) * 4,
                       // PS2 RGBA rows start at the top; PICA samples V=0 from the bottom.
                       // Adapt only the upload, preserving the source UV and CRC bytes.
                src = ((r.height - 1 - y) * r.width + x) * 4;
            target[dst] = static_cast<std::uint8_t>(std::min(255U, 2U * source[src + 3]));
            for (unsigned c = 1; c < 4; ++c)
                target[dst + c] = source[src + 3 - c];
        }
    return true;
}
} // namespace sh3::platform
