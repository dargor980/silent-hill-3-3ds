#pragma once
#include <atomic>
#include <cstdint>

namespace sh3::observer {
// Invalidation only, never a memory barrier proving writer exclusion.
// Zero is permanent exhaustion. No reset, allocation, callback or borrowed VM.
class RuntimeRevocation final {
public:
  explicit RuntimeRevocation(std::uint64_t initial = 1) noexcept : value_(initial) {}
  std::uint64_t current() const noexcept { return value_.load(); }
  std::uint64_t advance() noexcept {
    auto previous = value_.load();
    while (previous) {
      const auto next = previous == UINT64_MAX ? 0 : previous + 1;
      if (value_.compare_exchange_weak(previous, next)) return next;
    }
    return 0;
  }
private:
  static_assert(std::atomic<std::uint64_t>::is_always_lock_free);
  std::atomic<std::uint64_t> value_;
};
inline RuntimeRevocation& runtime_revocation() noexcept {
  static RuntimeRevocation value;
  return value;
}
} // namespace sh3::observer
