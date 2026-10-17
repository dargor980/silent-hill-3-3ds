#pragma once

#include <3ds.h>
#include <string>
#include <vector>

namespace audio_test {
struct Sdk {
    Result init_result{0}, flush_result{0};
    bool allocation_fails{false};
    bool initialized{false}, configured{false}, flushed{false}, queued{false};
    bool paused{false}, pause_set{false};
    void *memory{nullptr};
    std::size_t bytes{0};
    ndspWaveBuf *wave{nullptr};
    u32 frames{0}, dropped{0}, position{0};
    unsigned queries{0};
    std::vector<bool> pauses;
    std::vector<std::string> events;
};
Sdk &sdk();
} // namespace audio_test
