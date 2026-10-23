#include "sh3/domain/character_skinning.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::domain {
namespace {
bool bounded(float v, float limit) noexcept { return std::isfinite(v) && std::abs(v) <= limit; }
PoseMatrix product(const PoseMatrix &a, const PoseMatrix &b) noexcept {
    PoseMatrix result{};
    for (int c = 0; c < 4; ++c)
        for (int r = 0; r < 4; ++r)
            for (int k = 0; k < 4; ++k)
                result[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
    return result;
}
} // namespace
bool valid_character(const CharacterModel &m) noexcept {
    if (m.vertex_count < 3 || m.vertex_count > character_vertex_limit || m.index_count < 3 ||
        m.index_count > character_index_limit || m.index_count % 3 || !bounded(m.scale, 1) ||
        m.scale <= 0 || !bounded(m.center.x, 100000) || !bounded(m.center.y, 100000) ||
        !bounded(m.center.z, 100000))
        return false;
    for (std::size_t i = 0; i < 3; ++i) {
        if (m.targets[i] >= 3)
            return false;
        const auto &h = m.helpers[i];
        for (float value : h)
            if (!bounded(value, 100000))
                return false;
        if (h[3] != 0 || h[7] != 0 || h[11] != 0 || h[15] != 1)
            return false;
    }
    for (std::size_t j = 0; j < m.vertex_count; ++j) {
        const auto &v = m.vertices[j];
        if (v.primary >= 3 || v.count < 1 || v.count > 3)
            return false;
        unsigned sum = 0;
        for (unsigned i = 0; i < 3; ++i) {
            if (v.weights[i] > 4096 || (i >= v.count && v.weights[i] != 0))
                return false;
            sum += v.weights[i];
        }
        if (sum > 4096 || sum < 4097U - v.count)
            return false;
        for (unsigned i = 0; i < 2; ++i)
            if ((i + 1 < v.count && v.helpers[i] >= 3) || (i + 1 >= v.count && v.helpers[i] != 255))
                return false;
    }
    for (std::size_t i = 0; i < m.index_count; ++i)
        if (m.indices[i] >= m.vertex_count)
            return false;
    return true;
}
CharacterPalette character_palette(const CharacterModel &m, const SkeletonPose &pose) noexcept {
    CharacterPalette palette{};
    for (std::size_t i = 0; i < 3; ++i) {
        palette[i] = pose[i];
        palette[3 + i] = product(pose[m.targets[i]], m.helpers[i]);
    }
    return palette;
}
DeformedVertex deform_character_vertex(const CharacterVertex &v,
                                       const CharacterPalette &palette) noexcept {
    DeformedVertex out{};
    for (unsigned i = 0; i < v.count; ++i) {
        const auto &m = palette[i == 0 ? v.primary : 3 + v.helpers[i - 1]];
        const float weight = float(v.weights[i]) / 4096;
        for (int row = 0; row < 4; ++row) {
            float p = m[12 + row];
            for (int k = 0; k < 3; ++k)
                p += m[4 * k + row] * (float(v.position[k]) / 16);
            out.position[row] += weight * p;
            if (row < 3) {
                float n = 0;
                for (int k = 0; k < 3; ++k)
                    n += m[4 * k + row] * (float(v.normal[k]) / 4096);
                out.normal[row] += weight * n;
            }
        }
    }
    return out;
}
bool valid_character_draw(const CharacterDrawVertex *v, std::size_t count) noexcept {
    if (!v || count < 3 || count > character_index_limit || count % 3)
        return false;
    for (std::size_t i = 0; i < count; ++i) {
        for (float p : v[i].position)
            if (!bounded(p, 4))
                return false;
        if (v[i].position[3] < 4094.0F / 4096 || v[i].position[3] > 1.00001F)
            return false;
        for (float c : {v[i].color.x, v[i].color.y, v[i].color.z})
            if (!bounded(c, 1) || c < 0)
                return false;
        for (float uv : v[i].uv)
            if (!bounded(uv, 8))
                return false;
    }
    return true;
}
bool valid_character_materials(const CharacterMaterials &ranges, std::size_t count) noexcept {
    if (count < 9 || count > character_index_limit || count % 3)
        return false;
    std::size_t next = 0;
    for (std::size_t i = 0; i < ranges.size(); ++i) {
        const auto &r = ranges[i];
        if (r.first != next || r.count < 3 || r.count % 3 || r.count > count - next ||
            r.texture != i)
            return false;
        next += r.count;
    }
    return next == count;
}
bool character_draw(const CharacterModel &m, const SkeletonPose &pose, DeformedVertex *scratch,
                    std::size_t capacity, CharacterDrawVertex *out, std::size_t out_capacity,
                    bool neutral_light) noexcept {
    if (!scratch || !out || capacity < m.vertex_count || out_capacity < m.index_count)
        return false;
    const auto palette = character_palette(m, pose);
    for (std::size_t i = 0; i < m.vertex_count; ++i)
        scratch[i] = deform_character_vertex(m.vertices[i], palette);
    for (std::size_t i = 0; i < m.index_count; ++i) {
        const auto &v = scratch[m.indices[i]];
        const auto &source = m.vertices[m.indices[i]];
        out[i].uv = {float(source.uv[0]) / 4096, float(source.uv[1]) / 4096};
        const auto w = v.position[3];
        // Inspection-only rotation pi around X: Y up, determinant +1; retain W.
        out[i].position = {(v.position[0] - m.center.x * w) * m.scale + camera_target.x * w,
                           -(v.position[1] - m.center.y * w) * m.scale + camera_target.y * w,
                           -(v.position[2] - m.center.z * w) * m.scale + camera_target.z * w, w};
        const auto &n = v.normal;
        if (neutral_light) {
            out[i].color = {1, 1, 1};
            continue;
        }
        const auto length = std::sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
        if (!std::isfinite(length))
            return false;
        // Own two-sided inspection lighting; raw normals in scratch remain unchanged.
        const float diffuse =
            length > 1e-8F ? std::abs((0.3F * n[0] - 0.6F * n[1] - 0.74F * n[2]) / length) : 0;
        const float light = 0.25F + 0.75F * std::min(1.0F, diffuse);
        out[i].color = {0.95F * light, 0.78F * light, 0.52F * light};
    }
    return valid_character_draw(out, m.index_count);
}
} // namespace sh3::domain
