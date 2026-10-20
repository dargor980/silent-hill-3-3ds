#include "sh3_observer/macos_image_layout.hpp"
#include <mach/mach.h>
#include <limits>
#include <unistd.h>

namespace sh3::observer {
MacOSImageBytes::MacOSImageBytes(std::uintptr_t address) noexcept
  : MacOSImageBytes(address, {::getpid, ::mach_vm_read_overwrite}) {}
MacOSImageBytes::MacOSImageBytes(std::uintptr_t address, MacOSImageReadCalls calls) noexcept
  : address_(address), calls_(calls), owner_(calls.pid ? calls.pid() : 0) {}
bool MacOSImageBytes::read_at(std::uint64_t offset, void* bytes, std::size_t wanted, std::size_t& got) noexcept {
  got = 0;
  constexpr auto maximum = std::numeric_limits<std::uintptr_t>::max();
  if (address_ == 0 || !bytes || !calls_.pid || !calls_.copy || owner_ <= 0 || calls_.pid() != owner_ ||
      wanted == 0 || wanted > digest_block_size || offset > layout_command_limit + 32 ||
      wanted > layout_command_limit + 32 - offset || offset > maximum - address_ ||
      wanted > maximum - (address_ + offset)) return false;
  mach_vm_size_t copied{};
  if (calls_.copy(mach_task_self(), address_ + offset, wanted, reinterpret_cast<mach_vm_address_t>(bytes), &copied) != KERN_SUCCESS ||
      copied != wanted || calls_.pid() != owner_) return false;
  got = wanted; return true;
}
} // namespace sh3::observer
