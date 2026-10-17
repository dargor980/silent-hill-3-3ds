#include "sh3/application/diagnostic_app.hpp"

namespace sh3::application {
DiagnosticApp::DiagnosticApp(ports::IInputSource &input, ports::IDiagnosticView &view,
                             ports::ILifecycleLog &log) noexcept
    : input_(input), view_(view), log_(log) {}

bool DiagnosticApp::step() noexcept {
    const auto before = lifecycle_.state();
    if (before == domain::SessionState::stopped) {
        return false;
    }
    if (before == domain::SessionState::suspended) {
        // Only platform dispatch can resume an inactive session; input may have side effects.
        return true;
    }
    dispatch(input_.poll());
    const auto after = lifecycle_.state();
    // Rendering is forbidden while suspended and after shutdown.
    if (after != domain::SessionState::suspended && after != domain::SessionState::stopped) {
        view_.present(after);
    }
    return after != domain::SessionState::stopped;
}

void DiagnosticApp::dispatch(domain::LifecycleEvent event) noexcept {
    const auto before = lifecycle_.state();
    lifecycle_.apply(event);
    if (lifecycle_.state() != before) {
        log_.record(lifecycle_.state());
    }
}

domain::SessionState DiagnosticApp::state() const noexcept { return lifecycle_.state(); }
} // namespace sh3::application
