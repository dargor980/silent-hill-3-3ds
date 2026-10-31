#include "check.hpp"
#include "room_renderer.hpp"
#include "room_sdk.hpp"
#include "sh3/application/room_loop.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdio>

namespace {
using namespace sh3;
using Clock = std::chrono::steady_clock;
struct Samples {
    std::array<domain::WorkSample, 288> values{};
    unsigned count{};
    static std::uint64_t clock(void *) noexcept {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch())
            .count();
    }
    static void sink(void *context, const domain::WorkSample &value) noexcept {
        auto &s = *static_cast<Samples *>(context);
        CHECK(s.count < s.values.size() && value.frame == s.count);
        s.values[s.count++] = value;
    }
};
void stats(std::array<std::uint64_t, 256> values) {
    std::sort(values.begin(), values.end());
    std::printf("{\"median_ns\":%llu,\"p95_ns\":%llu,\"max_ns\":%llu}",
                static_cast<unsigned long long>(values[128]),
                static_cast<unsigned long long>(values[243]),
                static_cast<unsigned long long>(values.back()));
}
} // namespace
int main(int argc, char **argv) {
    CHECK(argc == 2);
    const auto load_start = Samples::clock(nullptr);
    std::unique_ptr<platform::RoomAssets> assets;
    CHECK(platform::read_room_runtime(argv[1], assets).error == ports::FileError::ok);
    const auto load_ns = Samples::clock(nullptr) - load_start;
    std::printf("{\"kind\":\"host_sdk_double_not_gpu\",\"load_ns\":%llu,\"audio\":\"not_executed\","
                "\"windows\":[",
                static_cast<unsigned long long>(load_ns));
    for (unsigned window = 0; window < 6; ++window) {
        room_sdk::reset();
        const auto mode =
            window % 2 ? platform::ctr::SkinningMode::hybrid : platform::ctr::SkinningMode::cpu;
        platform::RoomTextures textures(argv[1]);
        const auto start = Samples::clock(nullptr);
        platform::ctr::RoomRenderer renderer(assets->map, assets->rig.shared, textures, mode);
        const auto prepare_ns = Samples::clock(nullptr) - start;
        CHECK(renderer.ready() && renderer.skinning_mode() == mode);
        domain::InspectionLocomotionReader reader(assets->rig);
        auto loop = std::make_unique<application::RoomLoop>(
            assets->rig.profile, domain::locomotion_rig_skeleton(assets->rig), reader,
            assets->contacts, renderer, assets->spawn, assets->yaw);
        auto samples = std::make_unique<Samples>();
        domain::WorkTrace trace{Samples::clock, Samples::sink, samples.get()};
        renderer.trace(&trace);
        loop->trace(&trace);
        loop->step({}, 0);
        for (unsigned i = 1; i < 288; ++i) {
            application::MovementInput input;
            input.right = i % 128 < 32;
            input.left = i % 128 >= 32 && i % 128 < 64;
            input.forward = i % 128 >= 64 && i % 128 < 112;
            input.run = i % 128 >= 88;
            loop->step(input, 40000);
            CHECK(loop->fault() == application::RoomFault::none &&
                  loop->render_result() == ports::RenderResult::presented);
        }
        CHECK(trace.delivered == 288 && samples->count == 288);
        std::printf("%s{\"mode\":\"%s\",\"warmup\":32,\"samples\":256,\"failed\":0,\"prepare_"
                    "resources_ns\":%llu,\"phases\":[",
                    window ? "," : "", window % 2 ? "hybrid" : "cpu",
                    static_cast<unsigned long long>(prepare_ns));
        for (unsigned p = 0; p < unsigned(domain::WorkPhase::count); ++p) {
            std::array<std::uint64_t, 256> values{};
            for (unsigned i = 0; i < 256; ++i)
                values[i] = samples->values[32 + i].ticks[p];
            if (p)
                std::printf(",");
            stats(values);
        }
        std::printf("],\"whole_step\":");
        std::array<std::uint64_t, 256> wall{}, cadence{};
        for (unsigned i = 0; i < 256; ++i) {
            const auto &s = samples->values[32 + i];
            wall[i] = s.end_tick - s.begin_tick;
            cadence[i] = s.begin_tick - samples->values[31 + i].begin_tick;
            std::uint64_t phases = 0;
            for (auto t : s.ticks)
                phases += t;
            CHECK(phases <= wall[i] && s.steps == 1);
        }
        stats(wall);
        std::printf(",\"host_cadence\":");
        stats(cadence);
        std::printf("}");
    }
    std::puts("]}");
}
