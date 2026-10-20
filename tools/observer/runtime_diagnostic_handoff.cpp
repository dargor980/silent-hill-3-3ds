#include "sh3_observer/runtime_diagnostic_handoff.hpp"

namespace sh3::observer {
namespace { using Reason = DiagnosticRejection; using Clock = DiagnosticClock::Clock; }
RuntimeDiagnosticHandoff::RuntimeDiagnosticHandoff(std::uint64_t id,
    Clock::time_point deadline, DiagnosticClock& clock) noexcept
  : clock_(clock), id_(id), opened_(clock.now()), deadline_(deadline) {
  if (!id_ || id_ == UINT64_MAX || opened_ > Clock::time_point::max()-std::chrono::seconds(5) ||
      deadline_ > opened_+std::chrono::seconds(5)) stop(Reason::configuration);
  else if (deadline_ <= opened_) stop(Reason::deadline);
}
Reason RuntimeDiagnosticHandoff::stop(Reason reason) noexcept {
  if (reason < Reason::configuration || reason > Reason::unavailable) reason = Reason::protocol;
  auto expected = Reason::none;
  reason_.compare_exchange_strong(expected, reason);
  const auto first = reason_.load();
  if (published_.load() && ticket_) ticket_->cancel(first);
  return first;
}
void RuntimeDiagnosticHandoff::cancel(Reason reason) noexcept { stop(reason); }
Reason RuntimeDiagnosticHandoff::failure() noexcept {
  const auto reason = reason_.load();
  if (reason != Reason::none) return reason;
  const auto now = clock_.now();
  if (now < opened_) return stop(Reason::unavailable);
  if (now >= deadline_) return stop(Reason::deadline);
  if (published_.load()) {
    if (!ticket_) return stop(Reason::unavailable);
    if (ticket_->state() == RuntimeDiagnosticTicket::State::stopped) return stop(ticket_->failure());
  }
  return reason_.load();
}
bool RuntimeDiagnosticHandoff::execute(RuntimeDiagnosticQueue& queue) noexcept {
  if (started_.exchange(true)) return false;
  if (failure() == Reason::none) ticket_ = queue.queue_until(id_, deadline_);
  published_.store(true);
  // Together with stop's publication check, covers both sides of cancel/publish.
  if (failure() != Reason::none) {
    if (ticket_) ticket_->cancel(reason_.load());
    return false;
  }
  return true;
}
std::shared_ptr<RuntimeDiagnosticBinding> RuntimeDiagnosticHandoff::binding() noexcept {
  if (failure() != Reason::none || !published_.load() || !ticket_) return {};
  auto result = ticket_->binding();
  return failure() == Reason::none ? result : nullptr;
}
bool RuntimeDiagnosticHandoff::quiescent() noexcept {
  if (failure() == Reason::none) return false;
  if (!started_.load()) return true;
  if (!published_.load()) return false;
  return !ticket_ || ticket_->retired();
}
bool wait_runtime_diagnostic_stopped(RuntimeDiagnosticHandoff& handoff,
    DiagnosticWorker* worker, Clock::time_point deadline) {
  handoff.cancel();
  if (worker) worker->cancel();
  if (!handoff.quiescent()) return false;
  return !worker || worker->wait_stopped_until(deadline);
}
} // namespace sh3::observer
