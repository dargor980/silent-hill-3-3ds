#pragma once
#include "sh3_observer/diagnostic_worker.hpp"
#include "sh3_observer/runtime_revocation.hpp"
#include <atomic>
#include <thread>

namespace sh3::observer {
struct RuntimeDiagnosticSnapshot {
  std::uint64_t scope_id{}; // Local coordinator attempt, not the wire sequence.
  DiagnosticClock::Clock::time_point deadline{};
  DiagnosticEpochs epochs{};
  AdmissionProfile facts{};
};

// One CPU owner activates/revalidates; any actor may revoke. The snapshot never
// changes after publication. This is local supplied evidence, not attestation.
// Owner outlives activation; clock and optional revocation source outlive all references.
class RuntimeDiagnosticBinding final : public DiagnosticValidity {
public:
  explicit RuntimeDiagnosticBinding(DiagnosticClock& = system_diagnostic_clock(),
                                    const RuntimeRevocation* = nullptr) noexcept;
  bool activate(RuntimeDiagnosticSnapshot) noexcept;
  bool revalidate(RuntimeDiagnosticSnapshot) noexcept;
  void revoke(DiagnosticRejection = DiagnosticRejection::lifecycle) noexcept;
  DiagnosticRejection failure() const noexcept override;
  bool snapshot(RuntimeDiagnosticSnapshot&) const noexcept;
  DiagnosticClock& clock() const noexcept { return clock_; }
private:
  DiagnosticRejection stop(DiagnosticRejection) const noexcept;
  DiagnosticClock& clock_;
  const RuntimeRevocation* const revocation_;
  const std::uint64_t revision_;
  const std::thread::id owner_;
  bool attempted_{}; // Owner only; foreign calls only revoke.
  RuntimeDiagnosticSnapshot value_{};
  DiagnosticClock::Clock::time_point opened_{};
  std::atomic<bool> ready_{false};
  mutable std::atomic<DiagnosticRejection> reason_{DiagnosticRejection::none};
};

// The decorator is private: data and DW validity always share this binding.
// Native resources are still created and destroyed only by the worker.
std::unique_ptr<DiagnosticWorker> make_runtime_diagnostic_worker(
  DiagnosticExpectation, std::unique_ptr<DiagnosticWorkFactory>,
  std::shared_ptr<RuntimeDiagnosticBinding>);
} // namespace sh3::observer
