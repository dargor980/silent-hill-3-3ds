#pragma once
#include "sh3/domain/work_trace.hpp"
#include "sh3/ports/render_scene.hpp"
#include <algorithm>
#include <array>
#include <cmath>

namespace sh3::platform {
// Heap-owned, bounded diagnostic window. No allocation, I/O or sorting in the sink.
class SkinningCapture {
  public:
    static constexpr unsigned warmup = 32, capacity = 256;
    struct Summary {
        double median{}, p95{}, maximum{};
        unsigned count{};
    };
    void start() noexcept {
        count_ = seen_ = 0;
        active_ = true;
        complete_ = false;
    }
    void cancel() noexcept { active_ = complete_ = false; }
    void record(const domain::WorkSample &s) noexcept {
        if (!active_)
            return;
        if (s.gpu_valid && std::isfinite(s.gpu_ms) && s.gpu_ms >= 0) {
            for (unsigned i = 0; i < count_; ++i) {
                if (samples_[i].frame == s.gpu_frame &&
                    samples_[i].result == unsigned(ports::RenderResult::presented)) {
                    gpu_[i] = s.gpu_ms;
                    gpu_valid_[i] = true;
                }
            }
        }
        if (count_ < capacity && seen_++ >= warmup) {
            samples_[count_] = s;
            gpu_valid_[count_] = false;
            cadence_[count_] = count_ && s.begin_tick >= samples_[count_ - 1].begin_tick
                                   ? s.begin_tick - samples_[count_ - 1].begin_tick
                                   : 0;
            ++count_;
        }
        if (count_ == capacity &&
            (samples_.back().result != unsigned(ports::RenderResult::presented) ||
             gpu_valid_.back())) {
            active_ = false;
            complete_ = true;
        }
    }
    bool active() const noexcept { return active_; }
    bool complete() const noexcept { return complete_; }
    unsigned count() const noexcept { return count_; }
    unsigned failed() const noexcept {
        unsigned result = 0;
        for (unsigned i = 0; i < count_; ++i)
            result += samples_[i].result != unsigned(ports::RenderResult::presented);
        return result;
    }
    std::uint64_t first() const noexcept { return count_ ? samples_[0].frame : 0; }
    std::uint64_t last() const noexcept { return count_ ? samples_[count_ - 1].frame : 0; }
    // 0..9 disjoint CPU phases; 10 total controller call; 11 cadence; 12 GPU queue.
    Summary summarize(unsigned metric, std::uint64_t frequency) noexcept {
        Summary result;
        if (!complete_ || metric > 12 || !frequency)
            return result;
        for (unsigned i = 0; i < count_; ++i) {
            const auto &s = samples_[i];
            if (metric == 12 && !gpu_valid_[i])
                continue;
            if (metric == 11 && !i)
                continue;
            const double ms = metric == 12 ? gpu_[i]
                                           : double(metric < 10    ? s.ticks[metric]
                                                    : metric == 10 ? s.end_tick - s.begin_tick
                                                                   : cadence_[i]) *
                                                 1000 / frequency;
            scratch_[result.count++] = ms;
        }
        if (!result.count)
            return result;
        // Bounded insertion sort outside capture; no recursive library stack.
        for (unsigned i = 1; i < result.count; ++i) {
            const double value = scratch_[i];
            unsigned j = i;
            while (j && scratch_[j - 1] > value) {
                scratch_[j] = scratch_[j - 1];
                --j;
            }
            scratch_[j] = value;
        }
        const auto n = result.count;
        result.median = (scratch_[(n - 1) / 2] + scratch_[n / 2]) / 2;
        result.p95 = scratch_[(95 * n + 99) / 100 - 1];
        result.maximum = scratch_[n - 1];
        return result;
    }

  private:
    std::array<domain::WorkSample, capacity> samples_{};
    std::array<double, capacity> gpu_{}, scratch_{};
    std::array<std::uint64_t, capacity> cadence_{};
    std::array<bool, capacity> gpu_valid_{};
    unsigned count_{}, seen_{};
    bool active_{}, complete_{};
};
static_assert(sizeof(SkinningCapture) < 64 * 1024);
} // namespace sh3::platform
