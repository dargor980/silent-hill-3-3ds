#pragma once
#include <array>
#include <cstdint>
#include <optional>

namespace sh3::domain {
struct LocomotionClip {
    std::uint32_t id{}, count{};
    std::int32_t speed{}; // PAL speed already converted; increment = speed * ticks.
    std::uint32_t start{}, end{}, loop{}, trailing{}, packed_first{};
};
struct LocomotionProfile {
    std::uint32_t id{}, model_resource{}, animation_resource{}, sample_count{}, ticks{};
    std::uint32_t clip_count{};
    std::array<LocomotionClip, 5> clips{};
    struct ClipsView {
        const LocomotionClip *data;
        std::size_t count;
        constexpr const LocomotionClip *begin() const noexcept { return data; }
        constexpr const LocomotionClip *end() const noexcept { return data + count; }
    };
    // C++17 bounded view. Invalid counts expose no records; validation still rejects them.
    [[nodiscard]] constexpr ClipsView active_clips() const noexcept {
        return {clips.data(), clip_count <= clips.size() ? clip_count : 0};
    }
};
// Scalar identity only: validation here does not authenticate model/animation bytes.
inline constexpr LocomotionProfile heather_locomotion_profile{
    1, 522, 525, 58, 2, 3,
    {{{101, 10, 307, 0, 9, 1, 0, 0},
      {109, 24, 1996, 80, 103, 1, 0, 10},
      {113, 24, 2227, 176, 199, 1, 0, 34}}}};
inline constexpr LocomotionProfile heather_turns_profile{
    2, 522, 525, 78, 2, 5,
    {{{101, 10, 307, 0, 9, 1, 0, 0},
      {109, 24, 1996, 80, 103, 1, 0, 10},
      {113, 24, 2227, 176, 199, 1, 0, 34},
      {107, 10, 1152, 60, 69, 1, 0, 58},
      {108, 10, 1152, 70, 79, 1, 0, 68}}}};
[[nodiscard]] constexpr const LocomotionProfile *locomotion_profile(std::uint32_t id) noexcept {
    return id == 1 ? &heather_locomotion_profile : id == 2 ? &heather_turns_profile : nullptr;
}

enum class LocomotionMode : std::uint32_t { stable = 1, cached = 3, phase_blend = 5 };
enum class LocomotionError {
    ok, invalid_profile, invalid_state, invalid_ticks, unknown_clip,
    transition_busy, unsupported_transition, sample_unavailable, invalid_pose
};
struct LocomotionClock {
    std::uint32_t profile_id{}, source_id{}, target_id{};
    LocomotionMode mode{LocomotionMode::stable};
    std::uint32_t counter{}, blend{};
    bool saved_local_valid{}; // Evaluator owns and validates the actual pose cache.
};
inline constexpr LocomotionClock initial_locomotion_clock(
    const LocomotionProfile &profile = heather_locomotion_profile) noexcept {
    return {profile.id, 101, 101, LocomotionMode::stable, 0, 0, false};
}
struct LocomotionSamples {
    std::uint32_t clip_id{}, frame{}, following{}; // Relative to this clip.
    std::uint32_t source_frame{}, source_following{}; // Original ANM indices.
    std::uint32_t packed_frame{}, packed_following{};
};
enum class LocomotionEvaluation { clip, phase_blend, cached_blend };
enum class LocomotionCacheAction { none, capture_last, discard };
struct LocomotionPlan {
    LocomotionClock next{};
    LocomotionEvaluation evaluation{LocomotionEvaluation::clip};
    LocomotionCacheAction cache{LocomotionCacheAction::none};
    std::uint32_t pose_phase{}, fraction_q12{}, blend_q12{};
    LocomotionSamples source{}, target{};
};

// Shared metadata validation for initialization and update; no pose/resource authentication.
[[nodiscard]] bool valid_locomotion_profile(const LocomotionProfile &) noexcept;
// No pose reads, mutation of input, I/O or allocation. Error leaves out unchanged.
// An empty request means continue; request 0 is an unknown clip, not a sentinel.
// Publish next only after pose staging completes both channels successfully.
[[nodiscard]] LocomotionError plan_locomotion_update(
    const LocomotionProfile &, const LocomotionClock &, std::optional<std::uint32_t> request,
    std::uint32_t ticks, LocomotionPlan &out) noexcept;
} // namespace sh3::domain
