#include "sh3/domain/locomotion_clock.hpp"

namespace sh3::domain {
bool valid_locomotion_profile(const LocomotionProfile &p) noexcept {
    const auto &fixed = heather_locomotion_profile;
    if (p.id != fixed.id || p.model_resource != fixed.model_resource ||
        p.animation_resource != fixed.animation_resource || p.sample_count != fixed.sample_count ||
        p.ticks != fixed.ticks)
        return false;
    for (std::size_t i = 0; i < p.clips.size(); ++i) {
        const auto &a = p.clips[i], &b = fixed.clips[i];
        if (a.id != b.id || a.count != b.count || a.speed != b.speed || a.start != b.start ||
            a.end != b.end || a.loop != b.loop || a.trailing != b.trailing ||
            a.packed_first != b.packed_first)
            return false;
    }
    return true;
}
namespace {
constexpr std::uint32_t q12 = 4096;
using Mode = LocomotionMode;
using Error = LocomotionError;

const LocomotionClip *find(const LocomotionProfile &p, std::uint32_t id) noexcept {
    for (const auto &clip : p.clips)
        if (clip.id == id)
            return &clip;
    return nullptr;
}
bool moving(std::uint32_t id) noexcept { return id == 109 || id == 113; }
bool cached_edge(std::uint32_t source, std::uint32_t target) noexcept {
    return (source == 101 && target == 109) || (moving(source) && target == 101);
}
std::uint32_t first_blend(std::uint32_t target) noexcept { return target == 109 ? 768 : 1280; }
std::uint32_t blend_delta(std::uint32_t target) noexcept { return target == 109 ? 768 : 360; }
bool valid_state(const LocomotionProfile &p, const LocomotionClock &s) noexcept {
    const auto *target = find(p, s.target_id);
    if (s.profile_id != p.id || !target || !find(p, s.source_id) ||
        s.counter >= target->count * q12)
        return false;
    switch (s.mode) {
    case Mode::stable:
        return s.source_id == s.target_id && !s.blend && !s.saved_local_valid;
    case Mode::phase_blend:
        return moving(s.source_id) && moving(s.target_id) && s.source_id != s.target_id &&
               s.blend > 0 && s.blend < q12 && s.blend % 384 == 0 && !s.saved_local_valid;
    case Mode::cached:
        return cached_edge(s.source_id, s.target_id) && !s.counter && s.saved_local_valid &&
               s.blend >= first_blend(s.target_id) && s.blend < q12 &&
               (s.blend - first_blend(s.target_id)) % blend_delta(s.target_id) == 0;
    }
    return false;
}
std::uint32_t advance(std::uint32_t phase, const LocomotionClip &clip,
                      std::uint32_t ticks) noexcept {
    // All operands are bounded only after profile/state validation.
    const auto advanced = std::uint64_t(phase) + std::uint64_t(clip.speed) * ticks;
    const auto period = std::uint64_t(clip.count) * q12;
    return static_cast<std::uint32_t>(advanced % period);
}
LocomotionSamples samples(const LocomotionClip &clip, std::uint32_t phase) noexcept {
    const auto frame = phase / q12, following = (frame + 1) % clip.count;
    return {clip.id, frame, following, clip.start + frame, clip.start + following,
            clip.packed_first + frame, clip.packed_first + following};
}
} // namespace

LocomotionError plan_locomotion_update(const LocomotionProfile &profile,
                                      const LocomotionClock &current,
                                      std::optional<std::uint32_t> request,
                                      std::uint32_t ticks, LocomotionPlan &out) noexcept {
    if (!valid_locomotion_profile(profile))
        return Error::invalid_profile;
    if (!valid_state(profile, current))
        return Error::invalid_state;
    if (ticks != profile.ticks)
        return Error::invalid_ticks;
    if (request && !find(profile, *request))
        return Error::unknown_clip;
    const bool selection = request && *request != current.target_id;
    if (selection && current.mode != Mode::stable)
        return Error::transition_busy;
    if (selection && current.target_id == 101 && *request == 113)
        return Error::unsupported_transition;

    LocomotionPlan plan{};
    auto &next = plan.next;
    next = current;
    if (selection) {
        next.source_id = current.target_id;
        next.target_id = *request;
        if (moving(next.source_id) && moving(next.target_id))
            next.mode = Mode::phase_blend;
        else {
            next.mode = Mode::cached;
            next.counter = 0;
            next.saved_local_valid = true;
            plan.cache = LocomotionCacheAction::capture_last;
        }
    }
    const auto &target = *find(profile, next.target_id);
    plan.pose_phase = next.counter;
    if (next.mode == Mode::cached) {
        const auto beta = selection ? std::uint64_t(first_blend(next.target_id))
                                    : std::uint64_t(next.blend) + blend_delta(next.target_id);
        if (beta < q12) {
            next.blend = static_cast<std::uint32_t>(beta);
            plan.evaluation = LocomotionEvaluation::cached_blend;
            plan.blend_q12 = next.blend;
        } else {
            next.mode = Mode::stable;
            next.source_id = next.target_id;
            next.blend = 0;
            next.saved_local_valid = false;
            next.counter = advance(0, target, ticks);
            plan.cache = LocomotionCacheAction::discard;
        }
    } else {
        if (next.mode == Mode::phase_blend) {
            const auto beta = std::uint64_t(next.blend) + 384;
            if (beta < q12) {
                next.blend = static_cast<std::uint32_t>(beta);
                plan.evaluation = LocomotionEvaluation::phase_blend;
                plan.blend_q12 = next.blend;
                plan.source = samples(*find(profile, next.source_id), plan.pose_phase);
            } else {
                next.mode = Mode::stable;
                next.source_id = next.target_id;
                next.blend = 0;
                // Observed recursive exit: advance once BEFORE the stable evaluation.
                plan.pose_phase = advance(next.counter, target, ticks);
            }
        }
        next.counter = advance(plan.pose_phase, target, ticks);
    }
    plan.target = samples(target, plan.pose_phase);
    plan.fraction_q12 = plan.pose_phase % q12;
    out = plan;
    return Error::ok;
}
} // namespace sh3::domain
