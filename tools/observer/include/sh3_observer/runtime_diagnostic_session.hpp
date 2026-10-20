#pragma once
#include "sh3_observer/diagnostic_channel.hpp"
#include "sh3_observer/runtime_diagnostic_handoff.hpp"

namespace sh3::observer {
enum class RuntimeSessionResult { waiting, complete, rejected };
enum class RuntimeSessionClose { pending, closed, failed };

// Non-owning, sole IO thread. References outlive this session and all pending
// cleanup. The owner MUST close_until to closed/failed before destroying DW;
// pending retains all resources. Destruction cancels, never waits or joins.
class RuntimeDiagnosticSession final {
public:
  RuntimeDiagnosticSession(RuntimeDiagnosticHandoff&, DiagnosticWorker&, DiagnosticChannel&) noexcept;
  ~RuntimeDiagnosticSession() { cancel(); }
  RuntimeDiagnosticSession(const RuntimeDiagnosticSession&) = delete;
  RuntimeDiagnosticSession& operator=(const RuntimeDiagnosticSession&) = delete;
  RuntimeSessionResult step() noexcept;
  // IO observes this signal around reads and each delivery write. Does not
  // transfer ownership or join; the signal must outlive this synchronous call.
  RuntimeSessionResult step(const std::atomic<bool>& cancelled) noexcept;
  void cancel() noexcept;
  DiagnosticRejection failure() noexcept;
  RuntimeSessionClose close_until(DiagnosticClock::Clock::time_point join_deadline);
private:
  RuntimeSessionResult step_with_cancellation(const std::atomic<bool>*) noexcept;
  DiagnosticRejection stop(DiagnosticRejection) noexcept;
  bool check() noexcept;
  RuntimeDiagnosticHandoff& handoff_;
  DiagnosticWorker& worker_;
  DiagnosticChannel& channel_;
  DiagnosticClock& clock_;
  std::shared_ptr<RuntimeDiagnosticBinding> binding_;
  RuntimeDiagnosticSnapshot snapshot_{};
  DiagnosticClock::Clock::time_point last_, deadline_;
  std::array<std::uint8_t, diagnostic_request_size> packet_{};
  std::size_t received_{};
  DiagnosticRejection reason_{DiagnosticRejection::none};
  bool working_{}, channel_closed_{}, close_ok_{true};
};
} // namespace sh3::observer
