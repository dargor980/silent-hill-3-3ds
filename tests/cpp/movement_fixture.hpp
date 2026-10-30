#pragma once
#include "sh3/application/movement_controller.hpp"
#include <limits>

namespace movement_test {
struct Reader final : sh3::domain::LocomotionSampleReader {
    bool fail{};
    mutable unsigned calls{};
    void (*observe)(void *){};
    void *context{};
    bool read(std::uint32_t clip, std::uint32_t frame, std::uint32_t bone,
              sh3::domain::LocomotionTransform &out) const noexcept override {
        ++calls;
        if (observe) observe(context);
        if (fail) return false;
        out = {{8 + float(clip) / 16 + float(frame), float(bone) + 2, -4}, {0, 0, 0, 1}};
        return true;
    }
};
struct Contacts final : sh3::ports::IMovementContacts {
    mutable unsigned calls{};
    unsigned fail_at{std::numeric_limits<unsigned>::max()};
    void (*observe)(void *){};
    void *context{};
    sh3::ports::MovementContactStatus resolve(const sh3::ports::MovementContactQuery &q,
                                             sh3::domain::Vec3 &out) const noexcept override {
        if (observe) observe(context);
        if (calls++ == fail_at) return sh3::ports::MovementContactStatus::unavailable;
        out = q.requested; // Synthetic unobstructed space, never a production adapter.
        return sh3::ports::MovementContactStatus::accepted;
    }
};
inline sh3::domain::LocomotionSkeleton rig() {
    sh3::domain::LocomotionSkeleton result;
    result.bone_count = 2;
    result.parents[0] = -1; result.parents[1] = 0;
    result.channels[0] = 1; result.channels[1] = 2;
    return result;
}
inline constexpr auto profile = sh3::domain::heather_locomotion_profile;
inline constexpr sh3::domain::Vec3 spawn{100, -7, 200};
} // namespace movement_test
