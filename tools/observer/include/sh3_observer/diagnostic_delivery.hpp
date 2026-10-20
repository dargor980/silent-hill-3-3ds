#pragma once
#include "sh3_observer/diagnostic_worker.hpp"

namespace sh3::observer {
class DiagnosticDeliverySink {
public:
  virtual ~DiagnosticDeliverySink() = default;
  // One owner, outside CPU/gates. Return progress (possibly zero after waiting),
  // or false for terminal IO/peer failure. Never retain the borrowed byte range.
  virtual bool write(const std::uint8_t*, std::size_t, std::size_t&,
                     DiagnosticClock::Clock::duration maximum_wait) noexcept = 0;
};
enum class DiagnosticDeliveryResult { waiting, complete, rejected };
// Keeps the worker's deadline active during every sink call. May block up to the
// remaining budget if the trusted sink cooperates. Caller owns sink cleanup.
DiagnosticDeliveryResult deliver_diagnostic(DiagnosticWorker&, DiagnosticDeliverySink&) noexcept;
// Optional external cancellation observed by the sole IO owner at every write
// boundary. The atomic must outlive the call; already-sent bytes cannot be undone.
DiagnosticDeliveryResult deliver_diagnostic(DiagnosticWorker&, DiagnosticDeliverySink&,
                                            const std::atomic<bool>& cancelled) noexcept;
} // namespace sh3::observer
