#include "check.hpp"
#include "sh3/domain/locomotion_pose.hpp"
#include <cmath>
#include <cstring>
#include <limits>
#include <new>

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
using Error = LocomotionError;
using Mode = LocomotionMode;
constexpr auto profile = heather_locomotion_profile;
constexpr auto identity = LocomotionTransform{{}, {0, 0, 0, 1}};
struct Query { std::uint32_t clip, frame, bone; };
struct Reader final : LocomotionSampleReader {
    std::array<LocomotionLocalPose, 58> samples{};
    mutable std::array<Query, 1024> queries{};
    mutable unsigned calls{};
    unsigned fail_at = 1024;
    Reader() { for (auto &frame : samples) frame.fill(identity); }
    static unsigned packed(std::uint32_t clip, std::uint32_t frame) {
        for (const auto &c : profile.clips)
            if (c.id == clip) {
                CHECK(frame < c.count);
                return c.packed_first + frame;
            }
        CHECK(false);
        return 0;
    }
    LocomotionTransform &at(std::uint32_t clip, std::uint32_t frame, unsigned bone = 0) {
        return samples[packed(clip, frame)][bone];
    }
    bool read(std::uint32_t clip, std::uint32_t frame, std::uint32_t bone,
              LocomotionTransform &out) const noexcept override {
        CHECK(calls < queries.size() && bone < locomotion_bones);
        queries[calls] = {clip, frame, bone};
        if (calls++ == fail_at)
            return false;
        out = samples[packed(clip, frame)][bone];
        return true;
    }
};
LocomotionSkeleton skeleton(unsigned count = 2) {
    LocomotionSkeleton rig;
    rig.bone_count = count;
    for (unsigned i = 0; i < count; ++i) {
        rig.parents[i] = int(i) - 1;
        rig.channels[i] = i % 2 + 1;
    }
    return rig;
}
LocomotionClock stable(unsigned id, unsigned phase = 0) {
    return {1, id, id, Mode::stable, phase, 0, false};
}
LocomotionPlan plan(const LocomotionClock &clock, std::optional<std::uint32_t> request = {}) {
    LocomotionPlan p;
    CHECK(plan_locomotion_update(profile, clock, request, 2, p) == Error::ok);
    return p;
}
void near(float actual, float expected, float tolerance = 0.000001F) {
    CHECK(std::isfinite(actual) && std::abs(actual - expected) <= tolerance);
}
void unchanged(const LocomotionSkeleton &rig, const Reader &reader, const LocomotionPlan &p,
               const LocomotionPoseCache &cache, LocomotionPoseScratch &scratch, Error expected) {
    std::array<unsigned char, sizeof(cache)> before{};
    std::memcpy(before.data(), &cache, sizeof(cache));
    CHECK(stage_locomotion_pose(rig, reader, p, cache, scratch) == expected);
    CHECK(std::memcmp(before.data(), &cache, sizeof(cache)) == 0);
}
void initialization_and_wrap() {
    Reader reader;
    auto rig = skeleton();
    reader.at(101, 0).translation = {10, 20, 30};
    reader.at(101, 0).rotation = {0, 0, 0.6F, 0.8F};
    reader.at(101, 0, 1).translation = {2, 0, 0};
    LocomotionPoseScratch scratch;
    CHECK(initialize_locomotion_pose(rig, reader, scratch) == Error::ok);
    CHECK(reader.calls == 2 && reader.queries[0].bone == 1 && reader.queries[1].bone == 0);
    CHECK(scratch.next.last_valid && !scratch.next.saved_valid && scratch.next.bone_count == 2);
    near(scratch.model[1][12], 10.56F);
    near(scratch.model[1][13], 21.92F, 0.000004F);
    near(scratch.model[1][14], 30);
    auto cache = scratch.next;
    // A new parent pose must reach the child on this update, not on the next frame.
    reader.at(101, 0).translation = {12, 22, 32};
    unchanged(rig, reader, plan(stable(101)), cache, scratch, Error::ok);
    near(scratch.model[1][12], 12.56F);
    near(scratch.model[1][13], 23.92F, 0.000004F);
    near(scratch.model[1][14], 32);
    for (const auto &clip : profile.clips) {
        reader.at(clip.id, clip.count - 1).translation = {6, 4, 2};
        reader.at(clip.id, 0).translation = {2, 0, -2};
        reader.at(clip.id, clip.count - 1).rotation = {0, 0, 0, 1};
        reader.at(clip.id, 0).rotation = {0, 0, 0, -1};
        reader.calls = 0;
        const auto p = plan(stable(clip.id, clip.count * 4096 - 2048));
        unchanged(rig, reader, p, cache, scratch, Error::ok);
        near(scratch.next.last_local[0].translation.x, 4);
        near(scratch.next.last_local[0].translation.y, 2);
        near(scratch.next.last_local[0].translation.z, 0);
        near(scratch.next.last_local[0].rotation[3], 1);
        CHECK(reader.calls == 4);
        for (unsigned i = 0; i < reader.calls; ++i) {
            CHECK(reader.queries[i].clip == clip.id);
            CHECK(reader.queries[i].frame == (i % 2 ? 0 : clip.count - 1));
        }
    }
    reader.at(101, 0).rotation = {0, 0, 0, 1};
    reader.at(101, 1).rotation = {0, 0, 1, 0}; // dot=0 must retain the second sign.
    CHECK(stage_locomotion_pose(rig, reader, plan(stable(101, 2048)), cache, scratch) == Error::ok);
    near(scratch.next.last_local[0].rotation[2], std::sqrt(0.5F));
    near(scratch.next.last_local[0].rotation[3], std::sqrt(0.5F));
}
void frozen_cache() {
    Reader reader;
    auto rig = skeleton();
    LocomotionPoseScratch scratch;
    CHECK(initialize_locomotion_pose(rig, reader, scratch) == Error::ok);
    const auto initial = scratch.next;
    for (const auto edge : {std::array<unsigned, 2>{101, 109}, {109, 101}, {113, 101}}) {
        reader.at(edge[0], 0).translation = {0, 0, 0};
        reader.at(edge[0], 1).translation = {8, 4, -4};
        reader.at(edge[0], 1).rotation = {0.6F, 0, 0, 0.8F};
        auto p = plan(stable(edge[0], 3072));
        reader.calls = 0;
        CHECK(stage_locomotion_pose(rig, reader, p, initial, scratch) == Error::ok);
        auto cache = scratch.next;
        const auto frozen = cache.last_local;
        near(frozen[0].translation.x, 6);
        auto clock = p.next; // Already advanced; it must not be used to rebuild the cache.
        p = plan(clock, edge[1]);
        const auto count = edge[1] == 109 ? 5U : 8U;
        for (unsigned i = 0; i < count; ++i) {
            reader.calls = 0;
            unchanged(rig, reader, p, cache, scratch, Error::ok);
            CHECK(scratch.next.saved_valid);
            CHECK(std::memcmp(&frozen, &scratch.next.saved_local, sizeof(frozen)) == 0);
            CHECK(reader.calls == rig.bone_count);
            for (unsigned j = 0; j < reader.calls; ++j)
                CHECK(reader.queries[j].clip == edge[1] && reader.queries[j].frame == 0);
            cache = scratch.next;
            clock = p.next;
            p = plan(clock, edge[1]); // Repeated selection must not recapture the mixed result.
        }
        reader.calls = 0;
        unchanged(rig, reader, p, cache, scratch, Error::ok);
        CHECK(!scratch.next.saved_valid && p.next.mode == Mode::stable);
        CHECK(std::memcmp(&frozen, &scratch.next.saved_local, sizeof(frozen)) == 0);
        // Inactive cache bytes are retained, but the validity flag prevents reuse.
        CHECK(reader.calls == 4);
    }
}
void phase_blends() {
    Reader reader;
    auto rig = skeleton();
    LocomotionPoseScratch scratch;
    CHECK(initialize_locomotion_pose(rig, reader, scratch) == Error::ok);
    auto cache = scratch.next;
    for (const auto edge : {std::array<unsigned, 2>{109, 113}, {113, 109}}) {
        auto clock = stable(edge[0], 97040);
        for (unsigned i = 0; i < 11; ++i) {
            const auto p = plan(clock, edge[1]);
            reader.calls = 0;
            unchanged(rig, reader, p, cache, scratch, Error::ok);
            CHECK(reader.calls == (i < 10 ? 8U : 4U));
            for (unsigned j = 0; j < reader.calls; ++j) {
                const auto &query = reader.queries[j];
                const auto &window = i < 10 && j % 4 >= 2 ? p.source : p.target;
                CHECK(query.clip == window.clip_id);
                CHECK(query.frame == (j % 2 ? window.following : window.frame));
            }
            cache = scratch.next;
            clock = p.next;
        }
        CHECK(clock.mode == Mode::stable);
    }
}
void invalid_inputs() {
    Reader reader;
    auto rig = skeleton();
    LocomotionPoseScratch scratch;
    CHECK(initialize_locomotion_pose(rig, reader, scratch) == Error::ok);
    auto cache = scratch.next;
    const auto p = plan(initial_locomotion_clock());
    for (const auto count : {0U, 74U, std::numeric_limits<unsigned>::max()}) {
        auto bad = rig;
        bad.bone_count = count;
        unchanged(bad, reader, p, cache, scratch, Error::invalid_profile);
        CHECK(initialize_locomotion_pose(bad, reader, scratch) == Error::invalid_profile);
    }
    for (const auto parent : {-2, 1, 73}) {
        auto bad = rig;
        bad.parents[1] = parent;
        unchanged(bad, reader, p, cache, scratch, Error::invalid_profile);
    }
    for (const auto channel : {0, 3, 255}) {
        auto bad = rig;
        bad.channels[1] = channel;
        unchanged(bad, reader, p, cache, scratch, Error::invalid_profile);
    }
    cache.last_valid = false;
    unchanged(rig, reader, p, cache, scratch, Error::invalid_state);
    cache.last_valid = true;
    cache.bone_count = 1;
    unchanged(rig, reader, p, cache, scratch, Error::invalid_state);
    cache.bone_count = 2;
    unchanged(rig, reader, p, scratch.next, scratch, Error::invalid_state);
    auto bad = p;
    bad.next.profile_id = 2;
    unchanged(rig, reader, bad, cache, scratch, Error::invalid_state);
    for (auto member : {&LocomotionPlan::pose_phase, &LocomotionPlan::fraction_q12,
                        &LocomotionPlan::blend_q12}) {
        bad = p;
        bad.*member = 4096;
        unchanged(rig, reader, bad, cache, scratch, Error::invalid_state);
    }
    for (auto member : {&LocomotionSamples::clip_id, &LocomotionSamples::frame,
                        &LocomotionSamples::following, &LocomotionSamples::source_frame,
                        &LocomotionSamples::source_following, &LocomotionSamples::packed_frame,
                        &LocomotionSamples::packed_following}) {
        bad = p;
        ++(bad.target.*member);
        unchanged(rig, reader, bad, cache, scratch, Error::invalid_state);
    }
    bad = p;
    bad.evaluation = static_cast<LocomotionEvaluation>(99);
    unchanged(rig, reader, bad, cache, scratch, Error::invalid_state);
    bad = p;
    bad.cache = LocomotionCacheAction::capture_last;
    unchanged(rig, reader, bad, cache, scratch, Error::invalid_state);
    const auto nan = std::numeric_limits<float>::quiet_NaN();
    const auto inf = std::numeric_limits<float>::infinity();
    for (const auto value : {nan, inf, 100001.0F}) {
        for (auto member : {&Vec3::x, &Vec3::y, &Vec3::z}) {
            reader.at(101, 0, 1).translation.*member = value;
            unchanged(rig, reader, p, cache, scratch, Error::invalid_pose);
            reader.at(101, 0, 1) = identity;
        }
    }
    for (const auto q : {Quaternion{0, 0, 0, 0}, {0, 0, 0, 0.9F}, {nan, 0, 0, 1},
                         {0, inf, 0, 1}, {0, 0, 1.01F, 0}}) {
        reader.at(101, 0, 1).rotation = q;
        unchanged(rig, reader, p, cache, scratch, Error::invalid_pose);
        CHECK(initialize_locomotion_pose(rig, reader, scratch) == Error::invalid_pose);
        reader.at(101, 0, 1) = identity;
        cache.last_local[0].rotation = q;
        unchanged(rig, reader, p, cache, scratch, Error::invalid_pose);
        cache.last_local[0] = identity;
    }
    // Failure after the first channel. Only disposable scratch may have changed.
    for (unsigned failure = 0; failure < 4; ++failure) {
        reader.calls = 0;
        reader.fail_at = failure;
        unchanged(rig, reader, p, cache, scratch, Error::sample_unavailable);
    }
    reader.calls = 0;
    reader.fail_at = 1;
    CHECK(initialize_locomotion_pose(rig, reader, scratch) == Error::sample_unavailable);
    CHECK(!scratch.next.last_valid);
    reader.fail_at = 1024;
    reader.calls = 0;
    auto cached = plan(stable(109), 101);
    CHECK(stage_locomotion_pose(rig, reader, cached, cache, scratch) == Error::ok);
    cache = scratch.next;
    cached = plan(cached.next);
    cache.saved_local[0].rotation = {};
    unchanged(rig, reader, cached, cache, scratch, Error::invalid_pose);
    // The structural evaluator supports full capacity and multiple roots.
    rig = skeleton(73);
    rig.parents[2] = -1;
    reader.calls = 0;
    CHECK(initialize_locomotion_pose(rig, reader, scratch) == Error::ok);
    CHECK(reader.calls == 73);
}
void scan_transform(LocomotionTransform &t) {
    CHECK(std::scanf("%f%f%f%f%f%f%f", &t.translation.x, &t.translation.y, &t.translation.z,
                     &t.rotation[0], &t.rotation[1], &t.rotation[2], &t.rotation[3]) == 7);
}
void print_pose(const LocomotionClock &clock, const LocomotionPoseScratch &scratch) {
    std::printf("%u %u %u %u %u %u", clock.source_id, clock.target_id, unsigned(clock.mode),
                clock.counter, clock.blend, unsigned(scratch.next.saved_valid));
    for (unsigned i = 0; i < scratch.next.bone_count; ++i) {
        for (const auto &t : {scratch.next.last_local[i], scratch.next.saved_local[i]}) {
            std::printf(" %.9g %.9g %.9g", double(t.translation.x), double(t.translation.y),
                        double(t.translation.z));
            for (auto v : t.rotation) std::printf(" %.9g", double(v));
        }
        for (auto v : scratch.model[i]) std::printf(" %.9g", double(v));
    }
    std::puts("");
}
void vectors() {
    unsigned cases;
    CHECK(std::scanf("%u", &cases) == 1);
    for (unsigned scenario = 0; scenario < cases; ++scenario) {
        Reader reader;
        LocomotionSkeleton rig;
        auto clock = initial_locomotion_clock();
        unsigned mode, steps;
        CHECK(std::scanf("%u%u%u%u%u%u%u", &rig.bone_count, &clock.source_id, &clock.target_id,
                         &mode, &clock.counter, &clock.blend, &steps) == 7);
        CHECK(rig.bone_count > 0 && rig.bone_count <= 73 && steps < 100);
        clock.mode = static_cast<Mode>(mode);
        for (unsigned i = 0; i < rig.bone_count; ++i) {
            unsigned channel;
            CHECK(std::scanf("%d%u", &rig.parents[i], &channel) == 2);
            rig.channels[i] = channel;
        }
        for (auto &frame : reader.samples)
            for (unsigned i = 0; i < rig.bone_count; ++i)
                scan_transform(frame[i]);
        LocomotionPoseScratch scratch;
        CHECK(initialize_locomotion_pose(rig, reader, scratch) == Error::ok);
        print_pose(initial_locomotion_clock(), scratch);
        auto cache = scratch.next;
        for (unsigned i = 0; i < steps; ++i) {
            unsigned request, present;
            CHECK(std::scanf("%u%u", &request, &present) == 2);
            const auto p = plan(clock, present ? std::optional<std::uint32_t>{request} : std::nullopt);
            reader.calls = 0;
            CHECK(stage_locomotion_pose(rig, reader, p, cache, scratch) == Error::ok);
            print_pose(p.next, scratch);
            cache = scratch.next;
            clock = p.next;
        }
    }
}
} // namespace
int main(int argc, char **argv) {
    if (argc == 2 && std::strcmp(argv[1], "vectors") == 0) { vectors(); return 0; }
    forbid_allocation = true;
    initialization_and_wrap();
    frozen_cache();
    phase_blends();
    invalid_inputs();
    forbid_allocation = false;
    std::printf("Pose cache: %zu bytes; scratch: %zu bytes; allocation-free unit cases passed\n",
                sizeof(LocomotionPoseCache), sizeof(LocomotionPoseScratch));
}
