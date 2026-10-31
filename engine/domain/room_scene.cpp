#include "sh3/domain/room_scene.hpp"
#include "sh3/domain/inspection_locomotion.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::domain {
namespace {
bool bounded(float x, float limit) noexcept { return std::isfinite(x) && std::abs(x) <= limit; }
bool affine(const PoseMatrix &m) noexcept {
    for (auto x : m)
        if (!bounded(x, 1000000))
            return false;
    return m[3] == 0 && m[7] == 0 && m[11] == 0 && m[15] == 1;
}
bool instance_ok(const PoseMatrix &m) noexcept {
    if (!affine(m))
        return false;
    for (unsigned a = 0; a < 3; ++a)
        for (unsigned b = a; b < 3; ++b) {
            double dot = 0;
            for (unsigned r = 0; r < 3; ++r)
                dot += double(m[4 * a + r]) * m[4 * b + r];
            if (std::abs(dot - (a == b ? 1 : 0)) > .0001)
                return false;
        }
    const double det = double(m[0]) * (double(m[5]) * m[10] - double(m[6]) * m[9]) -
                       double(m[4]) * (double(m[1]) * m[10] - double(m[2]) * m[9]) +
                       double(m[8]) * (double(m[1]) * m[6] - double(m[2]) * m[5]);
    return det > .9999;
}
double depth(const CharacterDrawVertex &v) noexcept {
    const auto c = room_camera();
    const auto &p = v.position;
    return (double(p[0]) * (c.target.x - c.eye.x) + double(p[1]) * (c.target.y - c.eye.y) +
            double(p[2]) * (c.target.z - c.eye.z)) /
           p[3];
}
} // namespace
std::array<float, 4> room_position(const PoseMatrix &m, const std::array<float, 4> &p) noexcept {
    const float origin[3]{room_origin.x, room_origin.y, room_origin.z};
    std::array<float, 4> result{0, 0, 0, p[3]};
    for (unsigned r = 0; r < 3; ++r) {
        double v = (double(m[12 + r]) - origin[r]) * p[3];
        for (unsigned c = 0; c < 3; ++c)
            v += double(m[4 * c + r]) * p[c];
        result[r] = static_cast<float>(v * double(room_scale) * (r == 0 ? 1 : -1));
    }
    return result;
}
RoomCamera room_camera() noexcept {
    return {{275 * room_scale, 1000 * room_scale, 700 * room_scale},
            {275 * room_scale, 300 * room_scale, -100 * room_scale},
            80,
            .02F,
            12};
}
bool valid_room_vertex(const CharacterDrawVertex &v) noexcept {
    for (auto x : v.position)
        if (!bounded(x, 4096))
            return false;
    if (v.position[3] < 4094.0F / 4096 || v.position[3] > 1.00001F)
        return false;
    for (auto x : {v.color.x, v.color.y, v.color.z})
        if (!bounded(x, 1) || x < 0)
            return false;
    for (auto x : v.uv)
        if (!bounded(x, 8))
            return false;
    return true;
}
bool valid_room_map(const RoomMap &m) noexcept {
    if (!m.shape_count || m.shape_count > room_shapes || !m.vertex_count ||
        m.vertex_count > room_vertices || m.vertex_count % 3 ||
        (m.material_count != 0 && m.material_count != room_materials))
        return false;
    for (unsigned i = 0; i < m.material_count; ++i) {
        const auto &t = m.materials[i];
        if (t.width != 512 || t.height != 512 || !room_map_pass(t.pass))
            return false;
    }
    std::uint32_t next = 0, glass = 0;
    for (unsigned i = 0; i < m.shape_count; ++i) {
        const auto &s = m.shapes[i];
        if (!s.offset || s.first != next || !s.count || s.count % 3 ||
            s.count > m.vertex_count - next || s.glass > 1 || s.visible > 1 ||
            ((s.glass || !m.material_count) && (s.material || !s.visible)) ||
            (m.material_count && s.material >= m.material_count))
            return false;
        for (unsigned j = 0; j < i; ++j)
            if (m.shapes[j].offset == s.offset)
                return false;
        next += s.count;
        if (s.glass)
            glass += s.count;
    }
    if (next != m.vertex_count || glass > room_glass_vertices)
        return false;
    for (unsigned i = 0; i < m.vertex_count; ++i)
        if (!valid_room_vertex(m.vertices[i]) || m.vertices[i].position[3] != 1)
            return false;
    return true;
}
void room_diagnostic_colors(const RoomMap &map, CharacterDrawVertex *vertices) noexcept {
    if (map.material_count)
        return;
    constexpr Vec3 palette[]{{.68F, .78F, .88F}, {.80F, .61F, .38F}, {.42F, .74F, .66F},
                             {.76F, .47F, .48F}, {.61F, .54F, .79F}, {.70F, .73F, .44F}};
    for (unsigned i = 0; i < map.shape_count; ++i) {
        const auto &shape = map.shapes[i];
        if (shape.glass)
            continue;
        const auto base = palette[i % std::size(palette)];
        for (unsigned j = shape.first; j < shape.first + shape.count; j += 3) {
            std::array<double, 3> a{}, b{};
            for (unsigned axis = 0; axis < 3; ++axis) {
                a[axis] =
                    double(map.vertices[j + 1].position[axis]) - map.vertices[j].position[axis];
                b[axis] =
                    double(map.vertices[j + 2].position[axis]) - map.vertices[j].position[axis];
            }
            const double x = a[1] * b[2] - a[2] * b[1], y = a[2] * b[0] - a[0] * b[2],
                         z = a[0] * b[1] - a[1] * b[0], length2 = x * x + y * y + z * z;
            // Fixed unit light (-.48, .8, .36), two-sided because MAP winding is
            // not a visibility contract. Degenerate triangles keep a finite tint.
            const float light =
                length2 > 1e-24
                    ? float(.32 + .68 * std::min(1.0, std::abs(-.48 * x + .8 * y + .36 * z) /
                                                          std::sqrt(length2)))
                    : .65F;
            for (unsigned k = 0; k < 3; ++k)
                vertices[j + k].color = {base.x * light, base.y * light, base.z * light};
        }
    }
}
bool room_memory(const InspectionRig &m, RoomMemory &out) noexcept {
    if (rig_payload_error(m))
        return false;
    RoomMemory v{};
    v.textures = 256 * 256 * 4; // normalized glass palette 0, no unused MAP variants.
    for (unsigned i = 0; i < m.material_count; ++i) {
        const auto &t = m.materials[i];
        const std::size_t bytes = std::size_t(t.width) * std::size_t(t.height) * 4;
        v.textures += bytes;
        v.texture_staging = std::max(v.texture_staging, bytes);
    }
    v.texture_staging = std::max(v.texture_staging, std::size_t(256 * 256 * 4));
    v.map_resident = sizeof(RoomMap) + room_vertices * sizeof(CharacterDrawVertex);
    v.dynamic_resident = sizeof(RoomFrame) + room_dynamic_vertices * sizeof(CharacterDrawVertex);
    v.model_and_scratch = sizeof(InspectionLocomotion) + sizeof(RoomWorkspace) + 32768 + 4096;
    // Concurrent replacement input+candidate for MAP, and SRI2 reader staging.
    v.loader_staging = sizeof(RoomMap) + 32 + room_shapes * 24 + room_materials * 16 +
                       room_vertices * 36 + 2 * sizeof(InspectionLocomotion);
    // Command buffer, shaders, targets, double display buffers, code/BSS and SDK/heap margin.
    v.platform_reserve = 12 * 1024 * 1024;
    v.total = v.textures + v.texture_staging + v.map_resident + v.dynamic_resident +
              v.model_and_scratch + v.loader_staging + v.platform_reserve;
    if (v.textures > 32 * 1024 * 1024 || v.texture_staging > 2 * 1024 * 1024 ||
        v.map_resident > 2 * 1024 * 1024 || v.total > 64 * 1024 * 1024)
        return false;
    out = v;
    return true;
}
bool room_memory(const RoomMap &map, const InspectionRig &rig, RoomMemory &out) noexcept {
    RoomMemory v;
    if (!valid_room_map(map) || !room_memory(rig, v))
        return false;
    const auto bytes = map.material_count * std::size_t(512 * 512 * 4);
    const auto staging = map.material_count
                             ? std::max(v.texture_staging, std::size_t(512 * 512 * 4))
                             : v.texture_staging;
    v.total += bytes + staging - v.texture_staging;
    v.textures += bytes;
    v.texture_staging = staging;
    if (v.textures > 32 * 1024 * 1024 || v.total > 64 * 1024 * 1024)
        return false;
    out = v;
    return true;
}
bool room_frame(const RoomMap &map, const InspectionRig &m, const RigPose &pose,
                const PoseMatrix &instance, RoomWorkspace &work, RoomFrame &out) noexcept {
    return PreparedRoomScene(map, m).frame(pose, instance, work, out);
}
PreparedRoomScene::PreparedRoomScene(const RoomMap &map, const InspectionRig &model) noexcept
    : map_(map), model_(model), ready_(valid_room_map(map) && room_memory(map, model, memory_)) {}
