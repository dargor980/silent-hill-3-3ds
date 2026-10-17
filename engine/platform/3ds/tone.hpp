#pragma once

#include <3ds.h>
#include <cstdint>

namespace sh3::platform::ctr {
enum class ToneStatus { ready, ndsp_init_failed, pcm_alloc_failed, cache_flush_failed };

struct ToneSnapshot {
    ToneStatus status;
    Result sdk_result;
    u32 frames{0};
    u32 dropped_frames{0};
    u32 sample_position{0};
    bool paused{true};
};

[[nodiscard]] constexpr const char *tone_status_name(ToneStatus status) noexcept {
    switch (status) {
    case ToneStatus::ready:
        return "READY";
    case ToneStatus::ndsp_init_failed:
        return "NDSP_INIT_FAILED";
    case ToneStatus::pcm_alloc_failed:
        return "PCM_ALLOC_FAILED";
    case ToneStatus::cache_flush_failed:
        return "CACHE_FLUSH_FAILED";
    }
    return "UNKNOWN";
}

[[nodiscard]] constexpr const char *tone_stage_name(ToneStatus status) noexcept {
    switch (status) {
    case ToneStatus::ready:
        return "TONE";
    case ToneStatus::ndsp_init_failed:
        return "NDSP_INIT";
    case ToneStatus::pcm_alloc_failed:
        return "PCM_ALLOC";
    case ToneStatus::cache_flush_failed:
        return "CACHE_FLUSH";
    }
    return "UNKNOWN";
}

// Sole NDSP owner in this diagnostic; not shared with a mixer or another Tone.
class Tone final {
  public:
    explicit Tone(bool paused = false) noexcept;
    ~Tone();
    Tone(const Tone &) = delete;
    Tone &operator=(const Tone &) = delete;
    [[nodiscard]] ToneSnapshot snapshot() const noexcept;
    void pause(bool paused) noexcept;

  private:
    void release() noexcept;
    ToneStatus status_{ToneStatus::ndsp_init_failed};
    Result result_{0};
    bool initialized_{false};
    bool queued_{false};
    bool paused_{true};
    std::int16_t *samples_{nullptr};
    ndspWaveBuf wave_{};
};
} // namespace sh3::platform::ctr
