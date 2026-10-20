#include "sh3_observer/macos_slice_binding.hpp"
#include "sh3_observer/macos_page_binding.hpp"
#include "sh3_observer/macos_image_layout.hpp"
#include <cstring>
#include <dlfcn.h>
#include <unistd.h>

namespace sh3::observer {
namespace {
bool path(std::uintptr_t address, std::string& out) {
  out.clear(); Dl_info info{};
  if (!dladdr(reinterpret_cast<void*>(address),&info) || reinterpret_cast<std::uintptr_t>(info.dli_fbase) != address ||
      !info.dli_fname || info.dli_fname[0] != '/') return false;
  const auto size = strnlen(info.dli_fname,4097);
  if (size > 4096) return false;
  out.assign(info.dli_fname,size); return true;
}
bool same_region(const RegionVnode& a, const RegionVnode& b) noexcept {
  return a.address == b.address && a.size == b.size && a.region_offset == b.region_offset && same_file(a.file,b.file);
}
}
MacOSSliceMappings::MacOSSliceMappings() noexcept : MacOSSliceMappings({::getpid,path}) {}
MacOSSliceMappings::MacOSSliceMappings(MacOSSliceCalls calls) noexcept
  : calls_(calls), owner_(calls.pid ? calls.pid() : 0) {
  if (!calls_.pid || !calls_.path || owner_ <= 0) failure_ = SliceFailure::unavailable;
}
bool MacOSSliceMappings::fail(SliceFailure why) noexcept {
  if (failure_ == SliceFailure::none) failure_ = why;
  return false;
}
bool MacOSSliceMappings::read(std::uintptr_t address, SliceBinding& out) noexcept {
  out = {};
  if (failure_ != SliceFailure::none) return false;
  if (!address || calls_.pid() != owner_) return fail(SliceFailure::unavailable);
  RegionVnode first{},last{};
  if (vnodes_.query(address,first) != VnodeQuery::found || first.address != address) return fail(SliceFailure::invalid);
  std::string name;
  if (!calls_.path(address,name)) return fail(SliceFailure::unavailable);
  MacOSPageAnchor file(name); MacOSImageBytes resident(address); SliceBinding binding{};
  const auto result=bind_macho_slice({first.address,first.size,first.region_offset,first.file},file,file,resident,binding);
  if (!file.close()) return fail(SliceFailure::unavailable);
  if (result != SliceFailure::none) return fail(result);
  if (vnodes_.query(address,last) != VnodeQuery::found || !same_region(first,last) || calls_.pid() != owner_) return fail(SliceFailure::changed);
  out = binding; return true;
}
} // namespace sh3::observer
