#include "check.hpp"
#include "room_renderer.hpp"
#include "room_sdk.hpp"
#include "sh3/application/room_loop.hpp"
#include "sh3/platform/skinning_capture.hpp"
#include <algorithm>
#include <array>
#include <new>

namespace {
struct Allocation {
    void *pointer{};
    std::size_t bytes{};
};
std::array<Allocation, 1024> allocations{};
std::size_t live{}, high{}, calls{}, combined_high{};
bool forbid{};
void measure() {
    CHECK(!forbid);
    high = std::max(high, live);
    combined_high = std::max(combined_high, live + room_sdk::bytes);
}
void *allocate(std::size_t n, std::size_t alignment = 0) {
    CHECK(!forbid);
    void *p = nullptr;
    if (alignment) {
        if (posix_memalign(&p, alignment, n ? n : 1))
            p = nullptr;
    } else
        p = std::malloc(n ? n : 1);
    if (!p)
        throw std::bad_alloc();
    const auto slot =
        std::find_if(allocations.begin(), allocations.end(), [](auto a) { return !a.pointer; });
    CHECK(slot != allocations.end());
    *slot = {p, n};
    live += n;
    ++calls;
    measure();
    return p;
}
void release(void *p) noexcept {
    if (!p)
        return;
    CHECK(!forbid);
    const auto slot = std::find_if(allocations.begin(), allocations.end(),
                                   [p](auto a) { return a.pointer == p; });
    CHECK(slot != allocations.end());
    live -= slot->bytes;
    *slot = {};
    std::free(p);
    measure();
}
} // namespace
void *operator new(std::size_t n) { return allocate(n); }
void *operator new[](std::size_t n) { return allocate(n); }
void *operator new(std::size_t n, std::align_val_t a) { return allocate(n, std::size_t(a)); }
void *operator new[](std::size_t n, std::align_val_t a) { return allocate(n, std::size_t(a)); }
void *operator new(std::size_t n, const std::nothrow_t &) noexcept {
    try {
        return allocate(n);
    } catch (...) {
        return nullptr;
    }
}
void *operator new[](std::size_t n, const std::nothrow_t &t) noexcept {
    return ::operator new(n, t);
}
void *operator new(std::size_t n, std::align_val_t a, const std::nothrow_t &) noexcept {
    try {
        return allocate(n, std::size_t(a));
    } catch (...) {
        return nullptr;
    }
}
void *operator new[](std::size_t n, std::align_val_t a, const std::nothrow_t &t) noexcept {
    return ::operator new(n, a, t);
}
void operator delete(void *p) noexcept { release(p); }
void operator delete[](void *p) noexcept { release(p); }
void operator delete(void *p, std::size_t) noexcept { release(p); }
void operator delete[](void *p, std::size_t) noexcept { release(p); }
void operator delete(void *p, std::align_val_t) noexcept { release(p); }
void operator delete[](void *p, std::align_val_t) noexcept { release(p); }
void operator delete(void *p, std::size_t, std::align_val_t) noexcept { release(p); }
void operator delete[](void *p, std::size_t, std::align_val_t) noexcept { release(p); }
void operator delete(void *p, const std::nothrow_t &) noexcept { release(p); }
void operator delete[](void *p, const std::nothrow_t &) noexcept { release(p); }
void operator delete(void *p, std::align_val_t, const std::nothrow_t &) noexcept { release(p); }
void operator delete[](void *p, std::align_val_t, const std::nothrow_t &) noexcept { release(p); }

