#include "check.hpp"
#include "sh3/application/diagnostic_app.hpp"
#include "sh3/platform/bounded_log.hpp"
#include <array>

namespace {
using E = sh3::domain::LifecycleEvent;
using S = sh3::domain::SessionState;
class Input final : public sh3::ports::IInputSource {
  public:
    E next{E::none};
    unsigned calls{0};
    E poll() noexcept override {
        ++calls;
        return next;
    }
};
class View final : public sh3::ports::IDiagnosticView {
  public:
    unsigned calls{0};
    S last{S::stopped};
    void present(S state) noexcept override {
        ++calls;
        last = state;
    }
};
class CountingLog final : public sh3::ports::ILifecycleLog {
  public:
    unsigned count{0};
    void record(S) noexcept override { ++count; }
};

// RNF11.02/RNF11.03: identical consumer contract with two interchangeable log adapters.
void contract(sh3::ports::ILifecycleLog &log) {
    Input input;
    View view;
    sh3::application::DiagnosticApp app(input, view, log);
    CHECK(app.step());
    CHECK(view.last == S::running);
    input.next = E::toggle_pause;
    CHECK(app.step());
    CHECK(view.last == S::paused);
    input.next = E::suspend;
    CHECK(app.step());
    CHECK(app.state() == S::suspended);
    CHECK(view.calls == 2);
    app.dispatch(E::resume);
    input.next = E::none;
    CHECK(app.step());
    CHECK(view.last == S::paused);
    input.next = E::quit;
    CHECK(!app.step());
    CHECK(!app.step());
    CHECK(input.calls == 5);
    CHECK(view.calls == 3);
}
void suspended_and_terminal_contract() {
    Input input;
    View view;
    sh3::platform::BoundedLog log;
    sh3::application::DiagnosticApp app(input, view, log);
    app.dispatch(E::toggle_pause);
    app.dispatch(E::suspend);
    app.dispatch(E::suspend);
    CHECK(log.size() == 2);
    // Even an input source eager to quit cannot run while the platform has suspended us.
    input.next = E::quit;
    for (unsigned i = 0; i < 100; ++i) {
        CHECK(app.step());
    }
    CHECK(input.calls == 0 && view.calls == 0 && log.size() == 2);
    app.dispatch(E::resume);
    app.dispatch(E::resume);
    CHECK(app.state() == S::paused && log.size() == 3);
    input.next = E::none;
    CHECK(app.step() && view.last == S::paused && input.calls == 1);
    app.dispatch(E::quit);
    const auto stopped_events = log.size();
    for (const auto event : {E::resume, E::suspend, E::toggle_pause, E::quit, E::none}) {
        app.dispatch(event);
        CHECK(!app.step());
    }
    CHECK(log.size() == stopped_events && input.calls == 1 && view.calls == 1);
}
} // namespace

int main() {
    suspended_and_terminal_contract();
    CountingLog counting;
    contract(counting);
    CHECK(counting.count == 4);
    sh3::platform::BoundedLog bounded;
    contract(bounded);
    CHECK(bounded.size() == 4);
    CHECK(bounded.at(0) == S::paused);
    CHECK(bounded.at(1) == S::suspended);
    CHECK(bounded.at(2) == S::paused);
    CHECK(bounded.at(3) == S::stopped);
}
