#pragma once
#include "sh3_observer/artifact_manifest.hpp"

namespace sh3::observer {
inline constexpr std::size_t layout_command_limit = 1024 * 1024;
inline constexpr std::size_t layout_segment_capacity = 64;
struct ImageSegment {
  std::array<char, 16> name{};
  std::uint64_t address{}, size{}, file_offset{}, file_size{};
  std::uint32_t maximum_protection{}, initial_protection{}, sections{}, flags{};
};
struct ImageLayout {
  std::uint32_t cpu{}, subtype{}, type{}, flags{}, commands{}, command_bytes{};
  std::array<ImageSegment, layout_segment_capacity> segments{};
  std::size_t count{};
  std::uint64_t header_address{};
};
enum class LayoutFailure { none, invalid, unsupported, unavailable, changed };
// Structural metadata only. No assertion of page identity or relocation correctness.
LayoutFailure parse_image_layout(const void*, std::size_t, ImageLayout&) noexcept;
LayoutFailure read_image_layout(ByteSource&, ImageLayout&) noexcept;
} // namespace sh3::observer
