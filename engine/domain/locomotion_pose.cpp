#include "sh3/domain/locomotion_pose.hpp"
#include <cmath>

namespace sh3::domain {
namespace {
using Error = LocomotionError;
using Evaluation = LocomotionEvaluation;
using CacheAction = LocomotionCacheAction;
bool bounded(float value, float limit) noexcept {
    return std::isfinite(value) && std::abs(value) <= limit;
}
bool valid_transform(const LocomotionTransform &value) noexcept {
    const auto &t = value.translation;
    if (!bounded(t.x, 100000) || !bounded(t.y, 100000) || !bounded(t.z, 100000))
        return false;
    float norm = 0;
    for (const auto v : value.rotation) {
        if (!bounded(v, 1.001F))
            return false;
        norm += v * v;
    }
    return std::abs(norm - 1) <= 0.001F;
}
bool mix(const LocomotionTransform &a, const LocomotionTransform &b, std::uint32_t q12,
         LocomotionTransform &out) noexcept {
    const auto f = float(q12) / 4096;
    float dot = 0, norm = 0;
    for (std::size_t i = 0; i < 4; ++i)
        dot += a.rotation[i] * b.rotation[i];
    for (std::size_t i = 0; i < 4; ++i) {
        out.rotation[i] = a.rotation[i] * (1 - f) +
                          (dot < 0 ? -b.rotation[i] : b.rotation[i]) * f;
        norm += out.rotation[i] * out.rotation[i];
    }
    if (!std::isfinite(norm) || norm <= 0)
        return false;
    const auto length = std::sqrt(norm);
    for (auto &v : out.rotation)
        v /= length;
    out.translation = {a.translation.x * (1 - f) + b.translation.x * f,
                       a.translation.y * (1 - f) + b.translation.y * f,
                       a.translation.z * (1 - f) + b.translation.z * f};
    return valid_transform(out);
}
Error read(const LocomotionSampleReader &reader, std::uint32_t clip, std::uint32_t frame,
           std::uint32_t bone, LocomotionTransform &out) noexcept {
    if (!reader.read(clip, frame, bone, out))
        return Error::sample_unavailable;
    return valid_transform(out) ? Error::ok : Error::invalid_pose;
}
const LocomotionClip *find_clip(const LocomotionProfile &profile, std::uint32_t id) noexcept {
    for (const auto &clip : profile.active_clips())
        if (clip.id == id)
            return &clip;
    return nullptr;
}
bool valid_window(const LocomotionProfile &profile, const LocomotionSamples &s,
                  std::uint32_t id, std::uint32_t phase) noexcept {
    const auto *clip = find_clip(profile, id);
    if (!clip || s.clip_id != id || phase >= clip->count * 4096)
        return false;
    const auto frame = phase / 4096, following = (frame + 1) % clip->count;
    return s.frame == frame && s.following == following &&
           s.source_frame == clip->start + frame && s.source_following == clip->start + following &&
           s.packed_frame == clip->packed_first + frame &&
           s.packed_following == clip->packed_first + following;
}
bool valid_plan(const LocomotionPlan &p, const LocomotionPoseCache &current) noexcept {
    // Reuse scalar invariant validation; do not duplicate the transition state machine.
    LocomotionPlan unused;
    const auto *profile = locomotion_profile(p.next.profile_id);
    if (!profile || plan_locomotion_update(*profile, p.next, {}, 2, unused) != Error::ok ||
        !valid_window(*profile, p.target, p.next.target_id, p.pose_phase) ||
        p.fraction_q12 != p.pose_phase % 4096 || p.blend_q12 != p.next.blend)
        return false;
    switch (p.evaluation) {
    case Evaluation::clip:
        return p.next.mode == LocomotionMode::stable &&
               (current.saved_valid ? p.cache == CacheAction::discard
                                    : p.cache == CacheAction::none);
    case Evaluation::phase_blend:
        return p.next.mode == LocomotionMode::phase_blend && !current.saved_valid &&
               p.cache == CacheAction::none &&
               valid_window(*profile, p.source, p.next.source_id, p.pose_phase);
    case Evaluation::cached_blend:
        return p.next.mode == LocomotionMode::cached && p.pose_phase == 0 &&
               (current.saved_valid ? p.cache == CacheAction::none
                                    : p.cache == CacheAction::capture_last);
    }
    return false;
}
Error evaluate_bone(const LocomotionSampleReader &reader, const LocomotionPlan &plan,
                    std::uint32_t bone, const LocomotionPoseCache &next, bool cache_valid,
                    LocomotionTransform &out) noexcept {
    // Inspect all required reads even if one transform is invalid: unavailable data has
    // precedence over invalid_pose. Never interpolate a rejected transform or cache.
    const std::array<std::array<std::uint32_t, 2>, 4> addresses{{
        {{plan.target.clip_id, plan.target.frame}},
        {{plan.target.clip_id, plan.target.following}},
        {{plan.source.clip_id, plan.source.frame}},
        {{plan.source.clip_id, plan.source.following}}}};
    std::array<LocomotionTransform, 4> samples{};
    const unsigned count = plan.evaluation == Evaluation::cached_blend ? 1U :
                           plan.evaluation == Evaluation::phase_blend ? 4U : 2U;
    bool valid = cache_valid;
    for (unsigned i = 0; i < count; ++i) {
        const auto error = read(reader, addresses[i][0], addresses[i][1], bone, samples[i]);
        if (error == Error::sample_unavailable)
            return error;
        valid = valid && error == Error::ok;
    }
    if (!valid)
        return Error::invalid_pose;
    if (plan.evaluation == Evaluation::cached_blend)
        return mix(next.saved_local[bone], samples[0], plan.blend_q12, out) ? Error::ok
                                                                         : Error::invalid_pose;
    if (plan.evaluation == Evaluation::phase_blend) {
        LocomotionTransform first_mix, following_mix;
        if (!mix(samples[2], samples[0], plan.blend_q12, first_mix) ||
            !mix(samples[3], samples[1], plan.blend_q12, following_mix))
            return Error::invalid_pose;
        return mix(first_mix, following_mix, plan.fraction_q12, out) ? Error::ok
                                                                  : Error::invalid_pose;
    }
    return mix(samples[0], samples[1], plan.fraction_q12, out) ? Error::ok : Error::invalid_pose;
}
PoseMatrix local_matrix(const LocomotionTransform &v) noexcept {
    const auto x = v.rotation[0], y = v.rotation[1], z = v.rotation[2], w = v.rotation[3];
    return {1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
            2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
            2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
            v.translation.x, v.translation.y, v.translation.z, 1};
}
PoseMatrix product(const PoseMatrix &a, const PoseMatrix &b) noexcept {
    PoseMatrix out{};
    for (std::size_t c = 0; c < 4; ++c)
        for (std::size_t r = 0; r < 4; ++r)
            for (std::size_t k = 0; k < 4; ++k)
                out[4 * c + r] += a[4 * k + r] * b[4 * c + k];
    return out;
}
Error compose(const LocomotionSkeleton &rig, LocomotionPoseScratch &scratch) noexcept {
    // Both local channels are complete. A child in channel 2 may have a parent in channel 1.
    for (std::size_t bone = 0; bone < rig.bone_count; ++bone) {
        auto matrix = local_matrix(scratch.next.last_local[bone]);
        if (rig.parents[bone] >= 0)
            matrix = product(scratch.model[rig.parents[bone]], matrix);
        for (const auto value : matrix)
            if (!std::isfinite(value))
                return Error::invalid_pose;
        scratch.model[bone] = matrix;
    }
    return Error::ok;
}
} // namespace
bool valid_locomotion_skeleton(const LocomotionSkeleton &rig) noexcept {
    if (!rig.bone_count || rig.bone_count > locomotion_bones)
        return false;
    for (std::size_t i = 0; i < rig.bone_count; ++i)
        if (rig.parents[i] < -1 || rig.parents[i] >= static_cast<int>(i) ||
            (rig.channels[i] != 1 && rig.channels[i] != 2))
            return false;
    return true;
}
Error stage_locomotion_pose(const LocomotionSkeleton &rig, const LocomotionSampleReader &reader,
                            const LocomotionPlan &plan, const LocomotionPoseCache &current,
                            LocomotionPoseScratch &scratch) noexcept {
    if (!valid_locomotion_skeleton(rig))
        return Error::invalid_profile;
    if (&current == &scratch.next || !current.last_valid || current.bone_count != rig.bone_count ||
        !valid_plan(plan, current))
        return Error::invalid_state;
    bool cache_valid = true;
    for (std::size_t i = 0; i < rig.bone_count; ++i)
        if (!valid_transform(current.last_local[i]) ||
            (current.saved_valid && !valid_transform(current.saved_local[i])))
            cache_valid = false;
    scratch.next = current;
    if (plan.cache == CacheAction::capture_last) {
        scratch.next.saved_local = current.last_local;
        scratch.next.saved_valid = true;
    } else if (plan.cache == CacheAction::discard) {
        scratch.next.saved_valid = false;
    }
    auto pose_error = Error::ok;
    for (const auto channel : {2, 1})
        for (std::uint32_t bone = 0; bone < rig.bone_count; ++bone) {
            if (rig.channels[bone] != channel)
                continue;
            const auto error = evaluate_bone(reader, plan, bone, scratch.next, cache_valid,
                                             scratch.next.last_local[bone]);
            if (error == Error::sample_unavailable)
                return error;
            if (error != Error::ok)
                pose_error = error;
        }
    return pose_error == Error::ok ? compose(rig, scratch) : pose_error;
}
Error initialize_locomotion_pose(const LocomotionSkeleton &rig, const LocomotionSampleReader &reader,
                                LocomotionPoseScratch &scratch, std::uint32_t initial_clip,
                                const LocomotionProfile &profile) noexcept {
    if (!valid_locomotion_profile(profile) || !valid_locomotion_skeleton(rig))
        return Error::invalid_profile;
    if (!find_clip(profile, initial_clip))
        return Error::unknown_clip;
    scratch.next.bone_count = rig.bone_count;
    scratch.next.last_valid = false;
    scratch.next.saved_valid = false;
    scratch.next.last_local.fill({});
    scratch.next.saved_local.fill({});
    scratch.model.fill({});
    auto pose_error = Error::ok;
    for (const auto channel : {2, 1})
        for (std::uint32_t bone = 0; bone < rig.bone_count; ++bone) {
            if (rig.channels[bone] != channel)
                continue;
            LocomotionTransform first;
            const auto error = read(reader, initial_clip, 0, bone, first);
            if (error == Error::sample_unavailable)
                return error;
            if (error != Error::ok || !mix(first, first, 0, scratch.next.last_local[bone]))
                pose_error = Error::invalid_pose;
        }
    if (pose_error != Error::ok)
        return pose_error;
    const auto error = compose(rig, scratch);
    scratch.next.last_valid = error == Error::ok;
    return error;
}
} // namespace sh3::domain
