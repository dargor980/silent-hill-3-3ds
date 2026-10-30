#include "check.hpp"
#include "sh3/platform/inspection_animation.hpp"
#include "sh3/platform/inspection_character.hpp"
#include "sh3/platform/inspection_character_world.hpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>

using namespace sh3;
namespace {
domain::PoseMatrix identity() { return {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1}; }
void fixture(domain::CharacterModel &m, domain::CharacterWorld &w) {
    m.vertex_count = m.index_count = 9;
    m.scale = .01F;
    m.targets = {0, 1, 2};
    for (auto &h : m.helpers)
        h = identity();
    for (unsigned i = 0; i < 9; ++i) {
        m.indices[i] = i;
        m.vertices[i].weights = {4096, 0, 0};
    }
    w.scale = .001F;
    for (unsigned i = 0; i < 3; ++i) {
        w.instances[i].id = i + 1;
        w.instances[i].model = identity();
        w.instances[i].model[12] = float(i * 11);
    }
}
} // namespace
int main(int argc, char **argv) {
    static domain::CharacterModel model;
    domain::CharacterWorld world;
    fixture(model, world);
    if (argc >= 2 && std::strcmp(argv[1], "--asset") == 0) {
        CHECK(argc == 7);
        std::uint32_t scm{}, san{};
        domain::InspectionClip clip;
        CHECK(platform::read_inspection_character(argv[2], model, platform::system_stdio, &scm) ==
              ports::FileError::ok);
        CHECK(platform::read_inspection_animation(argv[3], clip, platform::system_stdio, &san) ==
              ports::FileError::ok);
        CHECK(platform::read_character_world(argv[4], world, model, scm, san,
                                             std::strtoul(argv[5], nullptr, 10)) ==
              ports::FileError::ok);
        static std::array<domain::DeformedVertex, domain::character_vertex_limit> v;
        static std::array<domain::WorldPosition, domain::character_vertex_limit> scratch;
        static std::array<domain::CharacterDrawVertex, domain::character_index_limit * 3> out;
        const auto pose = domain::evaluate_pose(clip, std::strtoul(argv[6], nullptr, 10));
        CHECK(
            domain::character_draw(model, pose, v.data(), v.size(), out.data(), out.size(), true));
        CHECK(domain::place_character(world, model, v.data(), v.size(), scratch.data(),
                                      scratch.size(), out.data(), out.size()));
        for (unsigned j = 0; j < 3; ++j)
            for (std::size_t i = 0; i < model.vertex_count; ++i) {
                const auto p = domain::rebase_character_position(world.instances[j], world.origin,
                                                                 v[i].position);
                std::printf("%u %zu ", j, i);
                for (float x : v[i].position)
                    std::printf("%.9g ", double(x));
                for (float x : p)
                    std::printf("%.9g ", double(x));
                std::puts("");
            }
        return 0;
    }
    if (argc >= 2) {
        auto api = platform::system_stdio;
        if (argc == 3 && std::strcmp(argv[2], "read") == 0)
            api.error = +[](FILE *) noexcept { return 1; };
        if (argc == 3 && std::strcmp(argv[2], "short") == 0)
            api.read = +[](void *p, std::size_t s, std::size_t n, FILE *f) {
                return std::fread(p, s, n > 1 ? n - 1 : n, f);
            };
        if (argc == 3 && std::strcmp(argv[2], "close") == 0)
            api.close = +[](FILE *f) {
                std::fclose(f);
                return -1;
            };
        world.reference_counter = 777;
        auto result = platform::read_character_world(argv[1], world, model, 1, 2, 3, api);
        if (result != ports::FileError::ok) {
            CHECK(world.reference_counter == 777);
            return 2;
        }
        CHECK(world.reference_counter == 0);
        return 0;
    }
    CHECK(domain::valid_character_world(world, model));
    domain::CharacterInstance instance{
        1, {0, 0, -1, 0, -1, 0, 0, 0, 0, 1, 0, 0, 100011, -100007, 200013, 1}};
    const float w = 4095.0F / 4096;
    const auto p =
        domain::rebase_character_position(instance, {100000, -100000, 200000}, {2, -3, 5, w});
    CHECK(p[0] == 11 * w + 3 && p[1] == -7 * w + 5 && p[2] == 13 * w - 2 && p[3] == w);
    std::array<domain::DeformedVertex, 9> v{};
    for (auto &x : v)
        x.position = {2, -3, 5, w};
    std::array<domain::WorldPosition, 9> scratch{};
    std::array<domain::CharacterDrawVertex, 27> out{};
    CHECK(domain::place_character(world, model, v.data(), 9, scratch.data(), 9, out.data(), 27));
    CHECK(out[0].position[3] == w && out[9].position[0] > out[0].position[0]);
    CHECK(out[18].color.x == 1 && out[18].uv[0] == 0);
    CHECK(!domain::place_character(world, model, nullptr, 9, scratch.data(), 9, out.data(), 27));
    CHECK(!domain::place_character(world, model, v.data(), 8, scratch.data(), 9, out.data(), 27));
    CHECK(!domain::place_character(world, model, v.data(), 9, scratch.data(), 8, out.data(), 27));
    CHECK(!domain::place_character(world, model, v.data(), 9, scratch.data(), 9, out.data(), 26));
    v[0].position[0] = std::numeric_limits<float>::infinity();
    CHECK(!domain::place_character(world, model, v.data(), 9, scratch.data(), 9, out.data(), 27));
    for (int variant = 0; variant < 13; ++variant) {
        auto bad = world;
        switch (variant) {
        case 0:
            bad.instances[1].id = 1;
            break;
        case 1:
            bad.instances[0].id = 0;
            break;
        case 2:
            bad.instances[0].id = 65536;
            break;
        case 3:
            bad.instances[0].model[0] = -1;
            break;
        case 4:
            bad.instances[0].model[0] = 2;
            break;
        case 5:
            bad.instances[0].model[3] = 1;
            break;
        case 6:
            bad.instances[0].model[12] = 1000001;
            break;
        case 7:
            bad.instances[0].model[12] = std::numeric_limits<float>::quiet_NaN();
            break;
        case 8:
            bad.scale = 0;
            break;
        case 9:
            bad.scale = 1;
            break;
        case 10:
            bad.origin.x = 1000001;
            break;
        case 11:
            bad.reference_counter = domain::clip_period;
            break;
        case 12:
            bad.instances[0].model[4] = .1F;
            break;
        }
        CHECK(!domain::valid_character_world(bad, model));
    }
    CHECK(platform::read_character_world(nullptr, world, model, 1, 2, 3) ==
          ports::FileError::invalid_target);
    CHECK(platform::read_character_world("/missing.scw", world, model, 1, 2, 3) ==
          ports::FileError::missing);
}
