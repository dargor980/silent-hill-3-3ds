#pragma once
#include "sh3/platform/inspection_locomotion.hpp"
#include "sh3/platform/room_movement_contacts.hpp"
#include "sh3/platform/room_scene.hpp"
#include "sh3/ports/rig_scene.hpp"
#include <memory>

namespace sh3::platform {
struct RoomAssets {
    domain::RoomMap map{};
    domain::InspectionLocomotion rig{};
    RoomMovementContacts contacts{};
    domain::Vec3 spawn{};
    float yaw{};
};
// Extra reserve covers simultaneous replacement RoomAssets plus path/CRC/loader stack.
inline constexpr std::size_t room_runtime_extra = 2 * 1024 * 1024;
static_assert(sizeof(RoomAssets) + 65536 <= room_runtime_extra);
[[nodiscard]] LocomotionLoadResult read_room_runtime(const char *directory,
                                                     std::unique_ptr<RoomAssets> &out,
                                                     StdioApi = system_stdio) noexcept;
class RoomTextures final : public ports::IRigTextures {
  public:
    explicit RoomTextures(const char *directory, StdioApi api = system_stdio) noexcept
        : directory_(directory), api_(api) {}
    // Slot 13 denotes normalized glass; the rig's slots remain untouched.
    bool read(const domain::RigMaterial &, std::uint8_t *, std::size_t) noexcept override;

  private:
    const char *directory_;
    StdioApi api_;
};
} // namespace sh3::platform
