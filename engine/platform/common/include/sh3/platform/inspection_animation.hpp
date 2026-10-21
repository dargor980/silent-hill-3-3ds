#pragma once
#include "sh3/domain/animation_pose.hpp"
#include "sh3/platform/stdio_files.hpp"
namespace sh3::platform {
[[nodiscard]] ports::FileError read_inspection_animation(const char *path,
                                                         domain::InspectionClip &destination,
                                                         StdioApi api = system_stdio) noexcept;
} // namespace sh3::platform
