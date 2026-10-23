#include "character_renderer.hpp"
#include "check.hpp"
#include "sdk.hpp"
#include <cstring>
#include <limits>
#include <memory>
int main(int argc, char **argv) {
    CHECK(argc == 2 || argc == 3);
    using namespace render_sdk;
    using R = sh3::ports::RenderResult;
    character = dynamic = character_material = true;
    character_instances = argc == 3 ? 3 : 1;
    const std::string scenario = argv[1];
    std::vector<sh3::domain::CharacterDrawVertex> mesh(9 * character_instances);
    mesh[0] = {{-1, -1, -2, 1}, {1, 0, 0}, {0, 0}};
    mesh[1] = {{1, -1, -2, 4095.0F / 4096}, {0, 1, 0}, {1, 0}};
    mesh[2] = {{0, 1, -2, 1}, {0, 0, 1}, {0, 1}};
    for (std::size_t i = 3; i < mesh.size(); ++i)
        mesh[i] = mesh[i % 3];
    auto data = std::make_unique<sh3::platform::CharacterMaterialData>();
    data->ranges = {{{0, 3, 0}, {3, 3, 1}, {6, 3, 2}}};
    for (std::size_t i = 0; i < data->pixels.size(); i += 4) {
        data->pixels[i] = 17;
        data->pixels[i + 1] = 45;
        data->pixels[i + 2] = 93;
        data->pixels[i + 3] = (i / 4) % 129;
    }
    if (scenario == "init_MATERIAL")
        data->ranges[1].first = 0;
    if (scenario == "init_PIXELS")
        data->pixels[3 + 2 * sh3::platform::character_texture_bytes] = 129;
    auto expect = [&] {
        const auto *p = reinterpret_cast<const unsigned char *>(mesh.data());
        expected_vertices.assign(p, p + mesh.size() * sizeof(mesh[0]));
    };
    expect();
    const bool init_failure = scenario.rfind("init_", 0) == 0;
    if (init_failure)
        failure = scenario.substr(5);
    {
        sh3::platform::ctr::CharacterRenderer renderer(9, data.get(), character_instances);
        data.reset();
        if (init_failure)
            CHECK(!renderer.ready());
        else {
            CHECK(renderer.ready());
            CHECK(renderer.present({}, mesh.data(), mesh.size()) == R::presented);
            const auto allocations_before = allocations;
            const auto events_before = events.size();
            if (scenario == "invalid") {
                CHECK(renderer.present({}, nullptr, 9) == R::unavailable);
                CHECK(renderer.present({}, mesh.data(), 0) == R::unavailable);
                CHECK(renderer.present({0, 0, 0}, mesh.data(), mesh.size()) == R::invalid_camera);
                mesh.back().position[3] = std::numeric_limits<float>::quiet_NaN();
                CHECK(renderer.present({}, mesh.data(), mesh.size()) == R::unavailable);
                CHECK(events.size() == events_before);
            } else if (scenario == "busy") {
                failure = "FRAME_BEGIN";
                CHECK(renderer.present({}, mesh.data(), mesh.size()) == R::busy);
                CHECK(events.back() == "FRAME_BEGIN" && frames == 1);
            } else if (scenario == "flush" || scenario == "draw") {
                failure = scenario == "flush" ? "VERTEX_FLUSH" : "DRAW_ON";
                CHECK(renderer.present({}, mesh.data(), mesh.size()) == R::unavailable);
                CHECK(!open_frame && draws == 3 * static_cast<int>(character_instances) &&
                      frames == 2);
            } else {
                CHECK(scenario == "normal");
                for (int i = 0; i < 1000; ++i) {
                    mesh[2].position[1] = i % 2 ? 1 : .5F;
                    expect();
                    CHECK(renderer.present({}, mesh.data(), mesh.size()) == R::presented);
                }
                CHECK(frames == 1001 && draws == 3003 * static_cast<int>(character_instances));
            }
            CHECK(allocations == allocations_before);
        }
    }
    CHECK(acquired == released && !pending && !open_frame);
    const auto before = acquired;
    sh3::platform::ctr::CharacterRenderer invalid(0);
    CHECK(!invalid.ready() && before == acquired);
    sh3::platform::ctr::CharacterRenderer bad_zero(9, nullptr, 0), bad_many(9, nullptr, 4);
    CHECK(!bad_zero.ready() && !bad_many.ready() && before == acquired);
}
