#pragma once
#include "sh3/domain/inspection_rig.hpp"
inline void make_rig(sh3::domain::InspectionRig &m) {
    m = {};
    m.bone_count = 2;
    m.sample_count = 2;
    m.helper_count = 1;
    m.vertex_count = 6;
    m.index_count = 6;
    m.material_count = 2;
    m.clip_id = 17;
    m.increment = 1024;
    m.scale = .1F;
    m.parents[0] = -1;
    m.parents[1] = 0;
    for (int f = 0; f < 2; ++f) {
        m.samples[f][0] = {{float(f) * 2, 0, 0}, {0, 0, 0, 1}};
        m.samples[f][1] = {{0, 1, 0}, {0, 0, 0, float(f ? -1 : 1)}};
    }
    m.helpers[0] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1};
    m.targets[0] = 1;
    for (int i = 0; i < 6; ++i) {
        auto &v = m.vertices[i];
        v.position = {std::int16_t(i % 3 * 16), 0, std::int16_t(i < 3 ? 0 : 16)};
        v.normal = {0, 4096, 0};
        v.uv = {std::int16_t(i % 3 * 1024), 0};
        v.weights = {2048, 2047, 0};
        v.primary = 0;
        v.count = 2;
        v.helpers = {0, 255};
        m.indices[i] = i;
    }
    m.materials[0] = {0, 3, 0, 128, 128, 0, 0};
    m.materials[1] = {3, 3, 1, 256, 128, 1, 0};
}
