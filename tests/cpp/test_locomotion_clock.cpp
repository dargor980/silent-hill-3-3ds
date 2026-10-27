#include "check.hpp"
#include "sh3/domain/locomotion_clock.hpp"
#include <cstring>
#include <limits>
#include <new>
#include <tuple>

namespace { bool forbid_allocation = false; }
void *operator new(std::size_t n) {
    if (forbid_allocation)
        std::abort();
    if (auto *p = std::malloc(n ? n : 1))
        return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }

namespace {
using namespace sh3::domain;
using Mode = LocomotionMode;
using Error = LocomotionError;
using Eval = LocomotionEvaluation;
using Cache = LocomotionCacheAction;
constexpr auto profile = heather_locomotion_profile;
constexpr auto max = std::numeric_limits<std::uint32_t>::max();
auto clock_values(const LocomotionClock &s) {
    return std::make_tuple(s.profile_id, s.source_id, s.target_id, s.mode, s.counter,
                           s.blend, s.saved_local_valid);
}
auto sample_values(const LocomotionSamples &s) {
    return std::make_tuple(s.clip_id, s.frame, s.following, s.source_frame, s.source_following,
                           s.packed_frame, s.packed_following);
}
bool same(const LocomotionPlan &a, const LocomotionPlan &b) {
    return clock_values(a.next) == clock_values(b.next) && a.evaluation == b.evaluation &&
           a.cache == b.cache && a.pose_phase == b.pose_phase && a.fraction_q12 == b.fraction_q12 &&
           a.blend_q12 == b.blend_q12 && sample_values(a.source) == sample_values(b.source) &&
           sample_values(a.target) == sample_values(b.target);
}
LocomotionClock stable(std::uint32_t id, std::uint32_t counter = 0) {
    return {1, id, id, Mode::stable, counter, 0, false};
}
LocomotionPlan update(const LocomotionClock &s, std::optional<std::uint32_t> request = {}) {
    LocomotionPlan out;
    CHECK(plan_locomotion_update(profile, s, request, 2, out) == Error::ok);
    return out;
}
void rejected(const LocomotionProfile &p, const LocomotionClock &s,
              std::optional<std::uint32_t> request, std::uint32_t ticks, Error error) {
    auto out = update(stable(109, 97040), 113);
    // Capture object representation to catch any partial writes, including padding.
    std::array<unsigned char, sizeof(out)> before{};
    std::memcpy(before.data(), &out, sizeof(out));
    const auto input = clock_values(s);
    CHECK(plan_locomotion_update(p, s, request, ticks, out) == error);
    CHECK(std::memcmp(before.data(), &out, sizeof(out)) == 0);
    CHECK(input == clock_values(s));
}
void invalid_profiles() {
    auto p = profile;
    for (auto member : {&LocomotionProfile::id, &LocomotionProfile::model_resource,
                        &LocomotionProfile::animation_resource, &LocomotionProfile::sample_count,
                        &LocomotionProfile::ticks}) {
        p = profile;
        p.*member = max;
        rejected(p, initial_locomotion_clock(), {}, 2, Error::invalid_profile);
    }
    for (std::size_t index = 0; index < 3; ++index) {
        for (auto member : {&LocomotionClip::id, &LocomotionClip::count, &LocomotionClip::start,
                            &LocomotionClip::end, &LocomotionClip::loop, &LocomotionClip::trailing,
                            &LocomotionClip::packed_first}) {
            p = profile;
            p.clips[index].*member = max;
            rejected(p, initial_locomotion_clock(), {}, 2, Error::invalid_profile);
        }
        for (auto speed : {0, -1, std::numeric_limits<std::int32_t>::max(),
                            std::numeric_limits<std::int32_t>::min()}) {
            p = profile;
            p.clips[index].speed = speed;
            rejected(p, initial_locomotion_clock(), {}, 2, Error::invalid_profile);
        }
    }
    // Strict precedence, even when later arguments are invalid too.
    rejected(p, {}, 0, 0, Error::invalid_profile);
}
void invalid_states_and_requests() {
    const auto idle = initial_locomotion_clock();
    for (auto member : {&LocomotionClock::profile_id, &LocomotionClock::source_id,
                        &LocomotionClock::target_id, &LocomotionClock::counter,
                        &LocomotionClock::blend}) {
        auto s = idle;
        s.*member = max;
        rejected(profile, s, 0, 0, Error::invalid_state);
    }
    for (auto invalid_mode : {0U, 2U, 4U, 6U, max}) {
        auto s = idle;
        s.mode = static_cast<Mode>(invalid_mode);
        rejected(profile, s, {}, 2, Error::invalid_state);
    }
    auto s = idle;
    s.saved_local_valid = true;
    rejected(profile, s, {}, 2, Error::invalid_state);
    s = idle;
    s.source_id = 109;
    rejected(profile, s, {}, 2, Error::invalid_state);
    for (auto ticks : {0U, 1U, 3U, max})
        rejected(profile, idle, 0, ticks, Error::invalid_ticks);
    for (auto clip : {0U, 1U, 100U, 65535U, max})
        rejected(profile, idle, clip, 2, Error::unknown_clip);
    rejected(profile, idle, 113, 2, Error::unsupported_transition);
    for (const auto &clip : profile.clips) {
        rejected(profile, stable(clip.id, clip.count * 4096), {}, 2, Error::invalid_state);
        for (auto phase : {0U, 4095U, 4096U, clip.count * 4096 - 1}) {
            const auto state = stable(clip.id, phase);
            const auto plan = update(state);
            CHECK(same(plan, update(state, clip.id)));
            CHECK(plan.evaluation == Eval::clip && plan.cache == Cache::none);
            CHECK(plan.next.mode == Mode::stable && !plan.next.saved_local_valid);
            CHECK(plan.pose_phase == phase && plan.fraction_q12 == phase % 4096);
        }
    }
}
void blends() {
    constexpr std::array<std::array<std::uint32_t, 2>, 5> edges{{
        {{101, 109}}, {{109, 101}}, {{113, 101}}, {{109, 113}}, {{113, 109}}
    }};
    for (const auto &edge : edges) {
        auto plan = update(stable(edge[0], 12345), edge[1]);
        const bool cached = edge[0] == 101 || edge[1] == 101;
        CHECK(plan.cache == (cached ? Cache::capture_last : Cache::none));
        CHECK(plan.next.source_id == edge[0] && plan.next.target_id == edge[1]);
        CHECK(plan.next.blend == (cached ? (edge[1] == 109 ? 768U : 1280U) : 384U));
        const auto mode = cached ? Mode::cached : Mode::phase_blend;
        const auto expected_poses = cached ? (edge[1] == 109 ? 5U : 8U) : 10U;
        unsigned poses = 0;
        while (plan.next.mode != Mode::stable) {
            CHECK(plan.next.mode == mode && ++poses <= expected_poses);
            CHECK(plan.next.saved_local_valid == cached);
            CHECK(plan.evaluation == (cached ? Eval::cached_blend : Eval::phase_blend));
            if (cached)
                CHECK(plan.pose_phase == 0 && plan.next.counter == 0);
            const auto state = plan.next;
            CHECK(same(update(state), update(state, state.target_id)));
            for (auto id : {101U, 109U, 113U})
                if (id != state.target_id)
                    rejected(profile, state, id, 2, Error::transition_busy);
            rejected(profile, state, 0, 2, Error::unknown_clip);
            for (auto bad_beta : {0U, state.blend - 1, 4096U, max}) {
                auto bad = state;
                bad.blend = bad_beta;
                rejected(profile, bad, {}, 2, Error::invalid_state);
            }
            auto bad = state;
            bad.saved_local_valid = !cached;
            rejected(profile, bad, {}, 2, Error::invalid_state);
            bad = state;
            bad.source_id = state.target_id;
            rejected(profile, bad, {}, 2, Error::invalid_state);
            if (cached) {
                bad = state;
                bad.counter = 1;
                rejected(profile, bad, {}, 2, Error::invalid_state);
            }
            plan = update(state);
            CHECK(plan.cache != Cache::capture_last); // The frozen source is not overwritten.
        }
        CHECK(poses == expected_poses);
        CHECK(plan.cache == (cached ? Cache::discard : Cache::none));
        CHECK(!plan.next.saved_local_valid && !plan.next.blend && !plan.blend_q12);
        CHECK(plan.next.source_id == edge[1] && plan.next.target_id == edge[1]);
        CHECK(plan.evaluation == Eval::clip && plan.source.clip_id == 0);
    }
    for (auto ids : {std::array<std::uint32_t, 2>{101, 113}, {109, 113}, {113, 109}}) {
        LocomotionClock bad{1, ids[0], ids[1], Mode::cached, 0, 1280, true};
        rejected(profile, bad, {}, 2, Error::invalid_state);
    }
    for (auto ids : {std::array<std::uint32_t, 2>{101, 109}, {109, 101}}) {
        LocomotionClock bad{1, ids[0], ids[1], Mode::phase_blend, 0, 384, false};
        rejected(profile, bad, {}, 2, Error::invalid_state);
    }
    // Input may alias next in the output plan; it is consumed before publication.
    auto plan = update(stable(109), 113);
    const auto expected = update(plan.next);
    CHECK(plan_locomotion_update(profile, plan.next, {}, 2, plan) == Error::ok);
    CHECK(same(plan, expected));
}

void print_samples(const LocomotionSamples &s) {
    std::printf(" %u %u %u %u %u %u %u", s.clip_id, s.frame, s.following,
                s.source_frame, s.source_following, s.packed_frame, s.packed_following);
}
void vectors() {
    // Test-only stdin protocol; the domain never parses or opens anything.
    unsigned source, target, mode, counter, blend, saved, requested, has_request, ticks;
    int fields;
    while ((fields = std::scanf("%u %u %u %u %u %u %u %u %u", &source, &target, &mode,
                                &counter, &blend, &saved, &requested, &has_request, &ticks)) != EOF) {
        CHECK(fields == 9 && saved <= 1 && has_request <= 1);
        LocomotionClock state{1, source, target, static_cast<Mode>(mode), counter, blend, bool(saved)};
        LocomotionPlan p;
        const auto request = has_request ? std::optional<std::uint32_t>{requested} : std::nullopt;
        const auto error = plan_locomotion_update(profile, state, request, ticks, p);
        std::printf("%u %u %u %u %u %u %u %u %u %u %u %u", unsigned(error), p.next.source_id,
                    p.next.target_id, unsigned(p.next.mode), p.next.counter, p.next.blend,
                    unsigned(p.next.saved_local_valid), unsigned(p.evaluation), unsigned(p.cache),
                    p.pose_phase, p.fraction_q12, p.blend_q12);
        print_samples(p.source);
        print_samples(p.target);
        std::putchar('\n');
    }
}
} // namespace

int main(int argc, char **argv) {
    if (argc == 2 && !std::strcmp(argv[1], "vectors")) {
        vectors();
        return 0;
    }
    CHECK(argc == 1);
    static_assert(sizeof(LocomotionClock) + sizeof(LocomotionPlan) < 512);
    forbid_allocation = true;
    invalid_profiles();
    invalid_states_and_requests();
    blends();
    forbid_allocation = false;
    std::printf("LocomotionClock: %zu bytes; LocomotionPlan: %zu bytes\n",
                sizeof(LocomotionClock), sizeof(LocomotionPlan));
}
