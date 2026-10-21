#include "check.hpp"
#include "sh3/application/render_probe.hpp"
#include "sh3/platform/checker_texture.hpp"
#include <array>
#include <cmath>
#include <limits>

namespace {
using namespace sh3;
class Renderer final : public ports::IRenderScene {
  public:
    ports::RenderResult present(const domain::OrbitCamera &camera) noexcept override {
        CHECK(domain::valid_camera(camera));
        last = camera;
        ++calls;
        return response;
    }
    domain::OrbitCamera last;
    unsigned calls{0};
    ports::RenderResult response{ports::RenderResult::presented};
};
bool same(const domain::OrbitCamera &a, const domain::OrbitCamera &b) {
    return a.yaw == b.yaw && a.elevation == b.elevation && a.distance == b.distance;
}
void camera() {
    const domain::OrbitCamera initial;
    CHECK(domain::valid_camera(initial));
    const auto eye = domain::camera_eye(initial);
    CHECK(eye.x > 0 && eye.y > 0 && eye.z > 0);
    const auto dx = eye.x - domain::camera_target.x;
    const auto dy = eye.y - domain::camera_target.y;
    const auto dz = eye.z - domain::camera_target.z;
    CHECK(std::abs(std::sqrt(dx * dx + dy * dy + dz * dz) - initial.distance) < 0.0001F);
    for (auto member : {&domain::OrbitCamera::yaw, &domain::OrbitCamera::elevation,
                        &domain::OrbitCamera::distance}) {
        for (const float invalid :
             {std::numeric_limits<float>::quiet_NaN(), std::numeric_limits<float>::infinity(),
              -std::numeric_limits<float>::infinity(), -10.0F, 10.0F}) {
            auto value = initial;
            value.*member = invalid;
            CHECK(!domain::valid_camera(value));
        }
    }
    Renderer renderer;
    application::RenderProbe app(renderer);
    app.step({1, 1, -1}, 100);
    CHECK(std::abs(app.camera().yaw - (initial.yaw + 0.1F)) < 0.0001F);
    CHECK(std::abs(app.camera().distance - 6.7F) < 0.0001F);
    for (int i = 0; i < 100; ++i) {
        app.step({100, 100, -100}, 1);
    }
    CHECK(app.camera().yaw == 0.55F && app.camera().elevation == 0.8F &&
          app.camera().distance == 3);
    for (int i = 0; i < 100; ++i) {
        app.step({-100, -100, 100}, 1);
    }
    CHECK(app.camera().yaw == -0.55F && app.camera().elevation == 0.1F &&
          app.camera().distance == 9);
    app.step({1, 1, 1, true}, 1);
    CHECK(same(app.camera(), initial));
    for (float seconds : {0.0F, -1.0F, std::numeric_limits<float>::quiet_NaN(),
                          std::numeric_limits<float>::infinity()}) {
        app.step({1, 1, 1}, seconds);
        CHECK(same(app.camera(), initial));
    }
    for (auto member : {&application::CameraInput::orbit, &application::CameraInput::elevate,
                        &application::CameraInput::zoom}) {
        application::CameraInput input{1, 1, 1};
        input.*member = std::numeric_limits<float>::quiet_NaN();
        app.step(input, 0.1F);
        CHECK(same(app.camera(), initial));
    }
    app.step({1, 0, 0}, 0.02F);
    CHECK(std::abs(app.camera().yaw - initial.yaw - 0.02F) < 0.0001F);
    // Regression: at the old +/-0.9 limit a side wall hid the cube.
    for (float yaw : {-0.55F, 0.55F}) {
        for (float elevation : {0.1F, 0.8F}) {
            for (float distance : {3.0F, 9.0F}) {
                const auto position = domain::camera_eye({yaw, elevation, distance});
                if (position.z > 2) {
                    const auto at_open_front = position.x * 4 / (position.z + 2);
                    CHECK(std::abs(at_open_front) < 3);
                } else {
                    CHECK(std::abs(position.x) < 3);
                }
            }
        }
    }
}
void lifecycle() {
    using E = domain::LifecycleEvent;
    using S = domain::SessionState;
    Renderer renderer;
    application::RenderProbe app(renderer);
    app.step({}, 0.02F);
    CHECK(renderer.calls == 1);
    const auto initial = app.camera();
    app.dispatch(E::suspend);
    app.dispatch(E::suspend);
    app.step({1, 1, 1, true, true}, 100);
    CHECK(renderer.calls == 1 && same(app.camera(), initial));
    app.dispatch(E::resume);
    CHECK(app.awaiting_release());
    app.step({1, 1, 1, false, false, true}, 100);
    CHECK(app.awaiting_release() && same(app.camera(), initial));
    app.step({1}, 100); // Defensively handle an input source omitting any_held.
    CHECK(app.awaiting_release());
    app.step({}, 100);
    CHECK(!app.awaiting_release() && same(app.camera(), initial));
    app.step({1}, 0.02F);
    CHECK(app.camera().yaw > initial.yaw);
    renderer.response = ports::RenderResult::busy;
    app.step({}, 0.02F);
    CHECK(app.state() == S::running && app.result() == ports::RenderResult::busy);
    const auto calls = renderer.calls;
    app.step({1, 1, 1, true, true}, 1);
    CHECK(app.state() == S::stopped && renderer.calls == calls);
    app.dispatch(E::resume);
    app.step({}, 1);
    CHECK(renderer.calls == calls);
    for (auto failure : {ports::RenderResult::invalid_camera, ports::RenderResult::unavailable}) {
        application::RenderProbe failing(renderer);
        renderer.response = failure;
        failing.step({}, 1);
        CHECK(failing.state() == S::stopped && failing.result() == failure);
    }
    application::RenderProbe exiting(renderer);
    exiting.dispatch(E::suspend);
    exiting.dispatch(E::resume);
    exiting.step({0, 0, 0, false, true, true}, 1);
    CHECK(exiting.state() == S::stopped);
    application::RenderProbe suspended_exit(renderer);
    suspended_exit.dispatch(E::suspend);
    suspended_exit.dispatch(E::quit);
    suspended_exit.dispatch(E::resume);
    CHECK(suspended_exit.state() == S::stopped);
}
void mesh() {
    const auto panel = domain::texture_panel();
    for (const auto &v : panel) {
        CHECK(v.color.x == 1 && v.color.y == 1 && v.color.z == 1);
        CHECK(v.position.z == domain::camera_target.z);
        CHECK(v.u == (v.position.x + 2) / 4);
        CHECK(v.v == (v.position.y + 1.25F) / 4);
    }
    // Both triangles must cover the square with positive area, without a UV seam.
    float area = 0;
    for (std::size_t i = 0; i < panel.size(); i += 3) {
        const auto &a = panel[i], &b = panel[i + 1], &c = panel[i + 2];
        const auto cross = (b.u - a.u) * (c.v - a.v) - (b.v - a.v) * (c.u - a.u);
        CHECK(cross > 0);
        area += cross / 2;
    }
    CHECK(area == 1);
    const auto scene = domain::synthetic_room();
    CHECK(scene.size() == 60);
    for (const auto &v : scene) {
        CHECK(std::isfinite(v.position.x) && std::isfinite(v.position.y) &&
              std::isfinite(v.position.z));
        CHECK(v.position.x >= -3 && v.position.x <= 3);
        CHECK(v.position.y >= 0 && v.position.y <= 3);
        CHECK(v.position.z >= -5 && v.position.z <= 2);
        CHECK(v.u >= 0 && v.u <= 6 && v.v >= 0 && v.v <= 6);
        CHECK(v.color.x >= 0 && v.color.x <= 1 && v.color.y >= 0 && v.color.y <= 1 &&
              v.color.z >= 0 && v.color.z <= 1);
    }
    // Every submitted triangle has nonzero area.
    for (std::size_t i = 0; i < scene.size(); i += 3) {
        const auto a = scene[i].position, b = scene[i + 1].position, c = scene[i + 2].position;
        const domain::Vec3 u{b.x - a.x, b.y - a.y, b.z - a.z};
        const domain::Vec3 v{c.x - a.x, c.y - a.y, c.z - a.z};
        const float x = u.y * v.z - u.z * v.y;
        const float y = u.z * v.x - u.x * v.z;
        const float z = u.x * v.y - u.y * v.x;
        CHECK(x * x + y * y + z * z > 0);
    }
    CHECK(scene[0].position.z == -1.25F); // Cube first.
    CHECK(scene[36].position.y == 0);     // Floor afterwards.
}
void texture() {
    std::array<std::uint8_t, platform::checker_bytes + 2> bytes{};
    bytes.front() = 11;
    bytes.back() = 22;
    platform::write_checker_texture(bytes.data() + 1);
    CHECK(bytes.front() == 11 && bytes.back() == 22);
    std::array<bool, 4096> seen{};
    for (std::size_t y = 0; y < 64; ++y) {
        for (std::size_t x = 0; x < 64; ++x) {
            const auto offset = platform::checker_texel_offset(x, y);
            CHECK(offset % 4 == 0 && offset < platform::checker_bytes);
            CHECK(!seen[offset / 4]);
            seen[offset / 4] = true;
            CHECK(bytes[offset + 1] == 255);
            if (x < 8 && y < 8) {
                CHECK(bytes[offset + 2] == 40 && bytes[offset + 3] == 40 &&
                      bytes[offset + 4] == 255);
            } else {
                const auto shade = ((x / 8 + y / 8) % 2) ? 100 : 240;
                CHECK(bytes[offset + 2] == shade && bytes[offset + 3] == shade &&
                      bytes[offset + 4] == shade);
            }
        }
    }
    // Independent golden offsets, including tile boundaries and the final texel.
    CHECK(platform::checker_texel_offset(1, 0) == 4);
    CHECK(platform::checker_texel_offset(0, 1) == 8);
    CHECK(platform::checker_texel_offset(7, 7) == 252);
    CHECK(platform::checker_texel_offset(8, 0) == 256);
    CHECK(platform::checker_texel_offset(0, 8) == 2048);
    CHECK(platform::checker_texel_offset(63, 63) == 16380);
}
} // namespace
int main() {
    camera();
    lifecycle();
    mesh();
    texture();
}
