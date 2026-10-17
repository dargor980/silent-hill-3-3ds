#include "sh3/platform/timing_window.hpp"
#include <algorithm>
#include <limits>

namespace sh3::platform {
TickDuration elapsed_ticks(std::uint64_t start, std::uint64_t end) noexcept {
    if (end < start) {
        return std::nullopt;
    }
    return end - start;
}

void TimingWindow::record(const FrameTimings &sample) noexcept {
    if (!sample.accepted && rejected_ != std::numeric_limits<std::uint64_t>::max()) {
        ++rejected_;
    }
    if (warmup_ != 0) {
        --warmup_;
        return;
    }
    samples_[next_] = sample;
    next_ = (next_ + 1) % capacity;
    if (size_ < capacity) {
        ++size_;
    }
}

void TimingWindow::reset() noexcept {
    size_ = next_ = 0;
    warmup_ = warmup_attempts;
    rejected_ = 0;
}

const FrameTimings *TimingWindow::at(std::size_t index) const noexcept {
    if (index >= size_) {
        return nullptr;
    }
    const auto oldest = size_ == capacity ? next_ : 0;
    return &samples_[(oldest + index) % capacity];
}

TimingSummary TimingWindow::summarize(TickDuration FrameTimings::*field) const noexcept {
    TimingSummary result;
    std::array<std::uint64_t, capacity> sorted{};
    for (std::size_t i = 0; i < size_; ++i) {
        const auto &duration = samples_[i].*field;
        if (duration) {
            sorted[result.valid++] = *duration;
        } else {
            ++result.invalid;
        }
    }
    if (result.valid != 0) {
        std::sort(sorted.begin(), sorted.begin() + result.valid);
        result.p95 = sorted[(95 * result.valid + 99) / 100 - 1];
        result.maximum = sorted[result.valid - 1];
    }
    return result;
}
} // namespace sh3::platform
