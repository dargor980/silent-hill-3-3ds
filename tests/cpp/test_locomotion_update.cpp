#include "check.hpp"
#include "sh3/domain/locomotion_update.hpp"
#include <cmath>
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
void *operator new(std::size_t n, std::align_val_t alignment) {
    if (forbid_allocation) std::abort();
    void *p = nullptr;
    if (posix_memalign(&p, std::size_t(alignment), n ? n : 1) == 0) return p;
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
constexpr auto profile = heather_locomotion_profile;
constexpr auto max = std::numeric_limits<std::uint32_t>::max();
constexpr auto nan = std::numeric_limits<float>::quiet_NaN();
constexpr auto inf = std::numeric_limits<float>::infinity();
using Bytes = std::array<unsigned char, sizeof(LocomotionState)>;
unsigned rejected_cases{}, successful_updates{};
Bytes bytes(const LocomotionState &s) {
    Bytes out{};
    std::memcpy(out.data(), &s, sizeof(s));
    return out;
}
enum class Fault { zero_quaternion, nan_x, nan_y, nan_z, inf_translation, large_translation,
                   nan_quaternion, inf_quaternion, short_quaternion, large_quaternion };
struct Reader final : LocomotionSampleReader {
    mutable unsigned calls{};
    unsigned missing_at = max, invalid_at = max;
    Fault fault{Fault::zero_quaternion};
    const LocomotionState *observed{};
    Bytes snapshot{};
    void watch(const LocomotionState &s) { observed = &s; snapshot = bytes(s); calls = 0; }
    void clear() { missing_at = invalid_at = max; calls = 0; observed = nullptr; }
    bool read(std::uint32_t clip, std::uint32_t frame, std::uint32_t bone,
              LocomotionTransform &out) const noexcept override {
        // Every callback, including the final one, must see the previous complete snapshot.
        if (observed) CHECK(std::memcmp(snapshot.data(), observed, sizeof(*observed)) == 0);
        CHECK(clip == 101 || clip == 109 || clip == 113);
        CHECK(frame < (clip == 101 ? 10U : 24U) && bone < locomotion_bones);
        const unsigned index = calls++, slot = clip == 101 ? 0 : clip == 109 ? 1 : 2;
        if (index == missing_at) return false;
        constexpr std::array<Quaternion, 4> rotations{{
            {{0, 0, 0, 1}}, {{0.6F, 0, 0, 0.8F}}, {{0, 0.8F, 0, 0.6F}}, {{0, 0, -1, 0}}}};
        out = {{float(slot) + float(frame) / 16 + float(bone) / 8,
                float(slot) / 4 - float(frame) / 32, float(bone) / 16 - float(frame) / 64},
               rotations[(frame + bone + slot) % 4]};
        if (index != invalid_at) return true;
        switch (fault) {
        case Fault::zero_quaternion: out.rotation = {}; break;
        case Fault::nan_x: out.translation.x = nan; break;
        case Fault::nan_y: out.translation.y = nan; break;
        case Fault::nan_z: out.translation.z = nan; break;
        case Fault::inf_translation: out.translation.x = inf; break;
        case Fault::large_translation: out.translation.x = 100001; break;
        case Fault::nan_quaternion: out.rotation[0] = nan; break;
        case Fault::inf_quaternion: out.rotation[1] = inf; break;
        case Fault::short_quaternion: out.rotation = {0, 0, 0, 0.9F}; break;
        case Fault::large_quaternion: out.rotation = {0, 0, 1.01F, 0}; break;
        }
        return true;
    }
};
LocomotionSkeleton skeleton(unsigned count = 2) {
    LocomotionSkeleton out;
    out.bone_count = count;
    for (unsigned i = 0; i < count; ++i) {
        out.parents[i] = int(i) - 1;
        out.channels[i] = i % 2 + 1;
    }
    return out;
}
void same(const LocomotionState &a, const LocomotionState &b) {
    const auto &x = a.clock, &y = b.clock;
    CHECK(x.profile_id == y.profile_id && x.source_id == y.source_id && x.target_id == y.target_id);
    CHECK(x.mode == y.mode && x.counter == y.counter && x.blend == y.blend);
    CHECK(x.saved_local_valid == y.saved_local_valid);
    CHECK(a.skeleton.bone_count == b.skeleton.bone_count);
    CHECK(a.skeleton.parents == b.skeleton.parents && a.skeleton.channels == b.skeleton.channels);
    CHECK(a.cache.bone_count == b.cache.bone_count && a.cache.last_valid == b.cache.last_valid);
    CHECK(a.cache.saved_valid == b.cache.saved_valid && a.model == b.model);
    for (unsigned i = 0; i < locomotion_bones; ++i) {
        for (bool saved : {false, true}) {
            const auto &u = saved ? a.cache.saved_local[i] : a.cache.last_local[i];
            const auto &v = saved ? b.cache.saved_local[i] : b.cache.last_local[i];
            CHECK(u.rotation == v.rotation && u.translation.x == v.translation.x);
            CHECK(u.translation.y == v.translation.y && u.translation.z == v.translation.z);
        }
    }
}
void start(Reader &reader, LocomotionState &state, LocomotionWorkspace &work, unsigned count = 2) {
    reader.clear();
    reader.watch(state);
    CHECK(initialize_locomotion(profile, skeleton(count), reader, state, work) == Error::ok);
    CHECK(reader.calls == count && state.cache.last_valid && !state.cache.saved_valid);
    CHECK(state.clock.counter == 0 && state.clock.target_id == 101);
    reader.clear();
}
void accepted(Reader &reader, LocomotionState &state, LocomotionWorkspace &work,
              std::optional<std::uint32_t> request = {}) {
    reader.watch(state);
    CHECK(update_locomotion(profile, reader, request, 2, state, work) == Error::ok);
    CHECK(state.clock.saved_local_valid == state.cache.saved_valid);
    ++successful_updates;
}
void rejected(const LocomotionProfile &p, Reader &reader, LocomotionState &state,
              LocomotionWorkspace &work, std::optional<std::uint32_t> request,
              unsigned ticks, Error expected, bool no_reads = false) {
    const auto before = bytes(state);
    reader.watch(state);
    CHECK(update_locomotion(p, reader, request, ticks, state, work) == expected);
    CHECK(bytes(state) == before);
    if (no_reads) CHECK(reader.calls == 0);
    ++rejected_cases;
}
void faulty_step(Reader &reader, LocomotionState &state, LocomotionWorkspace &work,
                 std::optional<std::uint32_t> request) {
    const auto before = state;
    reader.clear();
    accepted(reader, state, work, request);
    const auto after = state;
    const auto reads = reader.calls;
    CHECK(reads == (state.clock.mode == Mode::cached ? 2U :
                    state.clock.mode == Mode::phase_blend ? 8U : 4U));
    for (unsigned i = 0; i < reads; ++i) {
        for (bool missing : {true, false}) {
            state = before;
            reader.clear();
            if (missing) reader.missing_at = i;
            else reader.invalid_at = i;
            rejected(profile, reader, state, work, request, 2,
                     missing ? Error::sample_unavailable : Error::invalid_pose);
            // Retry on the same state/workspace must match an uninterrupted update exactly.
            reader.clear();
            accepted(reader, state, work, request);
            same(state, after);
        }
    }
    reader.clear();
}
void complete_sequences() {
    Reader reader;
    LocomotionState state;
    LocomotionWorkspace work;
    start(reader, state, work);
    faulty_step(reader, state, work, {});
    // All five supported edges, every beta and both exits, in one unmodified state chain.
    for (auto target : {109U, 113U, 109U, 101U, 109U, 113U, 101U}) {
        faulty_step(reader, state, work, target);
        while (state.clock.mode != Mode::stable)
            faulty_step(reader, state, work, target); // Current target is a no-op selection.
        const unsigned loop = target == 101 ? 67 : target == 109 ? 25 : 23;
        for (unsigned i = 0; i < loop; ++i)
            faulty_step(reader, state, work, {});
    }
}
void initial_failures_and_capacity() {
    Reader reader;
    LocomotionState state;
    LocomotionWorkspace work;
    start(reader, state, work, 73);
    const auto original = state;
    for (const auto count : {0U, 74U, max}) {
        auto rig = skeleton();
        rig.bone_count = count;
        reader.watch(state);
        const auto before = bytes(state);
        CHECK(initialize_locomotion(profile, rig, reader, state, work) == Error::invalid_profile);
        CHECK(bytes(state) == before && !reader.calls);
        ++rejected_cases;
    }
    auto bad_profile = profile;
    bad_profile.clips[1].packed_first = 0;
    reader.watch(state);
    auto before = bytes(state);
    CHECK(initialize_locomotion(bad_profile, skeleton(), reader, state, work) == Error::invalid_profile);
    CHECK(bytes(state) == before && !reader.calls);
    for (unsigned bone = 0; bone < 73; ++bone) {
        for (bool missing : {true, false}) {
            reader.clear();
            if (missing) reader.missing_at = bone;
            else reader.invalid_at = bone;
            reader.watch(state);
            before = bytes(state);
            CHECK(initialize_locomotion(profile, skeleton(73), reader, state, work) ==
                  (missing ? Error::sample_unavailable : Error::invalid_pose));
            CHECK(bytes(state) == before);
            ++rejected_cases;
        }
    }
    same(state, original);
    reader.clear();
    // A caller may reinitialize using the topology inside its current state.
    CHECK(initialize_locomotion(profile, state.skeleton, reader, state, work) == Error::ok);
    for (unsigned i = 0; i < 70; ++i) accepted(reader, state, work);
    for (auto target : {109U, 113U, 101U}) {
        accepted(reader, state, work, target);
        while (state.clock.mode != Mode::stable) accepted(reader, state, work);
    }
    auto rig = skeleton(1);
    reader.clear();
    CHECK(initialize_locomotion(profile, rig, reader, state, work) == Error::ok);
    rig.bone_count = 74; // The input rig is not borrowed by the published state.
    CHECK(state.skeleton.bone_count == 1);
    work.pose.model[72].fill(nan);
    accepted(reader, state, work);
    for (unsigned i = 1; i < 73; ++i) {
        CHECK(state.model[i] == PoseMatrix{});
        CHECK(state.cache.last_local[i].rotation == Quaternion{});
    }
}
void invalid_states_and_precedence() {
    Reader reader;
    LocomotionState state;
    LocomotionWorkspace work;
    rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
    start(reader, state, work);
    const auto initial = state;
    auto bad_profile = profile;
    bad_profile.id = 2;
    state.cache.last_valid = false;
    rejected(bad_profile, reader, state, work, 0, 0, Error::invalid_profile, true);
    rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
    state = initial;
    for (const auto count : {0U, 1U, 74U, max}) {
        state.cache.bone_count = count;
        rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
    }
    state = initial;
    state.cache.saved_valid = true;
    rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
    state = initial;
    for (const auto count : {0U, 74U, max}) {
        state.skeleton.bone_count = count;
        rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
    }
    state = initial;
    for (const auto parent : {-2, 1, 73}) {
        state.skeleton.parents[1] = parent;
        rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
    }
    state = initial;
    for (const auto owner : {0, 3, 255}) {
        state.skeleton.channels[1] = owner;
        rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
    }
    state = initial;
    for (auto field : {&LocomotionClock::profile_id, &LocomotionClock::source_id,
                       &LocomotionClock::target_id, &LocomotionClock::counter,
                       &LocomotionClock::blend}) {
        state.clock.*field = max;
        rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
        state = initial;
    }
    state.clock.mode = static_cast<Mode>(4);
    rejected(profile, reader, state, work, 0, 0, Error::invalid_state, true);
    state = initial;
    reader.missing_at = reader.invalid_at = 0;
    for (auto ticks : {0U, 1U, 3U, max})
        rejected(profile, reader, state, work, 0, ticks, Error::invalid_ticks, true);
    for (auto id : {0U, 65535U, max})
        rejected(profile, reader, state, work, id, 2, Error::unknown_clip, true);
    rejected(profile, reader, state, work, 113, 2, Error::unsupported_transition, true);
    reader.clear();
    accepted(reader, state, work, 109);
    rejected(profile, reader, state, work, 0, 2, Error::unknown_clip, true);
    rejected(profile, reader, state, work, 101, 2, Error::transition_busy, true);
    auto cached = state;
    state.cache.saved_valid = false;
    rejected(profile, reader, state, work, {}, 2, Error::invalid_state, true);
    state = cached;
    state.cache.saved_local[0].rotation = {};
    rejected(profile, reader, state, work, {}, 2, Error::invalid_pose);
    reader.missing_at = 1;
    rejected(profile, reader, state, work, {}, 2, Error::sample_unavailable);
    reader.clear();
    state = cached;
    while (state.clock.mode != Mode::stable) accepted(reader, state, work);
    accepted(reader, state, work, 113);
    rejected(profile, reader, state, work, 109, 2, Error::transition_busy, true);
    // Invalid samples before a later missing read, including within the same bone.
    reader.invalid_at = 0;
    for (auto missing : {1U, 4U, 7U}) {
        reader.missing_at = missing;
        rejected(profile, reader, state, work, {}, 2, Error::sample_unavailable);
    }
    reader.clear();
    for (unsigned fault = 0; fault <= unsigned(Fault::large_quaternion); ++fault) {
        reader.fault = static_cast<Fault>(fault);
        for (unsigned read = 0; read < 8; ++read) {
            reader.invalid_at = read;
            rejected(profile, reader, state, work, {}, 2, Error::invalid_pose);
        }
    }
    reader.clear();
    state = initial;
    for (unsigned i = 0; i < 16; ++i) {
        for (auto value : {nan, inf, -inf}) {
            state.model[0][i] = value;
            rejected(profile, reader, state, work, {}, 2, Error::invalid_pose);
            state = initial;
        }
    }
    for (auto i : {3U, 7U, 11U, 15U}) {
        state.model[0][i] = 2;
        rejected(profile, reader, state, work, {}, 2, Error::invalid_pose);
        state = initial;
    }
    for (auto member : {&Vec3::x, &Vec3::y, &Vec3::z}) {
        state.cache.last_local[0].translation.*member = inf;
        rejected(profile, reader, state, work, {}, 2, Error::invalid_pose);
        state = initial;
    }
    state.model[0][0] = nan;
    reader.missing_at = 3;
    rejected(profile, reader, state, work, {}, 2, Error::sample_unavailable);
    reader.clear();
    state = initial;
    reader.invalid_at = 0;
    reader.missing_at = 1;
    const auto before = bytes(state);
    reader.watch(state);
    CHECK(initialize_locomotion(profile, skeleton(), reader, state, work) == Error::sample_unavailable);
    CHECK(bytes(state) == before);
}
void explicit_restart() {
    Reader reader;
    LocomotionState state;
    LocomotionWorkspace work;
    start(reader, state, work);
    accepted(reader, state, work, 109);
    CHECK(state.cache.saved_valid);
    for (auto target : {101U, 109U, 113U}) {
        for (bool missing : {false, true}) {
            reader.clear();
            if (missing) reader.missing_at = 1;
            else reader.invalid_at = 1;
            reader.watch(state);
            const auto before = bytes(state);
            CHECK(initialize_locomotion(profile, state.skeleton, reader, state, work, target) ==
                  (missing ? Error::sample_unavailable : Error::invalid_pose));
            CHECK(bytes(state) == before);
        }
        reader.clear();
        reader.watch(state);
        CHECK(initialize_locomotion(profile, state.skeleton, reader, state, work, target) == Error::ok);
        CHECK(state.clock.source_id == target && state.clock.target_id == target);
        CHECK(state.clock.counter == 0 && state.clock.blend == 0 && state.clock.mode == Mode::stable);
        CHECK(!state.cache.saved_valid && !state.clock.saved_local_valid && reader.calls == 2);
        reader.clear();
        LocomotionTransform first;
        CHECK(reader.read(target, 0, 0, first));
        CHECK(state.cache.last_local[0].translation.x == first.translation.x);
        for (unsigned i = 0; i < 73; ++i)
            CHECK(state.cache.saved_local[i].rotation == Quaternion{});
    }
    for (auto unknown : {0U, 108U, max}) {
        reader.watch(state);
        const auto before = bytes(state);
        CHECK(initialize_locomotion(profile, state.skeleton, reader, state, work, unknown) == Error::unknown_clip);
        CHECK(bytes(state) == before && reader.calls == 0);
    }
}
void print_state(Error error, const LocomotionState &state) {
    const auto &clock = state.clock;
    std::printf("%u %u %u %u %u %u %u", unsigned(error), clock.source_id, clock.target_id,
                unsigned(clock.mode), clock.counter, clock.blend, unsigned(state.cache.saved_valid));
    for (unsigned i = 0; i < state.skeleton.bone_count; ++i) {
        for (const auto &t : {state.cache.last_local[i], state.cache.saved_local[i]}) {
            std::printf(" %.9g %.9g %.9g", double(t.translation.x), double(t.translation.y),
                        double(t.translation.z));
            for (auto v : t.rotation) std::printf(" %.9g", double(v));
        }
        for (auto v : state.model[i]) std::printf(" %.9g", double(v));
    }
    std::puts("");
}
void vectors() {
    Reader reader;
    LocomotionState state;
    LocomotionWorkspace work;
    start(reader, state, work);
    print_state(Error::ok, state);
    unsigned request, present, ticks;
    while (std::scanf("%u%u%u", &request, &present, &ticks) == 3) {
        reader.clear();
        const auto error = update_locomotion(profile, reader,
            present ? std::optional<std::uint32_t>{request} : std::nullopt, ticks, state, work);
        print_state(error, state);
    }
}
} // namespace
int main(int argc, char **argv) {
    if (argc == 2 && std::strcmp(argv[1], "vectors") == 0) { vectors(); return 0; }
    forbid_allocation = true;
    complete_sequences();
    initial_failures_and_capacity();
    invalid_states_and_precedence();
    explicit_restart();
    forbid_allocation = false;
    std::printf("%u rejected cases; %u successful/retried updates; no allocations\n",
                rejected_cases, successful_updates);
    std::printf("State %zu + workspace %zu = %zu / %zu bytes\n", sizeof(LocomotionState),
                sizeof(LocomotionWorkspace), sizeof(LocomotionState) + sizeof(LocomotionWorkspace),
                locomotion_memory_budget);
}
