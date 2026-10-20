#pragma once
#include "sh3_observer/pine_drain.hpp"

namespace sh3::observer {
// CPU-owned control port. Calls must be bounded and must not wait for CPU/UI,
// reserve data-queue space, or execute application callbacks. release undoes
// partial begin work, in dependency order, before returning.
class EffectDrainPort {
public:
  enum class Progress { pending, held, rejected };
  virtual ~EffectDrainPort() = default;
  virtual void begin(PineDrain::Request) noexcept = 0;
  virtual Progress poll(std::uint64_t id) noexcept = 0;
  virtual void release(std::uint64_t id) noexcept = 0;
};

// Owns the whole attempt. PINE stays closed through downstream release.
// Dependencies must outlive this CPU-thread-confined controller.
class RetainedDrain final {
public:
  using State = PineDrain::State;
  using Request = PineDrain::Request;
  using Identity = PineDrain::Identity;
  using Result = PineDrain::Result;
  RetainedDrain(CpuBoundary& cpu, BarrierSource& source, EffectDrainPort& effects) noexcept
      : pine_(cpu, source), effects_(effects) {}
  ~RetainedDrain();
  RetainedDrain(const RetainedDrain&) = delete;
  RetainedDrain& operator=(const RetainedDrain&) = delete;
  bool submit(Request) noexcept;
  State step(bool paused, Identity) noexcept;
  bool complete(bool paused, Identity) noexcept;
  bool cancel(std::uint64_t id) noexcept;
  Result retire() noexcept;
  Result status() const noexcept { return {request_.id, state_}; }
  bool active() const noexcept { return state_ != State::idle; }
  bool effects_started() const noexcept { return started_; }
private:
  bool terminal() const noexcept;
  State stop(State) noexcept;
  PineDrain pine_;
  EffectDrainPort& effects_;
  Request request_{};
  State state_{State::idle};
  bool started_{};
  bool stepping_{};
  bool retiring_{};
};
} // namespace sh3::observer