bool PreparedRoomScene::frame(const RigPose &pose, const PoseMatrix &instance, RoomWorkspace &work,
                              RoomFrame &out, WorkTrace *trace) const noexcept {
    WorkInterval interval(trace, WorkPhase::validation);
    if (!ready_ || !instance_ok(instance))
        return false;
    const auto &map = map_;
    const auto &m = model_;
    for (unsigned i = 0; i < m.bone_count; ++i)
        if (!affine(pose[i]))
            return false;
    interval.next(WorkPhase::palette);
    rig_palette(m, pose, work.palette);
    interval.next(WorkPhase::deform_cpu);
    for (unsigned i = 0; i < m.vertex_count; ++i) {
        const auto &v = m.vertices[i];
        auto &d = work.vertices[i];
        d.position = {};
        for (unsigned j = 0; j < v.count; ++j) {
            const auto &mat = work.palette[j == 0 ? v.primary : rig_bones + v.helpers[j - 1]];
            for (unsigned r = 0; r < 4; ++r) {
                float p = mat[12 + r];
                for (unsigned k = 0; k < 3; ++k)
                    p += mat[4 * k + r] * (float(v.position[k]) / 16);
                d.position[r] += (float(v.weights[j]) / 4096) * p;
            }
        }
        d.draw = {room_position(instance, d.position),
                  {1, 1, 1},
                  {float(v.uv[0]) / 4096, float(v.uv[1]) / 4096}};
        if (!valid_room_vertex(d.draw))
            return false;
    }
    interval.next(WorkPhase::sort_expand);
    std::size_t n = 0;
    for (unsigned i = 0; i < map.shape_count; ++i) {
        const auto &s = map.shapes[i];
        if (s.glass)
            for (unsigned j = s.first; j < s.first + s.count; j += 3)
                work.order[n++] = {depth(map.vertices[j]) + depth(map.vertices[j + 1]) +
                                       depth(map.vertices[j + 2]),
                                   j, m.material_count};
    }
    for (unsigned r = 0; r < m.material_count; ++r) {
        const auto &s = m.materials[r];
        if (s.blend)
            for (unsigned j = s.first; j < s.first + s.count; j += 3)
                work.order[n++] = {depth(work.vertices[m.indices[j]].draw) +
                                       depth(work.vertices[m.indices[j + 1]].draw) +
                                       depth(work.vertices[m.indices[j + 2]].draw),
                                   j, r};
    }
    // Total order handles equal depths reproducibly across host/ARM. No stable_sort heap.
    std::sort(work.order.begin(), work.order.begin() + n, [](const auto &a, const auto &b) {
        if (a.depth != b.depth)
            return a.depth > b.depth;
        return a.material != b.material ? a.material < b.material : a.first < b.first;
    });
    // All rejection checks precede writes to the published frame.
    out.vertex_count = out.range_count = 0;
    for (unsigned i = 0; i < map.shape_count; ++i) {
        const auto &s = map.shapes[i];
        if (!s.glass && s.visible)
            out.ranges[out.range_count++] = {
                map.material_count ? map.materials[s.material].pass : RoomPass::neutral, s.first,
                s.count, map.material_count ? m.material_count + 1 + s.material : 0};
    }
    for (unsigned r = 0; r < m.material_count; ++r) {
        const auto &s = m.materials[r];
        if (!s.blend) {
            out.ranges[out.range_count++] = {RoomPass::opaque, out.vertex_count, s.count, r};
            for (unsigned j = s.first; j < s.first + s.count; ++j)
                out.vertices[out.vertex_count++] = work.vertices[m.indices[j]].draw;
        }
    }
    for (std::size_t t = 0; t < n; ++t) {
        const auto &triangle = work.order[t];
        const bool glass = triangle.material == m.material_count;
        const auto pass = glass ? RoomPass::glass : RoomPass::hair;
        if (out.range_count && out.ranges[out.range_count - 1].pass == pass &&
            out.ranges[out.range_count - 1].texture == triangle.material)
            out.ranges[out.range_count - 1].count += 3;
        else
            out.ranges[out.range_count++] = {pass, out.vertex_count, 3, triangle.material};
        for (unsigned j = 0; j < 3; ++j)
            out.vertices[out.vertex_count++] =
                glass ? map.vertices[triangle.first + j]
                      : work.vertices[m.indices[triangle.first + j]].draw;
    }
    return true;
}
} // namespace sh3::domain
