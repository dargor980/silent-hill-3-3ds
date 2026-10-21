#include "sh3/domain/animation_pose.hpp"
#include <cmath>

namespace sh3::domain {
namespace {
Vec3 add(Vec3 a, Vec3 b) noexcept { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
Vec3 mul(Vec3 a, float k) noexcept { return {a.x * k, a.y * k, a.z * k}; }
Vec3 sub(Vec3 a, Vec3 b) noexcept { return add(a, mul(b, -1)); }
Vec3 cross(Vec3 a, Vec3 b) noexcept {
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
float length(Vec3 a) noexcept { return std::sqrt(a.x * a.x + a.y * a.y + a.z * a.z); }
bool bounded(float v, float limit) noexcept { return std::isfinite(v) && std::abs(v) <= limit; }
PoseMatrix local(const Quaternion &a, const Quaternion &b, Vec3 t, float f) noexcept {
    float dot = 0, norm = 0;
    for (int i = 0; i < 4; ++i)
        dot += a[i] * b[i];
    Quaternion q{};
    for (int i = 0; i < 4; ++i) {
        q[i] = a[i] * (1 - f) + (dot < 0 ? -b[i] : b[i]) * f;
        norm += q[i] * q[i];
    }
    const auto inv = 1 / std::sqrt(norm);
    for (auto &v : q)
        v *= inv;
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
            t.x,
            t.y,
            t.z,
            1};
}
PoseMatrix product(const PoseMatrix &a, const PoseMatrix &b) noexcept {
    PoseMatrix out{};
    for (int c = 0; c < 4; ++c)
        for (int r = 0; r < 4; ++r)
            for (int k = 0; k < 4; ++k)
                out[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
    return out;
}
} // namespace
bool valid_clip(const InspectionClip &clip) noexcept {
    if (clip.parents != std::array<int, 3>{-1, -1, 1} || !bounded(clip.scale, 1) ||
        clip.scale <= 0 || !bounded(clip.center.x, 100000) || !bounded(clip.center.y, 100000) ||
        !bounded(clip.center.z, 100000))
        return false;
    for (const auto &t : clip.translations)
        if (!bounded(t.x, 100000) || !bounded(t.y, 100000) || !bounded(t.z, 100000))
            return false;
    if (length(clip.translations[2]) * clip.scale < 0.001F)
        return false;
    // Conservative sphere bounds include all interpolated rotations, not just keyframes.
    for (int i = 0; i < 2; ++i)
        if ((length(sub(clip.translations[i], clip.center)) +
             (i == 1 ? length(clip.translations[2]) : 0)) *
                clip.scale >
            1.5F)
            return false;
    for (const auto &frame : clip.rotations)
        for (const auto &q : frame) {
            float norm = 0;
            for (float v : q) {
                if (!bounded(v, 1.001F))
                    return false;
                norm += v * v;
            }
            if (std::abs(norm - 1) > 0.001F)
                return false;
        }
    return true;
}
SkeletonPose evaluate_pose(const InspectionClip &clip, std::uint32_t counter) noexcept {
    counter %= clip_period;
    const auto current = counter / 4096, next = (current + 1) % 24;
    const auto fraction = float(counter % 4096) / 4096;
    SkeletonPose pose{};
    for (int i = 0; i < 3; ++i) {
        pose[i] = local(clip.rotations[current][i], clip.rotations[next][i], clip.translations[i],
                        fraction);
        if (clip.parents[i] >= 0)
            pose[i] = product(pose[clip.parents[i]], pose[i]);
    }
    return pose;
}
SkeletonMesh skeleton_mesh(const InspectionClip &clip, const SkeletonPose &pose) noexcept {
    SkeletonMesh mesh{};
    std::size_t index = 0;
    const auto vertex = [&](Vec3 p, Vec3 color) { mesh[index++] = {p, 0, 0, color}; };
    const auto arrow = [&](Vec3 origin, Vec3 tip, Vec3 u, Vec3 v, Vec3 color) {
        const auto a = add(origin, u), b = add(origin, v), c = sub(origin, add(u, v));
        for (auto p : std::array<Vec3, 12>{a, b, tip, b, c, tip, c, a, tip, a, c, b})
            vertex(p, color);
    };
    std::array<Vec3, 3> positions{};
    for (int i = 0; i < 3; ++i) {
        const auto &m = pose[i];
        const auto origin =
            add(mul(sub({m[12], m[13], m[14]}, clip.center), clip.scale), camera_target);
        positions[i] = origin;
        const std::array<Vec3, 3> axes{
            {{m[0], m[1], m[2]}, {m[4], m[5], m[6]}, {m[8], m[9], m[10]}}};
        constexpr std::array<Vec3, 3> colors{{{1, 0.2F, 0.2F}, {0.2F, 1, 0.2F}, {0.3F, 0.5F, 1}}};
        for (int j = 0; j < 3; ++j)
            arrow(origin, add(origin, mul(axes[j], 0.50F)), mul(axes[(j + 1) % 3], 0.07F),
                  mul(axes[(j + 2) % 3], 0.07F), colors[j]);
    }
    const auto delta = sub(positions[2], positions[1]);
    const auto axis = mul(delta, 1 / length(delta));
    const auto normal = cross(axis, std::abs(axis.y) < 0.9F ? Vec3{0, 1, 0} : Vec3{1, 0, 0});
    const auto u = mul(normal, 0.05F / length(normal));
    arrow(positions[1], positions[2], u, cross(axis, u), {0.8F, 0.8F, 0.8F});
    return mesh;
}
} // namespace sh3::domain
