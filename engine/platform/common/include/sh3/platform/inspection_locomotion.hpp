#pragma once
#include "sh3/domain/inspection_locomotion.hpp"
#include "sh3/platform/stdio_files.hpp"

namespace sh3::platform {
struct LocomotionLoadResult {
    ports::FileError error{ports::FileError::ok};
    const char *field{"none"}; // Static diagnostic, no ownership/allocation.
    std::uint32_t item{};      // Texture ordinal for bundle failures.
};
// SRI2 structure only. Success does not authenticate proprietary source hashes.
// All failures, including fclose, preserve every byte of out. Single owner thread.
[[nodiscard]] LocomotionLoadResult read_locomotion_rig(const char *path,
                                                       domain::InspectionLocomotion &out,
                                                       StdioApi = system_stdio) noexcept;
// Checks heather.sri and every numbered RGBA file's size/CRC before publication.
// Texture pixels are checked through one 64 KiB buffer, not retained or uploaded.
[[nodiscard]] LocomotionLoadResult read_locomotion_bundle(const char *directory,
                                                          domain::InspectionLocomotion &out,
                                                          StdioApi = system_stdio) noexcept;
} // namespace sh3::platform
