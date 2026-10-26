#include "sh3/domain/inspection_rig.hpp"
#include <algorithm>
#include <cmath>

namespace sh3::domain {
namespace {
bool bounded(float v, float limit = 100000) noexcept {
    return std::isfinite(v) && std::abs(v) <= limit;
}
bool vector_ok(Vec3 v) noexcept { return bounded(v.x) && bounded(v.y) && bounded(v.z); }
PoseMatrix product(const PoseMatrix &a, const PoseMatrix &b) noexcept {
    PoseMatrix out{};
    for (int c = 0; c < 4; ++c)
        for (int r = 0; r < 4; ++r)
            for (int k = 0; k < 4; ++k)
                out[4 * c + r] += a[4 * k + r] * b[4 * c + k];
    return out;
}
PoseMatrix interpolate(const RigSample &a, const RigSample &b, float f) noexcept {
    float dot = 0, norm = 0;
    for (int i = 0; i < 4; ++i)
        dot += a.rotation[i] * b.rotation[i];
    Quaternion q{};
    for (int i = 0; i < 4; ++i) {
        q[i] = a.rotation[i] * (1 - f) + (dot < 0 ? -b.rotation[i] : b.rotation[i]) * f;
        norm += q[i] * q[i];
    }
    for (auto &v : q)
        v /= std::sqrt(norm);
    const auto x = q[0], y = q[1], z = q[2], w = q[3];
    return {1 - 2 * (y * y + z * z),
            2 * (x * y + z * w),
            2 * (x * z - y * w),
            0,
            2 * (x * y - z * w),
            1 - 2 * (x * x + z * z),
            2 * (y * z + x * w),
            0,
            2 * (x * z + y * w),
            2 * (y * z - x * w),
            1 - 2 * (x * x + y * y),
            0,
            a.translation.x * (1 - f) + b.translation.x * f,
            a.translation.y * (1 - f) + b.translation.y * f,
            a.translation.z * (1 - f) + b.translation.z * f,
            1};
}
bool dimension(std::uint32_t v) noexcept { return v == 128 || v == 256 || v == 512 || v == 1024; }
bool draw_vertex_ok(const CharacterDrawVertex &v) noexcept {
    for (auto p : v.position)
        if (!bounded(p, 4))
            return false;
    if (v.position[3] < 4094.0F / 4096 || v.position[3] > 1.00001F)
        return false;
    for (auto c : {v.color.x, v.color.y, v.color.z})
        if (!bounded(c, 1) || c < 0)
            return false;
    for (auto uv : v.uv)
        if (!bounded(uv, 8))
            return false;
    return true;
}
} // namespace
bool valid_rig(const InspectionRig &m) noexcept {
    if (m.bone_count < 1 || m.bone_count > rig_bones || m.sample_count < 2 ||
        m.sample_count > rig_samples || m.helper_count > rig_helpers || m.vertex_count < 3 ||
        m.vertex_count > rig_vertices || m.index_count < 3 || m.index_count > rig_indices ||
        m.index_count % 3 || m.material_count < 1 || m.material_count > rig_materials ||
        !m.clip_id || m.clip_id > 65535 || !m.increment || m.increment > 65535 ||
        m.increment >= m.sample_count * 4096 || !vector_ok(m.center) || !bounded(m.scale, 1) ||
        m.scale <= 0)
        return false;
    for (std::size_t i = 0; i < m.bone_count; ++i) {
        if (m.parents[i] < -1 || m.parents[i] >= static_cast<int>(i))
            return false;
        for (std::size_t f = 0; f < m.sample_count; ++f) {
            const auto &s = m.samples[f][i];
            if (!vector_ok(s.translation))
                return false;
            float norm = 0;
            for (auto v : s.rotation) {
                if (!bounded(v, 1.001F))
                    return false;
                norm += v * v;
            }
            if (std::abs(norm - 1) > 0.001F)
                return false;
        }
    }
    for (std::size_t i = 0; i < m.helper_count; ++i) {
        if (m.targets[i] >= m.bone_count)
            return false;
        const auto &h = m.helpers[i];
        for (auto v : h)
            if (!bounded(v))
                return false;
        if (h[3] != 0 || h[7] != 0 || h[11] != 0 || h[15] != 1)
            return false;
    }
    for (std::size_t i = 0; i < m.vertex_count; ++i) {
        const auto &v = m.vertices[i];
        if (v.primary >= m.bone_count || v.count < 1 || v.count > 3)
            return false;
        unsigned sum = 0;
        for (unsigned j = 0; j < 3; ++j) {
            if (v.weights[j] > 4096 || (j >= v.count && v.weights[j]))
                return false;
            sum += v.weights[j];
        }
        if (sum > 4096 || sum < 4097U - v.count)
            return false;
        for (unsigned j = 0; j < 2; ++j)
            if ((j + 1 < v.count && v.helpers[j] >= m.helper_count) ||
                (j + 1 >= v.count && v.helpers[j] != 255))
                return false;
    }
    for (std::size_t i = 0; i < m.index_count; ++i)
        if (m.indices[i] >= m.vertex_count)
            return false;
    std::uint32_t next = 0, pixels = 0;
    bool blended = false;
    for (std::size_t i = 0; i < m.material_count; ++i) {
        const auto &r = m.materials[i];
        if (r.first != next || r.count < 3 || r.count % 3 || r.count > m.index_count - next ||
            r.texture != i || !dimension(r.width) || !dimension(r.height) || r.blend > 1 ||
            (blended && !r.blend))
            return false;
        next += r.count;
        pixels += r.width * r.height;
        blended = bool(r.blend);
    }
    return next == m.index_count && pixels <= 8 * 1024 * 1024;
}
void evaluate_rig(const InspectionRig &m, std::uint32_t counter, RigPose &out) noexcept {
    counter %= m.sample_count * 4096;
    const auto frame = counter / 4096, next = (frame + 1) % m.sample_count;
    const auto f = float(counter % 4096) / 4096;
    for (std::size_t i = 0; i < m.bone_count; ++i) {
        out[i] = interpolate(m.samples[frame][i], m.samples[next][i], f);
        if (m.parents[i] >= 0)
            out[i] = product(out[m.parents[i]], out[i]);
    }
}
void rig_palette(const InspectionRig &m, const RigPose &pose, RigPalette &out) noexcept {
    std::copy_n(pose.begin(), m.bone_count, out.begin());
    for (std::size_t i = 0; i < m.helper_count; ++i)
        out[rig_bones + i] = product(pose[m.targets[i]], m.helpers[i]);
}
bool valid_rig_draw(const CharacterDrawVertex *v, std::size_t count) noexcept {
    if (!v || count < 3 || count > rig_indices || count % 3)
        return false;
    for (std::size_t i = 0; i < count; ++i)
        if (!draw_vertex_ok(v[i]))
            return false;
    return true;
}
bool rig_draw(const InspectionRig &m, const RigPose &pose, const OrbitCamera &camera,
              RigPalette &palette, RigSortOrder &order, RigVertexScratch *scratch,
              std::size_t capacity, CharacterDrawVertex *out, std::size_t out_capacity) noexcept {
    if (!scratch || !out || capacity < m.vertex_count || out_capacity < m.index_count ||
        !valid_camera(camera))
        return false;
    rig_palette(m, pose, palette);
    for (std::size_t i = 0; i < m.vertex_count; ++i) {
        const auto &v = m.vertices[i];
        auto &d = scratch[i];
        d.position = {};
        const std::array<float, 3> local{float(v.position[0]) / 16,
                                        float(v.position[1]) / 16,
                                        float(v.position[2]) / 16};
        for (unsigned j = 0; j < v.count; ++j) {
            const auto &mat = palette[j == 0 ? v.primary : rig_bones + v.helpers[j - 1]];
            const float weight = float(v.weights[j]) / 4096;
            for (unsigned r = 0; r < 4; ++r) {
                float p = mat[12 + r];
                for (unsigned k = 0; k < 3; ++k)
                    p += mat[4 * k + r] * local[k];
                d.position[r] += weight * p;
            }
        }
        const auto w = d.position[3];
        // Inspection rotation pi about Z: Y up, original outfit facing the camera.
        d.draw = {
            {-(d.position[0] - m.center.x * w) * m.scale + camera_target.x * w,
             -(d.position[1] - m.center.y * w) * m.scale + camera_target.y * w,
             (d.position[2] - m.center.z * w) * m.scale + camera_target.z * w, w},
            {1, 1, 1},
            {float(v.uv[0]) / 4096, float(v.uv[1]) / 4096}};
        if (!draw_vertex_ok(d.draw))
            return false;
    }
    const auto emit = [&](std::size_t dest, std::size_t source) {
        out[dest] = scratch[m.indices[source]].draw;
    };
    // Transparent ranges are sorted individually in inspection camera depth, far to near.
    // The initial Heather profile has exactly one such range (all hair triangles).
    const auto eye = camera_eye(camera);
    const Vec3 forward{camera.target.x - eye.x, camera.target.y - eye.y, camera.target.z - eye.z};
    for (std::size_t r = 0; r < m.material_count; ++r) {
        const auto &range = m.materials[r];
        if (!range.blend) {
            for (std::size_t i = range.first; i < range.first + range.count; ++i)
                emit(i, i);
            continue;
        }
        for (std::size_t t = 0; t < range.count / 3; ++t) {
            float depth = 0;
            for (unsigned j = 0; j < 3; ++j) {
                const auto &p = scratch[m.indices[range.first + t * 3 + j]].draw.position;
                depth += (p[0] * forward.x + p[1] * forward.y + p[2] * forward.z) / p[3];
            }
            order[t] = {depth, static_cast<std::uint32_t>(t)};
        }
        std::sort(order.begin(), order.begin() + range.count / 3, [](auto a, auto b) {
            return a.depth != b.depth ? a.depth > b.depth : a.ordinal < b.ordinal;
        });
        for (std::size_t t = 0; t < range.count / 3; ++t)
            for (unsigned j = 0; j < 3; ++j)
                emit(range.first + t * 3 + j, range.first + order[t].ordinal * 3 + j);
    }
    return true;
}
} // namespace sh3::domain
