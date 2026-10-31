#include "check.hpp"
#include "sh3/domain/locomotion_update.hpp"
#include <cstring>
#include <limits>
#include <new>

namespace { bool forbid_allocation = false; }
void *operator new(std::size_t n) {
    if (forbid_allocation) std::abort();
    if (auto *p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void *operator new(std::size_t n, std::align_val_t a) {
    if (forbid_allocation) std::abort();
    void *p = nullptr;
    if (posix_memalign(&p, std::size_t(a), n ? n : 1) == 0) return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n, std::align_val_t a) { return ::operator new(n, a); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
void operator delete(void *p, std::align_val_t) noexcept { std::free(p); }
void operator delete(void *p, std::size_t, std::align_val_t) noexcept { std::free(p); }
void operator delete[](void *p, std::align_val_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t, std::align_val_t) noexcept { std::free(p); }

namespace {
using namespace sh3::domain;
using Error = LocomotionError;
using Mode = LocomotionMode;
constexpr auto profile = heather_turns_profile;
constexpr auto unlimited = std::numeric_limits<unsigned>::max();
constexpr LocomotionTransform identity{{}, {0, 0, 0, 1}};
unsigned rejections{}, successes{};
template <class T> auto bytes(const T &value) {
    std::array<unsigned char, sizeof(T)> out{};
    std::memcpy(out.data(), &value, sizeof(value));
    return out;
}
LocomotionSkeleton skeleton(unsigned count = 2) {
    LocomotionSkeleton rig{};
    rig.bone_count = count;
    for (unsigned i = 0; i < count; ++i) {
        rig.parents[i] = int(i) - 1;
        rig.channels[i] = i % 2 ? 1 : 2;
    }
    return rig;
}
struct Reader final : LocomotionSampleReader {
    mutable unsigned calls{};
    unsigned missing = unlimited, invalid = unlimited;
    unsigned source = 101, target = 107, source_frame{};
    bool literal{};
    LocomotionTransform first = identity, following = identity, destination = identity;
    const LocomotionState *observed{};
    std::array<unsigned char, sizeof(LocomotionState)> snapshot{};
    void watch(const LocomotionState &state) {
        observed = &state;
        snapshot = bytes(state);
        calls = 0;
    }
    bool read(std::uint32_t clip, std::uint32_t frame, std::uint32_t bone,
              LocomotionTransform &out) const noexcept override {
        if (observed) CHECK(bytes(*observed) == snapshot);
        const LocomotionClip *descriptor = nullptr;
        for (const auto &c : profile.active_clips()) if (c.id == clip) descriptor = &c;
        CHECK(descriptor && frame < descriptor->count && bone < locomotion_bones);
        const auto call = calls++;
        if (call == missing) return false;
        if (literal) {
            CHECK(clip == source || clip == target);
            out = bone ? LocomotionTransform{{5, -3, 2}, {0, 0, 0, 1}}
                       : clip == target ? destination : frame == source_frame ? first : following;
        } else {
            constexpr std::array<Quaternion, 4> rotations{{
                {{0, 0, 0, 1}}, {{0.6F, 0, 0, 0.8F}},
                {{0, 0.8F, 0, 0.6F}}, {{0, 0, -0.8F, 0.6F}}}};
            out = {{float(frame) / 16, float(bone) / 8, float(clip - 100) / 32},
                   rotations[(frame + clip + bone) % rotations.size()]};
        }
        if (call == invalid) out.rotation = {};
        return true;
    }
};
void start(Reader &reader, LocomotionState &state, LocomotionWorkspace &work,
           unsigned clip = 101, unsigned count = 2, const LocomotionProfile &p = profile) {
    reader.watch(state);
    CHECK(initialize_locomotion(p, skeleton(count), reader, state, work, clip) == Error::ok);
    CHECK(state.clock.profile_id == p.id && state.clock.source_id == clip);
    CHECK(state.clock.target_id == clip && state.clock.counter == 0 && state.clock.blend == 0);
    CHECK(state.clock.mode == Mode::stable && !state.cache.saved_valid);
}
void same(const LocomotionState &a, const LocomotionState &b) {
    // Padding is not a semantic success result; failures below compare object bytes.
    const auto &x = a.clock, &y = b.clock;
    CHECK(x.profile_id == y.profile_id && x.source_id == y.source_id && x.target_id == y.target_id);
    CHECK(x.mode == y.mode && x.counter == y.counter && x.blend == y.blend);
    CHECK(x.saved_local_valid == y.saved_local_valid && a.model == b.model);
    CHECK(a.cache.bone_count == b.cache.bone_count && a.cache.last_valid == b.cache.last_valid);
    CHECK(a.cache.saved_valid == b.cache.saved_valid);
    CHECK(a.skeleton.bone_count == b.skeleton.bone_count);
    CHECK(a.skeleton.parents == b.skeleton.parents && a.skeleton.channels == b.skeleton.channels);
    for (unsigned i = 0; i < locomotion_bones; ++i)
        for (bool saved : {false, true}) {
            const auto &u = saved ? a.cache.saved_local[i] : a.cache.last_local[i];
            const auto &v = saved ? b.cache.saved_local[i] : b.cache.last_local[i];
            CHECK(u.rotation == v.rotation && u.translation.x == v.translation.x);
            CHECK(u.translation.y == v.translation.y && u.translation.z == v.translation.z);
        }
}
void faulty_step(Reader &reader, LocomotionState &state, LocomotionWorkspace &work,
                 std::optional<unsigned> request) {
    const auto before = state;
    reader.watch(state);
    CHECK(update_locomotion(profile, reader, request, 2, state, work) == Error::ok);
    const auto after = state;
    const auto calls = reader.calls;
    ++successes;
    for (unsigned i = 0; i < calls; ++i)
        for (bool missing : {false, true}) {
            state = before;
            reader.watch(state);
            const auto saved = bytes(state);
            reader.missing = missing ? i : unlimited;
            reader.invalid = missing ? unlimited : i;
            CHECK(update_locomotion(profile, reader, request, 2, state, work) ==
                  (missing ? Error::sample_unavailable : Error::invalid_pose));
            CHECK(bytes(state) == saved);
            ++rejections;
            reader.invalid = reader.missing = unlimited;
            reader.watch(state);
            CHECK(update_locomotion(profile, reader, request, 2, state, work) == Error::ok);
            same(state, after);
            ++successes;
        }
}
void transactions() {
    Reader reader;
    LocomotionState state{};
    LocomotionWorkspace work{};
    for (unsigned turn : {107U, 108U}) {
        start(reader, state, work);
        for (unsigned i = 0; i < 17; ++i) faulty_step(reader, state, work, {});
        for (unsigned target : {turn, 101U}) {
            faulty_step(reader, state, work, target);
            const auto frozen = state.cache.saved_local;
            while (state.clock.mode != Mode::stable) {
                faulty_step(reader, state, work, target);
                CHECK(bytes(frozen) == bytes(state.cache.saved_local));
            }
            for (unsigned i = 0; i < 19; ++i) faulty_step(reader, state, work, {});
        }
    }
    // Maximum topology, both channels; initialization failure at every required read.
    start(reader, state, work, 108, 73);
    const auto before = bytes(state);
    for (unsigned i = 0; i < 73; ++i)
        for (bool missing : {true, false}) {
            reader.missing = missing ? i : unlimited;
            reader.invalid = missing ? unlimited : i;
            reader.watch(state);
            CHECK(initialize_locomotion(profile, state.skeleton, reader, state, work, 107) ==
                  (missing ? Error::sample_unavailable : Error::invalid_pose));
            CHECK(bytes(state) == before);
            ++rejections;
        }
    reader.invalid = reader.missing = unlimited;
    faulty_step(reader, state, work, 101);
    // Explicit reset in a cached turn removes all saved poses without advancing.
    start(reader, state, work);
    CHECK(!state.cache.saved_valid);
    for (const auto &t : state.cache.saved_local) CHECK(t.rotation == Quaternion{});
}
void reject_profile(const LocomotionProfile &p) {
    CHECK(!valid_locomotion_profile(p));
    LocomotionPlan out{};
    const auto sentinel = bytes(out);
    CHECK(plan_locomotion_update(p, {}, 0, 0, out) == Error::invalid_profile);
    CHECK(bytes(out) == sentinel);
    Reader reader;
    LocomotionState state{};
    LocomotionWorkspace work{};
    const auto before = bytes(state);
    CHECK(initialize_locomotion(p, skeleton(), reader, state, work) == Error::invalid_profile);
    CHECK(bytes(state) == before && reader.calls == 0);
    CHECK(initialize_locomotion_pose(skeleton(), reader, work.pose, 101, p) == Error::invalid_profile);
    ++rejections;
}
void profiles_and_plans() {
    for (const auto &fixed : {heather_locomotion_profile, profile}) {
        CHECK(valid_locomotion_profile(fixed));
        for (auto member : {&LocomotionProfile::id, &LocomotionProfile::clip_count,
                            &LocomotionProfile::model_resource, &LocomotionProfile::animation_resource,
                            &LocomotionProfile::sample_count, &LocomotionProfile::ticks}) {
            auto bad = fixed;
            bad.*member = unlimited;
            reject_profile(bad);
        }
        for (unsigned i = 0; i < 5; ++i) {
            for (auto member : {&LocomotionClip::id, &LocomotionClip::count, &LocomotionClip::start,
                                &LocomotionClip::end, &LocomotionClip::loop,
                                &LocomotionClip::trailing, &LocomotionClip::packed_first}) {
                auto bad = fixed;
                ++(bad.clips[i].*member); // Includes every inactive record of profile 1.
                reject_profile(bad);
            }
            auto bad = fixed;
            ++bad.clips[i].speed;
            reject_profile(bad);
        }
        for (const auto &clip : fixed.active_clips()) {
            Reader reader;
            LocomotionState state{};
            LocomotionWorkspace work{};
            start(reader, state, work, clip.id, 2, fixed);
        }
    }
    auto bad = profile;
    bad.clip_count = 6;
    CHECK(bad.active_clips().begin() == bad.active_clips().end());
    reject_profile(bad);
    bad = profile;
    bad.id = 1;
    reject_profile(bad);
    Reader reader;
    LocomotionState state{};
    LocomotionWorkspace work{};
    start(reader, state, work);
    for (auto id : {0U, 999U}) {
        const auto before = bytes(state);
        reader.watch(state);
        CHECK(initialize_locomotion(profile, state.skeleton, reader, state, work, id) == Error::unknown_clip);
        CHECK(bytes(state) == before && reader.calls == 0);
    }
    CHECK(plan_locomotion_update(profile, state.clock, 107, 2, work.plan) == Error::ok);
    for (auto id : {0U, 1U, 99U}) {
        auto forged = work.plan;
        forged.next.profile_id = id;
        reader.watch(state);
        CHECK(stage_locomotion_pose(state.skeleton, reader, forged, state.cache, work.pose) == Error::invalid_state);
        CHECK(reader.calls == 0);
    }
}
void print_clock(const LocomotionClock &s) {
    std::printf(" %u %u %u %u %u %u %u", s.profile_id, s.source_id, s.target_id,
                unsigned(s.mode), s.counter, s.blend, unsigned(s.saved_local_valid));
}
void print_pose(const LocomotionState &s) {
    std::printf("0");
    print_clock(s.clock);
    for (const auto &t : {s.cache.last_local[0], s.cache.saved_local[0]}) {
        std::printf(" %.9g %.9g %.9g", double(t.translation.x), double(t.translation.y), double(t.translation.z));
        for (auto v : t.rotation) std::printf(" %.9g", double(v));
    }
    for (unsigned b = 0; b < 2; ++b)
        for (auto v : s.model[b]) std::printf(" %.9g", double(v));
    std::puts("");
}
void read_transform(LocomotionTransform &t) {
    CHECK(std::scanf("%f%f%f%f%f%f%f", &t.translation.x, &t.translation.y, &t.translation.z,
                     &t.rotation[0], &t.rotation[1], &t.rotation[2], &t.rotation[3]) == 7);
}
void vectors() {
    char command;
    while (std::scanf(" %c", &command) == 1) {
        Reader reader;
        LocomotionState state{};
        LocomotionWorkspace work{};
        if (command == 'P') {
            unsigned phase;
            CHECK(std::scanf("%u%u%u", &reader.source, &reader.target, &phase) == 3);
            reader.literal = true;
            reader.source_frame = phase / 4096;
            read_transform(reader.first);
            read_transform(reader.following);
            read_transform(reader.destination);
            start(reader, state, work, reader.source);
            state.clock.counter = phase;
            reader.watch(state);
            CHECK(update_locomotion(profile, reader, {}, 2, state, work) == Error::ok);
            do {
                reader.watch(state);
                CHECK(update_locomotion(profile, reader, reader.target, 2, state, work) == Error::ok);
                print_pose(state);
            } while (state.clock.mode != Mode::stable);
        } else if (command == 'R') {
            unsigned count, target;
            CHECK(std::scanf("%u", &count) == 1);
            start(reader, state, work);
            while (count--) {
                CHECK(std::scanf("%u", &target) == 1);
                reader.watch(state);
                const auto error = update_locomotion(profile, reader, target, 2, state, work);
                CHECK(error == Error::ok);
                std::printf("%u", unsigned(error)); print_clock(state.clock); std::puts("");
            }
        } else {
            CHECK(command == 'C' || command == 'U');
            unsigned id, mode, saved, request, present, ticks;
            LocomotionClock clock;
            CHECK(std::scanf("%u%u%u%u%u%u%u%u%u%u%u", &id, &clock.profile_id,
                &clock.source_id, &clock.target_id, &mode, &clock.counter, &clock.blend,
                &saved, &request, &present, &ticks) == 11);
            clock.mode = static_cast<Mode>(mode);
            clock.saved_local_valid = saved;
            auto p = id == 1 ? heather_locomotion_profile : profile;
            p.id = id;
            const auto req = present ? std::optional<unsigned>{request} : std::nullopt;
            if (command == 'C') {
                LocomotionPlan plan{};
                const auto before = bytes(plan);
                const auto error = plan_locomotion_update(p, clock, req, ticks, plan);
                std::printf("%u", unsigned(error));
                if (error != Error::ok) CHECK(bytes(plan) == before);
                else {
                    print_clock(plan.next);
                    std::printf(" %u %u %u %u %u", unsigned(plan.evaluation), unsigned(plan.cache),
                                plan.pose_phase, plan.fraction_q12, plan.blend_q12);
                    for (auto s : {plan.source, plan.target})
                        std::printf(" %u %u %u %u %u %u %u", s.clip_id, s.frame, s.following,
                                    s.source_frame, s.source_following, s.packed_frame, s.packed_following);
                }
                std::puts("");
            } else {
                start(reader, state, work);
                state.clock = clock;
                state.cache.saved_valid = clock.saved_local_valid;
                state.cache.saved_local = state.cache.last_local;
                CHECK(std::scanf("%u%u", &reader.invalid, &reader.missing) == 2);
                reader.watch(state);
                const auto before = bytes(state);
                const auto error = update_locomotion(p, reader, req, ticks, state, work);
                std::printf("%u", unsigned(error));
                if (error != Error::ok) {
                    CHECK(bytes(state) == before);
                    if (error <= Error::unsupported_transition) CHECK(reader.calls == 0);
                } else print_clock(state.clock);
                std::puts("");
            }
        }
    }
}
} // namespace
int main(int argc, char **argv) {
    forbid_allocation = true;
    if (argc == 2 && std::strcmp(argv[1], "vectors") == 0) vectors();
    else {
        profiles_and_plans();
        transactions();
        std::printf("HG core: %u rejections; %u successful/retried steps; no allocations\n", rejections, successes);
        std::printf("Profile %zu; state %zu + workspace %zu = %zu / %zu bytes\n",
                    sizeof(LocomotionProfile), sizeof(LocomotionState), sizeof(LocomotionWorkspace),
                    sizeof(LocomotionState) + sizeof(LocomotionWorkspace), locomotion_memory_budget);
    }
    forbid_allocation = false;
}
