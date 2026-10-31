#pragma once
#include <cstdint>
#include <optional>

namespace sh3::platform {
// Successful submissions per elapsed second, including busy attempts and HUD cost.
// This measures application cadence, not display scanout or animation sample rate.
class FrameCadence final {
  public:
    explicit FrameCadence(std::uint64_t frequency) noexcept : frequency_(frequency) {}
    void reset() noexcept {
        anchored_ = false;
        frames_ = 0;
        measured_ = false;
    }
    void record(std::uint64_t now, bool presented) noexcept {
        if (!frequency_)
            return;
        if (!anchored_ || now < previous_) {
            reset();
            anchored_ = true;
            anchor_ = previous_ = now;
            return;
        }
        previous_ = now;
        frames_ += presented ? 1 : 0;
        const auto elapsed = now - anchor_;
        if (elapsed >= frequency_) {
            fps_ = double(frames_) * double(frequency_) / double(elapsed);
            measured_ = true;
            anchor_ = now;
            frames_ = 0;
        }
    }
    [[nodiscard]] std::optional<double> fps() const noexcept {
        return measured_ ? std::optional<double>{fps_} : std::nullopt;
    }

  private:
    const std::uint64_t frequency_;
    std::uint64_t anchor_{}, previous_{}, frames_{};
    bool anchored_{}, measured_{};
    double fps_{};
};
} // namespace sh3::platform
