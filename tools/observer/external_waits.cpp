#include "sh3_observer/external_waits.hpp"

namespace sh3::observer {
bool ExternalWaits::acquire() noexcept {
  auto old = active_.load(std::memory_order_acquire);
  // A bounded attempt cannot delay the foreign caller indefinitely. If capacity
  // or contention prevents accounting, fail closed for this observer lifetime.
  for (unsigned retry = 0; retry < 32; ++retry) {
    if (old >= capacity_) break;
    if (active_.compare_exchange_strong(old, old + 1, std::memory_order_acq_rel,
                                      std::memory_order_acquire)) return true;
  }
  poisoned_.store(true, std::memory_order_release);
  return false;
}
ExternalWaits::Wait::Wait(ExternalWaits& owner, bool needed) noexcept
    : owner_(owner), tracked_(needed && owner_.acquire()) {}
ExternalWaits::Wait::~Wait() {
  if (tracked_) owner_.active_.fetch_sub(1, std::memory_order_acq_rel);
}
bool ExternalWaits::pending() const noexcept {
  return poisoned_.load(std::memory_order_acquire) ||
         active_.load(std::memory_order_acquire) != 0;
}
} // namespace sh3::observer
