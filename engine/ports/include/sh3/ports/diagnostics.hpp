#pragma once

#include "sh3/domain/lifecycle.hpp"

namespace sh3::ports {
// Ports are separated by consumer responsibility; no service locator or platform headers.
class IInputSource {
  public:
    virtual ~IInputSource() = default;
    [[nodiscard]] virtual domain::LifecycleEvent poll() noexcept = 0;
};

class IDiagnosticView {
  public:
    virtual ~IDiagnosticView() = default;
    virtual void present(domain::SessionState state) noexcept = 0;
};

class ILifecycleLog {
  public:
    virtual ~ILifecycleLog() = default;
    // Log sinks may overwrite old records at capacity; they must not block or allocate per event.
    virtual void record(domain::SessionState state) noexcept = 0;
};
} // namespace sh3::ports
