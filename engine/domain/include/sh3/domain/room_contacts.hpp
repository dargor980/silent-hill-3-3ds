#pragma once
#include "sh3/domain/render_scene.hpp"
#include <array>
#include <cstddef>
#include <cstdint>

namespace sh3::domain {
inline constexpr std::size_t room_contact_capacity = 32;
inline constexpr std::size_t room_contact_budget = 4096;
// Include adapter/padding and all simultaneous helper frames, respectively.
// Verified for the supported host/ARM builds; no heap or persistent scratch.
inline constexpr std::size_t room_contact_resident_bound = 576;
inline constexpr std::size_t room_contact_stack_bound = 2560;
struct RoomContactMemory {
    std::size_t resident_bytes{room_contact_resident_bound};
    std::size_t scratch_bytes{room_contact_stack_bound};
};
enum class RoomContactProfile { static_xz_aabb_stop_v1 = 1 };
enum class RoomContactError {
    ok, unsupported_profile, capacity_exceeded, budget_exceeded, invalid_geometry,
    empty_floor, unavailable, invalid_query, out_of_bounds, off_floor, invalid_start
};
struct RoomContactBox { float xmin{}, xmax{}, zmin{}, zmax{}; };
struct RoomContactInput {
    RoomContactProfile profile{RoomContactProfile::static_xz_aabb_stop_v1};
    float half_extent{175}, guard{1};
    Vec3 origin{}; // Provenance only: boxes and query positions are already world coordinates.
    float floor_y{};
    RoomContactBox floor{};
    const RoomContactBox *blockers{};
    std::size_t blocker_count{};
};

// Owns a validated immutable geometry snapshot. Single-threaded publication.
class RoomContactScene final {
  public:
    // Input arrays live only through this call. Failure preserves every object byte.
    // Accounting may raise the measured reservations, never lower the built-in bounds.
    [[nodiscard]] RoomContactError prepare(const RoomContactInput &,
                                          RoomContactMemory = {}) noexcept;
    // Pure query. On error every output byte remains untouched. Both aliases are safe.
    [[nodiscard]] RoomContactError resolve(Vec3 from, Vec3 requested, Vec3 &accepted) const noexcept;
    bool ready() const noexcept { return ready_; }

  private:
    std::array<RoomContactBox, room_contact_capacity> boxes_{};
    RoomContactBox floor_{};
    Vec3 origin_{};
    float floor_y_{};
    std::uint32_t count_{};
    bool ready_{};
};
static_assert(sizeof(RoomContactScene) <= room_contact_resident_bound);
static_assert(room_contact_resident_bound + room_contact_stack_bound <= room_contact_budget);
} // namespace sh3::domain
