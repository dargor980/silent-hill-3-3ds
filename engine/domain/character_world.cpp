#include "sh3/domain/character_world.hpp"
#include <cmath>

namespace sh3::domain {
namespace {
bool bounded(float x, float limit) noexcept { return std::isfinite(x) && std::abs(x) <= limit; }
bool rigid(const PoseMatrix &m) noexcept {
    for (float x : m)
        if (!bounded(x, 1000000))
            return false;
    if (m[3] != 0 || m[7] != 0 || m[11] != 0 || m[15] != 1)
        return false;
    for (int c = 0; c < 3; ++c)
        for (int d = c; d < 3; ++d) {
            double dot = 0;
            for (int r = 0; r < 3; ++r)
                dot += double(m[c * 4 + r]) * m[d * 4 + r];
            if (std::abs(dot - (c == d ? 1.0 : 0.0)) > .002)
                return false;
        }
    const double det = double(m[0]) * (double(m[5]) * m[10] - double(m[9]) * m[6]) -
                       double(m[4]) * (double(m[1]) * m[10] - double(m[9]) * m[2]) +
                       double(m[8]) * (double(m[1]) * m[6] - double(m[5]) * m[2]);
    return std::abs(det - 1) <= .002;
}
} // namespace
bool valid_character_world(const CharacterWorld &w, const CharacterModel &m) noexcept {
    if (!valid_character(m) || w.reference_counter >= clip_period || !bounded(w.scale, 1) ||
        w.scale <= 0 || !bounded(w.origin.x, 1000000) || !bounded(w.origin.y, 1000000) ||
        !bounded(w.origin.z, 1000000))
        return false;
    const std::array<float, 3> center{m.center.x, m.center.y, m.center.z};
    const std::array<float, 3> origin{w.origin.x, w.origin.y, w.origin.z};
    for (std::size_t i = 0; i < w.instances.size(); ++i) {
        const auto &instance = w.instances[i];
        if (!instance.id || instance.id > 65535 || !rigid(instance.model))
            return false;
        for (std::size_t j = 0; j < i; ++j)
            if (w.instances[j].id == instance.id)
                return false;
        double distance2 = 0;
        for (int r = 0; r < 3; ++r) {
            double value = double(instance.model[12 + r]) - origin[r];
            for (int c = 0; c < 3; ++c)
                value += double(instance.model[4 * c + r]) * center[c];
            distance2 += value * value;
        }
        // Slightly inflate radius for the allowed orthonormal quantization error.
        if ((std::sqrt(distance2) + 1.004 * 1.4 / double(m.scale)) * w.scale > 1.401)
            return false;
    }
    return true;
}
WorldPosition rebase_character_position(const CharacterInstance &instance, Vec3 origin,
                                        const WorldPosition &p) noexcept {
    const std::array<float, 3> o{origin.x, origin.y, origin.z};
    WorldPosition result{0, 0, 0, p[3]};
    for (int r = 0; r < 3; ++r) {
        result[r] = (instance.model[12 + r] - o[r]) * p[3];
        for (int c = 0; c < 3; ++c)
            result[r] += instance.model[4 * c + r] * p[c];
    }
    return result;
}
bool place_character(const CharacterWorld &w, const CharacterModel &m,
                     const DeformedVertex *vertices, std::size_t count, WorldPosition *scratch,
                     std::size_t capacity, CharacterDrawVertex *out,
                     std::size_t out_capacity) noexcept {
    if (!vertices || !scratch || !out || count < m.vertex_count || capacity < m.vertex_count ||
        out_capacity < m.index_count * character_instance_limit)
        return false;
    for (std::size_t instance = 0; instance < character_instance_limit; ++instance) {
        for (std::size_t i = 0; i < m.vertex_count; ++i) {
            const auto p =
                rebase_character_position(w.instances[instance], w.origin, vertices[i].position);
            const auto weight = p[3];
            scratch[i] = {p[0] * w.scale + camera_target.x * weight,
                          -p[1] * w.scale + camera_target.y * weight,
                          -p[2] * w.scale + camera_target.z * weight, weight};
        }
        auto *block = out + instance * m.index_count;
        for (std::size_t i = 0; i < m.index_count; ++i) {
            const auto index = m.indices[i];
            block[i].position = scratch[index];
            block[i].color = {1, 1, 1};
            block[i].uv = {float(m.vertices[index].uv[0]) / 4096,
                           float(m.vertices[index].uv[1]) / 4096};
        }
        if (!valid_character_draw(block, m.index_count))
            return false;
    }
    return true;
}
} // namespace sh3::domain
