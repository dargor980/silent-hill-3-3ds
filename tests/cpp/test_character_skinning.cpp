#include "check.hpp"
#include "sh3/domain/character_skinning.hpp"
#include "sh3/platform/inspection_animation.hpp"
#include "sh3/platform/inspection_character.hpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>

namespace {
using namespace sh3;
domain::PoseMatrix identity() { return {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1}; }
bool near(float a, float b) { return std::abs(a - b) < 1e-5F; }
} // namespace
int main(int argc, char **argv) {
    using namespace sh3;
    static domain::CharacterModel m;
    if (argc >= 2) {
        auto api = platform::system_stdio;
        if (argc == 3 && std::strcmp(argv[2], "close-failure") == 0)
            api.close = +[](FILE *f) -> int {
                std::fclose(f);
                return -1;
            };
        if (argc == 3 && std::strcmp(argv[2], "read-failure") == 0)
            api.error = +[](FILE *) -> int { return 1; };
        if (argc == 3 && std::strcmp(argv[2], "short-read") == 0)
            api.read = +[](void *p, std::size_t s, std::size_t n, FILE *f) -> std::size_t {
                return std::fread(p, s, n > 1 ? n - 1 : n, f);
            };
        if (platform::read_inspection_character(argv[1], m, api) != ports::FileError::ok) {
            CHECK(m.vertex_count == 0);
            return 2;
        }
        if (argc == 4) {
            domain::InspectionClip clip;
            CHECK(platform::read_inspection_animation(argv[2], clip) == ports::FileError::ok);
            const auto pose = domain::evaluate_pose(clip, std::strtoul(argv[3], nullptr, 10));
            static std::array<domain::DeformedVertex, domain::character_vertex_limit> scratch;
            static std::array<domain::CharacterDrawVertex, domain::character_index_limit> draw;
            CHECK(domain::character_draw(m, pose, scratch.data(), scratch.size(), draw.data(),
                                         draw.size()));
            for (std::size_t i = 0; i < m.vertex_count; ++i) {
                for (auto x : scratch[i].position)
                    std::printf("%.9g ", double(x));
                for (auto x : scratch[i].normal)
                    std::printf("%.9g ", double(x));
                std::puts("");
            }
        }
        return 0;
    }
    m.vertex_count = m.index_count = 3;
    m.indices = {0, 1, 2};
    m.targets = {0, 1, 2};
    for (auto &h : m.helpers)
        h = identity();
    for (std::size_t i = 0; i < 3; ++i) {
        auto &v = m.vertices[i];
        v.position = {16, 32, 48};
        v.normal = {4096, 0, 0};
        v.weights = {4096, 0, 0};
    }
    CHECK(domain::valid_character(m));
    domain::SkeletonPose pose{identity(), identity(), identity()};
    pose[0][12] = 3;
    pose[1][13] = 4;
    pose[2][14] = 5;
    auto palette = domain::character_palette(m, pose);
    auto v = domain::deform_character_vertex(m.vertices[0], palette);
    CHECK((v.position == std::array<float, 4>({4, 2, 3, 1})));
    CHECK((v.normal == std::array<float, 3>({1, 0, 0})));
    // Noncommuting transform: helper translation then target rotation.
    m.helpers[0][12] = 2;
    m.targets[0] = 1;
    pose[1] = {0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0, 4, 0, 1};
    auto &vertex = m.vertices[0];
    vertex.count = 3;
    vertex.weights = {2048, 1023, 1023};
    vertex.helpers = {0, 2};
    palette = domain::character_palette(m, pose);
    v = domain::deform_character_vertex(vertex, palette);
    const float q = 1023.0F / 4096;
    CHECK(near(v.position[0], 2 - q));
    CHECK(near(v.position[1], 1 + 9 * q));
    CHECK(near(v.position[2], 1.5F + 11 * q));
    CHECK(v.position[3] == 4094.0F / 4096);
    CHECK(near(v.normal[0], .5F + q) && near(v.normal[1], q));
    m.center = {2, 3, 4};
    m.scale = .01F;
    std::array<domain::DeformedVertex, 3> scratch;
    std::array<domain::CharacterDrawVertex, 3> draw;
    CHECK(domain::character_draw(m, pose, scratch.data(), 3, draw.data(), 3));
    CHECK(near(draw[0].position[0], (v.position[0] - 2 * v.position[3]) * .01F));
    CHECK(
        near(draw[0].position[2], -(v.position[2] - 4 * v.position[3]) * .01F - 2 * v.position[3]));
    CHECK(near(draw[0].position[1],
               -(v.position[1] - 3 * v.position[3]) * .01F + .75F * v.position[3]));
    CHECK(draw[0].position[3] == v.position[3]);
    vertex.uv = {-4096, 2048};
    CHECK(domain::character_draw(m, pose, scratch.data(), 3, draw.data(), 3, true));
    CHECK(draw[0].uv[0] == -1 && draw[0].uv[1] == .5F);
    CHECK(draw[0].color.x == 1 && draw[0].color.y == 1 && draw[0].color.z == 1);
    draw[0].uv[0] = std::numeric_limits<float>::infinity();
    CHECK(!domain::valid_character_draw(draw.data(), 3));
    draw[0].uv[0] = -1;
    CHECK(!domain::character_draw(m, pose, nullptr, 3, draw.data(), 3));
    CHECK(!domain::character_draw(m, pose, scratch.data(), 2, draw.data(), 3));
    CHECK(!domain::character_draw(m, pose, scratch.data(), 3, draw.data(), 2));
    CHECK(!domain::valid_character_draw(nullptr, 3));
    CHECK(!domain::valid_character_draw(draw.data(), 2));
    draw[0].position[3] = 0;
    CHECK(!domain::valid_character_draw(draw.data(), 3));
    draw[0].position[3] = 1;
    draw[0].color.x = -1;
    CHECK(!domain::valid_character_draw(draw.data(), 3));
    vertex.weights[0] = 2040;
    CHECK(!domain::valid_character(m));
    vertex.weights[0] = 2048;
    vertex.helpers[0] = 3;
    CHECK(!domain::valid_character(m));
    vertex.helpers[0] = 0;
    m.indices[0] = 3;
    CHECK(!domain::valid_character(m));
    m.indices[0] = 0;
    m.helpers[0][3] = 1;
    CHECK(!domain::valid_character(m));
    m.helpers[0][3] = 0;
    m.scale = std::numeric_limits<float>::quiet_NaN();
    CHECK(!domain::valid_character(m));
    CHECK(platform::read_inspection_character(nullptr, m) == ports::FileError::invalid_target);
    CHECK(platform::read_inspection_character("/nonexistent/character.scm", m) ==
          ports::FileError::missing);
}
