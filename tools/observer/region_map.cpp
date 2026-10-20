#include "sh3_observer/region_map.hpp"
#include <limits>
#include <new>
#include <utility>

namespace sh3::observer {
bool same_region(const VmRegion& a, const VmRegion& b) noexcept {
  return a.address == b.address && a.size == b.size && a.offset == b.offset && a.object == b.object &&
    a.depth == b.depth && a.protection == b.protection && a.maximum_protection == b.maximum_protection &&
    a.inheritance == b.inheritance && a.tag == b.tag && a.flags == b.flags &&
    a.shadow_depth == b.shadow_depth && a.share_mode == b.share_mode && a.external == b.external && a.submap == b.submap &&
    a.flags_available == b.flags_available;
}
namespace {
RegionFailure acquire(RegionSource& source, RegionMap& map) {
  // Touch all output storage before querying: the observation must not grow it.
  map.regions.resize(region_capacity);
  std::size_t expected = 0;
  const auto maximum = std::numeric_limits<std::uint64_t>::max();
  for (unsigned pass = 0; pass < 2; ++pass) {
    std::uint64_t cursor = 0, bytes = 0;
    std::size_t count = 0;
    for (;;) {
      VmRegion r{};
      const auto status = source.query(cursor, r);
      if (status == RegionQuery::end) break;
      if (status != RegionQuery::found) return RegionFailure::unavailable;
      if (count == region_capacity || r.depth > region_depth_limit || r.submap) return RegionFailure::capacity;
      if (r.size == 0 || r.address < cursor || r.size > maximum - r.address ||
          r.size > maximum - r.offset || r.protection > 15 || r.maximum_protection > 15 ||
          (r.protection & ~r.maximum_protection) != 0 || r.size > maximum - bytes) return RegionFailure::invalid;
      if (pass == 0) map.regions[count] = r;
      else if (count >= expected || !same_region(map.regions[count], r)) return RegionFailure::changed;
      ++count; bytes += r.size; cursor = r.address + r.size;
    }
    if (pass == 0) { expected = count; map.bytes = bytes; }
    else if (count != expected) return RegionFailure::changed;
  }
  map.regions.resize(expected);
  return RegionFailure::none;
}
}
RegionFailure read_region_map(RegionSource& source, RegionMap& output) noexcept {
  try {
    RegionMap result;
    const auto failure = acquire(source, result);
    output = failure == RegionFailure::none ? std::move(result) : RegionMap{};
    return failure;
  } catch (const std::bad_alloc&) {
    output = {};
    return RegionFailure::unavailable;
  }
}
} // namespace sh3::observer