int main(int argc, char **argv) {
    using namespace sh3;
    static_assert(domain::room_dynamic_vertices <= 18096); // Stack gate's introsort bound.
    static_assert(sizeof(platform::RoomAssets) + 32768 <= platform::room_runtime_extra);
    CHECK(argc == 2 || argc == 3);
    room_sdk::reset();
    room_sdk::memory_changed = measure;
    const auto baseline = live;
    high = combined_high = baseline;
    std::unique_ptr<platform::RoomAssets> assets;
    CHECK(platform::read_room_runtime(argv[1], assets).error == ports::FileError::ok);
    CHECK(assets->rig.profile.id == 2 && assets->rig.shared.sample_count == 78);
    const auto load_peak = high - baseline;
    high = live;
    // A live old scene and candidate coexist until the replacement commits.
    CHECK(platform::read_room_runtime(argv[1], assets).error == ports::FileError::ok);
    const auto replacement_peak = high - baseline;
    domain::RoomMemory ledger;
    CHECK(domain::room_memory(assets->map, assets->rig.shared, ledger));
    auto accounted = ledger.total + platform::room_runtime_extra;
    CHECK(accounted <= (64 * 1024 * 1024) * 4 / 5); // RNF02.02: leave 20% headroom.
    std::size_t resident{}, rendering_peak{}, steady_calls{}, updates{};
    {
        platform::RoomTextures textures(argv[1]);
        auto mode = platform::ctr::SkinningMode::cpu;
        std::unique_ptr<platform::SkinningCapture> capture;
#ifdef SH3_TEST_HYBRID
        if (argc == 2)
            mode = platform::ctr::SkinningMode::hybrid;
        capture = std::make_unique<platform::SkinningCapture>();
#endif
        auto owner = std::make_unique<platform::ctr::RoomRenderer>(
            assets->map, assets->rig.shared, textures, mode, capture ? sizeof(*capture) : 0);
        auto &renderer = *owner;
        CHECK(renderer.skinning_mode() == mode);
        accounted = renderer.accounted_bytes();
        CHECK(accounted <= (64 * 1024 * 1024) * 4 / 5);
        CHECK(renderer.ready() && renderer.accounted_bytes() == accounted);
        domain::InspectionLocomotionReader reader(assets->rig);
        auto loop = std::make_unique<application::RoomLoop>(
            assets->rig.profile, domain::locomotion_rig_skeleton(assets->rig), reader,
            assets->contacts, renderer, assets->spawn, assets->yaw);
        domain::WorkTrace trace;
        if (capture) {
            trace.clock = [](void *) noexcept { return svcGetSystemTick(); };
            trace.sink = [](void *p, const domain::WorkSample &s) noexcept {
                static_cast<platform::SkinningCapture *>(p)->record(s);
            };
            trace.context = capture.get();
            renderer.trace(&trace);
            loop->trace(&trace);
            capture->start();
        }
        CHECK(loop->ready());
        loop->step({}, 0);
        resident = live + room_sdk::bytes - baseline;
        rendering_peak = combined_high - baseline;
        const auto before = calls;
        forbid = true;
        for (unsigned goal : {107U, 108U, 113U, 109U, 101U, 108U, 107U, 101U}) {
            application::MovementInput input;
            input.right = goal == 107;
            input.left = goal == 108;
            input.forward = goal == 109 || goal == 113;
            input.run = goal == 113;
            for (unsigned i = 0; i < 32; ++i) {
                CHECK(loop->step(input, 40000) == 1);
                ++updates;
                // Pause every phase of both caches; single-step, suspend and reset
                // keep using the same preallocated transaction/renderer storage.
                loop->dispatch(domain::LifecycleEvent::toggle_pause);
                loop->step({}, 0);
                auto advance = input;
                advance.advance = true;
                CHECK(loop->step(advance, 0) == 1);
                ++updates;
                loop->dispatch(domain::LifecycleEvent::suspend);
                loop->step(input, 10000000);
                loop->dispatch(domain::LifecycleEvent::resume);
                loop->step({}, 10000000);
                loop->dispatch(domain::LifecycleEvent::toggle_pause);
                loop->step({}, 0);
            }
            CHECK(loop->snapshot().animation.clock.target_id == goal);
        }
        application::MovementInput restart;
        restart.restart = true;
        loop->step(restart, 0);
        CHECK(loop->snapshot().movement.ordinal == 0 &&
              loop->snapshot().animation.clock.target_id == 101);
        if (capture) {
            CHECK(capture->complete());
            for (unsigned i = 0; i < 13; ++i)
                CHECK(capture->summarize(i, SYSCLOCK_ARM11).count);
        }
        forbid = false;
        steady_calls = calls - before;
        CHECK(!steady_calls && loop->fault() == application::RoomFault::none);
    }
    CHECK(!room_sdk::bytes && !room_sdk::active);
    assets.reset();
    CHECK(live == baseline);
    room_sdk::memory_changed = nullptr;
    CHECK(rendering_peak + ledger.platform_reserve <= accounted);
    std::printf("HG_RESOURCES {\"load_peak\":%zu,\"replacement_peak\":%zu,"
                "\"resident\":%zu,\"tracked_peak\":%zu,\"accounted\":%zu,"
                "\"platform_reserve\":%zu,\"updates\":%zu,\"step_allocations\":%zu,"
                "\"released\":true}\n",
                load_peak, replacement_peak, resident, rendering_peak, accounted,
                ledger.platform_reserve, updates, steady_calls);
}
