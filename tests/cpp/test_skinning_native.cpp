#include "check.hpp"
#include "render_doubles/citro3d.h"
#include "rig_fixture.hpp"
#include "sh3/domain/skinning_plan.hpp"
#include <cstring>
#include <iostream>
#include <limits>
#include <string_view>

using namespace sh3::domain;
namespace {
InspectionRig model;
RigPose pose;
RigPalette palette;
SkinRows scratch, rows, previous;
SkinPlanWorkspace work;
std::array<SkinVertex, rig_indices> vertices, old_vertices;
std::array<std::uint16_t, rig_indices> indices, old_indices;
std::array<SkinBatch, rig_indices / 3> batches, old_batches;
constexpr PoseMatrix identity{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
void hex(const void *p, std::size_t n) {
    const auto *bytes = static_cast<const unsigned char *>(p);
    for (std::size_t i = 0; i < n; ++i)
        std::printf("%02x", bytes[i]);
}
template <class T> void read(T &v) {
    long double x;
    CHECK(bool(std::cin >> x));
    v = T(x);
}
template <class T, std::size_t N> void read(std::array<T, N> &v) {
    for (auto &x : v)
        read(x);
}
void vectors() {
    unsigned cases;
    read(cases);
    for (unsigned i = 0; i < cases; ++i) {
        model = {};
        pose.fill(identity);
        unsigned n;
        read(n);
        for (unsigned j = 0; j < n; ++j) {
            unsigned id;
            read(id);
            CHECK(id < rig_bones);
            read(pose[id]);
            model.bone_count = std::max(model.bone_count, id + 1);
        }
        read(n);
        for (unsigned j = 0; j < n; ++j) {
            unsigned id;
            read(id);
            CHECK(id >= rig_bones && id < rig_bones + rig_helpers);
            id -= rig_bones;
            read(model.targets[id]);
            read(model.helpers[id]);
            model.helper_count = std::max(model.helper_count, id + 1);
        }
        std::array<std::uint16_t, 30> slots{};
        read(n);
        CHECK(n <= slots.size());
        for (unsigned j = 0; j < n; ++j)
            read(slots[j]);
        CharacterVertex v{};
        read(v.position);
        read(v.uv);
        read(v.weights);
        read(v.count);
        unsigned id;
        read(id);
        v.primary = std::uint8_t(id);
        v.helpers = {255, 255};
        for (unsigned j = 1; j < v.count; ++j) {
            read(id);
            v.helpers[j - 1] = std::uint8_t(id - rig_bones);
        }
        PoseMatrix instance;
        read(instance);
        SkinVertex packed;
        CHECK(skin_vertex(v, slots.data(), n, packed));
        rig_palette(model, pose, palette);
        CHECK(skin_rows(palette, instance, scratch, rows));
        hex(&packed, sizeof(packed));
        std::printf(" ");
        for (unsigned j = 0; j < n; ++j)
            for (auto &r : rows[slots[j]]) {
                const auto u = FVec4_New(r[0], r[1], r[2], r[3]);
                hex(&u, sizeof(u));
            }
        std::puts("");
    }
}
void plan_input() {
    make_rig(model);
    model.bone_count = rig_bones;
    model.helper_count = rig_helpers;
    for (unsigned i = 0; i < rig_bones; ++i) {
        model.parents[i] = -1;
        for (unsigned f = 0; f < 2; ++f)
            model.samples[f][i] = {{}, {0, 0, 0, 1}};
    }
    for (auto &m : model.helpers)
        m = identity;
    model.targets.fill(0);
    unsigned capacity;
    read(capacity);
    read(model.vertex_count);
    read(model.index_count);
    read(model.material_count);
    CHECK(model.vertex_count <= rig_vertices && model.index_count <= rig_indices &&
          model.material_count <= rig_materials);
    for (unsigned i = 0; i < model.vertex_count; ++i) {
        auto &v = model.vertices[i];
        read(v.position);
        read(v.uv);
        read(v.weights);
        read(v.count);
        read(v.primary);
        read(v.helpers);
    }
    for (unsigned i = 0; i < model.index_count; ++i)
        read(model.indices[i]);
    for (unsigned i = 0; i < model.material_count; ++i) {
        auto &m = model.materials[i];
        read(m.first);
        read(m.count);
        read(m.blend);
        m.texture = i;
        m.width = m.height = 128;
    }
    SkinCounts n;
    const SkinStorage storage{vertices.data(),
                              indices.data(),
                              batches.data(),
                              {vertices.size(), indices.size(), batches.size()}};
    if (!skin_plan(model, work, n, &storage, capacity)) {
        std::puts("REJECT");
        return;
    }
    std::printf("%zu %zu %zu\n", n.vertices, n.indices, n.batches);
    for (std::size_t i = 0; i < n.batches; ++i) {
        const auto &b = batches[i];
        std::printf("%u %u %u", b.first, b.count, b.material);
        for (unsigned j = 0; j < b.matrix_count; ++j)
            std::printf(" %u", b.slots[j]);
        std::puts("");
    }
    hex(indices.data(), n.indices * 2);
    std::puts("");
    hex(vertices.data(), n.vertices * sizeof(SkinVertex));
    std::puts("");
}
void unit() {
    WorkTrace trace;
    trace.begin();
    {
        WorkInterval interval(&trace, WorkPhase::palette);
        interval.next(WorkPhase::deform_cpu);
    }
    trace.end(0, 0);
    CHECK(trace.delivered == 1 && trace.sample.begin_tick == 0 && trace.sample.end_tick == 0);
    make_rig(model);
    SkinCounts n;
    SkinStorage storage{vertices.data(),
                        indices.data(),
                        batches.data(),
                        {vertices.size(), indices.size(), batches.size()}};
    CHECK(skin_plan(model, work, n, &storage) && n.vertices == 3 && n.indices == 3 &&
          n.batches == 1);
    old_vertices = vertices;
    old_indices = indices;
    old_batches = batches;
    const auto check_unchanged = [&] {
        CHECK(std::memcmp(vertices.data(), old_vertices.data(), sizeof(vertices)) == 0);
        CHECK(indices == old_indices &&
              std::memcmp(batches.data(), old_batches.data(), sizeof(batches)) == 0);
    };
    for (unsigned which = 0; which < 6; ++which) {
        auto bad = storage;
        if (which == 0)
            bad.capacity.vertices = 2;
        if (which == 1)
            bad.capacity.indices = 2;
        if (which == 2)
            bad.capacity.batches = 0;
        if (which == 3)
            bad.vertices = nullptr;
        if (which == 4)
            bad.indices = nullptr;
        if (which == 5)
            bad.batches = nullptr;
        CHECK(!skin_plan(model, work, n, &bad));
        check_unchanged();
    }
    for (auto capacity : {0U, 1U, 31U}) {
        CHECK(!skin_plan(model, work, n, &storage, capacity));
        check_unchanged();
    }
    model.indices[0] = 8192;
    CHECK(!skin_plan(model, work, n, &storage));
    check_unchanged();
    make_rig(model);
    // Duplicate original vertices are reused inside a batch but not across materials.
    model.materials[1].blend = 0;
    model.indices[3] = model.indices[0];
    model.indices[4] = model.indices[1];
    model.indices[5] = model.indices[0];
    CHECK(skin_plan(model, work, n, &storage) && n.vertices == 5 && n.batches == 2 &&
          indices[3] == 3 && indices[5] == 3);
    model.materials[0].blend = model.materials[1].blend = 1;
    CHECK(skin_plan(model, work, n, &storage) && !n.vertices && !n.indices && !n.batches);
    SkinVertex packed{}, old{};
    const std::uint16_t good[]{0, 73}, duplicate[]{0, 0}, wrong[]{73, 0}, high[]{0, 201};
    auto v = model.vertices[0];
    CHECK(skin_vertex(v, good, 2, packed));
    old = packed;
    CHECK(!skin_vertex(v, nullptr, 2, packed));
    CHECK(!skin_vertex(v, good, 0, packed));
    CHECK(!skin_vertex(v, good, 31, packed));
    for (auto slots : {duplicate, wrong, high})
        CHECK(!skin_vertex(v, slots, 2, packed));
    v.primary = 2;
    CHECK(!skin_vertex(v, good, 2, packed));
    v.primary = 0;
    for (auto count : {0U, 4U}) {
        v.count = std::uint8_t(count);
        CHECK(!skin_vertex(v, good, 2, packed));
    }
    v.count = 2;
    for (auto weights :
         {std::array<std::uint16_t, 3>{4097, 0, 0}, {2048, 2047, 1}, {1, 1, 0}, {4096, 4096, 0}}) {
        v.weights = weights;
        CHECK(!skin_vertex(v, good, 2, packed));
    }
    CHECK(std::memcmp(&old, &packed, sizeof(old)) == 0);
    palette.fill(identity);
    PoseMatrix instance = identity;
    instance[12] = 100000;
    instance[14] = 140000;
    CHECK(skin_rows(palette, instance, scratch, rows));
    previous = rows;
    palette[200][15] =
        std::numeric_limits<float>::infinity(); // Last column xyz is what GPU consumes.
    palette[200][14] = std::numeric_limits<float>::infinity();
    CHECK(!skin_rows(palette, instance, scratch, rows) && rows == previous);
    palette.fill(identity);
    instance[0] = std::numeric_limits<float>::quiet_NaN();
    CHECK(!skin_rows(palette, instance, scratch, rows) && rows == previous);
}
} // namespace
int main(int argc, char **argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--vectors")
        vectors();
    else if (argc == 2 && std::string_view(argv[1]) == "--plan")
        plan_input();
    else
        unit();
}
