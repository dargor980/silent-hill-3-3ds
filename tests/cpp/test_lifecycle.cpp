#include "check.hpp"
#include "sh3/domain/lifecycle.hpp"
#include <array>

int main() {
    using E = sh3::domain::LifecycleEvent;
    using S = sh3::domain::SessionState;
    // RF12.01/RF12.02: all events at each reachable state; suspension preserves pause.
    constexpr std::array<E, 5> events{E::none, E::toggle_pause, E::suspend, E::resume, E::quit};
    constexpr std::array<std::array<S, 5>, 5> expected{{
        {S::running, S::paused, S::suspended, S::running, S::stopped},
        {S::paused, S::running, S::suspended, S::paused, S::stopped},
        {S::suspended, S::suspended, S::suspended, S::running, S::stopped},
        {S::suspended, S::suspended, S::suspended, S::paused, S::stopped},
        {S::stopped, S::stopped, S::stopped, S::stopped, S::stopped},
    }};
    for (std::size_t row = 0; row < expected.size(); ++row) {
        for (std::size_t col = 0; col < events.size(); ++col) {
            sh3::domain::Lifecycle state;
            if (row == 1 || row == 3) {
                state.apply(E::toggle_pause);
            }
            if (row == 2 || row == 3) {
                state.apply(E::suspend);
            }
            if (row == 4) {
                state.apply(E::quit);
            }
            state.apply(events[col]);
            CHECK(state.state() == expected[row][col]);
        }
    }
    sh3::domain::Lifecycle repeated;
    repeated.apply(E::toggle_pause);
    repeated.apply(E::suspend);
    repeated.apply(E::suspend);
    repeated.apply(E::resume);
    CHECK(repeated.state() == S::paused);
    // Repeated cycles retain the prior pause state rather than overwriting it on a duplicate.
    for (unsigned i = 0; i < 10000; ++i) {
        repeated.apply(E::toggle_pause);
        const auto before = repeated.state();
        repeated.apply(E::suspend);
        repeated.apply(E::suspend);
        repeated.apply(E::toggle_pause);
        repeated.apply(E::resume);
        repeated.apply(E::resume);
        CHECK(repeated.state() == before);
    }
}
