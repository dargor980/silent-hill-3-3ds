#pragma once
#include <array>
#include <cstdint>

namespace sh3::domain {
enum class WorkPhase : unsigned {
    movement_contacts,
    animation_pose,
    validation,
    palette,
    deform_cpu,
    sort_expand,
    palette_rows,
    ownership_wait,
    copy_flush,
    submit,
    count
};
struct WorkSample {
    std::uint64_t frame{}, begin_tick{}, end_tick{};
    std::array<std::uint64_t, unsigned(WorkPhase::count)> ticks{};
    std::array<unsigned, unsigned(WorkPhase::count)> calls{};
    unsigned steps{}, result{};
    // Completed previous submission, acquired after FrameBegin ownership wait.
    std::uint64_t gpu_frame{};
    double gpu_ms{};
    bool gpu_valid{};
};
// One owner; synchronous sink may copy/aggregate but must not reenter or allocate
// on the rendering thread. GPU samples carry their own originating frame ID.
struct WorkTrace {
    using Clock = std::uint64_t (*)(void *) noexcept;
    using Sink = void (*)(void *, const WorkSample &) noexcept;
    Clock clock{};
    Sink sink{};
    void *context{};
    WorkSample sample{};
    std::uint64_t delivered{};
    void begin() noexcept {
        sample = {};
        sample.frame = delivered;
        if (clock)
            sample.begin_tick = clock(context);
    }
    void end(unsigned steps, unsigned result) noexcept {
        sample.steps = steps;
        sample.result = result;
        if (clock)
            sample.end_tick = clock(context);
        if (sink)
            sink(context, sample);
        ++delivered;
    }
};
class WorkInterval final {
  public:
    WorkInterval(WorkTrace *trace, WorkPhase phase) noexcept : trace_(trace), phase_(phase) {
        if (trace_ && trace_->clock)
            start_ = trace_->clock(trace_->context);
    }
    ~WorkInterval() { finish(); }
    void next(WorkPhase phase) noexcept {
        finish();
        phase_ = phase;
    }
    WorkInterval(const WorkInterval &) = delete;
    WorkInterval &operator=(const WorkInterval &) = delete;

  private:
    void finish() noexcept {
        if (!trace_ || !trace_->clock)
            return;
        const auto now = trace_->clock(trace_->context);
        trace_->sample.ticks[unsigned(phase_)] += now - start_;
        ++trace_->sample.calls[unsigned(phase_)];
        start_ = now; // Shared boundary; adjacent intervals never overlap.
    }
    WorkTrace *trace_;
    WorkPhase phase_;
    std::uint64_t start_{};
};
} // namespace sh3::domain
