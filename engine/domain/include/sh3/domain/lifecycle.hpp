#pragma once

namespace sh3::domain {
enum class SessionState { running, paused, suspended, stopped };
enum class LifecycleEvent { none, toggle_pause, suspend, resume, quit };

// Diagnostic lifecycle only; this does not define SH3's simulation frequency or game rules.
class Lifecycle final {
  public:
    [[nodiscard]] SessionState state() const noexcept;
    void apply(LifecycleEvent event) noexcept;

  private:
    SessionState state_{SessionState::running};
    SessionState before_suspend_{SessionState::running};
};
} // namespace sh3::domain
