#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>

namespace sh3::observer {
inline constexpr std::size_t region_capacity = 65536;
inline constexpr std::uint32_t region_depth_limit = 64;
struct VmRegion {
  std::uint64_t address{}, size{}, offset{}, object{};
  std::uint32_t depth{}, protection{}, maximum_protection{}, inheritance{}, tag{}, flags{};
  std::uint16_t shadow_depth{};
  std::uint8_t share_mode{};
  bool external{}, submap{}, flags_available{};
};
enum class RegionQuery { found, end, unavailable };
class RegionSource {
public:
  virtual ~RegionSource() = default;
  virtual RegionQuery query(std::uint64_t cursor, VmRegion&) noexcept = 0;
};
struct RegionMap { std::vector<VmRegion> regions; std::uint64_t bytes{}; };
enum class RegionFailure { none, invalid, capacity, unavailable, changed };
bool same_region(const VmRegion&, const VmRegion&) noexcept;
// Structural two-pass enumeration, not an atomic snapshot or page provenance.
RegionFailure read_region_map(RegionSource&, RegionMap&) noexcept;
} // namespace sh3::observer
