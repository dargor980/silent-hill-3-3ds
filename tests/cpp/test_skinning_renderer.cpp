#include "check.hpp"
#include "room_renderer.hpp"
#include "room_sdk.hpp"
#include "sh3/application/room_loop.hpp"
#include "skinning_gpu.hpp"
#include <array>
#include <cstring>
#include <limits>
#include <new>

namespace {
unsigned nothrow_calls{}, fail_nothrow{};
}
void *operator new(std::size_t size, const std::nothrow_t &) noexcept {
    if (++nothrow_calls == fail_nothrow)
        return nullptr;
    try {
        return ::operator new(size);
    } catch (const std::bad_alloc &) {
        return nullptr;
    }
}
void *operator new[](std::size_t size, const std::nothrow_t &) noexcept {
    if (++nothrow_calls == fail_nothrow)
        return nullptr;
    try {
        return ::operator new[](size);
    } catch (const std::bad_alloc &) {
        return nullptr;
    }
}
namespace {
using namespace sh3;
using Mode = platform::ctr::SkinningMode;
using R = ports::RenderResult;
std::array<std::uint64_t, 128> transparent{}, maps{};
std::array<std::uint32_t, 128> dynamic{};
struct Trace {
    std::uint64_t tick{}, delivered{};
    domain::WorkSample last{};
    static std::uint64_t clock(void *p) noexcept { return ++static_cast<Trace *>(p)->tick; }
    static void sink(void *p, const domain::WorkSample &s) noexcept {
        auto &t = *static_cast<Trace *>(p);
        CHECK(s.frame == t.delivered++);
        std::uint64_t ticks = 0, calls = 0;
        for (unsigned i = 0; i < unsigned(domain::WorkPhase::count); ++i) {
            ticks += s.ticks[i];
            calls += s.calls[i];
        }
        CHECK(ticks == calls); // Every interval has exactly one clock increment.
        t.last = s;
    }
};
void replay(const char *root, platform::RoomAssets &assets, Mode mode) {
    room_sdk::reset();
    platform::RoomTextures textures(root);
    platform::ctr::RoomRenderer renderer(assets.map, assets.rig.shared, textures, mode);
    CHECK(renderer.ready() && renderer.skinning_mode() == mode);
    domain::InspectionLocomotionReader reader(assets.rig);
    auto loop = std::make_unique<application::RoomLoop>(
        assets.rig.profile, domain::locomotion_rig_skeleton(assets.rig), reader, assets.contacts,
        renderer, assets.spawn, assets.yaw);
    Trace capture;
    domain::WorkTrace trace{Trace::clock, Trace::sink, &capture};
    renderer.trace(&trace);
    loop->trace(&trace);
    loop->step({}, 0);
    CHECK(!capture.last.gpu_valid);
    for (unsigned i = 0; i < 128; ++i) {
        application::MovementInput input;
        input.right = i < 32 || i >= 96;
        input.left = i >= 32 && i < 64;
        loop->step(input, 40000);
        CHECK(loop->fault() == application::RoomFault::none);
        CHECK(capture.last.gpu_valid && capture.last.gpu_frame == i);
        CHECK(capture.last.steps == 1 && capture.last.result == unsigned(R::presented));
        CHECK(capture.last.calls[unsigned(domain::WorkPhase::movement_contacts)] == 2);
        CHECK(capture.last.calls[unsigned(domain::WorkPhase::animation_pose)] == 2);
        CHECK(capture.last.calls[unsigned(domain::WorkPhase::deform_cpu)] == 1);
        CHECK(capture.last.calls[unsigned(domain::WorkPhase::palette_rows)] ==
              unsigned(mode == Mode::hybrid));
        if (mode == Mode::cpu) {
            transparent[i] = room_sdk::transparent_hash;
            maps[i] = room_sdk::map_hash;
            dynamic[i] = room_sdk::dynamic_digest();
        } else {
            CHECK(transparent[i] == room_sdk::transparent_hash && maps[i] == room_sdk::map_hash &&
                  dynamic[i] == room_sdk::dynamic_digest());
            bool seen_gpu = false, seen_transparent = false;
            for (unsigned j = 0; j < room_sdk::draw_count; ++j) {
                const auto d = room_sdk::draw_log[j];
                if (d.indexed) {
                    CHECK(!seen_transparent);
                    seen_gpu = true;
                } else if (d.texture == 12 || d.texture == 13) {
                    CHECK(seen_gpu);
                    seen_transparent = true;
                } else
                    CHECK(!seen_gpu);
            }
            CHECK(seen_gpu && seen_transparent);
        }
    }
    CHECK(capture.delivered == 129 && trace.delivered == 129);
    if (mode == Mode::hybrid)
        std::printf("HS native private/synthetic poses max host XYZ error: %.9g\n",
                    double(room_sdk::max_skin_error));
    const auto saved = room_sdk::dynamic_digest(), begins = room_sdk::begins;
    auto pose = loop->snapshot().animation.model;
    pose[0][0] = std::numeric_limits<float>::quiet_NaN();
    CHECK(renderer.present(pose, loop->snapshot().instance) == R::unavailable);
    CHECK(room_sdk::begins == begins && room_sdk::dynamic_digest() == saved);
    auto instance = loop->snapshot().instance;
    instance[0] = 2;
    CHECK(renderer.present(loop->snapshot().animation.model, instance) == R::unavailable);
    CHECK(room_sdk::begins == begins && room_sdk::dynamic_digest() == saved);
    for (auto fault : {"BUSY", "DYNAMIC_FLUSH", "DRAW_ON"}) {
        room_sdk::failure = fault;
        loop->step({}, 40000);
        CHECK(capture.delivered == trace.delivered);
        if (room_sdk::failure == "BUSY") {
            CHECK(loop->fault() == application::RoomFault::none &&
                  loop->render_result() == R::busy);
            CHECK(room_sdk::dynamic_digest() == saved);
            CHECK(!capture.last.gpu_valid);
        } else
            CHECK(loop->fault() == application::RoomFault::render);
        room_sdk::failure = {};
        loop->step({}, 0);
        CHECK(capture.last.gpu_valid == (std::strcmp(fault, "BUSY") == 0));
        application::MovementInput reset;
        reset.restart = true;
        loop->step(reset, 0);
        loop->step({}, 0);
        CHECK(loop->fault() == application::RoomFault::none &&
              loop->snapshot().movement.ordinal == 0);
    }
    loop->dispatch(domain::LifecycleEvent::suspend);
    const auto frames = room_sdk::frames;
    for (unsigned i = 0; i < 100; ++i)
        loop->step({}, 100000);
    CHECK(room_sdk::frames == frames);
    loop->dispatch(domain::LifecycleEvent::resume);
    loop->step({}, 10000000);
    CHECK(loop->snapshot().movement.ordinal == 0 && loop->fault() == application::RoomFault::none);
}
void failures(const char *root, platform::RoomAssets &assets) {
    {
        platform::ctr::SkinningGpu limited(assets.rig.shared, 0);
        CHECK(!limited.ready());
        static domain::RigPalette palette;
        CHECK(!limited.prepare(palette, {}));
        platform::ctr::SkinningGpu metadata_only(assets.rig.shared,
                                                 sizeof(platform::ctr::SkinningGpu) +
                                                     sizeof(domain::SkinPlanWorkspace));
        CHECK(!metadata_only.ready());
        const auto vertex_count = assets.rig.shared.vertex_count;
        assets.rig.shared.vertex_count = 0;
        platform::ctr::SkinningGpu invalid(assets.rig.shared, 1024 * 1024);
        CHECK(!invalid.ready());
        assets.rig.shared.vertex_count = vertex_count;
    }
    unsigned n = 0;
    {
        room_sdk::reset();
        platform::RoomTextures textures(root);
        nothrow_calls = 0;
        platform::ctr::RoomRenderer renderer(assets.map, assets.rig.shared, textures, Mode::hybrid);
        CHECK(renderer.ready() && renderer.skinning_mode() == Mode::hybrid);
        n = nothrow_calls;
    }
    for (unsigned failure = 1; failure <= n; ++failure) {
        room_sdk::reset();
        platform::RoomTextures textures(root);
        nothrow_calls = 0;
        fail_nothrow = failure;
        {
            platform::ctr::RoomRenderer renderer(assets.map, assets.rig.shared, textures,
                                                 Mode::hybrid);
            CHECK(!renderer.ready() || renderer.skinning_mode() == Mode::cpu);
        }
        fail_nothrow = 0;
        CHECK(!room_sdk::bytes && !room_sdk::active);
    }
    for (auto failure :
         {"LINEAR_2", "LINEAR_3", "HS_FLUSH", "HS_SHADER", "HS_EMPTY_SHADER", "HS_PROGRAM",
          "HS_VERTEX_SHADER", "HS_PALETTE", "HS_CLIP", "HS_ATTRIBUTE_0", "HS_ATTRIBUTE_1",
          "HS_ATTRIBUTE_2", "HS_ATTRIBUTE_3", "BUFFER_2"}) {
        room_sdk::reset();
        room_sdk::failure = failure;
        platform::RoomTextures textures(root);
        {
            platform::ctr::RoomRenderer renderer(assets.map, assets.rig.shared, textures,
                                                 Mode::hybrid);
            CHECK(renderer.ready() && renderer.skinning_mode() == Mode::cpu);
            CHECK(std::strcmp(renderer.skinning_status(), "HS_READY") != 0);
            domain::InspectionLocomotionReader reader(assets.rig);
            auto loop = std::make_unique<application::RoomLoop>(
                assets.rig.profile, domain::locomotion_rig_skeleton(assets.rig), reader,
                assets.contacts, renderer, assets.spawn, assets.yaw);
            loop->step({}, 0);
            loop->step({}, 40000);
            CHECK(loop->fault() == application::RoomFault::none && room_sdk::draws &&
                  !room_sdk::indexed_draws);
        }
        CHECK(!room_sdk::bytes && !room_sdk::active);
    }
    std::printf("HS fallback: %u allocation points and 14 SDK failures PASS\n", n);
}
} // namespace
int main(int argc, char **argv) {
    CHECK(argc == 2);
    std::unique_ptr<platform::RoomAssets> assets;
    CHECK(platform::read_room_runtime(argv[1], assets).error == ports::FileError::ok);
    replay(argv[1], *assets, Mode::cpu);
    replay(argv[1], *assets, Mode::hybrid);
    failures(argv[1], *assets);
    CHECK(!room_sdk::bytes && !room_sdk::active);
    std::puts("HS render: 128 poses, exact map/transparent buffers, restoration, faults and trace "
              "PASS (SDK double)");
}
