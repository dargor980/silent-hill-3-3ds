// Own frontend composition; Host and VMManager declarations precede this file.
#include "runtime_frontend.hpp"
namespace sh3::observer::pcsx2 {
namespace {
RuntimeRevocation request_ids;
class CpuQueue final : public RuntimeDiagnosticQueue {
public:
  std::shared_ptr<RuntimeDiagnosticTicket> queue_until(std::uint64_t id,
      DiagnosticClock::Clock::time_point deadline) noexcept override {
    return VMManager::Internal::QueueObserverRuntimeDiagnosticUntil(id, deadline);
  }
};
}
std::shared_ptr<RuntimeDiagnosticHandoff> queue_runtime_diagnostic(
    DiagnosticClock::Clock::time_point deadline) noexcept {
  if (VMManager::Internal::IsObserverCpuThread()) return {};
  const auto id = request_ids.advance();
  if (!id || id == UINT64_MAX) return {};
  std::shared_ptr<RuntimeDiagnosticHandoff> handoff;
  try {
    handoff = std::make_shared<RuntimeDiagnosticHandoff>(id, deadline);
    if (handoff->failure() != DiagnosticRejection::none) return handoff;
    Host::RunOnCPUThread([handoff] {
      CpuQueue queue;
      handoff->execute(queue);
    }, false);
  } catch (...) {
    if (handoff) handoff->cancel(DiagnosticRejection::unavailable);
  }
  return handoff;
}
} // namespace sh3::observer::pcsx2
