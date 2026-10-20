#pragma once
#include <chrono>
#include <cstdint>
#include <limits>
#include <memory>
#include <mutex>
#include <utility>

namespace sh3::observer {
// The gate must outlive every Work and Closure. No method waits for workers.
class CooperativeGate final {
  struct Token {
    CooperativeGate* owner{};
    ~Token();
  };
public:
  using Clock = std::chrono::steady_clock;
  enum class State : std::uint8_t { rejected, draining, held, timed_out, cancelled };
  class Work final {
  public:
    Work() = default;
    explicit operator bool() const noexcept { return bool(token_); }
  private:
    friend class CooperativeGate;
    explicit Work(std::shared_ptr<Token> token) noexcept : token_(std::move(token)) {}
    std::shared_ptr<Token> token_;
  };
  // Confined to its owning thread. poll() is the only readiness check.
  class Closure final {
  public:
    ~Closure();
    Closure(const Closure&) = delete;
    Closure& operator=(const Closure&) = delete;
    State poll() noexcept;
    void cancel() noexcept;
  private:
    friend class CooperativeGate;
    Closure(CooperativeGate&, Clock::time_point) noexcept;
    CooperativeGate& gate_;
    const Clock::time_point deadline_;
    bool owns_{};
    State state_{State::rejected};
  };
  explicit CooperativeGate(std::uint32_t capacity = std::numeric_limits<std::uint32_t>::max()) noexcept
    : capacity_(capacity) {}
  CooperativeGate(const CooperativeGate&) = delete;
  CooperativeGate& operator=(const CooperativeGate&) = delete;
  Work enter() noexcept;
  Closure close(Clock::time_point deadline) noexcept { return Closure(*this, deadline); }
private:
  void leave() noexcept;
  std::mutex mutex_;
  const std::uint32_t capacity_;
  std::uint32_t active_{};
  bool closed_{};
};
} // namespace sh3::observer
