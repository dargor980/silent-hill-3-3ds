#include "check.hpp"
#include "rig_fixture.hpp"
#include "sh3/application/rig_probe.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include "sh3/platform/inspection_rig.hpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <vector>

namespace {
using namespace sh3;
static domain::InspectionRig m, base;
static domain::RigPose pose;
static domain::RigPalette palette;
static domain::RigSortOrder order;
static std::array<domain::RigVertexScratch, domain::rig_vertices> scratch;
static std::array<domain::CharacterDrawVertex, domain::rig_indices> draw;
static std::vector<std::uint8_t> texture_source;
static int texture_fault{};
bool render() {
    return domain::rig_draw(m, pose, {}, palette, order, scratch.data(), scratch.size(),
                            draw.data(), draw.size());
}
bool near(float a, float b) { return std::abs(a - b) < 1e-5F; }
class Scene final : public ports::IRigScene {
  public:
    ports::RenderResult present_pose(const domain::OrbitCamera &,
                                     const domain::RigPose &) noexcept override {
        ++calls;
        return ports::RenderResult::presented;
    }
    int calls{};
};
} // namespace
int main(int argc, char **argv) {
    using namespace sh3;
    if (argc > 1) {
        auto api = platform::system_stdio;
        if (argc > 2 && std::strcmp(argv[2], "close-failure") == 0)
            api.close = +[](FILE *f) {
                std::fclose(f);
                return -1;
            };
        if (argc > 2 && std::strcmp(argv[2], "read-failure") == 0)
            api.error = +[](FILE *) noexcept { return 1; };
        if (argc > 2 && std::strcmp(argv[2], "short-read") == 0)
            api.read = +[](void *p, std::size_t s, std::size_t n, FILE *f) {
                return std::fread(p, s, n > 1 ? n - 1 : n, f);
            };
        if (platform::read_inspection_rig(argv[1], m, api) != ports::FileError::ok) {
            CHECK(m.vertex_count == 0);
            return 2;
        }
        const auto counter = argc > 2 ? std::strtoul(argv[2], nullptr, 10) : 0;
        domain::evaluate_rig(m, counter, pose);
        CHECK(render());
        if (argc > 3) {
            for (unsigned i = 0; i < m.bone_count; ++i) {
                for (auto f : pose[i])
                    std::printf("%.9g ", double(f));
                std::puts("");
            }
            for (unsigned i = 0; i < m.vertex_count; ++i) {
                for (auto f : scratch[i].position)
                    std::printf("%.9g ", double(f));
                std::puts("");
            }
        }
        return 0;
    }
    make_rig(base);
    m = base;
    CHECK(domain::valid_rig(m));
    domain::evaluate_rig(m, 2048, pose);
    CHECK(near(pose[0][12], 1) && near(pose[1][12], 1) && near(pose[1][13], 1));
    CHECK(render());
    CHECK(scratch[0].position[3] == 4095.0F / 4096);
    CHECK(near(scratch[0].position[0], .5F + 2 * 2047.0F / 4096));
    CHECK(near(draw[0].position[0], -scratch[0].position[0] * m.scale));
    domain::RigPose wrapped{};
    domain::evaluate_rig(m, 8192 + 2048, wrapped);
    CHECK(pose == wrapped);
    auto reject = [&](auto mutate) {
        m = base;
        mutate(m);
        CHECK(!domain::valid_rig(m));
    };
    reject([](auto &x) { x.bone_count = 0; });
    reject([](auto &x) { x.sample_count = 65; });
    reject([](auto &x) { x.helper_count = 129; });
    reject([](auto &x) { x.index_count = 5; });
    reject([](auto &x) { x.vertex_count = 8193; });
    reject([](auto &x) { x.material_count = 17; });
    reject([](auto &x) { x.increment = 8192; });
    reject([](auto &x) { x.scale = 0; });
    reject([](auto &x) { x.parents[1] = 1; });
    reject([](auto &x) { x.parents[0] = -2; });
    reject([](auto &x) { x.samples[0][0].translation.x = std::numeric_limits<float>::infinity(); });
    reject([](auto &x) { x.samples[1][0].rotation[0] = 2; });
    reject([](auto &x) { x.samples[0][0].rotation[3] = 0; });
    reject([](auto &x) { x.targets[0] = 2; });
    reject([](auto &x) { x.helpers[0][3] = 1; });
    reject([](auto &x) { x.helpers[0][0] = std::numeric_limits<float>::quiet_NaN(); });
    reject([](auto &x) { x.vertices[0].primary = 2; });
    reject([](auto &x) { x.vertices[0].count = 4; });
    reject([](auto &x) { x.vertices[0].weights[2] = 1; });
    reject([](auto &x) { x.vertices[0].weights[0] = 4097; });
    reject([](auto &x) { x.vertices[0].weights[0] = 2047; });
    reject([](auto &x) { x.vertices[0].helpers[0] = 1; });
    reject([](auto &x) { x.vertices[0].helpers[1] = 0; });
    reject([](auto &x) { x.indices[0] = 6; });
    reject([](auto &x) { x.materials[1].first = 0; });
    reject([](auto &x) { x.materials[0].texture = 1; });
    reject([](auto &x) { x.materials[0].width = 127; });
    reject([](auto &x) { x.materials[1].blend = 2; });
    reject([](auto &x) {
        x.materials[0].blend = 1;
        x.materials[1].blend = 0;
    });
    reject([](auto &x) { x.material_count = 1; });
    m = base;
    CHECK(render());
    CHECK(!domain::rig_draw(m, pose, {}, palette, order, nullptr, 6, draw.data(), 6));
    CHECK(!domain::rig_draw(m, pose, {}, palette, order, scratch.data(), 5, draw.data(), 6));
    CHECK(!domain::rig_draw(m, pose, {}, palette, order, scratch.data(), 6, draw.data(), 5));
    CHECK(!domain::rig_draw(m, pose, {0, 0, 0}, palette, order, scratch.data(), 6, draw.data(), 6));
    CHECK(!domain::valid_rig_draw(nullptr, 6));
    CHECK(!domain::valid_rig_draw(draw.data(), 5));
    draw[0].color.x = -1;
    CHECK(!domain::valid_rig_draw(draw.data(), 6));
    CHECK(render());
    draw[0].uv[0] = 9;
    CHECK(!domain::valid_rig_draw(draw.data(), 6));
    CHECK(render());
    draw[0].position[3] = 0;
    CHECK(!domain::valid_rig_draw(draw.data(), 6));
    pose[0][0] = std::numeric_limits<float>::infinity();
    CHECK(!render());
    CHECK(platform::read_inspection_rig(nullptr, m) == ports::FileError::invalid_target);
    CHECK(platform::read_inspection_rig("/nonexistent/rig.sri", m) == ports::FileError::missing);
    // Independent corner anchors cover non-square Morton layout and alpha normalization.
    domain::RigMaterial tm{0, 3, 0, 128, 256, 0, 0};
    texture_source.resize(128 * 256 * 4);
    for (unsigned y = 0; y < 256; ++y)
        for (unsigned x = 0; x < 128; ++x) {
            const auto at = (y * 128 + x) * 4;
            texture_source[at] = x;
            texture_source[at + 1] = y;
            texture_source[at + 2] = 17;
            texture_source[at + 3] = (x + y) % 129;
        }
    tm.crc = platform::inspection_crc32(texture_source.data(), texture_source.size());
    std::vector<std::uint8_t> tex(texture_source.size()), tiled(texture_source.size());
    auto api = platform::system_stdio;
    api.open = +[](const char *, const char *) -> FILE * {
        auto *f = std::tmpfile();
        CHECK(f);
        std::fwrite(texture_source.data(), 1, texture_source.size() - (texture_fault == 1), f);
        if (texture_fault == 2)
            std::fputc(0, f);
        std::rewind(f);
        return f;
    };
    CHECK(platform::read_rig_texture("own", tm, tex.data(), tex.size(), api) ==
          ports::FileError::ok);
    CHECK(tex == texture_source);
    CHECK(platform::upload_rig_texture(tm, tex.data(), tex.size(), tiled.data(), tiled.size()));
    for (const auto &anchor : std::array<std::array<unsigned, 3>, 7>{{{0, 0, 0},
                                                                      {1, 0, 1},
                                                                      {0, 1, 2},
                                                                      {7, 7, 63},
                                                                      {8, 0, 64},
                                                                      {0, 8, 1024},
                                                                      {127, 255, 32767}}}) {
        const auto x = anchor[0], y = anchor[1], at = anchor[2] * 4;
        const auto source_y = 255 - y;
        CHECK(tiled[at] == std::min(255U, 2 * ((x + source_y) % 129)));
        CHECK(tiled[at + 1] == 17 && tiled[at + 2] == source_y && tiled[at + 3] == x);
    }
    texture_fault = 1;
    CHECK(platform::read_rig_texture("own", tm, tex.data(), tex.size(), api) ==
          ports::FileError::invalid_data);
    texture_fault = 2;
    CHECK(platform::read_rig_texture("own", tm, tex.data(), tex.size(), api) ==
          ports::FileError::invalid_data);
    texture_fault = 0;
    tm.crc ^= 1;
    CHECK(platform::read_rig_texture("own", tm, tex.data(), tex.size(), api) ==
          ports::FileError::verify_failed);
    tm.crc ^= 1;
    auto io = api;
    io.error = +[](FILE *) noexcept { return 1; };
    CHECK(platform::read_rig_texture("own", tm, tex.data(), tex.size(), io) ==
          ports::FileError::read_failed);
    io = api;
    io.close = +[](FILE *f) {
        std::fclose(f);
        return -1;
    };
    CHECK(platform::read_rig_texture("own", tm, tex.data(), tex.size(), io) ==
          ports::FileError::close_failed);
    CHECK(platform::read_rig_texture(nullptr, tm, tex.data(), tex.size()) ==
          ports::FileError::invalid_target);
    CHECK(platform::read_rig_texture("/nonexistent/texture", tm, tex.data(), tex.size()) ==
          ports::FileError::missing);
    CHECK(!platform::upload_rig_texture(tm, tex.data(), tex.size(), tex.data(), tex.size()));
    CHECK(
        !platform::upload_rig_texture(tm, tex.data(), tex.size() - 1, tiled.data(), tiled.size()));
    CHECK(
        !platform::upload_rig_texture(tm, tex.data(), tex.size(), tiled.data(), tiled.size() - 1));
    tm.width = 127;
    CHECK(!platform::upload_rig_texture(tm, tex.data(), tex.size(), tiled.data(), tiled.size()));
    // Transparent sorting is independent of the order stored in the index buffer.
    m = base;
    m.material_count = 1;
    m.materials[0] = {0, 6, 0, 128, 128, 1, 0};
    domain::evaluate_rig(m, 0, pose);
    CHECK(render());
    CHECK(order[0].ordinal == 0 && order[1].ordinal == 1);
    for (unsigned i = 0; i < 3; ++i)
        std::swap(m.indices[i], m.indices[i + 3]);
    CHECK(render());
    CHECK(order[0].ordinal == 1 && order[1].ordinal == 0);
    Scene scene;
    application::RigProbe app(scene, base);
    app.step({}, {}, .04F);
    CHECK(app.counter() == 1024 && scene.calls == 1);
    app.step({}, {true, false, false}, .04F);
    CHECK(app.paused() && app.counter() == 1024);
    app.step({}, {false, true, false}, .04F);
    CHECK(app.counter() == 2048);
    app.step({}, {false, false, true}, .04F);
    CHECK(app.counter() == 0);
    app.step({}, {}, .04F, true);
    CHECK(app.face_view() && app.paused() && app.counter() == 0);
    CHECK(app.view().camera().distance == .65F && app.view().camera().target.y == 1.32F);
    for (unsigned i = 0; i < 100; ++i)
        app.step({0, 0, -1}, {}, .1F);
    CHECK(app.view().camera().distance == .45F && app.counter() == 0);
    app.step({}, {}, .04F, true);
    CHECK(!app.face_view() && app.view().camera().distance == 3);
    app.step({1, 1, 1}, {}, .04F, true);
    CHECK(app.face_view() && app.view().camera().distance == .65F);
    app.step({0, 0, 0, true}, {}, .04F, true);
    CHECK(!app.face_view() && app.view().camera().target.y == .75F);
    app.dispatch(domain::LifecycleEvent::suspend);
    const auto calls = scene.calls;
    app.step({}, {}, 10);
    CHECK(scene.calls == calls);
    app.dispatch(domain::LifecycleEvent::resume);
    app.step({}, {true, true, true}, 10, true);
    CHECK(app.counter() == 0 && app.paused() && !app.face_view());
    app.step({}, {}, .04F, true);
    CHECK(!app.face_view() && app.view().awaiting_release());
    app.step({}, {}, .04F);
    app.step({}, {true, false, false}, .04F);
    CHECK(!app.paused());
    app.step({}, {}, .04F);
    CHECK(app.counter() == 1024);
    app.step({0, 0, 0, false, true, true}, {true, true, true}, 1, true);
    CHECK(app.view().state() == domain::SessionState::stopped && !app.face_view());
    base.bone_count = 0;
    application::RigProbe invalid(scene, base);
    invalid.step({}, {}, 1);
    CHECK(invalid.view().result() == ports::RenderResult::unavailable);
}
