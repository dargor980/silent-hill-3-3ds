#include "check.hpp"
#include "movement_controls.hpp"
#include "room_main.hpp"
#include "room_renderer.hpp"
#include "room_sdk.hpp"
#include "sh3/application/room_loop.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include "sh3/platform/skinning_capture.hpp"
#include <algorithm>
#include <cstring>
#include <limits>
#include <new>

namespace {
unsigned allocations{}, nothrow_calls{}, fail_nothrow{};
}
void *operator new(std::size_t n) {
    ++allocations;
    if (auto *p = std::malloc(n ? n : 1))
        return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void *operator new(std::size_t n, const std::nothrow_t &) noexcept {
    if (++nothrow_calls == fail_nothrow)
        return nullptr;
    try {
        return ::operator new(n);
    } catch (...) {
        return nullptr;
    }
}
void *operator new[](std::size_t n, const std::nothrow_t &t) noexcept {
    return ::operator new(n, t);
}
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
#if defined(__cpp_sized_deallocation)
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
#endif
namespace {
using namespace sh3;
using namespace room_sdk;
using R = ports::RenderResult;
using E = ports::FileError;
using S = domain::SessionState;
unsigned opened{}, closed{}, reads{}, fail_open{}, fail_read{}, fail_close{}, read_error{},
    mutation{};
bool io_error{};
const char *mapped_root{}, *expected_prefix{};
std::FILE *open_file(const char *p, const char *m) {
    if (++opened == fail_open)
        return nullptr;
    if (mapped_root) {
        const auto prefix = std::strlen(expected_prefix);
        CHECK(std::strncmp(p, expected_prefix, prefix) == 0);
        CHECK(p[prefix] && !std::strchr(p + prefix, '/'));
        std::array<char, 512> path{};
        const auto size = std::snprintf(path.data(), path.size(), "%s/%s", mapped_root, p + prefix);
        CHECK(size > 0 && std::size_t(size) < path.size());
        return std::fopen(path.data(), m);
    }
    return std::fopen(p, m);
}
std::size_t read_file(void *p, std::size_t a, std::size_t b, std::FILE *f) {
    ++reads;
    if (reads == fail_read)
        return 0;
    if (reads == read_error) {
        io_error = true;
        return 0;
    }
    const auto n = std::fread(p, a, b, f);
    if (reads == 1 && mutation && b == 596 && n == 596) {
        auto *raw = static_cast<std::uint8_t *>(p);
        if (mutation <= 8) {
            const unsigned offsets[]{0, 0, 8, 12, 16, 20, 24, 28, 32};
            raw[offsets[mutation]] ^= 1;
        } else {
            float value = std::numeric_limits<float>::quiet_NaN();
            unsigned at = mutation == 9 ? 36 : mutation == 10 ? 48 : mutation == 11 ? 68 : 80;
            std::memcpy(raw + at, &value, 4);
        }
        if (mutation >= 9) {
            auto crc = platform::inspection_crc32(raw + 32, 564);
            std::memcpy(raw + 12, &crc, 4);
        }
    }
    return n;
}
int error_file(std::FILE *f) noexcept { return io_error || std::ferror(f); }
int close_file(std::FILE *f) {
    auto r = std::fclose(f);
    return ++closed == fail_close ? -1 : r;
}
platform::StdioApi api{open_file, read_file, std::fwrite, error_file, std::fflush, close_file};
void io_reset() {
    opened = closed = reads = 0;
    io_error = false;
    fail_open = fail_read = fail_close = read_error = mutation = 0;
}
void literal_paths(const char *root, std::unique_ptr<platform::RoomAssets> &assets) {
    for (auto directory :
         {"sdmc:/3ds/sh3_heather_room/", "sdmc:/3ds/sh3_heather_room", "room/", "room", "/"}) {
        io_reset();
        mapped_root = root;
        expected_prefix = std::strncmp(directory, "sdmc:", 5) == 0 ? "sdmc:/3ds/sh3_heather_room/"
                          : directory[0] == '/'                    ? "/"
                                                                   : "room/";
        CHECK(platform::read_room_runtime(directory, assets, api).error == E::ok);
        platform::RoomTextures textures(directory, api);
        std::array<std::uint8_t, 256 * 256 * 4> pixels{};
        domain::RigMaterial glass{0, 96, 13, 256, 256, 1, assets->map.glass_crc};
        CHECK(textures.read(glass, pixels.data(), pixels.size()));
        CHECK(opened == closed);
        mapped_root = expected_prefix = nullptr;
    }
    io_reset();
}
void loader(const char *root, std::unique_ptr<platform::RoomAssets> &assets) {
    CHECK(platform::read_room_runtime(root, assets).error == E::ok);
    literal_paths(root, assets);
    auto *old = assets.get();
    CHECK(platform::read_room_runtime(nullptr, assets).error == E::invalid_target);
    CHECK(platform::read_room_runtime("", assets).error == E::invalid_target);
    std::array<char, 512> long_path{};
    long_path.fill('a');
    long_path.back() = 0;
    CHECK(platform::read_room_runtime(long_path.data(), assets).error == E::invalid_target);
    for (unsigned i = 1; i <= 12; ++i) {
        io_reset();
        mutation = i;
        CHECK(platform::read_room_runtime(root, assets, api).error != E::ok && assets.get() == old);
        CHECK(opened == closed);
    }
    io_reset();
    CHECK(platform::read_room_runtime(root, assets, api).error == E::ok);
    old = assets.get();
    const auto opens = opened;
    for (unsigned i = 1; i <= opens; ++i) {
        io_reset();
        fail_open = i;
        CHECK(platform::read_room_runtime(root, assets, api).error != E::ok && assets.get() == old);
        CHECK(opened == closed + 1);
    }
    for (unsigned i = 1; i <= opens; ++i) {
        io_reset();
        fail_close = i;
        CHECK(platform::read_room_runtime(root, assets, api).error != E::ok && assets.get() == old);
        CHECK(opened == closed);
    }
    for (unsigned i : {1U, 3U, 4U, 7U, 9U}) {
        io_reset();
        fail_read = i;
        CHECK(platform::read_room_runtime(root, assets, api).error != E::ok && assets.get() == old);
    }
    for (unsigned i : {1U, 2U, 7U}) {
        io_reset();
        read_error = i;
        CHECK(platform::read_room_runtime(root, assets, api).error != E::ok && assets.get() == old);
    }
    io_reset();
    for (unsigned i = 1; i <= 6; ++i) {
        nothrow_calls = 0;
        fail_nothrow = i;
        CHECK(platform::read_room_runtime(root, assets).error != E::ok && assets.get() == old);
    }
    fail_nothrow = 0;
    platform::RoomTextures textures(root);
    std::array<std::uint8_t, 4> tiny{};
    domain::RigMaterial invalid{};
    invalid.texture = 14;
    CHECK(!textures.read(invalid, tiny.data(), tiny.size()));
    invalid.texture = 0;
    CHECK(!textures.read(invalid, tiny.data(), tiny.size()));
}
struct Textures final : ports::IRigTextures {
    platform::RoomTextures source;
    unsigned calls{}, fail_at{100}, corrupt_at{100};
    explicit Textures(const char *p) : source(p) {}
    bool read(const domain::RigMaterial &m, std::uint8_t *p, std::size_t n) noexcept override {
        const auto i = calls++;
        if (i == fail_at)
            return false;
        const auto good = source.read(m, p, n);
        if (i == corrupt_at)
            p[0] ^= 1;
        return good;
    }
};
void renderer_failures(const char *root, const platform::RoomAssets &a) {
    for (auto f : {"CITRO3D", "TARGET", "SHADER", "EMPTY_SHADER", "PROGRAM", "VERTEX_SHADER",
                   "UNIFORM", "LINEAR_0", "LINEAR_1", "STATIC_FLUSH", "ATTRIBUTE_0", "ATTRIBUTE_1",
                   "ATTRIBUTE_2", "BUFFER_0", "BUFFER_1", "TEXTURE_0", "TEXTURE_13",
                   "TEXTURE_FLUSH_0", "TEXTURE_FLUSH_13"}) {
        reset();
        failure = f;
        {
            Textures textures(root);
            platform::ctr::RoomRenderer r(a.map, a.rig.shared, textures);
            CHECK(!r.ready());
        }
        CHECK(!active && !bytes);
    }
    for (unsigned i = 1; i <= 3; ++i) {
        reset();
        nothrow_calls = 0;
        fail_nothrow = i;
        {
            Textures textures(root);
            platform::ctr::RoomRenderer r(a.map, a.rig.shared, textures);
            CHECK(!r.ready());
        }
        fail_nothrow = 0;
        CHECK(!bytes && !active);
    }
    for (unsigned i = 0; i < 14 + a.map.material_count; ++i) {
        reset();
        {
            Textures t(root);
            t.fail_at = i;
            platform::ctr::RoomRenderer r(a.map, a.rig.shared, t);
            CHECK(!r.ready());
        }
        CHECK(!bytes);
    }
    reset();
    {
        Textures t(root);
        t.corrupt_at = 13;
        platform::ctr::RoomRenderer r(a.map, a.rig.shared, t);
        CHECK(!r.ready());
    }
    CHECK(!bytes);
    for (unsigned i = 14; i < 14 + a.map.material_count; ++i) {
        for (auto fail : {"TEXTURE", "TEXTURE_FLUSH"}) {
            reset();
            char stage[64];
            std::snprintf(stage, sizeof(stage), "%s_%u", fail, i);
            failure = stage;
            {
                Textures t(root);
                platform::ctr::RoomRenderer r(a.map, a.rig.shared, t);
                CHECK(!r.ready());
            }
            CHECK(!bytes && !active);
        }
        reset();
        {
            Textures t(root);
            t.corrupt_at = i;
            platform::ctr::RoomRenderer r(a.map, a.rig.shared, t);
            CHECK(!r.ready());
        }
        CHECK(!bytes && !active);
    }
    reset();
    {
        Textures t(root);
        static domain::RoomMap empty;
        platform::ctr::RoomRenderer r(empty, a.rig.shared, t);
        CHECK(!r.ready());
    }
}
auto replay(const char *root, const platform::RoomAssets &a, unsigned hz, bool interrupts) {
    reset();
    Textures t(root);
    platform::ctr::RoomRenderer renderer(a.map, a.rig.shared, t);
    CHECK(renderer.ready());
    CHECK(renderer.accounted_bytes() <= 64 * 1024 * 1024);
    std::size_t static_bytes{};
    const auto *colored =
        static_cast<const domain::CharacterDrawVertex *>(static_data(static_bytes));
    CHECK(static_bytes == a.map.vertex_count * sizeof(domain::CharacterDrawVertex));
    unsigned recolored = 0;
    for (unsigned i = 0; i < a.map.shape_count; ++i) {
        const auto &shape = a.map.shapes[i];
        for (unsigned j = shape.first; j < shape.first + shape.count; ++j) {
            const auto &v = colored[j], &source = a.map.vertices[j];
            CHECK(v.position == source.position && v.uv == source.uv);
            CHECK(domain::valid_room_vertex(v));
            if (shape.glass)
                CHECK(std::memcmp(&v, &source, sizeof(v)) == 0);
            else
                recolored += std::memcmp(&v.color, &source.color, sizeof(v.color)) != 0;
        }
    }
    CHECK(a.map.material_count ? recolored == 0 : recolored > 0);
    const auto static_before =
        platform::inspection_crc32(reinterpret_cast<const std::uint8_t *>(colored), static_bytes);
    domain::InspectionLocomotionReader reader(a.rig);
    application::RoomLoop app(a.rig.profile, domain::locomotion_rig_skeleton(a.rig), reader,
                              a.contacts, renderer, a.spawn, a.yaw);
    {
        platform::ctr::MovementControls controls(app);
        std::uint64_t now = 0;
        controls.frame(0, 0, now);
        const auto before_allocations = allocations;
        unsigned blocked = 0;
        const auto segments = a.rig.profile.id == 2 ? 8U : 4U;
        for (unsigned segment = 0; segment < segments; ++segment) {
            const u32 input = segment == 0   ? 0
                              : segment == 1 ? KEY_DUP
                              : segment == 2 ? KEY_DUP | KEY_B
                              : segment == 3 ? KEY_DUP | KEY_DLEFT
                              : segment == 4 ? KEY_DRIGHT
                              : segment == 5 ? KEY_DLEFT
                              : segment == 6 ? 0
                                             : KEY_DLEFT | KEY_DRIGHT;
            const auto segment_position = app.snapshot().movement.position;
            const auto start = now;
            for (unsigned frame = 1; frame <= hz; ++frame) {
                now = start + SYSCLOCK_ARM11 * frame / hz;
                const auto previous = app.snapshot().movement;
                controls.frame(input, 0, now);
                const auto &current = app.snapshot().movement;
                if (segment && current.ordinal != previous.ordinal &&
                    current.position.x == previous.position.x &&
                    current.position.z == previous.position.z)
                    ++blocked;
            }
            CHECK(app.fault() == application::RoomFault::none);
            if (segment >= 4) {
                CHECK(app.snapshot().movement.position.x == segment_position.x &&
                      app.snapshot().movement.position.z == segment_position.z);
                CHECK(app.snapshot().animation.clock.target_id == (segment == 4   ? 107U
                                                                   : segment == 5 ? 108U
                                                                                  : 101U));
            }
            if (interrupts) {
                const auto instance = app.snapshot().instance;
                const auto ordinal = app.snapshot().movement.ordinal;
                controls.frame(KEY_A, KEY_A, ++now);
                controls.frame(0, 0, ++now);
                CHECK(app.state() == S::paused);
                callback(APTHOOK_ONSUSPEND, context);
                callback(APTHOOK_ONSLEEP, context);
                callback(APTHOOK_ONRESTORE, context);
                CHECK(app.state() == S::suspended);
                const auto oldframes = frames;
                controls.frame(KEY_DUP, 0, now += SYSCLOCK_ARM11 * 10);
                CHECK(frames == oldframes);
                callback(APTHOOK_ONWAKEUP, context);
                CHECK(app.state() == S::paused && app.awaiting_release());
                controls.frame(KEY_DUP, 0, ++now);
                CHECK(app.awaiting_release());
                controls.frame(0, 0, ++now);
                controls.frame(KEY_A, KEY_A, ++now);
                controls.frame(0, 0, ++now);
                CHECK(app.snapshot().instance == instance &&
                      app.snapshot().movement.ordinal == ordinal);
            }
        }
        CHECK(allocations == before_allocations &&
              app.snapshot().movement.ordinal == segments * 25);
        CHECK(static_before == platform::inspection_crc32(
                                   reinterpret_cast<const std::uint8_t *>(colored), static_bytes));
        CHECK(blocked > 0); // Wall/floor rejection still advances animation and ordinal.
        CHECK(app.snapshot().movement.position.y == a.spawn.y);
        const auto snapshot = app.snapshot();
        failure = "BUSY";
        const auto held_buffer = dynamic_digest();
        auto different = snapshot.instance;
        different[12] += 1;
        CHECK(renderer.present(snapshot.animation.model, different) == R::busy);
        CHECK(dynamic_digest() == held_buffer); // GPU-owned storage was never overwritten.
        controls.frame(0, 0, ++now);
        CHECK(app.render_result() == R::busy && app.fault() == application::RoomFault::none);
        for (auto f : {"DYNAMIC_FLUSH", "DRAW_ON"}) {
            failure = f;
            controls.frame(0, 0, ++now);
            CHECK(app.state() == S::paused && app.fault() == application::RoomFault::render &&
                  !open_frame);
            failure = {};
            controls.frame(0, 0, ++now);
            controls.frame(KEY_L, KEY_L, ++now);
            CHECK(app.fault() == application::RoomFault::none);
        }
        callback(APT_HookType(5), context);
        callback(APTHOOK_ONEXIT, context);
        CHECK(app.state() == S::stopped);
        CHECK(app.step({}, 40000) == 0);
        return snapshot;
    }
}
void pause_trace(const char *root, unsigned hz) {
    reset();
    std::uint64_t frame = 0;
    const auto add = [&](u32 held, u32 down = 0) {
        CHECK(length < script.size());
        script[length++] = {held, down, ++frame * SYSCLOCK_ARM11 / hz};
    };
    add(0);
    for (unsigned i = 0; i < hz * 9; ++i)
        add(0);
    add(KEY_A, KEY_A);
    add(0);
    add(KEY_L, KEY_L);
    add(0);
    for (unsigned i = 0; i < hz * 10; ++i)
        add(0);
    for (unsigned i = 0; i < hz * 2; ++i) {
        add(KEY_R | KEY_DUP, KEY_R);
        add(KEY_DUP);
    }
    for (unsigned i = 0; i < hz; ++i)
        add(0);
    add(KEY_R, KEY_R);
    // Holding R must not generate more steps; releasing it must not generate any.
    for (unsigned i = 0; i < hz; ++i)
        add(KEY_R);
    for (unsigned i = 0; i < hz; ++i)
        add(0);
    add(KEY_START, KEY_START);
    std::printf("\nPAUSE_TRACE_BEGIN %u\n", hz);
    CHECK(platform::ctr::run_room(root) == 0);
    CHECK(!active && !bytes && !screens && hooks == unhooks);
    std::printf("\nPAUSE_TRACE_END %u\n", hz);
}
void comparison_loop(const char *root) {
    for (bool fallback : {false, true}) {
        reset();
        if (fallback)
            failure = "HS_PALETTE";
        length = 0;
        auto add = [&](u32 held = 0, u32 down = 0, int event = -1) {
            const auto tick = std::uint64_t(length) * SYSCLOCK_ARM11 / 25;
            script[length++] = {held, down, tick, event};
        };
        add(KEY_L, KEY_L); // Held through launch cannot select.
        add();
        add(KEY_A | KEY_L, KEY_A | KEY_L); // Ambiguous choice ignored.
        add();
        add(KEY_A, KEY_A); // CPU.
        add();
        add(KEY_A, KEY_A); // RUNNING.
        add();
        add(KEY_X, KEY_X);
        for (unsigned i = 0; i < 300; ++i)
            add();
        add(KEY_Y, KEY_Y);
        add();
        add(KEY_SELECT, KEY_SELECT);
        add();
        add(KEY_L, KEY_L); // Hybrid, fresh paused pose.
        add();
        add(0, 0, APTHOOK_ONSLEEP);
        add(KEY_SELECT, KEY_SELECT, APTHOOK_ONWAKEUP); // Release gate protects menu too.
        add();
        add(KEY_A, KEY_A);
        add();
        add(KEY_X, KEY_X);
        for (unsigned i = 0; i < 300; ++i)
            add();
        add(KEY_Y, KEY_Y);
        add();
        add(KEY_SELECT | KEY_START, KEY_SELECT | KEY_START); // Exit wins.
        std::printf("\nHS_COMPARISON_BEGIN %u\n", unsigned(fallback));
        CHECK(platform::ctr::run_room(root, true) == 0);
        CHECK(!active && !bytes && !screens && hooks == unhooks);
        CHECK(hooks == 4); // Two menus and two complete owners, never overlapping.
        std::printf("\nHS_COMPARISON_END %u\n", unsigned(fallback));
    }
}
void main_loop(const char *root) {
    reset();
    length = 16;
    script[0] = {KEY_DUP, 0, 0};
    script[1] = {0, 0, SYSCLOCK_ARM11 / 25};
    script[2] = {KEY_DUP, 0, SYSCLOCK_ARM11 / 10};
    script[3] = {KEY_A, KEY_A, SYSCLOCK_ARM11 / 5};
    script[4] = {0, 0, SYSCLOCK_ARM11};
    script[5] = {KEY_R, KEY_R, SYSCLOCK_ARM11 + 1};
    script[6] = {0, 0, SYSCLOCK_ARM11 + 2, APTHOOK_ONSUSPEND};
    script[7] = {0, 0, SYSCLOCK_ARM11 + 3, APTHOOK_ONSLEEP};
    script[8] = {0, 0, SYSCLOCK_ARM11 + 4, APTHOOK_ONWAKEUP};
    script[9] = {KEY_DUP, 0, SYSCLOCK_ARM11 + 5, APTHOOK_ONRESTORE};
    script[10] = {0, 0, SYSCLOCK_ARM11 + 6};
    script[11] = {KEY_L, KEY_L, SYSCLOCK_ARM11 + 7};
    script[12] = {0, 0, SYSCLOCK_ARM11 + 8};
    script[13] = {KEY_A, KEY_A, SYSCLOCK_ARM11 + 9};
    script[14] = {0, 0, SYSCLOCK_ARM11 + 10};
    script[15] = {KEY_START, KEY_START, SYSCLOCK_ARM11 + 11};
    CHECK(platform::ctr::run_room(root) == 0);
    CHECK(!active && !bytes && !screens && hooks == unhooks);
    CHECK(speedups == 2 && speedup_disables == 1 && !cpu_fast);
    reset();
    failure = "TARGET";
    length = 4;
    script[0] = {KEY_L, KEY_L, 0};
    script[1] = {0, 0, 1};
    script[2] = {KEY_L, KEY_L, 2, -1, true};
    script[3] = {KEY_START, KEY_START, 3};
    CHECK(platform::ctr::run_room(root) == 0);
    CHECK(!bytes && hooks == unhooks);
    reset();
    length = 3;
    script[0] = {0, 0, 0, APTHOOK_ONSLEEP};
    script[1] = {0, 0, 1, APTHOOK_ONWAKEUP};
    script[2] = {KEY_START, KEY_START, 2};
    CHECK(platform::ctr::run_room("/missing-room-fixture") == 1);
    CHECK(hooks == unhooks && !bytes);
    CHECK(speedups == 2 && speedup_disables == 1);
    for (bool old_model : {false, true}) {
        reset();
        new_model = !old_model;
        if (!old_model)
            failure = "CPU_QUERY";
        length = 1;
        script[0] = {KEY_START, KEY_START, 0};
        CHECK(platform::ctr::run_room(root) == 0);
        CHECK(!speedups && !speedup_disables && !cpu_fast);
    }
}
} // namespace
int main(int argc, char **argv) {
    CHECK(argc == 2 || argc == 3);
    if (argc == 3 && std::strcmp(argv[2], "--pause-trace") == 0) {
        for (unsigned hz : {25U, 60U, 143U})
            pause_trace(argv[1], hz);
        return 0;
    }
    std::unique_ptr<platform::RoomAssets> a;
    if (argc == 2) {
        loader(argv[1], a);
        renderer_failures(argv[1], *a);
    } else
        CHECK(platform::read_room_runtime(argv[1], a).error == E::ok);
    if (argc == 3 && std::strcmp(argv[2], "--turns") == 0)
        CHECK(a->rig.profile.id == 2 && a->rig.shared.sample_count == 78);
    auto first = replay(argv[1], *a, 25, false);
    for (unsigned rate : {60U, 143U}) {
        auto next = replay(argv[1], *a, rate, true);
        CHECK(next.instance == first.instance && next.animation.model == first.animation.model &&
              next.animation.clock.counter == first.animation.clock.counter);
    }
    CHECK(!active && !bytes && hooks == unhooks);
    main_loop(argv[1]);
    if (argc == 3 && std::strcmp(argv[2], "--turns") == 0)
        comparison_loop(argv[1]);
    std::printf("Room runtime: read/render/HID/clock/contacts/APT/retry/cleanup PASS; extra=%zu "
                "controller=%zu\n",
                platform::room_runtime_extra, sizeof(application::RoomLoop));
}
