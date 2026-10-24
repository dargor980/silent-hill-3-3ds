#include "sh3/domain/render_scene.hpp"
#include <cmath>
#include <cstddef>

namespace sh3::domain {
MaterialBackdrop material_backdrop() noexcept {
    MaterialBackdrop mesh{};
    std::size_t offset = 0;
    for (int y = 0; y < 4; ++y) {
        for (int x = 0; x < 4; ++x) {
            const float left = -2.2F + x * 1.1F, bottom = -1.45F + y * 1.1F;
            const Vec3 color = (x + y) % 2 ? Vec3{0.85F, 0.85F, 0.85F} : Vec3{0.12F, 0.22F, 0.32F};
            const SceneVertex a{{left, bottom, -2.3F}, 0, 0, color};
            const SceneVertex b{{left + 1.1F, bottom, -2.3F}, 0, 0, color};
            const SceneVertex c{{left + 1.1F, bottom + 1.1F, -2.3F}, 0, 0, color};
            const SceneVertex d{{left, bottom + 1.1F, -2.3F}, 0, 0, color};
            for (const auto &v : {a, b, c, a, c, d})
                mesh[offset++] = v;
        }
    }
    return mesh;
}
TexturePanel texture_panel() noexcept {
    constexpr Vec3 white{1, 1, 1};
    constexpr SceneVertex a{{-2, -1.25F, -2}, 0, 0, white};
    constexpr SceneVertex b{{2, -1.25F, -2}, 1, 0, white};
    constexpr SceneVertex c{{2, 2.75F, -2}, 1, 1, white};
    constexpr SceneVertex d{{-2, 2.75F, -2}, 0, 1, white};
    return {a, b, c, a, c, d};
}
SceneMesh synthetic_room() noexcept {
    SceneMesh mesh{};
    std::size_t offset = 0;
    const auto quad = [&](Vec3 a, Vec3 b, Vec3 c, Vec3 d, Vec3 color, float repeat) {
        mesh[offset++] = {a, 0, 0, color};
        mesh[offset++] = {b, repeat, 0, color};
        mesh[offset++] = {c, repeat, repeat, color};
        mesh[offset++] = {a, 0, 0, color};
        mesh[offset++] = {c, repeat, repeat, color};
        mesh[offset++] = {d, 0, repeat, color};
    };
    // Submit the cube first: the later floor/walls must not overwrite nearer fragments.
    constexpr Vec3 a{-0.75F, 0, -1.25F}, b{0.75F, 0, -1.25F};
    constexpr Vec3 c{0.75F, 1.5F, -1.25F}, d{-0.75F, 1.5F, -1.25F};
    constexpr Vec3 e{-0.75F, 0, -2.75F}, f{0.75F, 0, -2.75F};
    constexpr Vec3 g{0.75F, 1.5F, -2.75F}, h{-0.75F, 1.5F, -2.75F};
    quad(a, b, c, d, {1.0F, 0.72F, 0.25F}, 1);
    quad(f, e, h, g, {0.8F, 0.4F, 0.15F}, 1);
    quad(e, a, d, h, {0.7F, 0.4F, 0.2F}, 1);
    quad(b, f, g, c, {0.9F, 0.55F, 0.2F}, 1);
    quad(d, c, g, h, {1.0F, 0.9F, 0.5F}, 1);
    quad(e, f, b, a, {0.5F, 0.3F, 0.15F}, 1);
    quad({-3, 0, 2}, {3, 0, 2}, {3, 0, -5}, {-3, 0, -5}, {0.6F, 0.65F, 0.7F}, 6);
    quad({-3, 0, -5}, {3, 0, -5}, {3, 3, -5}, {-3, 3, -5}, {0.3F, 0.7F, 0.7F}, 3);
    quad({-3, 0, 2}, {-3, 0, -5}, {-3, 3, -5}, {-3, 3, 2}, {0.25F, 0.5F, 0.65F}, 3);
    quad({3, 0, -5}, {3, 0, 2}, {3, 3, 2}, {3, 3, -5}, {0.25F, 0.6F, 0.5F}, 3);
    return mesh;
}

bool valid_camera(const OrbitCamera &camera) noexcept {
    return std::isfinite(camera.yaw) && std::isfinite(camera.elevation) &&
           std::isfinite(camera.distance) && camera.yaw >= -0.55F && camera.yaw <= 0.55F &&
           camera.elevation >= 0.1F && camera.elevation <= 0.8F && camera.distance >= 0.45F &&
           camera.distance <= 9.0F && std::isfinite(camera.target.x) &&
           std::isfinite(camera.target.y) && std::isfinite(camera.target.z) &&
           std::abs(camera.target.x) <= 10 && std::abs(camera.target.y) <= 10 &&
           std::abs(camera.target.z) <= 10;
}
Vec3 camera_eye(const OrbitCamera &camera) noexcept {
    const float horizontal = camera.distance * std::cos(camera.elevation);
    return {camera.target.x + horizontal * std::sin(camera.yaw),
            camera.target.y + camera.distance * std::sin(camera.elevation),
            camera.target.z + horizontal * std::cos(camera.yaw)};
}
} // namespace sh3::domain
