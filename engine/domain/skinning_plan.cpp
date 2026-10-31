#include "sh3/domain/skinning_plan.hpp"
#include <algorithm>
#include <cmath>
#include <limits>

namespace sh3::domain {
namespace {
std::uint16_t slot(const CharacterVertex &v, unsigned j) noexcept {
    return j ? std::uint16_t(rig_bones + v.helpers[j - 1]) : v.primary;
}
bool traverse(const InspectionRig &m, SkinPlanWorkspace &w, const SkinStorage *s, SkinCounts &n,
              std::size_t capacity) noexcept {
    for (unsigned material = 0; material < m.material_count; ++material) {
        const auto &range = m.materials[material];
        if (range.blend)
            continue;
        auto first = range.first;
        while (first < range.first + range.count) {
            auto &used = w.used;
            used.fill(false);
            unsigned count = 0, end = first;
            while (end < range.first + range.count) {
                auto &next = w.next;
                next = used;
                unsigned size = count;
                for (unsigned k = 0; k < 3; ++k) {
                    const auto &v = m.vertices[m.indices[end + k]];
                    for (unsigned j = 0; j < v.count; ++j) {
                        const auto id = slot(v, j);
                        if (!next[id]) {
                            next[id] = true;
                            ++size;
                        }
                    }
                }
                if (size > capacity)
                    break; // A valid SRI triangle uses at most nine identities.
                used = next;
                count = size;
                end += 3;
            }
            if (end == first)
                return false;
            auto &batch = w.batch;
            batch = {std::uint32_t(n.indices), end - first, material, count, {}};
            unsigned local = 0;
            for (unsigned id = 0; id < used.size(); ++id)
                if (used[id])
                    batch.slots[local++] = std::uint16_t(id);
            w.remap.fill(std::numeric_limits<std::uint16_t>::max());
            for (unsigned i = first; i < end; ++i) {
                const auto original = m.indices[i];
                auto &mapped = w.remap[original];
                if (mapped == std::numeric_limits<std::uint16_t>::max()) {
                    mapped = std::uint16_t(n.vertices++);
                    if (s)
                        (void)skin_vertex(m.vertices[original], batch.slots.data(), count,
                                          s->vertices[mapped]);
                }
                if (s)
                    s->indices[n.indices] = mapped;
                ++n.indices;
            }
            if (s)
                s->batches[n.batches] = batch;
            ++n.batches;
            first = end;
        }
    }
    return true;
}
} // namespace
std::size_t SkinCounts::bytes() const noexcept {
    return vertices * sizeof(SkinVertex) + indices * sizeof(std::uint16_t) +
           batches * sizeof(SkinBatch);
}
bool skin_plan(const InspectionRig &m, SkinPlanWorkspace &w, SkinCounts &out,
               const SkinStorage *storage, std::size_t capacity) noexcept {
    if (!capacity || capacity > skinning_capacity || rig_payload_error(m))
        return false;
    SkinCounts n{};
    if (!traverse(m, w, nullptr, n, capacity))
        return false;
    if (storage) {
        const auto &s = *storage;
        if (s.capacity.vertices < n.vertices || s.capacity.indices < n.indices ||
            s.capacity.batches < n.batches || (n.vertices && !s.vertices) ||
            (n.indices && !s.indices) || (n.batches && !s.batches))
            return false;
        SkinCounts written{};
        (void)traverse(m, w, &s, written, capacity);
    }
    out = n;
    return true;
}
bool skin_vertex(const CharacterVertex &v, const std::uint16_t *slots, std::size_t n,
                 SkinVertex &out) noexcept {
    if (!slots || !n || n > skinning_capacity || v.count < 1 || v.count > 3)
        return false;
    for (std::size_t i = 0; i < n; ++i)
        if (slots[i] >= rig_bones + rig_helpers || (i && slots[i - 1] >= slots[i]))
            return false;
    SkinVertex p{};
    p.position = {float(v.position[0]) / 16, float(v.position[1]) / 16, float(v.position[2]) / 16,
                  1};
    p.uv = {float(v.uv[0]) / 4096, float(v.uv[1]) / 4096, 0, 1};
    unsigned sum = 0;
    for (unsigned j = 0; j < 3; ++j) {
        if (v.weights[j] > 4096 || (j >= v.count && v.weights[j]))
            return false;
        sum += v.weights[j];
        p.weights[j] = float(v.weights[j]) / 4096;
        if (j < v.count) {
            const auto id = slot(v, j);
            const auto *it = std::lower_bound(slots, slots + n, id);
            if (it == slots + n || *it != id)
                return false;
            p.rows[j] = float(3 * (it - slots));
        }
    }
    if (sum < 4097U - v.count || sum > 4096)
        return false;
    p.weights[3] = float(sum) / 4096;
    out = p;
    return true;
}
bool skin_rows(const RigPalette &palette, const PoseMatrix &instance, SkinRows &scratch,
               SkinRows &out) noexcept {
    const float origin[]{room_origin.x, room_origin.y, room_origin.z};
    for (std::size_t id = 0; id < palette.size(); ++id)
        for (unsigned r = 0; r < 3; ++r)
            for (unsigned c = 0; c < 4; ++c) {
                double v = c == 3 ? double(instance[12 + r]) - origin[r] : 0;
                for (unsigned k = 0; k < 3; ++k)
                    v += double(instance[4 * k + r]) * palette[id][4 * c + k];
                const auto value = float(v * double(room_scale) * (r == 0 ? 1 : -1));
                if (!std::isfinite(value))
                    return false;
                scratch[id][r][c] = value;
            }
    out = scratch;
    return true;
}
} // namespace sh3::domain
