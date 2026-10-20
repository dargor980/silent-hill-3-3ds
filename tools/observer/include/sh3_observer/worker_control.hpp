#pragma once
#include <atomic>
#include <chrono>
#include <cstdint>
#include <semaphore>

namespace sh3::observer {
// Multiple notifiers, exactly one consumer. Wakeups are hints, not predicates.
class ControlWakeup final {
public:
  using Clock = std::chrono::steady_clock;
  void notify() noexcept;
  bool try_wait() noexcept;
  bool wait_until(Clock::time_point deadline) noexcept;
private:
  std::atomic_bool pending_{false};
  std::binary_semaphore signal_{0};
};

// One CPU actor calls request/release; one worker calls start/acknowledge/stop.
// The worker must stop effects while held and must not exit on stop(retained/retry).
// Neither this object nor owner_wakeup may be destroyed before both actors exit.
class WorkerControl final {
public:
  struct Token {
    std::uint32_t generation{}, id{};
    friend bool operator==(Token, Token) = default;
  };
  enum class Status { invalid, pending, held, released, offline };
  enum class StopResult { stopped, retained, retry, stale };
  struct Lifecycle { std::uint32_t generation{}; bool online{}; };
  static constexpr std::uint32_t max_request_id = 0x1fffffff;

  explicit WorkerControl(ControlWakeup& owner_wakeup) noexcept : owner_wakeup_(owner_wakeup) {}
  bool start(std::uint32_t generation) noexcept;
  [[nodiscard]] StopResult stop(std::uint32_t generation) noexcept;
  bool request(Token) noexcept;
  Token pending(std::uint32_t generation) const noexcept;
  bool acknowledge(Token) noexcept;
  bool release(Token) noexcept;
  Status status(Token) const noexcept;
  Lifecycle lifecycle() const noexcept;
  bool wait_worker_until(ControlWakeup::Clock::time_point deadline) noexcept {
    return worker_wakeup_.wait_until(deadline);
  }
private:
  enum class Phase : std::uint64_t { offline, running, requested, held };
  static bool valid(Token) noexcept;
  static std::uint64_t pack(Token, Phase) noexcept;
  static Token token(std::uint64_t) noexcept;
  static Phase phase(std::uint64_t) noexcept;
  static_assert(std::atomic<std::uint64_t>::is_always_lock_free);
  std::atomic<std::uint64_t> word_{0};
  ControlWakeup worker_wakeup_;
  ControlWakeup& owner_wakeup_;
};
} // namespace sh3::observer
