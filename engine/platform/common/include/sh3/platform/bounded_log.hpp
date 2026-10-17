#pragma once

#include "sh3/ports/diagnostics.hpp"
#include <array>
#include <cstddef>
#include <optional>

namespace sh3::platform {
class BoundedLog final : public ports::ILifecycleLog {
  public:
    static constexpr std::size_t capacity = 32;
    void record(domain::SessionState state) noexcept override;
    [[nodiscard]] std::size_t size() const noexcept;
    // Chronological index, oldest retained entry first. Out of range returns no value.
    [[nodiscard]] std::optional<domain::SessionState> at(std::size_t index) const noexcept;

  private:
    std::array<domain::SessionState, capacity> entries_{};
    std::size_t next_{0};
    std::size_t size_{0};
};
} // namespace sh3::platform
