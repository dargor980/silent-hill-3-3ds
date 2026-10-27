#include "check.hpp"
#include "sh3/application/locomotion_probe.hpp"
#include "sh3/domain/locomotion_update.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include "sh3/platform/inspection_locomotion.hpp"
#include "sh3/platform/inspection_rig.hpp"
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <new>
#include <string>
#include <vector>

namespace {
bool track_allocations{};
unsigned allocations{}, fail_allocation{};
} // namespace
void *operator new(std::size_t n) {
    if (track_allocations && ++allocations == fail_allocation)
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
using Model = domain::InspectionLocomotion;
static Model out, model_copy;
static std::array<unsigned char, sizeof(Model)> before;
static domain::LocomotionState state;
static domain::LocomotionWorkspace workspace;
using Bytes = std::vector<std::uint8_t>;
Bytes wire, pixels[2];
unsigned opens{}, closes{}, reads{}, fail_open{}, fail_read{}, short_read{}, fail_close{};
std::size_t position{};
int active{};
bool io_error{}, watch{};
unsigned rejections{};
const std::array<const char *, 3> *expected_paths{};
void unchanged() {
    if (watch)
        CHECK(std::memcmp(&out, before.data(), sizeof(out)) == 0);
}
void put(Bytes &b, std::size_t at, std::uint32_t x, unsigned n = 4) {
    for (unsigned i = 0; i < n; ++i)
        b.at(at + i) = static_cast<std::uint8_t>(x >> (8 * i));
}
void add(Bytes &b, std::uint32_t x, unsigned n = 4) {
    const auto at = b.size();
    b.resize(at + n);
    put(b, at, x, n);
}
void number(Bytes &b, float f) {
    std::uint32_t x;
    std::memcpy(&x, &f, 4);
    add(b, x);
}
void crc(Bytes &b) { put(b, 60, platform::inspection_crc32(b.data() + 96, b.size() - 96)); }
Bytes fixture() {
    for (unsigned t = 0; t < 2; ++t) {
        pixels[t].resize(128 * 256 * 4);
        for (std::size_t i = 0; i < pixels[t].size(); ++i)
            pixels[t][i] = static_cast<std::uint8_t>(i * 17 + t * 23);
    }
    Bytes b{'S', '3', 'R', 'I', 'v', '2', 0, 0};
    b.resize(96);
    const std::uint32_t header[]{36, 58, 1, 3, 6, 2, 3, 2, 25, 1, 522, 525};
    for (unsigned i = 0; i < 12; ++i)
        put(b, 8 + 4 * i, header[i]);
    for (auto v : {0.F, 0.F, 0.F, .01F})
        number(b, v);
    for (unsigned i = 0; i < 36; ++i)
        add(b, i < 2 ? 0xffffffffU : 1);
    const unsigned bones[]{0,  1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11, 12, 13, 14, 15, 16, 17,
                           21, 24, 25, 26, 27, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42};
    const unsigned upper[]{1, 3, 5, 7, 8, 10, 12, 13, 14, 16, 17, 21, 27, 33, 35};
    for (auto bone : bones) {
        add(b, bone, 2);
        add(b, std::find(std::begin(upper), std::end(upper), bone) == std::end(upper) ? 1 : 2, 1);
        add(b, 0, 1);
    }
    const unsigned clips[][8]{{101, 10, 307, 0, 9, 1, 0, 0},
                              {109, 24, 1996, 80, 103, 1, 0, 10},
                              {113, 24, 2227, 176, 199, 1, 0, 34}};
    for (const auto &c : clips) {
        for (unsigned i = 0; i < 5; ++i)
            add(b, c[i], 2);
        add(b, c[5], 1);
        add(b, c[6], 1);
        add(b, c[7]);
        add(b, 0);
    }
    for (unsigned f = 0; f < 58; ++f)
        for (unsigned bone = 0; bone < 36; ++bone) {
            const auto source = f < 10 ? f : f < 34 ? f + 70 : f + 142;
            for (float v : {float(source + bone) / 16, float(bone) / 32, -0.F, 0.F, 0.F, 0.F, 1.F})
                number(b, v);
        }
    add(b, 1);
    for (unsigned i = 0; i < 16; ++i)
        number(b, i % 5 == 0 ? 1.F : 0.F);
    for (unsigned i = 0; i < 3; ++i) {
        for (unsigned j = 0; j < 8; ++j)
            add(b, j == 0 ? 16 + i : 0, 2);
        add(b, 2048, 2);
        add(b, 2047, 2);
        add(b, 0, 2);
        add(b, 0, 1);
        add(b, 2, 1);
        add(b, 0, 1);
        add(b, 255, 1);
        add(b, 0, 2);
    }
    for (auto i : {0, 1, 2, 2, 1, 0})
        add(b, unsigned(i), 2);
    for (unsigned t = 0; t < 2; ++t) {
        for (auto v : {3 * t, 3U, t, 128U, 256U, t,
                       platform::inspection_crc32(pixels[t].data(), pixels[t].size())})
            add(b, v);
    }
    put(b, 56, static_cast<std::uint32_t>(b.size() - 96));
    crc(b);
    return b;
}
FILE *open_file(const char *p, const char *) {
    unchanged();
    ++opens;
    if (expected_paths) {
        CHECK(opens <= expected_paths->size());
        if (std::strcmp(p, (*expected_paths)[opens - 1]) != 0)
            std::fprintf(stderr, "open path: expected '%s', got '%s'\n",
                         (*expected_paths)[opens - 1], p);
        CHECK(std::strcmp(p, (*expected_paths)[opens - 1]) == 0);
    }
    position = 0;
    io_error = false;
    if (opens == fail_open) {
        errno = ENOENT;
        return nullptr;
    }
    active = std::strstr(p, "texture-00.rgba") ? 0 : std::strstr(p, "texture-01.rgba") ? 1 : -1;
    return reinterpret_cast<FILE *>(&active);
}
std::size_t read_file(void *p, std::size_t size, std::size_t count, FILE *) {
    unchanged();
    CHECK(size == 1);
    ++reads;
    const auto &data = active < 0 ? wire : pixels[active];
    const auto n = std::min(count, data.size() - position);
    const auto actual = reads == short_read && n ? n - 1 : n;
    if (actual)
        std::memcpy(p, data.data() + position, actual);
    position += actual;
    io_error |= reads == fail_read; // ferror is sticky until fclose/clearerr.
    return actual;
}
int close_file(FILE *) {
    unchanged();
    return ++closes == fail_close ? -1 : 0;
}
auto api() {
    auto a = platform::system_stdio;
    a.open = open_file;
    a.read = read_file;
    a.error = +[](FILE *) noexcept {
        unchanged();
        return int(io_error);
    };
    a.close = close_file;
    return a;
}
void reset() {
    opens = closes = reads = fail_open = fail_read = short_read = fail_close = 0;
    allocations = fail_allocation = 0;
    std::memcpy(before.data(), &out, sizeof(out));
    watch = true;
}
void rejected(platform::LocomotionLoadResult r, E expected, const char *field = nullptr) {
    if (r.error != expected)
        std::fprintf(
            stderr,
            "case %u: expected %s, got %s (%s), opens/reads/closes %u/%u/%u, faults %u/%u/%u/%u\n",
            rejections, platform::file_error_name(expected), platform::file_error_name(r.error),
            r.field, opens, reads, closes, fail_open, fail_read, fail_close, fail_allocation);
    CHECK(r.error == expected);
    unchanged();
    if (field)
        CHECK(std::strcmp(r.field, field) == 0);
    CHECK(opens == closes || opens == closes + 1);
    ++rejections;
    watch = false;
}
void dump(const Model &m) {
    const auto &g = m.shared;
    std::printf("P %u %u %u %u %u\n", m.profile.id, m.profile.model_resource,
                m.profile.animation_resource, m.profile.ticks, m.inspection_hz);
    std::printf("F %.9g %.9g %.9g %.9g\n", double(g.center.x), double(g.center.y),
                double(g.center.z), double(g.scale));
    for (unsigned i = 0; i < g.bone_count; ++i)
        std::printf("B %u %d %u\n", m.source_bones[i], g.parents[i], m.channels[i]);
    for (const auto &c : m.profile.clips)
        std::printf("C %u %u %d %u %u %u %u %u 0\n", c.id, c.count, c.speed, c.start, c.end, c.loop,
                    c.trailing, c.packed_first);
    domain::InspectionLocomotionReader reader(m);
    for (const auto &c : m.profile.clips)
        for (unsigned f = 0; f < c.count; ++f)
            for (unsigned b = 0; b < g.bone_count; ++b) {
                domain::LocomotionTransform tr{};
                CHECK(reader.read(c.id, f, b, tr));
                std::printf("S %.9g %.9g %.9g", double(tr.translation.x), double(tr.translation.y),
                            double(tr.translation.z));
                for (auto v : tr.rotation)
                    std::printf(" %.9g", double(v));
                std::puts("");
            }
    for (unsigned i = 0; i < g.helper_count; ++i) {
        std::printf("H %u", g.targets[i]);
        for (auto v : g.helpers[i])
            std::printf(" %.9g", double(v));
        std::puts("");
    }
    for (unsigned i = 0; i < g.vertex_count; ++i) {
        const auto &v = g.vertices[i];
        std::printf("V");
        for (auto x : v.position)
            std::printf(" %d", x);
        for (auto x : v.normal)
            std::printf(" %d", x);
        for (auto x : v.uv)
            std::printf(" %d", x);
        for (auto x : v.weights)
            std::printf(" %u", x);
        std::printf(" %u %u %u %u 0\n", v.primary, v.count, v.helpers[0], v.helpers[1]);
    }
    std::printf("I");
    for (unsigned i = 0; i < g.index_count; ++i)
        std::printf(" %u", g.indices[i]);
    std::puts("");
    for (unsigned i = 0; i < g.material_count; ++i) {
        const auto &r = g.materials[i];
        std::printf("M %u %u %u %u %u %u %u\n", r.first, r.count, r.texture, r.width, r.height,
                    r.blend, r.crc);
    }
}
// Test-only replay anchor: reconstruct a stable local pose from SRI2 and a
// scalar phase, never from captured matrices/cache. Subsequent rows use only
// the public transaction API. This is not a runtime state-loading interface.
int trace(const Model &m) {
    unsigned clip{}, phase{};
    if (std::scanf("%u%u", &clip, &phase) != 2)
        return 3;
    const domain::InspectionLocomotionReader reader(m);
    if (domain::initialize_locomotion(m.profile, domain::locomotion_rig_skeleton(m), reader, state,
                                      workspace) != domain::LocomotionError::ok)
        return 3;
    state.clock = {1, clip, clip, domain::LocomotionMode::stable, phase, 0, false};
    unsigned request{};
    do {
        const auto error = domain::update_locomotion(
            m.profile, reader, request ? std::optional<std::uint32_t>(request) : std::nullopt, 2,
            state, workspace);
        if (error != domain::LocomotionError::ok)
            return 3;
        const auto &c = state.clock;
        std::printf("%u %u %u %u %u %u", c.source_id, c.target_id, unsigned(c.mode), c.counter,
                    c.blend, unsigned(c.saved_local_valid));
        for (unsigned b = 0; b < m.shared.bone_count; ++b)
            for (auto v : state.model[b])
                std::printf(" %.9g", double(v));
        std::puts("");
    } while (std::scanf("%u", &request) == 1);
    return std::feof(stdin) ? 0 : 3;
}
} // namespace
int main(int argc, char **argv) {
    if (argc > 1) {
        std::memcpy(before.data(), &out, sizeof(out));
        const auto r = argc > 2 ? platform::read_locomotion_bundle(argv[1], out)
                                : platform::read_locomotion_rig(argv[1], out);
        if (r.error != E::ok) {
            CHECK(std::memcmp(before.data(), &out, sizeof(out)) == 0);
            std::fprintf(stderr, "%s %s %u\n", platform::file_error_name(r.error), r.field, r.item);
            return 2;
        }
        if (argc == 3 && std::strcmp(argv[2], "trace") == 0)
            return trace(out);
        dump(out);
        return 0;
    }
    const auto good = fixture();
    wire = good;
    reset();
    CHECK(platform::read_locomotion_bundle("own", out, api()).error == E::ok);
    watch = false;
    CHECK(opens == 3 && closes == 3 && reads == 9);
    // libctru receives these literal paths. Host/emulator path normalization
    // must not hide an extra separator between the directory and file name.
    const std::array<const char *, 3> sd_paths{
        "sdmc:/3ds/sh3_heather_probe/heather.sri",
        "sdmc:/3ds/sh3_heather_probe/texture-00.rgba",
        "sdmc:/3ds/sh3_heather_probe/texture-01.rgba"};
    const std::array<const char *, 3> relative_paths{
        "own/heather.sri", "own/texture-00.rgba", "own/texture-01.rgba"};
    const std::array<const char *, 3> root_paths{
        "/heather.sri", "/texture-00.rgba", "/texture-01.rgba"};
    for (const auto *directory : {"sdmc:/3ds/sh3_heather_probe",
                                  "sdmc:/3ds/sh3_heather_probe/", "own", "own/", "/"}) {
        reset();
        expected_paths = std::strncmp(directory, "sdmc:", 5) == 0 ? &sd_paths
                         : directory[0] == '/' ? &root_paths : &relative_paths;
        CHECK(platform::read_locomotion_bundle(directory, out, api()).error == E::ok);
        CHECK(opens == 3 && closes == 3 && reads == 9);
        expected_paths = nullptr;
        watch = false;
    }
    CHECK(!domain::locomotion_rig_error(out));
    CHECK(!domain::valid_rig(out.shared));
    model_copy = out;
    reset();
    rejected({platform::read_inspection_rig("own", out.shared, api()), "SRI1"}, E::invalid_data);
    // Every callback saw the old output, including the last texture's close.
    auto bad = [&](std::size_t at, std::uint32_t value, unsigned n = 4, bool fix_crc = true) {
        wire = good;
        put(wire, at, value, n);
        if (fix_crc && at >= 96)
            crc(wire);
        reset();
        rejected(platform::read_locomotion_rig("own", out, api()),
                 at == 60 || (!fix_crc && at >= 96) ? E::verify_failed : E::invalid_data);
    };
    for (auto size : {0U, 1U, 35U, 37U, 73U, 74U, 0xffffffffU})
        bad(8, size);
    for (auto size : {0U, 57U, 59U, 64U, 65U, 0xffffffffU})
        bad(12, size);
    for (auto item : {16U, 20U, 24U, 28U})
        bad(item, 0xffffffffU);
    bad(20, 2);
    bad(24, 0);
    bad(24, 4);
    bad(28, 0);
    for (auto at : {32U, 36U, 40U, 44U, 48U, 52U, 56U})
        bad(at, 0);
    bad(56, 0xffffffffU);
    bad(60, 1);
    bad(4, '1', 1);
    bad(0, 'X', 1);
    for (unsigned at = 64; at < 96; ++at)
        bad(at, 1, 1);
    for (unsigned i = 0; i < 36; ++i) {
        bad(256 + i * 4, 65535, 2);
        bad(258 + i * 4, 0, 1);
        bad(259 + i * 4, 1, 1);
    }
    for (unsigned i = 0; i < 60; ++i)
        bad(400 + i, good[400 + i] ^ 1, 1);
    bad(112, 0);
    bad(116, 0xfffffffeU);
    bad(252, 36);
    for (auto bits : {0x7fc00000U, 0x7f800000U, 0xff800000U, 0x47c35080U}) {
        bad(96, bits);
        bad(460, bits);
        bad(58928, bits);
    }
    bad(108, 0);
    bad(108, 0xbf800000U);
    bad(484, 0);
    bad(484, 0x40000000U);
    bad(58924, 36);
    bad(58928 + 12, 0x3f800000U);
    const auto vertex = 58992U, index = vertex + 84, material = index + 12;
    bad(vertex + 22, 36, 1);
    bad(vertex + 23, 0, 1);
    bad(vertex + 23, 4, 1);
    bad(vertex + 16, 4097, 2);
    bad(vertex + 16, 0, 2);
    bad(vertex + 20, 1, 2);
    bad(vertex + 24, 1, 1);
    bad(vertex + 25, 0, 1);
    bad(vertex + 26, 1, 2);
    bad(index, 3, 2);
    for (auto entry : {0U, 4U, 8U, 12U, 16U, 20U})
        bad(material + entry, 0xffffffffU);
    bad(material + 4, 0);
    bad(material + 4, 4);
    bad(material + 28, 0);
    bad(material + 28 + 4, 0);
    wire = good;
    put(wire, material + 20, 1);
    put(wire, material + 48, 0);
    crc(wire);
    reset();
    rejected(platform::read_locomotion_rig("own", out, api()), E::invalid_data, "materials");
    wire = good;
    put(wire, material + 32, 0xffffffffU);
    crc(wire);
    reset();
    rejected(platform::read_locomotion_rig("own", out, api()), E::invalid_data);
    // Valid integer ranges but insufficient material coverage.
    wire.assign(good.begin(), good.end() - 28);
    put(wire, 28, 1);
    put(wire, 56, static_cast<std::uint32_t>(wire.size() - 96));
    crc(wire);
    reset();
    rejected(platform::read_locomotion_rig("own", out, api()), E::invalid_data, "materials");
    // Valid per-texture dimensions exceeding the total pixel budget.
    wire.assign(good.begin(), good.begin() + index);
    for (unsigned i = 0; i < 27; ++i)
        add(wire, i % 3, 2);
    for (unsigned i = 0; i < 9; ++i)
        for (auto x : {i * 3, 3U, i, 1024U, 1024U, 0U, 0U})
            add(wire, x);
    put(wire, 24, 27);
    put(wire, 28, 9);
    put(wire, 56, static_cast<std::uint32_t>(wire.size() - 96));
    crc(wire);
    reset();
    rejected(platform::read_locomotion_rig("own", out, api()), E::invalid_data, "materials");
    // Every header cut and both sides of every section/record boundary.
    std::vector<std::size_t> cuts;
    for (unsigned i = 0; i < 96; ++i)
        cuts.push_back(i);
    for (unsigned i = 96; i <= 460; i += 4)
        cuts.push_back(i);
    for (unsigned f = 0; f < 58; ++f) {
        cuts.push_back(460 + f * 36 * 28);
        cuts.push_back(460 + (f + 1) * 36 * 28 - 1);
    }
    for (auto at : {58924U, 58928U, 58992U, 59020U, 59048U, index, material, material + 28}) {
        cuts.push_back(at - 1);
        cuts.push_back(at);
        cuts.push_back(at + 1);
    }
    cuts.push_back(good.size() - 1);
    for (auto cut : cuts) {
        wire.assign(good.begin(), good.begin() + cut);
        reset();
        rejected(platform::read_locomotion_rig("own", out, api()), E::invalid_data);
    }
    wire = good;
    wire.push_back(0);
    reset();
    rejected(platform::read_locomotion_rig("own", out, api()), E::invalid_data);
    bad(460, good[460] ^ 1, 1, false);
    wire = good;
    for (unsigned i = 1; i <= 9; ++i) {
        reset();
        fail_read = i;
        rejected(platform::read_locomotion_bundle("own", out, api()), E::read_failed);
    }
    for (auto i : {1U, 2U, 4U, 5U, 7U, 8U}) {
        reset();
        short_read = i;
        rejected(platform::read_locomotion_bundle("own", out, api()), E::invalid_data);
    }
    for (unsigned i = 1; i <= 3; ++i) {
        reset();
        fail_open = i;
        rejected(platform::read_locomotion_bundle("own", out, api()), E::missing);
        reset();
        fail_close = i;
        rejected(platform::read_locomotion_bundle("own", out, api()), E::close_failed);
        reset();
        fail_allocation = i;
        track_allocations = true;
        const auto r = platform::read_locomotion_bundle("own", out, api());
        track_allocations = false;
        CHECK(allocations == i);
        rejected(r, E::read_failed);
    }
    reset();
    fail_read = 2;
    fail_close = 1;
    rejected(platform::read_locomotion_rig("own", out, api()), E::read_failed, "payload");
    for (bool bundle : {false, true}) {
        reset();
        auto a = api();
        a.open = +[](const char *, const char *) -> FILE * {
            unchanged();
            ++opens;
            errno = EACCES;
            return nullptr;
        };
        rejected(bundle ? platform::read_locomotion_bundle("own", out, a)
                        : platform::read_locomotion_rig("own", out, a),
                 E::read_failed, "open");
    }
    reset();
    auto a = api();
    a.open = +[](const char *p, const char *m) -> FILE * {
        auto *f = open_file(p, m);
        if (opens == 2) {
            errno = EACCES;
            return nullptr;
        }
        return f;
    };
    rejected(platform::read_locomotion_bundle("own", out, a), E::read_failed, "texture.open");
    for (auto path : {static_cast<const char *>(nullptr), ""}) {
        reset();
        rejected(platform::read_locomotion_rig(path, out, api()), E::invalid_target);
        reset();
        rejected(platform::read_locomotion_bundle(path, out, api()), E::invalid_target);
    }
    std::string long_root(512, 'a');
    reset();
    rejected(platform::read_locomotion_bundle(long_root.c_str(), out, api()), E::invalid_target);
    long_root.resize(499);
    reset();
    rejected(platform::read_locomotion_bundle(long_root.c_str(), out, api()), E::invalid_target,
             "texture.path");
    // All texture errors, including the last file, retain an already valid model.
    for (unsigned i = 0; i < 2; ++i) {
        const auto saved = pixels[i];
        pixels[i][17] ^= 1;
        reset();
        rejected(platform::read_locomotion_bundle("own", out, api()), E::verify_failed,
                 "texture.crc32");
        pixels[i] = saved;
        pixels[i].pop_back();
        reset();
        rejected(platform::read_locomotion_bundle("own", out, api()), E::invalid_data,
                 "texture.length");
        pixels[i] = saved;
        pixels[i].push_back(0);
        reset();
        rejected(platform::read_locomotion_bundle("own", out, api()), E::invalid_data,
                 "texture.length");
        pixels[i] = saved;
    }
    // Header rejection happens before any allocation; successful retry publishes a fresh model.
    wire = good;
    put(wire, 24, 0xffffffffU);
    reset();
    track_allocations = true;
    const auto invalid = platform::read_locomotion_rig("own", out, api());
    track_allocations = false;
    CHECK(allocations == 0);
    rejected(invalid, E::invalid_data);
    wire = good;
    reset();
    CHECK(platform::read_locomotion_rig("own", out, api()).error == E::ok);
    watch = false;
    CHECK(!domain::locomotion_rig_error(out));
    CHECK(out.shared.samples[58][0].rotation[3] == 0);
    CHECK(out.shared.materials[2].count == 0);
    const auto domain_bad = [&](auto change, const char *field) {
        out = model_copy;
        change(out);
        CHECK(std::strcmp(domain::locomotion_rig_error(out), field) == 0);
    };
    domain_bad([](auto &m) { m.profile.id = 0; }, "profile");
    domain_bad([](auto &m) { m.inspection_hz = 24; }, "profile");
    domain_bad([](auto &m) { m.shared.clip_id = 101; }, "profile");
    domain_bad([](auto &m) { m.shared.increment = 614; }, "profile");
    domain_bad([](auto &m) { m.shared.bone_count = 35; }, "counts");
    domain_bad([](auto &m) { m.shared.sample_count = 59; }, "counts");
    out = model_copy;
    domain::InspectionLocomotionReader reader(out);
    domain::LocomotionTransform tr{};
    for (const auto &c : out.profile.clips) {
        CHECK(reader.read(c.id, c.count - 1, 0, tr));
        CHECK(tr.translation.x == float(c.end) / 16);
        const auto previous = tr;
        CHECK(!reader.read(c.id, c.count, 0, tr));
        CHECK(std::memcmp(&tr, &previous, sizeof(tr)) == 0);
    }
    CHECK(!reader.read(0, 0, 0, tr));
    CHECK(!reader.read(101, 0, 36, tr));
    out.shared.bone_count = 74;
    CHECK(!reader.read(101, 0, 73, tr));
    out = model_copy;
    out.shared.sample_count = 65;
    CHECK(!reader.read(101, 0, 0, tr));
    out = model_copy;
    out.profile.clips[0].packed_first = 0xffffffffU;
    CHECK(!reader.read(101, 0, 0, tr));
    out = model_copy;
    out.profile.clips[0].packed_first = 57;
    CHECK(!reader.read(101, 1, 0, tr));
    out = model_copy;
    const auto skeleton = domain::locomotion_rig_skeleton(out);
    CHECK(domain::initialize_locomotion(out.profile, skeleton, reader, state, workspace) ==
          domain::LocomotionError::ok);
    for (unsigned i = 0; i < 500; ++i) {
        std::optional<std::uint32_t> request;
        if (i == 0)
            request = 109;
        if (i == 30)
            request = 113;
        if (i == 60)
            request = 101;
        CHECK(domain::update_locomotion(out.profile, reader, request, 2, state, workspace) ==
              domain::LocomotionError::ok);
    }
    // Loader -> concrete SRI2 reader -> application -> skin/sort, without a legacy SRI1 clock.
    struct Scene final : ports::IRigScene {
        domain::RigPalette palette{};
        domain::RigSortOrder order{};
        std::array<domain::RigVertexScratch, 3> scratch{};
        std::array<domain::CharacterDrawVertex, 6> vertices{};
        unsigned frames{};
        ports::RenderResult present_pose(const domain::OrbitCamera &camera,
                                         const domain::RigPose &pose) noexcept override {
            CHECK(domain::rig_draw(out.shared, pose, camera, palette, order, scratch.data(),
                                    scratch.size(), vertices.data(), vertices.size()));
            ++frames;
            return ports::RenderResult::presented;
        }
    } scene;
    application::LocomotionProbe app(scene, out.profile, skeleton, reader);
    CHECK(app.ready() && !domain::valid_rig(out.shared));
    track_allocations = true;
    allocations = 0;
    for (unsigned i = 0; i < 500; ++i) {
        application::LocomotionInput input{};
        input.next_clip = i == 0 || i == 30 || i == 60;
        app.step({}, input, .04F);
        CHECK(app.error() == domain::LocomotionError::ok);
    }
    track_allocations = false;
    CHECK(allocations == 0 && scene.frames == 500 && app.snapshot().clock.target_id == 101);
    std::printf("SRI2 native: %u rejections with byte-identical output; bundle/reader/500 updates "
                "PASS; model %zu bytes\n",
                rejections, sizeof(Model));
    return 0;
}
