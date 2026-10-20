#pragma once
#include <atomic>
#include <cstdint>

namespace sh3::observer {
// Host-owned identity only. Reading it does not synchronize guest memory.
// Zero is permanent exhaustion; no reset or save-state interface exists.
class HostEpoch final {
public:
  explicit HostEpoch(std::uint64_t initial = 1) noexcept : value_(initial) {}
  HostEpoch(const HostEpoch&) = delete;
  HostEpoch& operator=(const HostEpoch&) = delete;
  std::uint64_t current() const noexcept { return value_.load(std::memory_order_relaxed); }
  std::uint64_t advance() noexcept;
private:
  std::atomic<std::uint64_t> value_;
};
} // namespace sh3::observer
