#include "check.hpp"
#include "renderer.hpp"
#include "sdk.hpp"
#include <cstring>

int main(int argc, char **argv) {
    CHECK(argc == 2);
    using namespace render_sdk;
    using R = sh3::ports::RenderResult;
    geometry = true;
    dynamic = true;
    const std::string scenario = argv[1];
    std::array<sh3::domain::SceneVertex, 3> mesh{{{{-1, -1, -2}, 0, 0, {1, 0, 0}},
                                                  {{1, -1, -2}, 1, 0, {0, 1, 0}},
                                                  {{0, 1, -2}, 0, 1, {0, 0, 1}}}};
    auto expect = [&] {
        const auto *raw = reinterpret_cast<const unsigned char *>(mesh.data());
        expected_vertices.assign(raw, raw + sizeof(mesh));
    };
    expect();
    {
        sh3::platform::ctr::SceneRenderer renderer(
            sh3::platform::InspectionMesh{mesh.data(), mesh.size()});
        CHECK(renderer.ready());
        CHECK(renderer.present_mesh({}, mesh.data(), mesh.size()) == R::presented);
        const auto before = allocations;
        const auto event_count = events.size();
        if (scenario == "invalid") {
            CHECK(renderer.present_mesh({}, mesh.data(), 0) == R::unavailable);
            CHECK(renderer.present_mesh({}, nullptr, 3) == R::unavailable);
            CHECK(events.size() == event_count && frames == 1);
        } else if (scenario == "busy") {
            failure = "FRAME_BEGIN";
            CHECK(renderer.present_mesh({}, mesh.data(), 3) == R::busy);
            CHECK(events.back() == "FRAME_BEGIN" && frames == 1);
        } else if (scenario == "flush") {
            failure = "VERTEX_FLUSH";
            CHECK(renderer.present_mesh({}, mesh.data(), 3) == R::unavailable);
            CHECK(!open_frame && draws == 1 && frames == 2);
        } else if (scenario == "draw") {
            failure = "DRAW_ON";
            CHECK(renderer.present_mesh({}, mesh.data(), 3) == R::unavailable);
            CHECK(!open_frame && draws == 1 && frames == 2);
        } else {
            CHECK(scenario == "normal");
            for (int i = 0; i < 1000; ++i) {
                mesh[2].position.y = i % 2 ? 1 : 0.5F;
                expect();
                CHECK(renderer.present_mesh({}, mesh.data(), 3) == R::presented);
            }
            CHECK(frames == 1001 && draws == 1001);
        }
        CHECK(allocations == before);
    }
    CHECK(acquired == released && !pending && !open_frame);
}
