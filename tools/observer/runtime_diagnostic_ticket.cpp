#include "sh3_observer/runtime_diagnostic_ticket.hpp"
namespace sh3::observer {
std::shared_ptr<RuntimeDiagnosticTicket> make_runtime_diagnostic_ticket(
    const RuntimeRevocation& generation, DiagnosticClock& clock) noexcept {
  try { return std::make_shared<RuntimeDiagnosticTicket>(generation, clock); }
  catch (...) { return {}; }
}
} // namespace sh3::observer
