#include "sh3_observer/macos_region_map.hpp"
#include <unistd.h>

namespace sh3::observer {
MacOSRegionSource::MacOSRegionSource() noexcept : MacOSRegionSource({::getpid, ::mach_vm_region_recurse}) {}
MacOSRegionSource::MacOSRegionSource(MacOSRegionCalls calls) noexcept
  : calls_(calls), owner_(calls.pid ? calls.pid() : 0) {}
RegionQuery MacOSRegionSource::query(std::uint64_t cursor, VmRegion& output) noexcept {
  output = {};
  if (!calls_.pid || !calls_.region || owner_ <= 0 || calls_.pid() != owner_) return RegionQuery::unavailable;
  mach_vm_address_t address = cursor;
  mach_vm_size_t size{};
  natural_t depth = region_depth_limit;
  vm_region_submap_info_data_64_t info{};
  mach_msg_type_number_t count = VM_REGION_SUBMAP_INFO_V2_COUNT_64;
  const auto status = calls_.region(mach_task_self(), &address, &size, &depth,
      reinterpret_cast<vm_region_recurse_info_t>(&info), &count);
  if (calls_.pid() != owner_) return RegionQuery::unavailable;
  if (status == KERN_INVALID_ADDRESS) return RegionQuery::end;
  if (status != KERN_SUCCESS || count != VM_REGION_SUBMAP_INFO_V2_COUNT_64 ||
      (info.is_submap != 0 && info.is_submap != 1) || info.external_pager > 1) return RegionQuery::unavailable;
  output = {address, size, info.offset, info.object_id_full, depth,
    static_cast<std::uint32_t>(info.protection), static_cast<std::uint32_t>(info.max_protection),
    static_cast<std::uint32_t>(info.inheritance), info.user_tag, 0, info.shadow_depth,
    info.share_mode, info.external_pager != 0, info.is_submap != 0};
#ifdef VM_REGION_FLAG_JIT_ENABLED
  output.flags = info.flags;
  output.flags_available = true;
#endif
  return RegionQuery::found;
}
} // namespace sh3::observer
