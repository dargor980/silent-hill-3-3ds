#pragma once
#include "sh3_observer/platform_diagnostic.hpp"
#include <chrono>
#include <memory>

namespace sh3::observer {
class DiagnosticClock {
public:
  using Clock = std::chrono::steady_clock;
  virtual ~DiagnosticClock() = default;
  // Trusted, nonblocking and nonreentrant. Must outlive the worker.
  virtual Clock::time_point now() noexcept = 0;
};
DiagnosticClock& system_diagnostic_clock() noexcept;
class DiagnosticValidity {
public:
  virtual ~DiagnosticValidity() = default;
  // Called under DW's mutex. Must be fast, nonblocking and nonreentrant; no IO,
  // callbacks, worker methods or locks shared with the CPU coordinator.
  virtual DiagnosticRejection failure() const noexcept = 0;
};
struct DiagnosticWorkerState;
class DiagnosticBudget final {
public:
  bool checkpoint() noexcept;
  DiagnosticClock::Clock::duration remaining() noexcept;
private:
  friend struct DiagnosticWorkerState;
  explicit DiagnosticBudget(DiagnosticWorkerState& state) noexcept : state_(state) {}
  DiagnosticWorkerState& state_;
};
struct DiagnosticObservation {
  PlatformInventoryResult inventory{};
  AdmissionProfile facts{};
  DiagnosticEpochs epochs{};
};
class DiagnosticWork {
public:
  virtual ~DiagnosticWork() = default;
  virtual DiagnosticRejection prepare(DiagnosticBudget&) = 0;
  virtual DiagnosticRejection sample(DiagnosticBudget&, DiagnosticObservation&) = 0;
  // Called on the same worker, after the last callback returns, including errors.
  virtual bool close() noexcept = 0;
};
class DiagnosticWorkFactory {
public:
  virtual ~DiagnosticWorkFactory() = default;
  // Constructor/configuration must not do preparation or acquire live resources.
  virtual std::unique_ptr<DiagnosticWork> create(DiagnosticBudget&) = 0;
};
enum class DiagnosticWorkerPhase { idle, queued, preparing, sampling, ready, closing, stopped, delivering };
struct DiagnosticWorkerStatus {
  DiagnosticRejection reason{DiagnosticRejection::none};
  DiagnosticWorkerPhase phase{DiagnosticWorkerPhase::idle};
  bool cleanup_verified{}, joined{};
};
struct DiagnosticCompletion {
  DiagnosticBytes bytes{};
  AdmissionReport gates{};
  // Historical diagnostic only. No capture capability, even when gates are clear.
};
class DiagnosticWorker final {
public:
  DiagnosticWorker(DiagnosticExpectation, std::unique_ptr<DiagnosticWorkFactory>,
                   DiagnosticClock& = system_diagnostic_clock(),
                   std::shared_ptr<const DiagnosticValidity> = {});
  // Cancels and joins. Owner must destroy outside CPU/worker and retained gates.
  ~DiagnosticWorker();
  DiagnosticWorker(const DiagnosticWorker&) = delete;
  DiagnosticWorker& operator=(const DiagnosticWorker&) = delete;
  bool submit(const DiagnosticRequest&, const DiagnosticEpochs&) noexcept;
  bool take(DiagnosticCompletion&) noexcept;
  // Retained-delivery mode. Local absolute deadline includes earlier IO; never
  // extends the worker's own 5s/2s maximum. Do not mix with submit/take.
  bool submit_until(const DiagnosticRequest&, const DiagnosticEpochs&,
                    DiagnosticClock::Clock::time_point) noexcept;
  bool take_for_delivery(DiagnosticCompletion&) noexcept;
  bool delivery_checkpoint() noexcept;
  DiagnosticClock::Clock::duration delivery_remaining() noexcept;
  bool complete_delivery() noexcept;
  void cancel() noexcept;
  void peer_lost() noexcept;
  void lifecycle(const DiagnosticEpochs&) noexcept;
  DiagnosticWorkerStatus status() noexcept;
  // Identity only, not evidence of validity. The retained pointer is immutable.
  bool bound_to(const DiagnosticValidity&) const noexcept;
  // Sole lifecycle owner, never CPU/worker. A timeout retains all resources.
  // True means thread joined AND close() succeeded; inspect status on false.
  bool wait_stopped_until(DiagnosticClock::Clock::time_point);
private:
  bool submit_impl(const DiagnosticRequest&, const DiagnosticEpochs&,
                   const DiagnosticClock::Clock::time_point*) noexcept;
  std::unique_ptr<DiagnosticWorkerState> state_;
};
} // namespace sh3::observer
