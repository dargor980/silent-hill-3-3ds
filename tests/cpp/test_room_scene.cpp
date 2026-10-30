#include "check.hpp"
#include "rig_fixture.hpp"
#include "sh3/domain/inspection_movement.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include "sh3/platform/inspection_locomotion.hpp"
#include "sh3/platform/room_scene.hpp"
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <new>
#include <vector>

namespace {
bool track{};
unsigned allocations{}, fail_allocation{};
} // namespace
void *operator new(std::size_t n) {
    if (track && ++allocations == fail_allocation)
        throw std::bad_alloc();
    if (auto *p = std::malloc(n ? n : 1))
        return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void *operator new(std::size_t n, const std::nothrow_t &) noexcept {
    try {
        return ::operator new(n);
    } catch (const std::bad_alloc &) {
        return nullptr;
    }
}
void *operator new[](std::size_t n, const std::nothrow_t &) noexcept {
    try {
        return ::operator new[](n);
    } catch (const std::bad_alloc &) {
        return nullptr;
    }
}
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
#if defined(__cpp_sized_deallocation)
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
#endif

namespace {
using namespace sh3;
using E = ports::FileError;
using Bytes = std::vector<std::uint8_t>;
static domain::RoomMap map, previous;
static domain::InspectionRig rig;
static domain::RoomFrame frame, old_frame;
static domain::RoomWorkspace work;
Bytes wire;
unsigned calls{}, short_call{}, error_call{}, open_failure{}, close_failure{}, closed{};
std::size_t cursor{};
std::FILE *open_file(const char *, const char *) {
    cursor = calls = closed = 0;
    if (open_failure) {
        errno = open_failure == 1 ? ENOENT : EACCES;
        return nullptr;
    }
    return reinterpret_cast<std::FILE *>(1);
}
std::size_t read_file(void *p, std::size_t size, std::size_t n, std::FILE *) {
    CHECK(size == 1);
    ++calls;
    if (calls == short_call)
        return 0;
    n = std::min(n, wire.size() - cursor);
    std::memcpy(p, wire.data() + cursor, n);
    cursor += n;
    return n;
}
int error_file(std::FILE *) noexcept { return calls == error_call; }
int close_file(std::FILE *) {
    ++closed;
    return close_failure ? -1 : 0;
}
const platform::StdioApi api{open_file,  read_file,   std::fwrite,
                             error_file, std::fflush, close_file};
void put(Bytes &b, std::size_t at, std::uint32_t v) {
    for (unsigned j = 0; j < 4; ++j)
        b.at(at + j) = std::uint8_t(v >> (8 * j));
}
void number(Bytes &b, std::size_t at, float f) {
    std::uint32_t v;
    std::memcpy(&v, &f, 4);
    put(b, at, v);
}
void crc() { put(wire, 20, platform::inspection_crc32(wire.data() + 32, wire.size() - 32)); }
Bytes fixture() {
    Bytes b(32 + 3 * 16 + 9 * 36);
    std::memcpy(b.data(), "S3RMv1\0\0", 8);
    put(b, 8, 3);
    put(b, 12, 9);
    put(b, 16, b.size() - 32);
    put(b, 28, 1);
    for (unsigned i = 0; i < 3; ++i) {
        put(b, 32 + i * 16, 100 + i);
        put(b, 36 + i * 16, i * 3);
        put(b, 40 + i * 16, 3);
        put(b, 44 + i * 16, i ? 1 : 0);
    }
    for (unsigned i = 0; i < 9; ++i) {
        const float values[]{
            float(i % 3), 0, float(int(i / 3) * 100 - 100), 1, .55F, .58F, .62F, 0, 1};
        for (unsigned j = 0; j < 9; ++j)
            number(b, 80 + i * 36 + j * 4, values[j]);
    }
    put(b, 20, platform::inspection_crc32(b.data() + 32, b.size() - 32));
    return b;
}
void reject(E error) {
    CHECK(platform::read_room_map("own", map, api) == error);
    CHECK(std::memcmp(&map, &previous, sizeof(map)) == 0);
}
void reader_tests() {
    wire = fixture();
    CHECK(platform::read_room_map("own", map, api) == E::ok && closed == 1);
    CHECK(map.shape_count == 3 && map.vertex_count == 9);
    CHECK(map.vertices[3].position[0] == 0 && map.vertices[3].position[2] == 0);
    previous = map;
    CHECK(platform::read_room_map(nullptr, map, api) == E::invalid_target);
    CHECK(platform::read_room_map("", map, api) == E::invalid_target);
    open_failure = 1;
    reject(E::missing);
    open_failure = 2;
    reject(E::read_failed);
    open_failure = 0;
    for (auto n : {1U, 2U}) {
        short_call = n;
        reject(E::invalid_data);
    }
    short_call = 0;
    for (auto n : {1U, 3U}) {
        error_call = n;
        reject(E::read_failed);
    }
    error_call = 0;
    close_failure = 1;
    reject(E::close_failed);
    close_failure = 0;
    for (unsigned n : {1U, 2U}) {
        track = true;
        allocations = 0;
        fail_allocation = n;
        reject(E::read_failed);
        track = false;
    }
    fail_allocation = 0;
    for (auto at : {0U, 8U, 12U, 16U, 28U}) {
        wire = fixture();
        put(wire, at, 0);
        reject(E::invalid_data);
    }
    for (const auto &entry :
         std::initializer_list<std::pair<unsigned, unsigned>>{{8, 32}, {12, 27903}, {12, 8}}) {
        wire = fixture();
        put(wire, entry.first, entry.second);
        reject(E::invalid_data);
    }
    wire = fixture();
    wire.push_back(1);
    reject(E::invalid_data);
    wire = fixture();
    wire.back() ^= 1;
    reject(E::verify_failed);
    for (const auto &entry : std::initializer_list<std::pair<unsigned, float>>{
             {92, .5F},
             {80, 32769},
             {80, std::numeric_limits<float>::infinity()},
             {96, -1},
             {100, 2},
             {108, 9},
             {112, std::numeric_limits<float>::quiet_NaN()}}) {
        wire = fixture();
        number(wire, entry.first, entry.second);
        crc();
        reject(E::invalid_data);
    }
    wire = fixture();
    put(wire, 44, 2);
    crc();
    reject(E::invalid_data);
    wire = fixture();
    CHECK(platform::read_room_map("own", map, api) == E::ok);
}
void original_materials() {
    const auto old = fixture();
    std::vector<std::uint8_t> v(32 + 3 * 24 + 9 * 16 + 9 * 36);
    std::memcpy(v.data(), "S3RMv2\0\0", 8);
    put(v, 8, 3);
    put(v, 12, 9);
    put(v, 16, v.size() - 32);
    put(v, 28, 2);
    for (unsigned i = 0; i < 3; ++i) {
        put(v, 32 + i * 24, 100 + i);
        put(v, 36 + i * 24, i * 3);
        put(v, 40 + i * 24, 3);
        put(v, 48 + i * 24, i);
        put(v, 52 + i * 24, i != 1);
    }
    for (unsigned i = 0; i < 9; ++i) {
        put(v, 104 + i * 16, 512);
        put(v, 108 + i * 16, 512);
        put(v, 116 + i * 16, i == 0 ? 6 : i == 2 ? 5 : 4);
    }
    std::memcpy(v.data() + 248, old.data() + 80, 9 * 36);
    wire = v;
    crc();
    v = wire;
    CHECK(platform::read_room_map("original", map, api) == E::ok);
    previous = map;
    for (const auto &entry : std::initializer_list<std::pair<unsigned, unsigned>>{
             {28, 3}, {48, 9}, {52, 2}, {104, 256}, {108, 0}, {116, 3}, {116, 7}, {44, 2}}) {
        wire = v;
        put(wire, entry.first, entry.second);
        crc();
        reject(E::invalid_data);
    }
    wire = v;
    wire.back() ^= 1;
    reject(E::verify_failed);
    wire = v;
    close_failure = 1;
    reject(E::close_failed);
    close_failure = 0;
    make_rig(rig);
    domain::RoomMemory legacy, original;
    CHECK(domain::room_memory(rig, legacy));
    CHECK(domain::room_memory(map, rig, original));
    CHECK(original.textures == legacy.textures + 9 * 1024 * 1024);
    CHECK(original.texture_staging >= 1024 * 1024);
    static domain::RoomMap copy;
    copy = map;
    domain::room_diagnostic_colors(map, copy.vertices.data());
    CHECK(std::memcmp(copy.vertices.data(), map.vertices.data(), 9 * 36) == 0);
    domain::RigPose pose{};
    domain::evaluate_rig(rig, 0, pose);
    domain::PoseMatrix instance;
    CHECK(domain::make_inspection_movement_model({100275, 0, 140000}, 0, instance));
    track = true;
    allocations = 0;
    CHECK(domain::room_frame(map, rig, pose, instance, work, frame));
    CHECK(allocations == 0);
    track = false;
    CHECK(frame.ranges[0].pass == domain::RoomPass::map_blend && frame.ranges[0].first == 0);
    CHECK(frame.ranges[1].pass == domain::RoomPass::map_cutout && frame.ranges[1].first == 6);
    CHECK(frame.ranges[0].texture == rig.material_count + 1);
    CHECK(frame.ranges[1].texture == rig.material_count + 3);
    CHECK(frame.ranges[2].pass == domain::RoomPass::opaque);
    for (auto n : {1U, 10U}) {
        copy = map;
        copy.material_count = n;
        CHECK(!domain::valid_room_map(copy));
    }
    copy = map;
    copy.material_count = 0;
    CHECK(!domain::valid_room_map(copy));
    copy = map;
    copy.shapes[1].glass = 1;
    CHECK(!domain::valid_room_map(copy));
    copy = map;
    copy.shape_count = 0;
    CHECK(!domain::room_memory(copy, rig, original));
    // Input size, CRC and alpha orientation are independent of the renderer/SDK.
    std::vector<std::uint8_t> pixels(512 * 512 * 4), gpu(pixels.size(), 77);
    for (unsigned y = 0; y < 512; ++y)
        for (unsigned x = 0; x < 512; ++x) {
            const auto at = (y * 512 + x) * 4;
            pixels[at] = x & 255;
            pixels[at + 1] = y & 255;
            pixels[at + 2] = (x + y) & 255;
            pixels[at + 3] = (x ^ y) & 255;
        }
    CHECK(!platform::upload_room_texture(nullptr, pixels.size(), gpu.data(), gpu.size()));
    CHECK(!platform::upload_room_texture(pixels.data(), pixels.size(), nullptr, gpu.size()));
    CHECK(!platform::upload_room_texture(pixels.data(), pixels.size(), pixels.data(), gpu.size()));
    CHECK(!platform::upload_room_texture(pixels.data(), pixels.size() - 1, gpu.data(), gpu.size()));
    CHECK(!platform::upload_room_texture(pixels.data(), pixels.size(), gpu.data(), gpu.size() - 1));
    CHECK(gpu[0] == 77);
    CHECK(platform::upload_room_texture(pixels.data(), pixels.size(), gpu.data(), gpu.size()));
    for (unsigned tile = 0; tile < 4096; ++tile)
        for (unsigned code = 0; code < 64; ++code) {
            unsigned x = (tile % 64) * 8, y = (tile / 64) * 8;
            for (unsigned bit = 0; bit < 3; ++bit) {
                x += ((code >> (bit * 2)) & 1) << bit;
                y += ((code >> (bit * 2 + 1)) & 1) << bit;
            }
            for (unsigned c = 0; c < 4; ++c)
                CHECK(gpu[(tile * 64 + code) * 4 + c] == pixels[(y * 512 + x) * 4 + 3 - c]);
        }
    wire = fixture();
    CHECK(platform::read_room_map("own", map, api) == E::ok);
}
void diagnostic_colors() {
    static domain::RoomMap source, original;
    source.shape_count = 3;
    source.vertex_count = 18;
    source.shapes[0] = {11, 0, 12, 0};
    source.shapes[1] = {12, 12, 3, 0};
    source.shapes[2] = {13, 15, 3, 1};
    for (unsigned i = 0; i < source.vertex_count; ++i)
        source.vertices[i] = {{0, 0, 0, 1}, {.55F, .58F, .62F}, {.25F, .75F}};
    // Horizontal, reversed winding, vertical, degenerate, another shape, glass.
    source.vertices[1].position[0] = 1;
    source.vertices[2].position[2] = 1;
    source.vertices[4].position[2] = 1;
    source.vertices[5].position[0] = 1;
    source.vertices[7].position[1] = 1;
    source.vertices[8].position[2] = 1;
    source.vertices[13].position[0] = source.vertices[16].position[0] = 1;
    source.vertices[14].position[2] = source.vertices[17].position[2] = 1;
    CHECK(domain::valid_room_map(source));
    original = source;
    std::array<domain::CharacterDrawVertex, 18> colored{};
    std::copy_n(source.vertices.begin(), colored.size(), colored.begin());
    track = true;
    allocations = 0;
    domain::room_diagnostic_colors(source, colored.data());
    CHECK(allocations == 0);
    track = false;
    CHECK(std::memcmp(&source, &original, sizeof(source)) == 0);
    for (unsigned i = 0; i < colored.size(); ++i) {
        CHECK(colored[i].position == source.vertices[i].position);
        CHECK(colored[i].uv == source.vertices[i].uv);
        CHECK(domain::valid_room_vertex(colored[i]));
        if (i >= 15)
            CHECK(std::memcmp(&colored[i], &source.vertices[i], sizeof(colored[i])) == 0);
    }
    // Analytic axis normals under the unit key direction: no copied implementation.
    CHECK(std::abs(colored[0].color.x - .68F * .864F) < 1e-6F);
    CHECK(std::abs(colored[6].color.x - .68F * .6464F) < 1e-6F);
    CHECK(std::abs(colored[9].color.x - .68F * .65F) < 1e-6F);
    CHECK(colored[0].color.x == colored[3].color.x);  // two-sided, winding invariant
    CHECK(colored[0].color.x != colored[12].color.x); // separate shapes remain distinct
    for (unsigned i = 0; i < 15; i += 3)
        CHECK(std::memcmp(&colored[i].color, &colored[i + 1].color, sizeof(domain::Vec3)) == 0 &&
              std::memcmp(&colored[i].color, &colored[i + 2].color, sizeof(domain::Vec3)) == 0);
    const auto once = colored;
    domain::room_diagnostic_colors(source, colored.data());
    CHECK(std::memcmp(colored.data(), once.data(), sizeof(colored)) == 0);
}
void domain_tests() {
    make_rig(rig);
    domain::RigPose pose{};
    domain::evaluate_rig(rig, 0, pose);
    domain::PoseMatrix instance;
    CHECK(domain::make_inspection_movement_model({100275, 0, 140000}, 0, instance));
    const auto p = domain::room_position(instance, {2, -3, 4, .5F});
    CHECK(std::abs(p[0] - (2 + 275 * .5F) * .002F) < 1e-7F && p[3] == .5F);
    CHECK(std::abs(p[1] - .006F) < 1e-7F && std::abs(p[2] + .008F) < 1e-7F);
    domain::RoomMemory memory;
    CHECK(domain::room_memory(rig, memory) && memory.total < 64 * 1024 * 1024);
    track = true;
    allocations = 0;
    CHECK(domain::room_frame(map, rig, pose, instance, work, frame));
    CHECK(allocations == 0);
    track = false;
    CHECK(frame.vertex_count == 12 && frame.ranges[0].pass == domain::RoomPass::neutral);
    CHECK(frame.ranges[1].pass == domain::RoomPass::opaque);
    bool glass = false, hair = false;
    double previous_depth = 1e100;
    const auto camera = domain::room_camera();
    for (unsigned i = 2; i < frame.range_count; ++i) {
        const auto &r = frame.ranges[i];
        glass |= r.pass == domain::RoomPass::glass;
        hair |= r.pass == domain::RoomPass::hair;
        for (unsigned j = r.first; j < r.first + r.count; j += 3) {
            double d = 0;
            for (unsigned k = 0; k < 3; ++k) {
                const auto &v = frame.vertices[j + k].position;
                d += (double(v[0]) * (camera.target.x - camera.eye.x) +
                      double(v[1]) * (camera.target.y - camera.eye.y) +
                      double(v[2]) * (camera.target.z - camera.eye.z)) /
                     v[3];
            }
            CHECK(d <= previous_depth);
            previous_depth = d;
        }
    }
    CHECK(glass && hair);
    old_frame = frame;
    // Hostile instance, pose and geometry must not publish even a partial range/count.
    for (auto at : {0U, 3U, 12U, 15U}) {
        auto bad = instance;
        bad[at] = std::numeric_limits<float>::quiet_NaN();
        CHECK(!domain::room_frame(map, rig, pose, bad, work, frame));
    }
    auto bad = instance;
    bad[0] = 2;
    CHECK(!domain::room_frame(map, rig, pose, bad, work, frame));
    bad = instance;
    bad[0] = -1;
    CHECK(!domain::room_frame(map, rig, pose, bad, work, frame));
    bad = instance;
    bad[3] = 1;
    CHECK(!domain::room_frame(map, rig, pose, bad, work, frame));
    bad = instance;
    bad[15] = 0;
    CHECK(!domain::room_frame(map, rig, pose, bad, work, frame));
    auto broken = pose;
    broken[0][15] = 0;
    CHECK(!domain::room_frame(map, rig, broken, instance, work, frame));
    broken = pose;
    broken[0][12] = 1000000;
    broken[0][0] = 1000000;
    rig.vertices[0].position[0] = 160;
    CHECK(!domain::room_frame(map, rig, broken, instance, work, frame));
    rig.vertices[0].position[0] = 0;
    CHECK(std::memcmp(&old_frame, &frame, sizeof(frame)) == 0);
    previous = map;
    for (auto n : {0U, 32U}) {
        map.shape_count = n;
        CHECK(!domain::valid_room_map(map));
    }
    map = previous;
    for (auto n : {0U, 27903U, 8U}) {
        map.vertex_count = n;
        CHECK(!domain::valid_room_map(map));
    }
    map = previous;
    for (auto value : {0U, 4U, 12U}) {
        map.shapes[0].count = value;
        CHECK(!domain::valid_room_map(map));
    }
    map = previous;
    map.shapes[0].offset = 0;
    CHECK(!domain::valid_room_map(map));
    map = previous;
    map.shapes[1].offset = map.shapes[0].offset;
    CHECK(!domain::valid_room_map(map));
    map = previous;
    map.shapes[0].first = 1;
    CHECK(!domain::valid_room_map(map));
    map = previous;
    map.shape_count = 2;
    CHECK(!domain::valid_room_map(map));
    map = previous;
    map.shapes[0].glass = 2;
    CHECK(!domain::valid_room_map(map));
    map = previous;
    map.vertices[0].position[3] = .9999F;
    CHECK(!domain::valid_room_map(map));
    map = previous;
    map.shapes[2].count = 99;
    map.vertex_count = 105;
    CHECK(!domain::valid_room_map(map));
    map = previous;
    auto v = map.vertices[0];
    for (float x : {-1.F, 2.F, std::numeric_limits<float>::quiet_NaN()}) {
        v.color.x = x;
        CHECK(!domain::valid_room_vertex(v));
    }
    v = map.vertices[0];
    v.position[3] = .9F;
    CHECK(!domain::valid_room_vertex(v));
    v.position[3] = 1.1F;
    CHECK(!domain::valid_room_vertex(v));
    v.position[3] = 1;
    v.position[0] = 5000;
    CHECK(!domain::valid_room_vertex(v));
    v = map.vertices[0];
    v.uv[1] = -9;
    CHECK(!domain::valid_room_vertex(v));
    rig.materials[0].width = rig.materials[0].height = 1024;
    CHECK(!domain::room_memory(rig, memory)); // Staging must not exceed 2 MiB.
    make_rig(rig);
    rig.bone_count = 0;
    CHECK(!domain::room_memory(rig, memory));
    CHECK(!domain::room_frame(map, rig, pose, instance, work, frame));
    make_rig(rig);
    // Repeated equal-depth triangles, all transparent and all opaque, no hidden allocation.
    for (auto &vtx : map.vertices)
        vtx.position = {0, 0, 0, 1};
    for (auto blend : {0U, 1U}) {
        rig.materials[0].blend = rig.materials[1].blend = blend;
        track = true;
        allocations = 0;
        for (unsigned i = 0; i < 100; ++i)
            CHECK(domain::room_frame(map, rig, pose, instance, work, frame));
        CHECK(allocations == 0);
        track = false;
        old_frame = frame;
        domain::PreparedRoomScene prepared(map, rig);
        CHECK(prepared.ready());
        CHECK(prepared.frame(pose, instance, work, frame));
        CHECK(std::memcmp(&frame, &old_frame, sizeof(frame)) == 0);
        auto invalid_instance = instance;
        invalid_instance[15] = 0;
        CHECK(!prepared.frame(pose, invalid_instance, work, frame));
        CHECK(std::memcmp(&frame, &old_frame, sizeof(frame)) == 0);
    }
}
void output(const void *p, std::size_t n) {
    std::cout.write(static_cast<const char *>(p), n);
    CHECK(std::cout.good());
}
class Sample final : public domain::LocomotionSampleReader {
  public:
    const domain::InspectionRig &model;
    unsigned index{};
    explicit Sample(const domain::InspectionRig &m) : model(m) {}
    bool read(std::uint32_t, std::uint32_t, std::uint32_t bone,
              domain::LocomotionTransform &out) const noexcept override {
        out = {model.samples[index][bone].translation, model.samples[index][bone].rotation};
        return true;
    }
};
void capture(const char *root, bool diagnostic) {
    std::uint32_t bytes{};
    std::cin.read(reinterpret_cast<char *>(&bytes), 4);
    CHECK(bytes <= 32 + 31 * 24 + 9 * 16 + 27900 * 36);
    wire.resize(bytes);
    std::cin.read(reinterpret_cast<char *>(wire.data()), bytes);
    CHECK(std::cin.good() && platform::read_room_map("stdin", map, api) == E::ok);
    static domain::InspectionLocomotion model;
    CHECK(platform::read_locomotion_bundle(root, model).error == E::ok);
    domain::RoomMemory memory;
    CHECK(domain::room_memory(map, model.shared, memory));
    const std::uint64_t ledger[]{memory.textures,          memory.texture_staging,
                                 memory.map_resident,      memory.dynamic_resident,
                                 memory.model_and_scratch, memory.loader_staging,
                                 memory.platform_reserve,  memory.total};
    output(ledger, sizeof(ledger));
    const auto camera = domain::room_camera();
    const float camera_values[]{camera.eye.x,    camera.eye.y,      camera.eye.z,
                                camera.target.x, camera.target.y,   camera.target.z,
                                camera.fov,      camera.near_plane, camera.far_plane};
    output(camera_values, sizeof(camera_values));
    output(&map.shape_count, 4);
    output(&map.vertex_count, 4);
    for (unsigned i = 0; i < map.shape_count; ++i)
        output(&map.shapes[i], 16); // Stable capture protocol; SRM2 metadata checked separately.
    if (diagnostic) {
        std::copy_n(map.vertices.begin(), map.vertex_count, previous.vertices.begin());
        domain::room_diagnostic_colors(map, previous.vertices.data());
    }
    output(diagnostic ? previous.vertices.data() : map.vertices.data(),
           map.vertex_count * sizeof(domain::CharacterDrawVertex));
    Sample source(model.shared);
    const auto skeleton = domain::locomotion_rig_skeleton(model);
    static domain::LocomotionPoseScratch scratch;
    std::uint32_t count{};
    std::cin.read(reinterpret_cast<char *>(&count), 4);
    CHECK(count <= 2048);
    for (unsigned i = 0; i < count; ++i) {
        std::uint32_t sample{};
        float p[4]{};
        std::cin.read(reinterpret_cast<char *>(&sample), 4);
        std::cin.read(reinterpret_cast<char *>(p), 16);
        CHECK(std::cin.good() && sample < model.shared.sample_count);
        source.index = sample;
        CHECK(domain::initialize_locomotion_pose(skeleton, source, scratch) ==
              domain::LocomotionError::ok);
        domain::PoseMatrix instance;
        CHECK(domain::make_inspection_movement_model({p[0], p[1], p[2]}, p[3], instance));
        track = true;
        allocations = 0;
        CHECK(domain::room_frame(map, model.shared, scratch.model, instance, work, frame));
        CHECK(allocations == 0);
        track = false;
        output(&frame.vertex_count, 4);
        output(&frame.range_count, 4);
        output(frame.ranges.data(), frame.range_count * sizeof(domain::RoomRange));
        output(frame.vertices.data(), frame.vertex_count * sizeof(domain::CharacterDrawVertex));
    }
}
} // namespace
int main(int argc, char **argv) {
    if (argc == 3 &&
        (std::string(argv[1]) == "capture" || std::string(argv[1]) == "capture-diagnostic")) {
        capture(argv[2], std::string(argv[1]) == "capture-diagnostic");
        return 0;
    }
    CHECK(argc == 1);
    reader_tests();
    original_materials();
    diagnostic_colors();
    domain_tests();
    std::cout << "Shared room: transforms, W, global transparency, budgets, atomicity and no "
                 "allocations PASS\n";
}
