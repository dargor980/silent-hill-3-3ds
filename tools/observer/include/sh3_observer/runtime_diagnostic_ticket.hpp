#pragma once
#include "sh3_observer/runtime_diagnostic.hpp"

namespace sh3::observer {
// CPU constructs/publishes/revalidates; IO may observe readiness and cancel.
// Cancellation never dispatches to CPU, joins DW, or closes native resources.
class RuntimeDiagnosticTicket final {
public:
  enum class State { pending, ready, stopped };
  explicit RuntimeDiagnosticTicket(const RuntimeRevocation& generation,
      DiagnosticClock& clock = system_diagnostic_clock())
    : binding_(std::make_shared<RuntimeDiagnosticBinding>(clock, &generation)),
      owner_(std::this_thread::get_id()) {}
  State state() const noexcept {
    const auto state = state_.load();
    const auto reason = binding_->failure();
    if (state == State::stopped || (state == State::ready && reason != DiagnosticRejection::none) ||
        (state == State::pending && reason != DiagnosticRejection::unavailable &&
         reason != DiagnosticRejection::none)) return State::stopped;
    return state;
  }
  bool publish(RuntimeDiagnosticSnapshot value) noexcept {
    if (state_.load() != State::pending || !binding_->activate(value)) {
      cancel(DiagnosticRejection::lifecycle); return false;
    }
    auto expected = State::pending;
    if (!state_.compare_exchange_strong(expected, State::ready)) return false;
    return state() == State::ready;
  }
  bool revalidate(RuntimeDiagnosticSnapshot value) noexcept {
    if (state() != State::ready || !binding_->revalidate(value)) {
      cancel(DiagnosticRejection::lifecycle); return false;
    }
    return true;
  }
  void cancel(DiagnosticRejection reason = DiagnosticRejection::cancelled) noexcept {
    binding_->revoke(reason); state_.store(State::stopped);
  }
  std::shared_ptr<RuntimeDiagnosticBinding> binding() const noexcept {
    return state() == State::ready ? binding_ : nullptr;
  }
  DiagnosticRejection failure() const noexcept { return binding_->failure(); }
  // CPU calls only AFTER releasing all guards. Revocation alone is not retirement.
  bool retire() noexcept {
    if (std::this_thread::get_id() != owner_) return false;
    cancel(); retired_.store(true); return true;
  }
  bool retired() const noexcept { return retired_.load(); }
private:
  static_assert(std::atomic<State>::is_always_lock_free);
  const std::shared_ptr<RuntimeDiagnosticBinding> binding_;
  const std::thread::id owner_;
  std::atomic<State> state_{State::pending};
  std::atomic<bool> retired_{false};
};
// Allocation is caught in the exception-enabled worker library, not VMManager.
std::shared_ptr<RuntimeDiagnosticTicket> make_runtime_diagnostic_ticket(
  const RuntimeRevocation&, DiagnosticClock& = system_diagnostic_clock()) noexcept;
} // namespace sh3::observer
