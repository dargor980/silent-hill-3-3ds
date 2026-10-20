#pragma once
#include "sh3_observer/retained_drain.hpp"
#include "sh3_observer/worker_control.hpp"

namespace sh3::observer {
// CPU-owned adapter. These operations never dispatch callbacks, reserve data
// slots or wait for another thread. release retires exactly the supplied token.
class WorkerPort {
public:
  using Token = WorkerControl::Token;
  virtual ~WorkerPort() = default;
  virtual WorkerControl::Lifecycle lifecycle() const noexcept = 0;
  virtual bool request(Token) noexcept = 0;
  virtual WorkerControl::Status status(Token) const noexcept = 0;
  virtual void release(Token) noexcept = 0;
};

// Owns only worker tokens; RetainedDrain owns the CPU/PINE/epoch envelope.
// All methods, including destruction, run on that same CPU actor. Dependencies
// outlive this object. A smaller lifetime ticket budget can fail closed earlier.
class WorkerDrain final : public EffectDrainPort {
public:
  WorkerDrain(WorkerPort& vu, WorkerPort& gs,
              std::uint32_t ticket_budget = WorkerControl::max_request_id) noexcept;
  ~WorkerDrain();
  WorkerDrain(const WorkerDrain&) = delete;
  WorkerDrain& operator=(const WorkerDrain&) = delete;
  void begin(PineDrain::Request) noexcept override;
  Progress poll(std::uint64_t id) noexcept override;
  void release(std::uint64_t id) noexcept override;
private:
  bool sessions_match() const noexcept;
  WorkerPort& vu_;
  WorkerPort& gs_;
  const std::uint32_t budget_;
  std::uint32_t last_ticket_{};
  std::uint64_t last_attempt_{};
  PineDrain::Request attempt_{};
  WorkerControl::Token vu_token_{}, gs_token_{};
  WorkerControl::Lifecycle vu_session_{}, gs_session_{};
  Progress progress_{Progress::rejected};
};
} // namespace sh3::observer
