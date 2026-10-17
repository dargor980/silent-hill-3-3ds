#pragma once

#include "sh3/domain/lifecycle.hpp"
#include "sh3/ports/diagnostics.hpp"

namespace sh3::application {
class DiagnosticApp final {
  public:
    DiagnosticApp(ports::IInputSource &input, ports::IDiagnosticView &view,
                  ports::ILifecycleLog &log) noexcept;
    // False once stopped. No input/view effects while suspended or after shutdown.
    [[nodiscard]] bool step() noexcept;
    // The platform calls this on the same thread as step(), including to resume suspension.
    void dispatch(domain::LifecycleEvent event) noexcept;
    [[nodiscard]] domain::SessionState state() const noexcept;

  private:
    domain::Lifecycle lifecycle_{};
    ports::IInputSource &input_;
    ports::IDiagnosticView &view_;
    ports::ILifecycleLog &log_;
};
} // namespace sh3::application
