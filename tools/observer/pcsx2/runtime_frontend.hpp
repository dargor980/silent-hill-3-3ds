#pragma once
#include "sh3_observer/runtime_diagnostic_handoff.hpp"

namespace sh3::observer::pcsx2 {
// IO owner only. Fixed local deadline includes earlier receive/queue time.
// Retain and cancel the returned request before abandoning the IO operation.
std::shared_ptr<RuntimeDiagnosticHandoff> queue_runtime_diagnostic(
  DiagnosticClock::Clock::time_point deadline) noexcept;
}
