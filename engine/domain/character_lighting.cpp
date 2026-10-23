#include "sh3/domain/character_lighting.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::domain {
namespace {
template <std::size_t N>
bool bounded(const std::array<float, N> &v, float low, float high) noexcept {
    for (float x : v)
        if (!std::isfinite(x) || x < low || x > high)
            return false;
    return true;
}
float dot(const LightVector &a, const LightVector &b) noexcept {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
float saturate(float x) noexcept { return std::clamp(x, 0.0F, 1.0F); }
} // namespace
bool valid_character_lighting(const CharacterLighting &l, const CharacterModel &m) noexcept {
    if (!valid_character(m) || l.reference_counter >= clip_period ||
        !bounded(l.model_to_capture, -100000, 100000) || !bounded(l.ambient, 0, 255) ||
        !bounded(l.spot.position, -100000, 100000) || !bounded(l.spot.direction, -16, 16) ||
        !bounded(l.spot.color, 0, 16) || !bounded(l.spot.attenuation, -1000000, 1000000))
        return false;
    for (unsigned i = 0; i < 3; ++i)
        if (l.ambient[i] > 16)
            return false;
    const auto &t = l.model_to_capture;
    if (t[3] != 0 || t[7] != 0 || t[11] != 0 || t[15] != 1)
        return false;
    for (unsigned c = 0; c < 3; ++c)
        for (unsigned d = 0; d < 3; ++d) {
            float product = 0;
            for (unsigned r = 0; r < 3; ++r)
                product += t[c * 4 + r] * t[d * 4 + r];
            if (std::abs(product - (c == d ? 1.0F : 0.0F)) > 0.002F)
                return false;
        }
    const auto determinant = t[0] * (t[5] * t[10] - t[9] * t[6]) -
                             t[4] * (t[1] * t[10] - t[9] * t[2]) +
                             t[8] * (t[1] * t[6] - t[5] * t[2]);
    if (std::abs(determinant - 1) > 0.002F)
        return false;
    for (const auto &d : l.directionals)
        if (!bounded(d.direction, -16, 16) || !bounded(d.color, 0, 16))
            return false;
    std::size_t nv = 0, ni = 0;
    for (const auto &r : l.ranges) {
        if (r.first_vertex != nv || r.first_index != ni || r.vertex_count < 3 ||
            r.index_count < 3 || r.index_count % 3 || r.vertex_count > m.vertex_count - nv ||
            r.index_count > m.index_count - ni || !bounded(r.diffuse, 0, 128) ||
            !bounded(r.ambient, 0, 128))
            return false;
        for (std::size_t i = ni; i < ni + r.index_count; ++i)
            if (m.indices[i] < nv || m.indices[i] >= nv + r.vertex_count)
                return false;
        nv += r.vertex_count;
        ni += r.index_count;
    }
    return nv == m.vertex_count && ni == m.index_count;
}
bool shade_character_vertex(const CharacterLighting &l, const CharacterLightRange &material,
                            const DeformedVertex &v, LightColor &out) noexcept {
    LightVector p{}, n{};
    const auto &m = l.model_to_capture;
    for (unsigned row = 0; row < 3; ++row) {
        p[row] = m[12 + row] * v.position[3];
        for (unsigned k = 0; k < 3; ++k) {
            p[row] += m[4 * k + row] * v.position[k];
            n[row] += m[4 * k + row] * v.normal[k];
        }
    }
    if (!bounded(p, -1000000, 1000000) || !bounded(n, -1000, 1000))
        return false;
    LightVector delta{};
    for (unsigned k = 0; k < 3; ++k)
        delta[k] = p[k] - l.spot.position[k];
    const float distance = std::sqrt(dot(delta, delta));
    if (!std::isfinite(distance) || distance <= 0)
        return false;
    for (float &x : delta)
        x /= distance;
    const auto &a = l.spot.attenuation;
    const float radial = a[0] / distance + a[1], cone = a[2] * dot(l.spot.direction, delta) + a[3];
    if (!std::isfinite(radial) || !std::isfinite(cone))
        return false;
    const float intensity = saturate(dot(n, delta)) * saturate(radial) * saturate(cone);
    LightColor accumulated{};
    for (unsigned k = 0; k < 4; ++k)
        accumulated[k] = l.spot.color[k] * intensity;
    for (const auto &d : l.directionals) {
        const float lambert = std::max(0.0F, dot(d.direction, n));
        for (unsigned k = 0; k < 4; ++k)
            accumulated[k] += d.color[k] * lambert;
    }
    LightColor result{};
    for (unsigned k = 0; k < 4; ++k)
        result[k] = (k < 3 ? material.ambient[k] : 1) * l.ambient[k] +
                    (k < 3 ? material.diffuse[k] : 1) * accumulated[k];
    // Inputs validated at load; this also detects non-finite intermediate output.
    for (float value : result)
        if (!std::isfinite(value))
            return false;
    out = result;
    return true;
}
bool light_character(const CharacterLighting &l, const CharacterModel &m,
                     const DeformedVertex *vertices, std::size_t nv, LightVector *colors,
                     std::size_t nc, CharacterDrawVertex *draw, std::size_t nd) noexcept {
    if (!vertices || !colors || !draw || nv < m.vertex_count || nc < m.vertex_count ||
        nd < m.index_count)
        return false;
    for (const auto &range : l.ranges) {
        for (std::size_t j = range.first_vertex; j < range.first_vertex + range.vertex_count; ++j) {
            LightColor c{};
            if (!shade_character_vertex(l, range, vertices[j], c))
                return false;
            for (unsigned k = 0; k < 3; ++k)
                colors[j][k] = std::trunc(std::clamp(c[k], 0.0F, 128.0F)) / 128;
        }
    }
    for (std::size_t j = 0; j < m.index_count; ++j) {
        const auto &c = colors[m.indices[j]];
        draw[j].color = {c[0], c[1], c[2]};
    }
    return valid_character_draw(draw, m.index_count);
}
} // namespace sh3::domain
