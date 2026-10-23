#include "check.hpp"
#include "sh3/domain/character_lighting.hpp"
#include "sh3/platform/inspection_animation.hpp"
#include "sh3/platform/inspection_character.hpp"
#include "sh3/platform/inspection_character_lighting.hpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>

using namespace sh3;
namespace {
domain::PoseMatrix identity() { return {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1}; }
bool near(float a, float b) { return std::abs(a - b) < 1e-5F; }
void fixture(domain::CharacterModel &m, domain::CharacterLighting &l) {
    m.vertex_count = m.index_count = 45;
    m.scale = .01F;
    m.targets = {0, 1, 2};
    for (auto &h : m.helpers)
        h = identity();
    for (unsigned i = 0; i < 45; ++i) {
        m.indices[i] = i;
        m.vertices[i].weights = {4096, 0, 0};
        m.vertices[i].position = {0, 0, 32};
        m.vertices[i].normal = {0, 0, 4096};
    }
    l.model_to_capture = identity();
    l.ambient = {.1F, .2F, .3F, 120};
    l.spot = {{0, 0, 0}, {0, 0, 1}, {10, 12, 14, 2}, {1, 0, .25F, .25F}};
    for (unsigned i = 0; i < 15; ++i)
        l.ranges[i] = {i * 3, 3, i * 3, 3, {2, 3, 4}, {5, 6, 7}};
}
} // namespace
int main(int argc, char **argv) {
    static domain::CharacterModel model;
    domain::CharacterLighting light;
    fixture(model, light);
    if (argc >= 2 && std::strcmp(argv[1], "--asset") == 0) {
        CHECK(argc == 7);
        std::uint32_t scm{}, san{};
        domain::InspectionClip clip;
        CHECK(platform::read_inspection_character(argv[2], model, platform::system_stdio, &scm) ==
              ports::FileError::ok);
        CHECK(platform::read_inspection_animation(argv[3], clip, platform::system_stdio, &san) ==
              ports::FileError::ok);
        CHECK(platform::read_character_lighting(argv[4], light, model, scm, san,
                                                std::strtoul(argv[5], nullptr, 10)) ==
              ports::FileError::ok);
        if (std::strcmp(argv[6], "stdin") == 0) {
            unsigned range{};
            domain::DeformedVertex v;
            while (std::scanf("%u %f %f %f %f %f %f %f", &range, &v.position[0], &v.position[1],
                              &v.position[2], &v.position[3], &v.normal[0], &v.normal[1],
                              &v.normal[2]) == 8) {
                CHECK(range < 15);
                domain::LightColor c{};
                CHECK(domain::shade_character_vertex(light, light.ranges[range], v, c));
                for (float x : c)
                    std::printf("%.9g ", double(x));
                std::puts("");
            }
        } else {
            const auto pose = domain::evaluate_pose(clip, std::strtoul(argv[6], nullptr, 10));
            static std::array<domain::DeformedVertex, domain::character_vertex_limit> vertices;
            static std::array<domain::CharacterDrawVertex, domain::character_index_limit> draw;
            static std::array<domain::LightVector, domain::character_vertex_limit> colors;
            CHECK(domain::character_draw(model, pose, vertices.data(), vertices.size(), draw.data(),
                                         draw.size(), true));
            CHECK(domain::light_character(light, model, vertices.data(), vertices.size(),
                                          colors.data(), colors.size(), draw.data(), draw.size()));
            for (const auto &r : light.ranges)
                for (std::size_t i = r.first_vertex; i < r.first_vertex + r.vertex_count; ++i) {
                    domain::LightColor c{};
                    CHECK(domain::shade_character_vertex(light, r, vertices[i], c));
                    for (float x : vertices[i].position)
                        std::printf("%.9g ", double(x));
                    for (float x : vertices[i].normal)
                        std::printf("%.9g ", double(x));
                    for (float x : c)
                        std::printf("%.9g ", double(x));
                    for (float x : colors[i])
                        std::printf("%.9g ", double(x));
                    std::puts("");
                }
        }
        return 0;
    }
    if (argc >= 2) {
        auto api = platform::system_stdio;
        if (argc == 3 && std::strcmp(argv[2], "read") == 0)
            api.error = +[](FILE *) { return 1; };
        if (argc == 3 && std::strcmp(argv[2], "short") == 0)
            api.read = +[](void *p, std::size_t s, std::size_t n, FILE *f) {
                return std::fread(p, s, n > 1 ? n - 1 : n, f);
            };
        if (argc == 3 && std::strcmp(argv[2], "close") == 0)
            api.close = +[](FILE *f) {
                std::fclose(f);
                return -1;
            };
        light.reference_counter = 777;
        const auto result = platform::read_character_lighting(argv[1], light, model, 1, 2, 3, api);
        if (result != ports::FileError::ok) {
            CHECK(light.reference_counter == 777);
            return 2;
        }
        CHECK(light.reference_counter == 0);
        return 0;
    }
    CHECK(domain::valid_character_lighting(light, model));
    domain::DeformedVertex v{{0, 0, 2, 1}, {0, 0, 1}};
    domain::LightColor c{};
    CHECK(domain::shade_character_vertex(light, light.ranges[0], v, c));
    CHECK(near(c[0], 5.5F) && near(c[1], 10.2F) && near(c[2], 16.1F) && near(c[3], 120.5F));
    auto normal2 = v;
    normal2.normal[2] = 2;
    domain::LightColor doubled{};
    CHECK(domain::shade_character_vertex(light, light.ranges[0], normal2, doubled));
    CHECK(c == doubled);
    light.directionals[0] = {{0, 0, 2}, {1, 2, 3, 4}};
    CHECK(domain::shade_character_vertex(light, light.ranges[0], normal2, c));
    CHECK(near(c[0], 13.5F) && near(c[3], 136.5F));
    light.directionals[0] = {};
    light.model_to_capture[14] = 10;
    v.position[3] = .5F;
    CHECK(domain::shade_character_vertex(light, light.ranges[0], v, c));
    CHECK(near(c[0], .5F + 10.0F / 7)); // translation uses W: Z=7, not 12.
    light.model_to_capture = identity();
    v = {{0, 0, 0, 1}, {0, 0, 1}};
    c = {9, 8, 7, 6};
    CHECK(!domain::shade_character_vertex(light, light.ranges[0], v, c));
    CHECK(c[0] == 9);
    v.position[0] = std::numeric_limits<float>::quiet_NaN();
    CHECK(!domain::shade_character_vertex(light, light.ranges[0], v, c));
    std::array<domain::DeformedVertex, 45> vertices;
    std::array<domain::CharacterDrawVertex, 45> draw, original;
    std::array<domain::LightVector, 45> colors;
    domain::SkeletonPose pose{identity(), identity(), identity()};
    CHECK(domain::character_draw(model, pose, vertices.data(), 45, draw.data(), 45, true));
    original = draw;
    light.ranges[1].diffuse = {0, 0, 0};
    light.ranges[1].ambient = {0, 0, 0};
    CHECK(domain::light_character(light, model, vertices.data(), 45, colors.data(), 45, draw.data(),
                                  45));
    CHECK(draw[0].color.x == 5.0F / 128 && draw[3].color.x == 0);
    for (std::size_t i = 0; i < 45; ++i) {
        CHECK(draw[i].position == original[i].position);
        CHECK(draw[i].uv == original[i].uv);
    }
    CHECK(!domain::light_character(light, model, nullptr, 45, colors.data(), 45, draw.data(), 45));
    CHECK(!domain::light_character(light, model, vertices.data(), 44, colors.data(), 45,
                                   draw.data(), 45));
    CHECK(!domain::light_character(light, model, vertices.data(), 45, colors.data(), 44,
                                   draw.data(), 45));
    CHECK(!domain::light_character(light, model, vertices.data(), 45, colors.data(), 45,
                                   draw.data(), 44));
    vertices[0].position = {0, 0, 0, 1};
    CHECK(!domain::light_character(light, model, vertices.data(), 45, colors.data(), 45,
                                   draw.data(), 45));
    auto bad = light;
    bad.ranges[1].first_vertex = 0;
    CHECK(!domain::valid_character_lighting(bad, model));
    bad = light;
    bad.ranges[0].vertex_count = 0xffffffff;
    CHECK(!domain::valid_character_lighting(bad, model));
    bad = light;
    bad.ranges[14].index_count = 6;
    CHECK(!domain::valid_character_lighting(bad, model));
    model.indices[0] = 4;
    CHECK(!domain::valid_character_lighting(light, model));
    model.indices[0] = 0;
    bad = light;
    bad.model_to_capture[0] = -1;
    CHECK(!domain::valid_character_lighting(bad, model));
    bad = light;
    bad.model_to_capture[0] = 2;
    CHECK(!domain::valid_character_lighting(bad, model));
    bad = light;
    bad.model_to_capture[3] = 1;
    CHECK(!domain::valid_character_lighting(bad, model));
    bad = light;
    bad.ambient[0] = 17;
    CHECK(!domain::valid_character_lighting(bad, model));
    bad = light;
    bad.directionals[1].color[0] = -1;
    CHECK(!domain::valid_character_lighting(bad, model));
    bad = light;
    bad.spot.attenuation[0] = std::numeric_limits<float>::infinity();
    CHECK(!domain::valid_character_lighting(bad, model));
    CHECK(platform::read_character_lighting(nullptr, light, model, 1, 2, 3) ==
          ports::FileError::invalid_target);
    CHECK(platform::read_character_lighting("/missing.scl", light, model, 1, 2, 3) ==
          ports::FileError::missing);
}
