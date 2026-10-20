#include "sh3_observer/physical_writes.hpp"
#include "sh3_observer/capture.hpp"
#include "sh3_observer/host_epoch.hpp"
#include "sh3_observer/runtime_revocation.hpp"
#include <limits>
#include <mutex>

namespace sh3::observer {
namespace {
std::mutex binding_mutex;
PhysicalWrites* binding{};
HostEpoch epoch;
constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
}
LifetimeNotice PhysicalWrites::notice(std::uint64_t cycle, LifetimeKind kind) const noexcept {
  auto stamp = guard_.report().last;
  // Saturation deliberately produces a duplicate; LG rejects exhausted sequences.
  if (stamp.serial != maximum) ++stamp.serial;
  stamp.cycle = cycle;
  return {stamp, kind, 0, 0};
}
bool PhysicalWrites::write(std::uint64_t address, std::uint64_t size,
                           std::uint64_t cycle) noexcept {
  auto event = notice(cycle, LifetimeKind::write);
  if (ram_base_ < page_size || ram_base_ % page_size != 0 || ram_base_ > maximum - ram_size ||
      size == 0 || address > maximum - size) return guard_.notify(event);
  const auto end = address + size;
  const auto ram_end = ram_base_ + ram_size;
  if (end <= ram_base_ || address >= ram_end) return true;
  if (address < ram_base_ || end > ram_end) return guard_.notify(event);
  event.offset = static_cast<std::uint32_t>(address - ram_base_);
  event.size = static_cast<std::uint32_t>(size);
  return guard_.notify(event);
}
bool PhysicalWrites::unknown(std::uint64_t cycle) noexcept {
  return guard_.notify(notice(cycle, LifetimeKind::lost));
}
bool PhysicalWrites::lifecycle(LifetimeKind kind, std::uint64_t cycle) noexcept {
  switch (kind) {
    case LifetimeKind::reset: case LifetimeKind::restore: case LifetimeKind::remap:
    case LifetimeKind::settings: case LifetimeKind::shutdown: case LifetimeKind::lost:
      return guard_.notify(notice(cycle, kind));
    default: return unknown(cycle);
  }
}
WriteBinding::WriteBinding(PhysicalWrites& target) noexcept {
  const std::lock_guard<std::mutex> lock(binding_mutex);
  if (!binding) { binding = &target; connected_ = true; }
}
WriteBinding::~WriteBinding() {
  const std::lock_guard<std::mutex> lock(binding_mutex);
  if (connected_) binding = nullptr;
}
void before_host_write(std::uint64_t address, std::uint64_t size, std::uint64_t cycle) noexcept {
  const std::lock_guard<std::mutex> lock(binding_mutex);
  if (binding) binding->write(address, size, cycle);
}
void before_untracked_write(std::uint64_t cycle) noexcept {
  const std::lock_guard<std::mutex> lock(binding_mutex);
  if (binding) binding->unknown(cycle);
}
std::uint64_t host_epoch() noexcept { return epoch.current(); }
void before_lifecycle(LifetimeKind kind, std::uint64_t cycle) noexcept {
  runtime_revocation().advance(); // Before the legacy serialized guard or any effect.
  const std::lock_guard<std::mutex> lock(binding_mutex);
  epoch.advance();
  if (binding) binding->lifecycle(kind, cycle);
}
} // namespace sh3::observer
