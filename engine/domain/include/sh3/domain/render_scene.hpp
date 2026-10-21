#pragma once

#include <array>

namespace sh3::domain {
struct Vec3 {
    float x, y, z;
};
struct SceneVertex {
    Vec3 position;
    float u, v;
    Vec3 color;
};
using SceneMesh = std::array<SceneVertex, 60>;
[[nodiscard]] SceneMesh synthetic_room() noexcept;
using TexturePanel = std::array<SceneVertex, 6>;
[[nodiscard]] TexturePanel texture_panel() noexcept;
// Own opaque reference behind the planar material sample.
using MaterialBackdrop = std::array<SceneVertex, 96>;
[[nodiscard]] MaterialBackdrop material_backdrop() noexcept;

struct OrbitCamera {
    float yaw{0.35F};
    float elevation{0.35F};
    float distance{7.0F};
};
[[nodiscard]] bool valid_camera(const OrbitCamera &camera) noexcept;
[[nodiscard]] Vec3 camera_eye(const OrbitCamera &camera) noexcept;
inline constexpr Vec3 camera_target{0.0F, 0.75F, -2.0F};
} // namespace sh3::domain
