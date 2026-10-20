#pragma once
#include "sh3_observer/cooperative_gate.hpp"
#include "sh3_observer/cpu_boundary.hpp"
#include <optional>

namespace sh3::observer {
class BarrierSource {
public:
  virtual ~BarrierSource() = default;
  virtual CooperativeGate::Closure close(CooperativeGate::Clock::time_point) noexcept = 0;
};
// CPU-thread confined. Dependencies must outlive the controller.
class PineDrain final {
public:
  using Clock = CooperativeGate::Clock;
  enum class State { idle, queued, draining, held, completed, cancelled, timed_out, invalidated, rejected };
  struct Identity { std::uint64_t vm{}, server{}; };
  struct Request { std::uint64_t id{}; Identity identity{}; Clock::time_point deadline{}; };
  struct Result { std::uint64_t id{}; State state{State::idle}; };
  PineDrain(CpuBoundary& cpu, BarrierSource& source) noexcept : cpu_(cpu), source_(source) {}
  ~PineDrain();
  PineDrain(const PineDrain&) = delete;
  PineDrain& operator=(const PineDrain&) = delete;
  bool submit(Request) noexcept;
  State step(bool paused, Identity) noexcept;
  bool complete(bool paused, Identity) noexcept;
  bool cancel(std::uint64_t id) noexcept;
  Result retire() noexcept;
  Result status() const noexcept { return {request_.id, state_}; }
  bool active() const noexcept { return state_ != State::idle; }
private:
  struct Lease {
    Lease(BarrierSource& source, Clock::time_point deadline) noexcept : closure(source.close(deadline)) {}
    CooperativeGate::Closure closure;
  };
  bool terminal() const noexcept;
  CpuBoundary& cpu_;
  BarrierSource& source_;
  Request request_{};
  std::uint64_t last_id_{};
  State state_{State::idle};
  std::optional<Lease> lease_;
};
} // namespace sh3::observer
