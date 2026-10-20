#pragma once
#include <atomic>
#include <cstdint>
#include <limits>

namespace sh3::observer {
// Announces foreign threads about to wait synchronously for CPU. This signal
// never releases worker tokens or dispatches callbacks; CPU remains the owner.
class ExternalWaits final {
public:
  static constexpr std::uint32_t max_waiters = std::numeric_limits<std::uint32_t>::max();
  explicit ExternalWaits(std::uint32_t capacity = max_waiters) noexcept : capacity_(capacity) {}
  ExternalWaits(const ExternalWaits&) = delete;
  ExternalWaits& operator=(const ExternalWaits&) = delete;
  class Wait final {
  public:
    ~Wait();
    Wait(const Wait&) = delete;
    Wait& operator=(const Wait&) = delete;
    bool tracked() const noexcept { return tracked_; }
  private:
    friend class ExternalWaits;
    Wait(ExternalWaits& owner, bool needed) noexcept;
    ExternalWaits& owner_;
    bool tracked_;
  };
  Wait wait(bool needed = true) noexcept { return Wait(*this, needed); }
  bool pending() const noexcept;
private:
  bool acquire() noexcept;
  const std::uint32_t capacity_;
  std::atomic_uint32_t active_{0};
  std::atomic_bool poisoned_{false};
};
} // namespace sh3::observer
