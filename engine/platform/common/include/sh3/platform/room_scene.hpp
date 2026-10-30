#pragma once
#include "sh3/domain/room_scene.hpp"
#include "sh3/platform/stdio_files.hpp"

namespace sh3::platform {
// SRM1/SRM2 contain local MAP geometry. CRC/structure validation does not authenticate source
// hashes. One common transform is applied while loading. Failure (including close) preserves out.
[[nodiscard]] ports::FileError read_room_map(const char *, domain::RoomMap &,
                                             StdioApi = system_stdio) noexcept;
// Fixed 512x512 RGBA8, normalized alpha; no vertical flip. Distinct buffers.
[[nodiscard]] bool upload_room_texture(const std::uint8_t *, std::size_t, std::uint8_t *,
                                       std::size_t) noexcept;
} // namespace sh3::platform
