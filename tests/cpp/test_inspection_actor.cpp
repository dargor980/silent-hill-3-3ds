#include "check.hpp"
#include "sh3/application/inspection_actor.hpp"
#include <cmath>
#include <cstring>
#include <limits>
#include <new>
#include <utility>

namespace { bool forbid_allocation = false; }
void *operator new(std::size_t n) {
    if (forbid_allocation) std::abort();
    if (auto *p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }

namespace {
using namespace sh3;
using Actor = application::InspectionActor;
using Snapshot = application::InspectionActorSnapshot;
using Error = application::InspectionActorError;
using AnimationError = domain::LocomotionError;
using Motion = domain::InspectionMotion;
using Turn = domain::InspectionTurn;
using Intent = domain::InspectionMovementIntent;
using Bytes = std::array<unsigned char, sizeof(Snapshot)>;
constexpr auto profile = domain::heather_locomotion_profile;
constexpr auto maximum = std::numeric_limits<unsigned>::max();
constexpr auto nan = std::numeric_limits<float>::quiet_NaN();
constexpr auto inf = std::numeric_limits<float>::infinity();
unsigned failures{}, updates{}, callbacks{};
Bytes bytes(const Actor &actor) {
    Bytes result;
    std::memcpy(result.data(), &actor.snapshot(), result.size());
    return result;
}
void near(double a, double b) { CHECK(std::isfinite(a) && std::abs(a - b) < .0001); }
void same(domain::Vec3 a, domain::Vec3 b) { CHECK(a.x == b.x && a.y == b.y && a.z == b.z); }
struct Watch {
    Actor *actor{};
    Bytes before{};
    bool ready{}, reenter{};
    void begin(Actor &a, bool nested = true) {
        actor = &a; before = bytes(a); ready = a.ready(); reenter = nested;
    }
    void check() const noexcept {
        if (!actor) return;
        ++callbacks;
        CHECK(bytes(*actor) == before && actor->ready() == ready);
        if (reenter) {
            CHECK(actor->step({}, 2).error == Error::busy);
            CHECK(actor->reset({1, 2, 3}, 0).error == Error::busy);
            CHECK(bytes(*actor) == before && actor->ready() == ready);
        }
    }
};
struct Reader final : domain::LocomotionSampleReader {
    Watch *watch{};
    mutable unsigned calls{};
    unsigned missing_at{maximum}, invalid_at{maximum};
    void clear() { calls = 0; missing_at = invalid_at = maximum; }
    bool read(std::uint32_t clip, std::uint32_t frame, std::uint32_t bone,
              domain::LocomotionTransform &out) const noexcept override {
        if (watch) watch->check();
        CHECK((clip == 101 || clip == 109 || clip == 113) && bone < 73);
        const auto index = calls++;
        if (index == missing_at) {
            out.translation = {nan, nan, nan}; // A failed reader may poison its scratch.
            return false;
        }
        const auto channel_offset = bone % 2 ? -3.F : 8.F;
        out = {{channel_offset + float(frame) / 8 + float(clip - 101),
                2 + float(bone), -4 - float(bone) / 2}, {0, 0, 0, 1}};
        if (index == invalid_at) out.rotation = {}; // Both channels must validate.
        return true;
    }
};
enum class ContactMode { correct, block, unavailable, unsupported, unknown, partial, unwritten, fixed };
struct Contacts final : ports::IMovementContacts {
    Watch *watch{};
    mutable unsigned calls{};
    mutable ports::MovementContactQuery last{};
    ContactMode mode{ContactMode::correct};
    domain::Vec3 fixed{};
    ports::MovementContactStatus resolve(const ports::MovementContactQuery &q,
                                         domain::Vec3 &out) const noexcept override {
        if (watch) watch->check();
        ++calls;
        last = q;
        switch (mode) {
        case ContactMode::correct: out = {q.requested.x + 3, q.requested.y + 4, q.requested.z - 5}; break;
        case ContactMode::block: out = q.from; break;
        case ContactMode::unavailable: out = {123, 456, 789}; return ports::MovementContactStatus::unavailable;
        case ContactMode::unsupported: return ports::MovementContactStatus::unsupported;
        case ContactMode::unknown: return static_cast<ports::MovementContactStatus>(99);
        case ContactMode::partial: out.x = q.requested.x; break;
        case ContactMode::unwritten: break;
        case ContactMode::fixed: out = fixed; break;
        }
        return ports::MovementContactStatus::accepted;
    }
};
domain::LocomotionSkeleton skeleton(unsigned count = 2) {
    domain::LocomotionSkeleton s;
    s.bone_count = count;
    for (unsigned i = 0; i < count; ++i) {
        s.parents[i] = int(i) - 1;
        s.channels[i] = i % 2 + 1;
    }
    return s;
}
unsigned clip(Motion motion) { return motion == Motion::idle ? 101 : motion == Motion::walk ? 109 : 113; }
void same_animation(const domain::LocomotionState &a, const domain::LocomotionState &b) {
    CHECK(a.clock.profile_id == b.clock.profile_id && a.clock.source_id == b.clock.source_id &&
          a.clock.target_id == b.clock.target_id && a.clock.mode == b.clock.mode &&
          a.clock.counter == b.clock.counter && a.clock.blend == b.clock.blend &&
          a.clock.saved_local_valid == b.clock.saved_local_valid);
    CHECK(a.skeleton.bone_count == b.skeleton.bone_count && a.skeleton.parents == b.skeleton.parents &&
          a.skeleton.channels == b.skeleton.channels && a.model == b.model);
    CHECK(a.cache.last_valid == b.cache.last_valid && a.cache.saved_valid == b.cache.saved_valid &&
          a.cache.bone_count == b.cache.bone_count);
    for (unsigned i = 0; i < 73; ++i) {
        same(a.cache.last_local[i].translation, b.cache.last_local[i].translation);
        same(a.cache.saved_local[i].translation, b.cache.saved_local[i].translation);
        CHECK(a.cache.last_local[i].rotation == b.cache.last_local[i].rotation);
        CHECK(a.cache.saved_local[i].rotation == b.cache.saved_local[i].rotation);
    }
}
void reject(Actor &actor, Reader &reader, Contacts &contacts, Watch &watch,
            Intent intent, unsigned ticks, Error error, bool query_expected,
            AnimationError animation = AnimationError::ok) {
    const auto before = bytes(actor);
    const auto ready = actor.ready();
    reader.calls = contacts.calls = 0;
    watch.begin(actor);
    const auto result = actor.step(intent, ticks);
    CHECK(result.error == error && result.animation == animation);
    CHECK(bytes(actor) == before && actor.ready() == ready);
    CHECK(contacts.calls == unsigned(query_expected));
    if (!query_expected) CHECK(reader.calls == 0);
    ++failures;
}
void initial_and_preflight() {
    Watch watch;
    Reader reader; reader.watch = &watch;
    Contacts contacts; contacts.watch = &watch;
    auto topology = skeleton();
    auto metadata = profile;
    Actor actor(metadata, topology, reader, contacts);
    topology.channels[1] = 0; metadata.id = 99; // Constructor owns both metadata objects.
    CHECK(!actor.ready());
    reject(actor, reader, contacts, watch, {}, 2, Error::not_initialized, false);
    const auto empty = bytes(actor);
    CHECK(actor.reset({nan, 0, 0}, 0).error == Error::invalid_placement);
    CHECK(bytes(actor) == empty && !actor.ready());
    for (auto index : {0U, 1U}) {
        reader.clear(); reader.missing_at = index; watch.begin(actor);
        CHECK(actor.reset({1, 2, 3}, 0).animation == AnimationError::sample_unavailable);
        CHECK(bytes(actor) == empty && !actor.ready() && contacts.calls == 0);
    }
    reader.clear(); watch.begin(actor);
    CHECK(actor.reset({10, -7, 20}, 0).error == Error::ok && actor.ready());
    CHECK(actor.snapshot().movement.ordinal == 0 && actor.snapshot().animation.clock.counter == 0);
    CHECK(actor.snapshot().animation.skeleton.channels[1] == 2 && contacts.calls == 0);
    reject(actor, reader, contacts, watch, {Motion::run, Turn::none}, 2,
           Error::animation_rejected, false, AnimationError::unsupported_transition);
    for (auto ticks : {0U, 1U, 3U, maximum}) {
        reject(actor, reader, contacts, watch, {}, ticks, Error::movement_rejected, false);
        CHECK(actor.step({}, ticks).movement == domain::InspectionMovementError::invalid_ticks);
    }
    reject(actor, reader, contacts, watch, {static_cast<Motion>(-1), Turn::none}, 2,
           Error::movement_rejected, false);
    reject(actor, reader, contacts, watch, {Motion::idle, static_cast<Turn>(9)}, 2,
           Error::movement_rejected, false);
    watch.begin(actor);
    CHECK(actor.step({Motion::walk, Turn::none}, 2).error == Error::ok);
    reject(actor, reader, contacts, watch, {}, 2, Error::animation_rejected, false,
           AnimationError::transition_busy);
    // Continue the active target before requesting another: no frozen/bypassed blend.
    while (actor.snapshot().animation.clock.mode != domain::LocomotionMode::stable) {
        watch.begin(actor);
        CHECK(actor.step({Motion::walk, Turn::none}, 2).error == Error::ok);
    }
    watch.begin(actor);
    CHECK(actor.step({}, 2).error == Error::ok);

    const auto before = bytes(actor);
    CHECK(actor.reset({1, 2, 3}, domain::inspection_movement_pi).error == Error::invalid_placement);
    CHECK(bytes(actor) == before && actor.ready());
    for (unsigned index = 0; index < 2; ++index) {
        for (bool missing : {true, false}) {
            reader.clear(); watch.begin(actor);
            if (missing) reader.missing_at = index; else reader.invalid_at = index;
            const auto result = actor.reset({200, 300, 400}, 1);
            CHECK(result.error == Error::animation_rejected);
            CHECK(result.animation == (missing ? AnimationError::sample_unavailable : AnimationError::invalid_pose));
            CHECK(bytes(actor) == before && actor.ready());
        }
    }
    reader.clear(); watch.begin(actor);
    CHECK(actor.reset({200, 300, 400}, 1).error == Error::ok);
    CHECK(actor.snapshot().animation.clock.target_id == 101 && actor.snapshot().movement.ordinal == 0);
    CHECK(!actor.snapshot().animation.cache.saved_valid);
    auto bad_profile = profile; bad_profile.id = 0;
    Reader plain_reader;
    Actor bad(bad_profile, skeleton(), plain_reader, contacts);
    CHECK(bad.reset({}, 0).animation == AnimationError::invalid_profile && !bad.ready());
    Actor bad_rig(profile, {}, plain_reader, contacts);
    CHECK(bad_rig.reset({}, 0).animation == AnimationError::invalid_profile && !bad_rig.ready());
}
void contact_failures_and_placement() {
    Watch watch;
    Reader reader; reader.watch = &watch;
    Contacts contacts; contacts.watch = &watch;
    Actor actor(profile, skeleton(), reader, contacts);
    watch.begin(actor);
    CHECK(actor.reset({100, -7, 200}, domain::inspection_movement_pi / 2).error == Error::ok);
    for (const auto &pair : {std::pair{ContactMode::unavailable, Error::contacts_unavailable},
                           std::pair{ContactMode::unsupported, Error::contacts_unsupported},
                           std::pair{ContactMode::unknown, Error::invalid_contact},
                           std::pair{ContactMode::unwritten, Error::invalid_contact},
                           std::pair{ContactMode::partial, Error::invalid_contact}}) {
        contacts.mode = pair.first;
        reject(actor, reader, contacts, watch, {Motion::walk, Turn::none}, 2, pair.second, true);
        CHECK(reader.calls == 0);
    }
    contacts.mode = ContactMode::fixed;
    for (auto member : {&domain::Vec3::x, &domain::Vec3::y, &domain::Vec3::z}) {
        for (float value : {nan, inf, -inf, 1000001.F, -1000001.F}) {
            contacts.fixed = {}; contacts.fixed.*member = value;
            reject(actor, reader, contacts, watch, {Motion::walk, Turn::none}, 2, Error::invalid_contact, true);
            CHECK(reader.calls == 0);
        }
    }
    contacts.mode = ContactMode::correct; watch.begin(actor);
    CHECK(actor.step({Motion::walk, Turn::none}, 2).error == Error::ok);
    const auto &s = actor.snapshot();
    same(contacts.last.from, {100, -7, 200});
    near(contacts.last.requested.x, 128); near(contacts.last.requested.z, 200);
    CHECK(contacts.last.requested.y == -7 && contacts.last.ordinal == 1);
    same(s.movement.position, {131, -3, 195});
    // Local root is nonzero; it has NOT been offset by accepted world coordinates.
    const auto &root = s.animation.model[0];
    CHECK(root[12] > 8 && root[12] < 16 && root[13] == 2 && root[14] == -4);
    const auto &m = s.instance;
    near(m[0] * root[12] + m[8] * root[14] + m[12], 131 - 4);
    near(m[5] * root[13] + m[13], -3 + 2);
    near(m[2] * root[12] + m[10] * root[14] + m[14], 195 - double(root[12]));
    CHECK(m[12] == s.movement.position.x && m[13] == s.movement.position.y &&
          m[14] == s.movement.position.z);
    const auto previous = s.movement.position;
    const auto beta = s.animation.clock.blend;
    contacts.mode = ContactMode::block; watch.begin(actor);
    CHECK(actor.step({Motion::walk, Turn::left}, 2).error == Error::ok);
    same(actor.snapshot().movement.position, previous);
    CHECK(actor.snapshot().movement.ordinal == 2 && actor.snapshot().animation.clock.blend > beta);
    near(actor.snapshot().movement.yaw, domain::inspection_movement_pi / 2 - .088);

    contacts.mode = ContactMode::fixed; contacts.fixed = {};
    watch.begin(actor);
    CHECK(actor.step({Motion::walk, Turn::none}, 2).error == Error::ok);
    same(actor.snapshot().movement.position, {}); // A fully written zero is a valid result.
    CHECK(actor.snapshot().instance[12] == 0 && actor.snapshot().instance[13] == 0 &&
          actor.snapshot().instance[14] == 0);
    contacts.mode = ContactMode::fixed; contacts.fixed = {1000000, -0.F, 1000000};
    watch.begin(actor);
    CHECK(actor.step({Motion::walk, Turn::none}, 2).error == Error::ok);
    CHECK(std::signbit(actor.snapshot().movement.position.y) && std::signbit(actor.snapshot().instance[13]));
    reject(actor, reader, contacts, watch, {Motion::walk, Turn::none}, 2,
           Error::movement_rejected, false);
}
void checked_step(Actor &actor, Reader &reader, Contacts &contacts, Watch &watch, Motion motion) {
    // Independent integration reference: existing HL on its own, and analytic world position.
    auto expected = actor.snapshot().animation;
    domain::LocomotionWorkspace work;
    Reader clean;
    CHECK(domain::update_locomotion(profile, clean, clip(motion), 2, expected, work) == AnimationError::ok);
    const unsigned reads = clean.calls;
    const auto old = actor.snapshot().movement;
    for (unsigned index = 0; index < reads; ++index) {
        for (bool missing : {true, false}) {
            reader.clear();
            if (missing) reader.missing_at = index; else reader.invalid_at = index;
            reject(actor, reader, contacts, watch, {motion, Turn::none}, 2,
                   Error::animation_rejected, true,
                   missing ? AnimationError::sample_unavailable : AnimationError::invalid_pose);
        }
    }
    reader.clear(); watch.begin(actor);
    CHECK(actor.step({motion, Turn::none}, 2).error == Error::ok);
    CHECK(reader.calls == reads);
    same_animation(actor.snapshot().animation, expected);
    const float distance = motion == Motion::idle ? 0 : motion == Motion::walk ? 28 : 70;
    same(actor.snapshot().movement.position, {old.position.x + 3, old.position.y + 4,
                                             old.position.z + distance - 5});
    CHECK(actor.snapshot().movement.ordinal == old.ordinal + 1);
    ++updates;
}
void all_edges_and_capacity() {
    Watch watch;
    Reader reader; reader.watch = &watch;
    Contacts contacts; contacts.watch = &watch;
    Actor actor(profile, skeleton(), reader, contacts);
    watch.begin(actor);
    CHECK(actor.reset({10, 20, 30}, 0).error == Error::ok);
    checked_step(actor, reader, contacts, watch, Motion::idle);
    for (auto motion : {Motion::walk, Motion::run, Motion::walk, Motion::idle,
                        Motion::walk, Motion::run, Motion::idle}) {
        checked_step(actor, reader, contacts, watch, motion);
        while (actor.snapshot().animation.clock.mode != domain::LocomotionMode::stable)
            checked_step(actor, reader, contacts, watch, motion);
        for (unsigned i = 0; i < 70; ++i)
            checked_step(actor, reader, contacts, watch, motion); // Includes complete clip wraps.
    }
    Reader large_reader;
    Contacts large_contacts;
    Actor large(profile, skeleton(73), large_reader, large_contacts);
    CHECK(large.reset({}, 0).error == Error::ok);
    CHECK(large.step({Motion::walk, Turn::right}, 2).error == Error::ok);
    CHECK(large.snapshot().animation.skeleton.bone_count == 73);
    CHECK(large.snapshot().animation.cache.last_valid && large.snapshot().animation.model[72][15] == 1);
    const auto before = bytes(large);
    large_reader.calls = 0; large_reader.missing_at = 72;
    CHECK(large.reset({10, 0, 0}, 0).animation == AnimationError::sample_unavailable);
    CHECK(bytes(large) == before);
}
} // namespace

int main() {
    forbid_allocation = true;
    initial_and_preflight();
    contact_failures_and_placement();
    all_edges_and_capacity();
    forbid_allocation = false;
    std::printf("InspectionActor: %zu bytes; %u rejections; %u retried updates; %u observed callbacks\n",
                sizeof(Actor), failures, updates, callbacks);
}
