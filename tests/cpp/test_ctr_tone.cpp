#include "audio_sdk.hpp"
#include "check.hpp"
#include "tone.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <string>
#include <type_traits>

namespace {
using sh3::platform::ctr::Tone;
using sh3::platform::ctr::ToneStatus;
static_assert(!std::is_copy_constructible_v<Tone> && !std::is_move_constructible_v<Tone>);

void check_pcm() {
    const auto *pcm = static_cast<const std::int16_t *>(audio_test::sdk().memory);
    CHECK(pcm && pcm[0] == 0);
    std::int64_t sum = 0, squares = 0;
    unsigned rising = 0;
    int minimum = 0, maximum = 0;
    for (std::size_t i = 0; i < 22050; ++i) {
        const int sample = pcm[i];
        CHECK(sample >= -2048 && sample <= 2048);
        minimum = std::min(minimum, sample);
        maximum = std::max(maximum, sample);
        sum += sample;
        squares += sample * sample;
        if (i > 0 && pcm[i - 1] <= 0 && sample > 0) {
            ++rising;
        }
    }
    // Frequency, DC, energy and loop boundary checks independent of sin implementation.
    CHECK(rising == 440 && minimum <= -2047 && maximum >= 2047);
    CHECK(std::abs(sum) < 22050);
    const double rms = std::sqrt(static_cast<double>(squares) / 22050.0);
    CHECK(rms > 1446 && rms < 1449);
    CHECK(std::abs(static_cast<int>(pcm[22049]) - pcm[0]) < 300);
}
} // namespace

int main(int argc, char **argv) {
    CHECK(argc == 2);
    const std::string scenario = argv[1];
    auto &s = audio_test::sdk();
    ToneStatus expected = ToneStatus::ready;
    if (scenario == "init_failure") {
        s.init_result = -1234;
        expected = ToneStatus::ndsp_init_failed;
    } else if (scenario == "alloc_failure") {
        s.allocation_fails = true;
        expected = ToneStatus::pcm_alloc_failed;
    } else if (scenario == "flush_failure") {
        s.flush_result = -5678;
        expected = ToneStatus::cache_flush_failed;
    } else {
        CHECK(scenario == "normal" || scenario == "initial_mute");
    }
    const bool muted = scenario == "initial_mute";
    {
        Tone tone(muted);
        auto snapshot = tone.snapshot();
        CHECK(snapshot.status == expected);
        if (expected != ToneStatus::ready) {
            CHECK(!s.initialized && !s.memory && !s.queued);
            CHECK(snapshot.sdk_result == (scenario == "init_failure" ? -1234 : s.flush_result));
            CHECK(snapshot.frames == 0 && snapshot.dropped_frames == 0 &&
                  snapshot.sample_position == 0 && snapshot.paused);
            tone.pause(false);
            tone.pause(true);
            CHECK(s.queries == 0 && s.pauses.empty());
        } else {
            CHECK(snapshot.sdk_result == 0 && snapshot.paused == muted);
            CHECK(s.initialized && s.queued && s.bytes == 44100);
            CHECK(s.pauses == std::vector<bool>{muted});
            check_pcm();
            CHECK(s.events ==
                  (std::vector<std::string>{"init", "alloc", "flush", "output", "reset", "interp",
                                            "rate", "format", "mix", "pause", "add"}));
            tone.pause(muted);
            CHECK(s.pauses.size() == 1);
            tone.pause(!muted);
            tone.pause(!muted);
            tone.pause(muted);
            CHECK(s.pauses == (std::vector<bool>{muted, !muted, muted}));
            s.frames = std::numeric_limits<u32>::max();
            s.dropped = 7;
            s.position = 22049;
            snapshot = tone.snapshot();
            CHECK(snapshot.frames == s.frames && snapshot.dropped_frames == 7 &&
                  snapshot.sample_position == 22049 && snapshot.paused == muted);
            s.frames = s.position = 0; // SDK reset/wrap is reported directly, not inferred time.
            snapshot = tone.snapshot();
            CHECK(snapshot.frames == 0 && snapshot.sample_position == 0);
            CHECK(s.queries == 9);
        }
    }
    CHECK(!s.initialized && !s.queued && !s.memory && !s.wave);
    if (scenario == "init_failure") {
        CHECK(s.events == std::vector<std::string>{"init"});
    } else if (scenario == "alloc_failure") {
        CHECK(s.events == (std::vector<std::string>{"init", "alloc", "exit"}));
    } else if (scenario == "flush_failure") {
        CHECK(s.events == (std::vector<std::string>{"init", "alloc", "flush", "exit", "free"}));
    } else {
        CHECK((std::vector<std::string>{s.events.end() - 3, s.events.end()} ==
               std::vector<std::string>{"clear", "exit", "free"}));
    }
}
