#include "sh3_observer/host_epoch.hpp"
#include <limits>

namespace sh3::observer {
std::uint64_t HostEpoch::advance() noexcept {
  auto previous = current();
  while (previous != 0) {
    const auto next = previous == std::numeric_limits<std::uint64_t>::max() ? 0 : previous + 1;
    if (value_.compare_exchange_weak(previous, next, std::memory_order_relaxed)) return next;
  }
  return 0;
}
} // namespace sh3::observer
