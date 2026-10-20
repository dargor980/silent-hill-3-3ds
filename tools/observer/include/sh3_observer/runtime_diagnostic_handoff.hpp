#pragma once
#include "sh3_observer/runtime_diagnostic_ticket.hpp"

namespace sh3::observer {
class RuntimeDiagnosticQueue {
public:
  virtual ~RuntimeDiagnosticQueue() = default;
  // Runs on CPU; validates CPU identity and uses this exact local deadline.
  virtual std::shared_ptr<RuntimeDiagnosticTicket> queue_until(
    std::uint64_t id, DiagnosticClock::Clock::time_point deadline) noexcept = 0;
};

// IO owns cancellation. A queued callback must retain a shared_ptr to this object.
// A sole CPU callback writes ticket_ once; readers wait for published_. Clock is
// trusted/nonblocking and must outlive all callbacks, tickets and DW references.
class RuntimeDiagnosticHandoff final {
public:
  RuntimeDiagnosticHandoff(std::uint64_t, DiagnosticClock::Clock::time_point,
                          DiagnosticClock& = system_diagnostic_clock()) noexcept;
  ~RuntimeDiagnosticHandoff() { cancel(); }
  bool execute(RuntimeDiagnosticQueue&) noexcept;
  void cancel(DiagnosticRejection = DiagnosticRejection::cancelled) noexcept;
  DiagnosticRejection failure() noexcept;
  std::shared_ptr<RuntimeDiagnosticBinding> binding() noexcept;
  DiagnosticClock& clock() const noexcept { return clock_; }
  DiagnosticClock::Clock::time_point deadline() const noexcept { return deadline_; }
  // True only when cancellation prevents acquisition, or CPU confirms retirement.
  bool quiescent() noexcept;
private:
  DiagnosticRejection stop(DiagnosticRejection) noexcept;
  DiagnosticClock& clock_;
  const std::uint64_t id_;
  const DiagnosticClock::Clock::time_point opened_, deadline_;
  std::atomic<bool> started_{false}, published_{false};
  std::atomic<DiagnosticRejection> reason_{DiagnosticRejection::none};
  std::shared_ptr<RuntimeDiagnosticTicket> ticket_; // Immutable after publication.
};

// IO owner only. False retains the worker and handoff; retry after CPU retires.
// Never destroys resources, dispatches a callback, or waits for CPU acknowledgement.
bool wait_runtime_diagnostic_stopped(RuntimeDiagnosticHandoff&, DiagnosticWorker*,
                                    DiagnosticClock::Clock::time_point);
} // namespace sh3::observer
