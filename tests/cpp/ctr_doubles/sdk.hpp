#pragma once

#include "tone.hpp"
#include <citro2d.h>
#include <string>
#include <vector>

namespace ctr_test {
enum class Failure { none, citro3d, citro2d, target };
struct Rectangle {
    float x, y, z, width, height;
    u32 color;
};
struct Sdk {
    Failure failure{Failure::none};
    std::vector<u32> keys{KEY_START};
    std::vector<u32> held;
    bool exit_hook{false};
    bool frame_allowed{true};
    Result audio_result{0};
    sh3::platform::ctr::ToneStatus audio_status{sh3::platform::ctr::ToneStatus::ready};
    std::vector<APT_HookType> hooks;
    std::vector<std::vector<APT_HookType>> hook_batches;
    bool initial_tone_paused{false};
    bool gfx{false}, c3d{false}, c2d{false}, target{false}, tone{false}, frame{false};
    bool pending_gpu{false};
    aptHookCookie *cookie{nullptr};
    aptHookFn callback{nullptr};
    void *context{nullptr};
    unsigned clears{0};
    unsigned reset_metrics_loop{0};
    unsigned scanned_loop{0};
    unsigned apt_close_loop{0};
    std::vector<unsigned> input_loops;
    std::vector<unsigned> frame_loops;
    unsigned loops{0}, scans{0}, reads{0}, begins{0}, ends{0}, flushes{0}, swaps{0}, waits{0};
    std::vector<std::string> resources;
    std::vector<Rectangle> rectangles;
    std::vector<bool> pauses;
};
Sdk &sdk();
} // namespace ctr_test
