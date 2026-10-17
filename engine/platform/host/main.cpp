#include "sh3/application/diagnostic_app.hpp"
#include "sh3/platform/bounded_log.hpp"
#include <array>
#include <cstdio>

namespace {
class ScriptedInput final : public sh3::ports::IInputSource {
  public:
    sh3::domain::LifecycleEvent poll() noexcept override {
        using E = sh3::domain::LifecycleEvent;
        constexpr std::array<E, 4> script{E::none, E::toggle_pause, E::suspend, E::quit};
        return index_ < script.size() ? script[index_++] : E::quit;
    }

  private:
    std::size_t index_{0};
};
class ConsoleView final : public sh3::ports::IDiagnosticView {
  public:
    void present(sh3::domain::SessionState state) noexcept override {
        std::printf("synthetic diagnostic state=%d\n", static_cast<int>(state));
    }
};
} // namespace

int main() {
    ScriptedInput input;
    ConsoleView view;
    sh3::platform::BoundedLog log;
    sh3::application::DiagnosticApp app(input, view, log);
    while (app.step()) {
        if (app.state() == sh3::domain::SessionState::suspended) {
            // Scripted platform wakeup, independent of the inactive input source.
            app.dispatch(sh3::domain::LifecycleEvent::resume);
        }
    }
    const bool passed = app.state() == sh3::domain::SessionState::stopped && log.size() == 4;
    std::printf("diagnostic=%s retained_events=%zu\n", passed ? "passed" : "failed", log.size());
    return passed ? 0 : 1;
}
