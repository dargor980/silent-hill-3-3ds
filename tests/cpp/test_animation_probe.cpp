#include "check.hpp"
#include "sh3/application/animation_probe.hpp"
#include "sh3/application/skeleton_presenter.hpp"
#include "sh3/platform/inspection_animation.hpp"
#include "sh3/platform/inspection_geometry.hpp"
#include <cmath>
#include <cstring>
#include <limits>

namespace {
using namespace sh3;
struct Renderer final : ports::IDynamicScene {
    int calls{0};
    ports::RenderResult result{ports::RenderResult::presented};
    ports::RenderResult present_mesh(const domain::OrbitCamera &, const domain::SceneVertex *v,
                                     std::size_t count) noexcept override {
        CHECK(platform::valid_inspection_mesh({v, count}));
        CHECK(count == 120);
        ++calls;
        return result;
    }
};
domain::InspectionClip fixture() {
    domain::InspectionClip c;
    c.scale = 0.5F;
    c.translations = {domain::Vec3{-1, 0, 0}, domain::Vec3{0, 0, 0}, domain::Vec3{0, 1, 0}};
    for (std::size_t i = 0; i < 24; ++i) {
        const float angle = float(i) * 0.02F;
        for (auto &q : c.rotations[i])
            q = {0, 0, std::sin(angle), std::cos(angle)};
    }
    return c;
}
} // namespace
int main(int argc, char **argv) {
    if (argc >= 2) {
        sh3::domain::InspectionClip c{};
        auto api = sh3::platform::system_stdio;
        if (argc == 3 && std::strcmp(argv[2], "close-failure") == 0)
            api.close = +[](FILE *f) -> int {
                std::fclose(f);
                return -1;
            };
        if (argc == 3 && std::strcmp(argv[2], "read-failure") == 0)
            api.error = +[](FILE *) -> int { return 1; };
        if (argc == 3 && std::strcmp(argv[2], "short-read") == 0)
            api.read = +[](void *p, std::size_t size, std::size_t count, FILE *f) -> std::size_t {
                return std::fread(p, size, count > 1 ? count - 1 : count, f);
            };
        if (sh3::platform::read_inspection_animation(argv[1], c, api) !=
            sh3::ports::FileError::ok) {
            CHECK(c.scale == 1 && c.rotations[0][0][3] == 0); // Never publish partial data.
            return 2;
        }
        if (argc == 3)
            for (std::uint32_t counter = 0; counter < domain::clip_period; counter += 257) {
                const auto pose = domain::evaluate_pose(c, counter);
                const auto mesh = domain::skeleton_mesh(c, pose);
                CHECK(platform::valid_inspection_mesh({mesh.data(), mesh.size()}));
                std::printf("%u", counter);
                for (const auto &m : pose)
                    for (auto v : m)
                        std::printf(" %.9g", double(v));
                std::puts("");
            }
        return 0;
    }
    using E = domain::LifecycleEvent;
    const auto clip = fixture();
    CHECK(domain::valid_clip(clip));
    auto bad = clip;
    bad.parents[1] = 2;
    CHECK(!domain::valid_clip(bad));
    bad = clip;
    bad.rotations[23][2] = {0, 0, 0, 0};
    CHECK(!domain::valid_clip(bad));
    bad = clip;
    bad.center.x = std::numeric_limits<float>::infinity();
    CHECK(!domain::valid_clip(bad));
    bad = clip;
    bad.translations[2] = {0, 0, 0};
    CHECK(!domain::valid_clip(bad));
    bad = clip;
    bad.scale = 0;
    CHECK(!domain::valid_clip(bad));
    auto signed_clip = clip;
    for (auto &v : signed_clip.rotations[1][1])
        v = -v;
    const auto a = domain::evaluate_pose(clip, 2048), b = domain::evaluate_pose(signed_clip, 2048);
    for (std::size_t i = 0; i < 3; ++i)
        for (std::size_t j = 0; j < 16; ++j)
            CHECK(std::abs(a[i][j] - b[i][j]) < 1e-6F);
    CHECK(domain::evaluate_pose(clip, domain::clip_period) == domain::evaluate_pose(clip, 0));
    for (std::uint32_t counter = 0; counter < domain::clip_period; counter += 17) {
        const auto pose = domain::evaluate_pose(clip, counter);
        const auto mesh = domain::skeleton_mesh(clip, pose);
        CHECK(platform::valid_inspection_mesh({mesh.data(), mesh.size()}));
        float distance = 0;
        for (int i = 12; i < 15; ++i)
            distance += (pose[2][i] - pose[1][i]) * (pose[2][i] - pose[1][i]);
        CHECK(std::abs(distance - 1) < 1e-5F);
    }
    Renderer renderer;
    application::SkeletonPresenter presenter(renderer, clip);
    application::AnimationProbe app(presenter, clip);
    CHECK(app.view().camera().distance == 4.0F);
    app.step({1, 1, 1, false, false, true}, {}, 0.1F);
    app.step({0, 0, 0, true, false, true}, {false, false, true}, 0);
    CHECK(app.view().camera().distance == 4.0F && app.view().camera().yaw == 0.35F);
    app.step({}, {}, 0.04F);
    CHECK(app.counter() == 3686);
    app.step({}, {true, false, false}, 0.04F);
    CHECK(app.paused() && app.counter() == 3686);
    app.step({}, {}, 99);
    CHECK(app.counter() == 3686);
    app.step({}, {false, true, false}, 99);
    CHECK(app.counter() == 7372);
    app.step({}, {false, false, true}, 99);
    CHECK(app.counter() == 0 && app.paused());
    app.dispatch(E::suspend);
    const auto calls = renderer.calls;
    app.step({}, {true, true, true}, 99);
    CHECK(renderer.calls == calls && app.counter() == 0 && app.paused());
    app.dispatch(E::resume);
    app.step({1, 0, 0, false, false, true}, {true, true, true}, 99);
    CHECK(app.counter() == 0 && app.paused() && app.view().awaiting_release());
    app.step({}, {}, 99);
    CHECK(app.counter() == 0 && !app.view().awaiting_release());
    app.step({}, {true, false, false}, 99);
    CHECK(!app.paused() && app.counter() == 0);
    app.step({}, {}, -1);
    app.step({}, {}, std::numeric_limits<float>::quiet_NaN());
    CHECK(app.counter() == 0);
    app.step({}, {}, 99);
    CHECK(app.counter() == 7372); // dt limited to .1 seconds.
    app.dispatch(E::suspend);
    app.dispatch(E::resume);
    app.step({}, {}, 99);
    CHECK(app.counter() == 7372); // No elapsed-time jump on immediate neutral resume.
    app.step({}, {}, 0.02F);
    CHECK(app.counter() == 11058);
    renderer.result = ports::RenderResult::busy;
    app.step({}, {}, 0.04F);
    CHECK(app.view().state() == domain::SessionState::running);
    renderer.result = ports::RenderResult::unavailable;
    app.step({}, {}, 0);
    CHECK(app.view().state() == domain::SessionState::stopped);
    application::AnimationProbe quit(presenter, clip);
    quit.dispatch(E::suspend);
    quit.dispatch(E::resume);
    quit.step({0, 0, 0, false, true, true}, {}, 99);
    CHECK(quit.view().state() == domain::SessionState::stopped && quit.counter() == 0);
    renderer.result = ports::RenderResult::presented;
    application::AnimationProbe slow(presenter, clip), fast(presenter, clip);
    for (int i = 0; i < 1000; ++i)
        slow.step({}, {}, 0.04F);
    for (int i = 0; i < 4000; ++i)
        fast.step({}, {}, 0.01F);
    CHECK(slow.counter() == fast.counter() &&
          slow.counter() == (1000 * 3686) % domain::clip_period);
    application::AnimationProbe invalid(presenter, bad);
    invalid.step({}, {}, 0);
    CHECK(invalid.view().state() == domain::SessionState::stopped);
    domain::InspectionClip output = clip;
    CHECK(platform::read_inspection_animation(nullptr, output) == ports::FileError::invalid_target);
    CHECK(platform::read_inspection_animation("/nonexistent/sh3-animation.san", output) ==
          ports::FileError::missing);
    CHECK(output.rotations == clip.rotations);
}
