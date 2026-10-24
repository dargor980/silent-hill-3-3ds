#include "check.hpp"
#include "rig_fixture.hpp"
#include "rig_renderer.hpp"
#include "sdk.hpp"
#include <algorithm>
#include <limits>

class Textures final : public sh3::ports::IRigTextures {
  public:
    bool read(const sh3::domain::RigMaterial &m, std::uint8_t *out,
              std::size_t n) noexcept override {
        if (render_sdk::failure == "TEXTURE_READ_" + std::to_string(m.texture))
            return false;
        CHECK(n == m.width * m.height * 4);
        std::fill_n(out, n, 128);
        return true;
    }
};
int main(int argc, char **argv) {
    CHECK(argc == 2);
    using namespace render_sdk;
    using R = sh3::ports::RenderResult;
    rig = character = dynamic = true;
    const std::string scenario = argv[1];
    static sh3::domain::InspectionRig m;
    make_rig(m);
    m.index_count = 39;
    m.material_count = 13;
    for (unsigned i = 0; i < 13; ++i) {
        const auto w = i == 11 ? 512U : 128U, h = i == 11 ? 1024U : 128U;
        m.materials[i] = {i * 3, 3, i, w, h, i == 12 ? 1U : 0U, 0};
        rig_dimensions.emplace_back(w, h);
        for (unsigned j = 0; j < 3; ++j)
            m.indices[i * 3 + j] = j;
    }
    std::vector<sh3::domain::CharacterDrawVertex> mesh(39);
    for (auto &v : mesh)
        v = {{0, 0, -2, 1}, {1, 1, 1}, {0, 0}};
    const auto expect = [&] {
        auto *p = reinterpret_cast<unsigned char *>(mesh.data());
        expected_vertices.assign(p, p + mesh.size() * sizeof(mesh[0]));
    };
    expect();
    Textures textures;
    const bool init_failure = scenario.rfind("init_", 0) == 0;
    if (init_failure)
        failure = scenario.substr(5);
    {
        sh3::platform::ctr::RigRenderer renderer(m, textures);
        if (init_failure)
            CHECK(!renderer.ready());
        else {
            CHECK(renderer.ready());
            CHECK(renderer.present({}, mesh.data(), mesh.size()) == R::presented);
            const auto before = allocations;
            if (scenario == "invalid") {
                CHECK(renderer.present({}, nullptr, 39) == R::unavailable);
                CHECK(renderer.present({}, mesh.data(), 38) == R::unavailable);
                CHECK(renderer.present({0, 0, 0}, mesh.data(), 39) == R::invalid_camera);
                mesh[0].position[3] = std::numeric_limits<float>::quiet_NaN();
                CHECK(renderer.present({}, mesh.data(), 39) == R::unavailable);
            } else if (scenario == "busy") {
                failure = "FRAME_BEGIN";
                CHECK(renderer.present({}, mesh.data(), 39) == R::busy);
            } else if (scenario == "flush" || scenario == "draw") {
                failure = scenario == "flush" ? "VERTEX_FLUSH" : "DRAW_ON";
                CHECK(renderer.present({}, mesh.data(), 39) == R::unavailable);
                CHECK(!open_frame);
            } else {
                CHECK(scenario == "normal");
                for (unsigned i = 0; i < 1000; ++i) {
                    mesh[0].position[0] = i % 2 ? .1F : 0;
                    expect();
                    const sh3::domain::OrbitCamera camera =
                        i % 2 ? sh3::domain::OrbitCamera{0, .1F, .45F, {0, 1.32F, -1.98F}}
                              : sh3::domain::OrbitCamera{};
                    expected_focus[0] = camera.target.x;
                    expected_focus[1] = camera.target.y;
                    expected_focus[2] = camera.target.z;
                    CHECK(renderer.present(camera, mesh.data(), 39) == R::presented);
                }
                CHECK(frames == 1001 && draws == 13013);
            }
            CHECK(allocations == before);
        }
    }
    CHECK(acquired == released && !pending && !open_frame);
    m.bone_count = 0;
    const auto before = acquired;
    sh3::platform::ctr::RigRenderer invalid(m, textures);
    CHECK(!invalid.ready() && before == acquired);
}
