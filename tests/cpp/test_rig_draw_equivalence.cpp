#include "check.hpp"
#include "rig_fixture.hpp"
#include <algorithm>
#include <cmath>
#include <vector>

namespace {
using namespace sh3::domain;
static InspectionRig model;
static RigPose pose;
static RigPalette palette;
static RigSortOrder order;
static std::array<RigVertexScratch, rig_vertices> scratch;
static std::array<CharacterDrawVertex, rig_indices> output;

// Scalar reference deliberately repeats all work for every index, like the baseline.
CharacterDrawVertex reference(std::size_t index) {
    const auto &v = model.vertices[index];
    std::array<float, 4> position{};
    for (unsigned influence = 0; influence < v.count; ++influence) {
        const auto &matrix = palette[influence ? rig_bones + v.helpers[influence - 1] : v.primary];
        for (unsigned row = 0; row < 4; ++row) {
            float value = matrix[12 + row];
            for (unsigned column = 0; column < 3; ++column)
                value += matrix[4 * column + row] * (float(v.position[column]) / 16);
            position[row] += float(v.weights[influence]) / 4096 * value;
        }
    }
    const float w = position[3];
    return {{-(position[0] - model.center.x * w) * model.scale + camera_target.x * w,
             -(position[1] - model.center.y * w) * model.scale + camera_target.y * w,
             (position[2] - model.center.z * w) * model.scale + camera_target.z * w, w},
            {1, 1, 1}, {float(v.uv[0]) / 4096, float(v.uv[1]) / 4096}};
}
} // namespace

int main() {
    make_rig(model);
    model.helper_count = 2;
    model.helpers[1] = model.helpers[0];
    model.helpers[1][14] = -.75F;
    model.targets[1] = 0;
    model.center = {.4F, -.2F, .7F};
    model.index_count = rig_indices;
    model.materials[0].count = 9000;
    model.materials[1].first = 9000;
    model.materials[1].count = 9000;
    for (unsigned i = 0; i < model.index_count; ++i)
        model.indices[i] = (i * 5) % 6;
    for (unsigned i = 0; i < model.vertex_count; ++i) {
        auto &v = model.vertices[i];
        v.count = 1 + i % 3;
        v.weights = v.count == 1 ? std::array<std::uint16_t, 3>{4096, 0, 0}
                    : v.count == 2 ? std::array<std::uint16_t, 3>{2048, 2047, 0}
                                   : std::array<std::uint16_t, 3>{1365, 1365, 1364};
        v.helpers = {std::uint8_t(v.count > 1 ? 0 : 255),
                     std::uint8_t(v.count > 2 ? 1 : 255)};
        v.uv[0] = -2048;
    }
    CHECK(valid_rig(model));
    std::vector<CharacterDrawVertex> expected(rig_indices);
    std::vector<std::pair<float, unsigned>> sorted(3000);
    for (unsigned sample = 0; sample < 32; ++sample) {
        const OrbitCamera camera = sample % 2 ? OrbitCamera{-.4F, .1F, .45F, {0, 1.32F, -1.98F}}
                                             : OrbitCamera{.5F, .7F, 8};
        evaluate_rig(model, sample * 257, pose);
        CHECK(rig_draw(model, pose, camera, palette, order, scratch.data(), scratch.size(),
                       output.data(), output.size()));
        for (unsigned i = 0; i < model.index_count; ++i)
            expected[i] = reference(model.indices[i]);
        const auto eye = camera_eye(camera);
        const Vec3 forward{camera.target.x - eye.x, camera.target.y - eye.y, camera.target.z - eye.z};
        for (unsigned i = 0; i < sorted.size(); ++i) {
            float depth = 0;
            for (unsigned j = 0; j < 3; ++j) {
                const auto &p = expected[9000 + i * 3 + j].position;
                depth += (p[0] * forward.x + p[1] * forward.y + p[2] * forward.z) / p[3];
            }
            sorted[i] = {depth, i};
        }
        std::stable_sort(sorted.begin(), sorted.end(), [](auto a, auto b) { return a.first > b.first; });
        for (unsigned i = 0; i < model.index_count; ++i) {
            const auto source = i < 9000 ? i : 9000 + sorted[(i - 9000) / 3].second * 3 + i % 3;
            const auto &a = output[i], &b = expected[source];
            CHECK(a.position == b.position && a.uv == b.uv);
            CHECK(a.color.x == b.color.x && a.color.y == b.color.y && a.color.z == b.color.z);
        }
        CHECK(valid_rig_draw(output.data(), model.index_count));
    }
}
