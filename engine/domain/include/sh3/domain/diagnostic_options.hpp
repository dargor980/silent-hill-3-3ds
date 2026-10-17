#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace sh3::domain {
struct DiagnosticOptions {
    bool tone_enabled{true};
};
struct OptionsRecord {
    DiagnosticOptions options{};
    std::uint32_t generation{0};
};
using OptionsBytes = std::array<std::uint8_t, 16>;
[[nodiscard]] OptionsBytes encode_options(OptionsRecord record) noexcept;
// On failure the output is unchanged. This codec has no filesystem dependency.
[[nodiscard]] bool decode_options(const std::uint8_t *bytes, std::size_t size,
                                  OptionsRecord &output) noexcept;
} // namespace sh3::domain
