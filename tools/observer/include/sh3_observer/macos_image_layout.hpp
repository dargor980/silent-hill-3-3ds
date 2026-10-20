#pragma once
#include "sh3_observer/image_layout.hpp"
#include <mach/mach_vm.h>

namespace sh3::observer {
struct MacOSImageReadCalls {
  int (*pid)();
  decltype(&::mach_vm_read_overwrite) copy;
};
class MacOSImageBytes final : public ByteSource {
public:
  explicit MacOSImageBytes(std::uintptr_t) noexcept;
  MacOSImageBytes(std::uintptr_t, MacOSImageReadCalls) noexcept;
  bool read_at(std::uint64_t, void*, std::size_t, std::size_t&) noexcept override;
private:
  const std::uintptr_t address_;
  const MacOSImageReadCalls calls_;
  const int owner_;
};
} // namespace sh3::observer
