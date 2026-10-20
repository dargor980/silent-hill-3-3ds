#pragma once
#include "sh3_observer/macho_slice.hpp"
#include "sh3_observer/macos_region_vnode.hpp"
#include <string>

namespace sh3::observer {
struct MacOSSliceCalls { int (*pid)(); bool (*path)(std::uintptr_t, std::string&); };
class MacOSSliceMappings final : public SliceBindingSource {
public:
  MacOSSliceMappings() noexcept;
  explicit MacOSSliceMappings(MacOSSliceCalls) noexcept;
  bool read(std::uintptr_t, SliceBinding&) noexcept override;
  SliceFailure failure() const noexcept { return failure_; }
private:
  bool fail(SliceFailure) noexcept;
  const MacOSSliceCalls calls_;
  const int owner_;
  MacOSRegionVnodeSource vnodes_;
  SliceFailure failure_{SliceFailure::none};
};
} // namespace sh3::observer
