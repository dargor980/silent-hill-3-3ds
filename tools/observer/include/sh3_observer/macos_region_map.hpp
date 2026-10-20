#pragma once
#include "sh3_observer/region_map.hpp"
#include <mach/mach.h>
#include <mach/mach_vm.h>

namespace sh3::observer {
struct MacOSRegionCalls { int (*pid)(); decltype(&::mach_vm_region_recurse) region; };
class MacOSRegionSource final : public RegionSource {
public:
  MacOSRegionSource() noexcept;
  explicit MacOSRegionSource(MacOSRegionCalls) noexcept;
  RegionQuery query(std::uint64_t, VmRegion&) noexcept override;
private:
  MacOSRegionCalls calls_;
  int owner_;
};
} // namespace sh3::observer
