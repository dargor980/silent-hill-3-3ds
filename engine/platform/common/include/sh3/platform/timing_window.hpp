#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace sh3::platform {
using TickDuration = std::optional<std::uint64_t>;
[[nodiscard]] TickDuration elapsed_ticks(std::uint64_t start, std::uint64_t end) noexcept;

struct FrameTimings {
    TickDuration begin_wait;
    TickDuration draw_submit;
    TickDuration audio_poll;
    bool accepted{false};
};
struct TimingSummary {
    TickDuration p95;
    TickDuration maximum;
    std::size_t valid{0};
    std::size_t invalid{0};
};

class TimingWindow final {
  public:
    static constexpr std::size_t capacity = 120;
    static constexpr std::size_t warmup_attempts = 60;
    void record(const FrameTimings &sample) noexcept;
    void reset() noexcept;
    [[nodiscard]] std::size_t size() const noexcept { return size_; }
    [[nodiscard]] std::size_t warmup_remaining() const noexcept { return warmup_; }
    [[nodiscard]] std::uint64_t rejected() const noexcept { return rejected_; }
    [[nodiscard]] const FrameTimings *at(std::size_t index) const noexcept;
    [[nodiscard]] TimingSummary summarize(TickDuration FrameTimings::*field) const noexcept;

  private:
    std::array<FrameTimings, capacity> samples_{};
    std::size_t size_{0};
    std::size_t next_{0};
    std::size_t warmup_{warmup_attempts};
    std::uint64_t rejected_{0};
};
static_assert(sizeof(TimingWindow) <= 8192, "Keep diagnostic storage bounded on 3DS");
} // namespace sh3::platform
