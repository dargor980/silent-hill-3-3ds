#include "check.hpp"
#include "renderer.hpp"
#include "sdk.hpp"
#include <algorithm>
#include <limits>
#include <memory>

int main(int argc, char **argv) {
    CHECK(argc == 2 || argc == 3);
    using namespace render_sdk;
    using R = sh3::ports::RenderResult;
    failure = argv[1];
    material = argc == 3 && std::string(argv[2]) == "material";
    inspection = material || (argc == 3 && std::string(argv[2]) == "texture");
    geometry = material || (argc == 3 && std::string(argv[2]) == "geometry");
    const bool runtime = failure == "normal" || failure == "FRAME_BEGIN" || failure == "DRAW_ON" ||
                         failure == "invalid_camera";
    {
        std::vector<std::uint8_t> pixels(sh3::platform::inspection_bytes, 255);
        std::unique_ptr<sh3::platform::ctr::SceneRenderer> owned;
        std::vector<sh3::domain::SceneVertex> vertices{{{-1, -1, -2}, 0, 0, {1, 0, 0}},
                                                       {{1, -1, -2}, 1, 0, {0, 1, 0}},
                                                       {{0, 1, -2}, 0, 1, {0, 0, 1}}};
        const auto *raw = reinterpret_cast<const unsigned char *>(vertices.data());
        expected_vertices.assign(raw, raw + vertices.size() * sizeof(vertices[0]));
        if (material)
            owned = std::make_unique<sh3::platform::ctr::SceneRenderer>(
                sh3::platform::InspectionMesh{
                    vertices.data(), failure == "invalid_mesh" ? 0 : vertices.size()},
                sh3::platform::InspectionPixels{
                    pixels.data(), failure == "invalid_pixels" ? 0 : pixels.size()});
        else if (geometry)
            owned =
                std::make_unique<sh3::platform::ctr::SceneRenderer>(sh3::platform::InspectionMesh{
                    vertices.data(), failure == "invalid_mesh" ? 0 : vertices.size()});
        else if (inspection)
            owned =
                std::make_unique<sh3::platform::ctr::SceneRenderer>(sh3::platform::InspectionPixels{
                    pixels.data(), failure == "invalid_pixels" ? 0 : pixels.size()});
        else
            owned = std::make_unique<sh3::platform::ctr::SceneRenderer>();
        auto &renderer = *owned;
        // Renderer must not keep the borrowed pixels for subsequent frames.
        vertices.clear();
        vertices.shrink_to_fit();
        pixels.clear();
        pixels.shrink_to_fit();
        CHECK(renderer.ready() == runtime);
        if (!runtime) {
            auto expected = failure;
            if (failure == "EMPTY_SHADER")
                expected = "SHADER";
            if (failure == "invalid_mesh")
                expected = "GEOMETRY_DATA";
            if (failure == "invalid_pixels")
                expected = "TEXTURE_DATA";
            if (failure.rfind("ATTRIBUTES_", 0) == 0)
                expected = "ATTRIBUTES";
            CHECK(renderer.stage() == expected);
            CHECK(renderer.present({}) == R::unavailable);
        } else {
            const auto before = allocations;
            if (failure == "invalid_camera") {
                auto camera = sh3::domain::OrbitCamera{};
                camera.yaw = std::numeric_limits<float>::quiet_NaN();
                CHECK(renderer.present(camera) == R::invalid_camera);
                CHECK(frames == 0 && draws == 0);
                CHECK(std::find(events.begin(), events.end(), "FRAME_BEGIN") == events.end());
            } else if (failure == "FRAME_BEGIN") {
                CHECK(renderer.present({}) == R::busy);
                CHECK(frames == 0 && draws == 0);
            } else if (failure == "DRAW_ON") {
                CHECK(renderer.present({}) == R::unavailable);
                CHECK(frames == 1 && draws == 0 && !open_frame);
            } else {
                for (unsigned i = 0; i < 1000; ++i) {
                    CHECK(renderer.present({}) == R::presented);
                }
                CHECK(frames == 1000 && draws == (material ? 2000 : 1000) && pending);
            }
            CHECK(allocations == before);
        }
    }
    CHECK(acquired == released && !pending && !open_frame);
    if (acquired > 1) {
        const auto deleted = std::find(events.begin(), events.end(), "target_delete");
        CHECK(deleted != events.end());
        for (const auto *name : {"texture_free", "vertices_free", "program_free", "shader_free"}) {
            const auto it = std::find(events.begin(), events.end(), name);
            CHECK(it == events.end() || deleted < it);
        }
    }
    if (acquired)
        CHECK(events.back() == "fini");
}
