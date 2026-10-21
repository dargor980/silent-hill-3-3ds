#include "character_renderer.hpp"
#include "check.hpp"
#include "sdk.hpp"
#include <cstring>
#include <limits>
int main(int argc, char **argv) {
    CHECK(argc == 2);
    using namespace render_sdk;
    using R = sh3::ports::RenderResult;
    character = dynamic = true;
    const std::string scenario = argv[1];
    std::array<sh3::domain::CharacterDrawVertex, 3> mesh{{{{-1, -1, -2, 1}, {1, 0, 0}},
                                                          {{1, -1, -2, 4095.0F / 4096}, {0, 1, 0}},
                                                          {{0, 1, -2, 1}, {0, 0, 1}}}};
    auto expect = [&] {
        const auto *p = reinterpret_cast<const unsigned char *>(mesh.data());
        expected_vertices.assign(p, p + sizeof(mesh));
    };
    expect();
    const bool init_failure = scenario.rfind("init_", 0) == 0;
    if (init_failure)
        failure = scenario.substr(5);
    {
        sh3::platform::ctr::CharacterRenderer renderer(3);
        if (init_failure)
            CHECK(!renderer.ready());
        else {
            CHECK(renderer.ready());
            CHECK(renderer.present({}, mesh.data(), 3) == R::presented);
            const auto allocations_before = allocations;
            const auto events_before = events.size();
            if (scenario == "invalid") {
                CHECK(renderer.present({}, nullptr, 3) == R::unavailable);
                CHECK(renderer.present({}, mesh.data(), 0) == R::unavailable);
                CHECK(renderer.present({0, 0, 0}, mesh.data(), 3) == R::invalid_camera);
                mesh[0].position[3] = std::numeric_limits<float>::quiet_NaN();
                CHECK(renderer.present({}, mesh.data(), 3) == R::unavailable);
                CHECK(events.size() == events_before);
            } else if (scenario == "busy") {
                failure = "FRAME_BEGIN";
                CHECK(renderer.present({}, mesh.data(), 3) == R::busy);
                CHECK(events.back() == "FRAME_BEGIN" && frames == 1);
            } else if (scenario == "flush" || scenario == "draw") {
                failure = scenario == "flush" ? "VERTEX_FLUSH" : "DRAW_ON";
                CHECK(renderer.present({}, mesh.data(), 3) == R::unavailable);
                CHECK(!open_frame && draws == 1 && frames == 2);
            } else {
                CHECK(scenario == "normal");
                for (int i = 0; i < 1000; ++i) {
                    mesh[2].position[1] = i % 2 ? 1 : .5F;
                    expect();
                    CHECK(renderer.present({}, mesh.data(), 3) == R::presented);
                }
                CHECK(frames == 1001 && draws == 1001);
            }
            CHECK(allocations == allocations_before);
        }
    }
    CHECK(acquired == released && !pending && !open_frame);
    const auto before = acquired;
    sh3::platform::ctr::CharacterRenderer invalid(0);
    CHECK(!invalid.ready() && before == acquired);
}
